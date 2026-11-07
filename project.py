"""STAT 386: senior data careers across employers.

Default: analyze the saved jobs.csv without contacting any websites.
--rebuild: recreate jobs.csv from the private saved raw snapshot.
--collect: resume a public salary search, capped at five roles/company.
--collect --fresh: begin a separate new search.

The code follows the class sequence: collect -> clean -> validate -> summarize -> plot.
"""

import argparse
from datetime import datetime, timezone
from html import unescape
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import time

import pandas as pd
import requests
import matplotlib

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".project-cache/matplotlib"))
matplotlib.use("Agg")  # Save figures to files without opening a separate window.
import matplotlib.pyplot as plt


# 1. Settings and the employer list
# Directory identifiers are input data. All boards use the same public API.
# LastRound AI supplies candidate boards; open-ats-feed guides their visit order.
# Both directories are incomplete, so this is a purposive sample.
MAX_ROLES = 5
SEED = 386
REQUEST_DELAY = 3  # Seconds; the course recommends one request every few seconds.
RAW_PATH = ROOT / ".project-cache/raw_jobs.json"
DATA_PATH = ROOT / "jobs.csv"
OUTPUT = ROOT / "output"

COMPANY_ALIASES = {
    "artefactlinkedin": {"company": "Artefact", "company_key": "artefact"}
}
# Its board says "LinkedIn Job Wrapping", but the introduction identifies Artefact:
# https://job-boards.greenhouse.io/artefactlinkedin

EXCLUDED_BOARDS = {
    "xai": "Its current SpaceXSI descriptions identify SpaceX; the spacex board already uses that employer's allowance.",
    "wpp": "WPP Media identifies itself as WPP's operating unit; wppmedia already uses the group's allowance.",
    "vmlenterprisesolutions": "Its published employer is VML/WPP Enterprise Solutions; wppmedia already uses the WPP allowance.",
    "fanaticscollectibles": "Its introduction names Fanatics Commerce and Collectibles as the same Fanatics platform; retain only fanaticscommerce."
}

# Candidate identifiers are loaded from a larger pinned directory and cached locally.
DIRECTORY_URL = "https://raw.githubusercontent.com/fyrosofttech/lastroundai-hiring-data/2816bfadd65b7bbec23701dd036bcc7496c729db/ats-directory/lastroundai-ats-company-directory-2026-08.csv"
ACTIVITY_URL = "https://raw.githubusercontent.com/veresk06/open-ats-feed/main/actor/data/companies.json"
TARGET_ROLES = 300
MIN_COMPANIES = 101
INFER_ANNUAL_MIN = 25000  # Exploratory plausibility limits
INFER_ANNUAL_MAX = 1000000

SKILL_PATTERNS = {
    "python": r"\bpython\b", "sql": r"\bsql\b",
    "pytorch": r"\bpytorch\b", "tensorflow": r"\btensor\s?flow\b",
    "aws": r"\baws\b|\bamazon web services\b", "azure": r"\bazure\b",
    "gcp": r"\bgcp\b|\bgoogle cloud\b", "spark": r"\b(?:apache\s+)?spark\b|\bpyspark\b",
    "excel": r"\bmicrosoft excel\b|\badvanced excel\b|\bexcel\s+(?:skills|spreadsheets)\b",
    "tableau": r"\btableau\b", "power_bi": r"\bpower\s?bi\b",
}

# 2. Small text helpers: clean HTML, identify roles, and match skill names.

def plain_text(value):
    # Greenhouse sometimes encodes tags as &lt;p&gt;, so I decoded it before stripping.
    text = unescape(unescape(str(value or "")))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()

def skill_mentions(text):
    flags = {}
    for name, pattern in SKILL_PATTERNS.items():
        flags["mentions_" + name] = int(bool(re.search(pattern, text, re.I)))
    flags["mentions_r"] = int(bool(
        re.search(r"(?<![\w&$-])(?<!& )R(?![\w$]|-\w|\s*&\s*\w)", text)
        or re.search(r"\br\s+(?:programming|language)\b", text, re.I)
    ))
    flags["mentions_cloud"] = int(bool(
        flags["mentions_aws"] or flags["mentions_azure"] or flags["mentions_gcp"]
        or re.search(r"\bcloud\b", text, re.I)
    ))
    return flags

def classify_seniority(title):
    if re.search(r"\b(?:intern\w*|junior|jr\.?|apprentice\w*|graduate)\b|entry.level|new.grad|early.career", title, re.I):
        return None
    if re.search(r"\b(?:chief|vice president|VP|head|director)\b", title, re.I):
        return "Leadership"
    if re.search(r"\bmanager\b", title, re.I):
        return "Management"
    if re.search(r"\b(?:staff|principal|distinguished|lead)\b", title, re.I):
        return "Staff / principal / lead"
    if re.search(r"\bsenior\b|\bsr\b", title, re.I):
        return "Senior"
    return None

def classify_title(title, description=""):
    # Commercial AI roles are outside the technical/analytical scope of this study.
    if re.search(r"business ownership|freelance.*(?:trainer|training)", title, re.I):
        return None
    if re.search(r"\b(?:product\s+(?:manager|management|strategy)|project manager|business manager|solutions manager|sales engineer)\b", title, re.I):
        return None
    ml = re.search(r"\b(?:machine[ -]learning|deep learning|ML|AI|LLM|NLP|MLOps|computer vision|natural language)\b", title, re.I)
    technical = re.search(r"\b(?:engineer\w*|scientist\w*|research\w*|architect\w*)\b", title, re.I)
    management = re.search(r"\b(?:manager|director|head|lead)\b", title, re.I)
    commercial = re.search(
        r"\b(?:sales|partners?|partnerships?|alliances?|client|customer|success|marketing|"
        r"accounts?|GTM|capacity|strategy|sourcing|procurement|finance|enablement|"
        r"organizational|program|process|events|community|engagement|field|design)\b|business development",
        title, re.I)
    technical = technical or (management and not commercial)
    if ml and technical:
        return "Machine learning / AI"
    if re.search(r"\bdata\s+scien(?:tist|ce)\b", title, re.I):
        return "Data science"
    if re.search(r"\b(?:analytics engineer\w*|business intelligence|BI engineer\w*|BI developer\w*)\b", title, re.I):
        return "Analytics engineering / BI"
    if re.search(r"\b(?:data|ETL)\s+(?:engineer\w*|architect\w*)\b|\bdata (?:platform|infrastructure)\b", title, re.I):
        return "Data engineering"
    if re.search(r"\b(?:data|business|product|marketing|risk|fraud|growth|customer|operations|insights)\s+(?:systems?\s+)?analy(?:st|tics)\b", title, re.I):
        return "Data / business analytics"
    if re.search(r"\b(?:quantitative|decision)\s+(?:research\w*|analy\w*|scien\w*)\b", title, re.I):
        return "Applied / quantitative science"
    if re.search(r"\b(?:applied|research) scientist\b", title, re.I) and re.search(
            r"\bmachine learning\b|\bdeep learning\b|\bdata science\b", description, re.I):
        return "Applied / quantitative science"
    return None

# 3. Salary parsing. Preserve reported fields and label any annual-pay inference.

def number(value):
    try:
        result = float(value)
        return result if 0 < result < float("inf") else None
    except (TypeError, ValueError):
        return None

def parse_amount(value, scale=""):
    """Read written amounts, including an explicit k/m suffix and common separators."""
    value = str(value).strip()
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", value):
        value = value.replace(",", "").replace(".", "")
    else:
        value = value.replace(",", ".")
    amount = number(value)
    if amount is not None:
        amount *= {"k": 1000, "m": 1000000}.get(scale.lower(), 1)
    return amount


def pay_period(text):
    """Unknown is kept unknown; no hourly-to-annual conversion is made."""
    patterns = {
        "hour": r"\bhourly\b|per hour|an hour|/\s*(?:hr|hour)\b",
        "month": r"\bmonthly\b|per month|/\s*month\b",
        "week": r"\bweekly\b|per week|/\s*week\b",
        "year": r"\bannual(?:ized)?\s+(?:(?:base|cash|gross|total)\s+)?(?:salary|pay|compensation)"
                r"|\bannually\b|per year|per annum|\byearly\b|/\s*(?:yr|year)\b",
    }
    found = []
    for period, pattern in patterns.items():
        if re.search(pattern, text, re.I):
            found.append(period)
    return found[0] if len(found) == 1 else "unspecified"


def pay_kind(text):
    if re.search(r"\bOTE\b|on.target earnings|total compensation", text, re.I):
        return "total_compensation"
    if re.search(r"\bbase\b", text, re.I):
        return "base_pay"
    return "pay"


def salary_ranges(text):
    """Find pay ranges in text; retain stated currency and period separately."""
    symbols = r"USD|CAD|AUD|SGD|GBP|EUR|INR|PLN|BRL|JPY|CHF|SEK|NOK|DKK|MXN|NZD|HKD|TWD|US\$|CA\$|C\$|AU\$|A\$|R\$|\$|£|€|₹"
    written_period = r"(?:/\s*(?:year|yr|hour|hr|month)|\s+per\s+(?:year|hour|month))"
    geography = r"(?:\s+in our lowest geographic market)?"
    pattern = (rf"(?P<symbol>{symbols})\s*(?P<low>\d[\d,.]*)(?P<low_scale>[kKmM]?)"
               rf"\s*(?:{written_period})?{geography}\s*(?:[-–—]|to)\s*(?:(?P<second>{symbols})\s*)?"
               r"(?P<high>\d[\d,.]*)(?P<high_scale>[kKmM]?)(?!\d)")
    symbol_currency = {"US$": "USD", "CA$": "CAD", "C$": "CAD", "AU$": "AUD", "A$": "AUD",
                       "R$": "BRL", "£": "GBP", "€": "EUR", "₹": "INR", "$": "unspecified_dollar"}
    codes = r"USD|CAD|AUD|SGD|GBP|EUR|INR|PLN|BRL|JPY|CHF|SEK|NOK|DKK|MXN|NZD|HKD|TWD"
    ranges = []
    for match in re.finditer(pattern, text, re.I):
        before = text[max(0, match.start() - 220):match.start()]
        after = text[match.end():match.end() + 100]
        context = before + match.group() + after
        if not re.search(r"salary|base pay|pay range|pay rate|hourly rate|compensation|annual pay|monthly pay|wage", context, re.I):
            continue
        if re.search(r"funding|revenue|valuation|sign.on bonus|equity grant", before[-70:], re.I) and not re.search(r"salary|base pay|pay range", before[-70:], re.I):
            continue
        low_scale = match.group("low_scale")
        high_scale = match.group("high_scale")
        if not low_scale and high_scale and (parse_amount(match.group("low")) or 0) < 1000:
            low_scale = high_scale
        low = parse_amount(match.group("low"), low_scale)
        high = parse_amount(match.group("high"), high_scale)
        if low is None or high is None or high < low:
            continue
        symbol = match.group("symbol").upper()
        currency = symbol_currency.get(symbol, symbol)
        second = match.group("second")
        if second:
            second_currency = symbol_currency.get(second.upper(), second.upper())
            if second_currency != currency:
                continue  # Bounds in different currencies do not form one pay range.
        suffix = re.match(rf"\s*({codes})\b", after, re.I)
        prefix = re.search(rf"\b({codes})\s*$", before, re.I)
        if suffix:
            currency = suffix.group(1).upper()
        elif prefix:
            currency = prefix.group(1).upper()
        period = pay_period(context)
        if period == "year" and high < 1000:
            continue
        ranges.append({"min": low, "max": high, "currency": currency, "period": period,
                       "kind": pay_kind(context), "method": "description_text", "label": "Advertised pay range"})
    return ranges


def posted_pay(job, description):
    """Prefer employer-configured Greenhouse pay fields; fall back to labeled text."""
    text_ranges = salary_ranges(description)
    structured = []
    for item in job.get("pay_input_ranges") or []:
        low_cents = number(item.get("min_cents"))
        high_cents = number(item.get("max_cents"))
        low = low_cents / 100 if low_cents is not None else None
        high = high_cents / 100 if high_cents is not None else None
        if low is None and high is None:
            continue
        if low is not None and high is not None and high < low:
            continue
        label = plain_text(item.get("title"))
        explanation = plain_text(item.get("blurb"))
        currency = str(item.get("currency_type") or "unspecified").upper()
        period = pay_period(label + " " + explanation)
        explicit_period = str(item.get("period") or item.get("frequency") or "").lower()
        period_names = {"annual": "year", "annually": "year", "year": "year", "yearly": "year",
                        "hour": "hour", "hourly": "hour", "monthly": "month", "month": "month"}
        period = period_names.get(explicit_period, period)
        # Use text timing only when its exact range matches this structured range
        for text_range in text_ranges:
            if text_range["min"] == low and text_range["max"] == high:
                if period == "unspecified":
                    period = text_range["period"]
        if period == "year" and max(low or 0, high or 0) < 1000:
            continue
        structured.append({"min": low, "max": high, "currency": currency, "period": period,
                           "kind": pay_kind(label + " " + explanation), "method": "greenhouse_pay_field", "label": label})
    # This makes sure it does not count the same displayed range a second time through text extraction
    for item in text_ranges:
        duplicate = False
        for known in structured:
            if item["min"] == known["min"] and item["max"] == known["max"] and item["currency"] in [known["currency"], "unspecified_dollar"]:
                duplicate = True
                break
        if not duplicate:
            structured.append(item)
    return structured


def is_us_location(location):
    """Recognize explicit US locations; avoid treating generic remote work as US."""
    if re.search(r"Canada|Toronto|Vancouver|Montreal|United Kingdom|\bUK\b|London|India|"
                 r"Singapore|Australia|Germany|France|Poland|Ireland|Netherlands|"
                 r"Brazil|Israel|Spain|Europe|EMEA|APAC|Worldwide|Global", location, re.I):
        return False
    if re.search(r"\bUnited States\b|\bUSA\b|\bUS\b|U\.S\.", location, re.I):
        return True
    abbreviations = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
                     "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX "
                     "UT VT VA WA WV WI WY DC").split()
    if re.search(r",\s*(?:" + "|".join(abbreviations) + r")\b", location):
        return True
    states = ("Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
              "Florida|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|"
              "Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|"
              "Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|"
              "North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|"
              "South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|"
              "Wisconsin|Wyoming|District of Columbia")
    return bool(re.search(r"\b(?:" + states + r")\b", location, re.I))


def annual_usd_ranges(ranges, location, description):
    """Prefer confirmed annual pay; otherwise use a clearly labeled inference."""
    complete = [item for item in ranges
                if item["currency"] == "USD" and item["kind"] != "total_compensation"
                and item["min"] is not None and item["max"] is not None
                and math.isfinite(item["min"]) and math.isfinite(item["max"])
                and 0 < item["min"] < item["max"]]
    confirmed = [item for item in complete if item["period"] == "year" and item["max"] >= 1000]
    if confirmed:
        return confirmed, "confirmed"
    # Magnitude alone is insufficient: USD and US geography must also be explicit.
    other_period = (r"\bhourly\b|\b(?:daily|weekly|monthly)\s+(?:base\s+)?"
                    r"(?:pay|salary|rate|wage|compensation)\b|per\s+(?:hour|day|week|month)\b"
                    r"|/\s*(?:hr|hour|day|week|mo|month)\b")
    if not is_us_location(location) or re.search(other_period, description, re.I):
        return [], "not_comparable"
    inferred = [item for item in complete if item["period"] == "unspecified"
                and INFER_ANNUAL_MIN <= item["min"] < item["max"] <= INFER_ANNUAL_MAX]
    return (inferred, "inferred") if inferred else ([], "not_comparable")


def select_salaried_sample(data):
    """Keep at least one role from every contributing company before filling to 300."""
    pool = data.loc[data["salary_posted"] == 1].copy()
    if len(pool) < TARGET_ROLES or pool["company_key"].nunique() < MIN_COMPANIES:
        raise ValueError("The collection has not reached 300 salaried roles across 101 companies.")
    shuffled = pool.sample(frac=1, random_state=SEED)
    first = shuffled.drop_duplicates("company_key")
    if len(first) > TARGET_ROLES:
        chosen = first.head(TARGET_ROLES)
    else:
        remaining = shuffled.loc[~shuffled["job_id"].isin(first["job_id"])]
        chosen = pd.concat([first, remaining.head(TARGET_ROLES - len(first))])
    return chosen.sort_values(["company", "job_group", "job_id"]).reset_index(drop=True)


# 4. Collect only selected role details, preserving raw responses for later cleaning.

def company_key(name):
    """Make small differences in employer labels share the same five-role allowance."""
    name = re.sub(r"^(?:careers at|careers|jobs at)\s+", "", name.strip(), flags=re.I)
    name = re.sub(r"\b(?:incorporated|inc|llc|ltd|limited|corporation|corp)\.?$", "", name, flags=re.I)
    key = re.sub(r"\W+", "", name.casefold())
    if re.search(r"\bwpp\b", name, re.I):
        return "wpp"
    # These groups publish regional or operating-unit boards under one brand.
    for brand in ["doordash", "fanatics", "spacex", "wpp"]:
        if key.startswith(brand):
            return brand
    return key


def choose_roles(jobs, limit):
    """Take a role from each available family before selecting more of the same kind."""
    shuffled = list(jobs)
    random.Random(SEED).shuffle(shuffled)
    groups = {}
    for job in shuffled:
        group = classify_title(plain_text(job.get("title")))
        if group is None:
            group = "Applied / quantitative science"
        if group not in groups:
            groups[group] = []
        groups[group].append(job)
    selected = []
    while len(selected) < limit and any(groups.values()):
        for group in sorted(groups):
            if groups[group] and len(selected) < limit:
                selected.append(groups[group].pop())
    return selected


def get_json(session, url):
    """A timeout limits waiting; the delay separately controls request frequency."""
    response = session.get(url, timeout=30)
    time.sleep(REQUEST_DELAY)
    if response.status_code == 404:
        return None
    if response.status_code == 429:
        raise RuntimeError("Rate limit reached. Stop collection and wait before trying again.")
    response.raise_for_status()  # Stop on access blocks or other failed responses
    return response.json()


def load_boards():
    """Use a full-alphabet directory; active-board counts guide request order only."""
    cache = ROOT / ".project-cache"
    cache.mkdir(exist_ok=True)
    directory = cache / "board-directory.csv"
    activity = cache / "board-activity-index.json"
    if not directory.exists():
        response = requests.get(DIRECTORY_URL, timeout=45)
        response.raise_for_status()
        directory.write_bytes(response.content)
    if not activity.exists():
        response = requests.get(ACTIVITY_URL, timeout=45)
        response.raise_for_status()
        activity.write_bytes(response.content)
    table = pd.read_csv(directory)
    boards = table.loc[table["ats_vendor"] == "greenhouse", "board_slug"].drop_duplicates().tolist()
    boards = [board for board in boards if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", board)]
    index = json.loads(activity.read_text(encoding="utf-8"))
    counts = dict(index["providers"]["greenhouse"]["live"])
    random.Random(SEED).shuffle(boards)
    boards.sort(key=lambda board: counts.get(board, 0), reverse=True)
    return boards


def collect_jobs(fresh=False):
    """Resume a capped search until 300 salaried roles represent at least 101 companies."""
    base = ROOT / ".project-cache/salary-search"
    base.mkdir(parents=True, exist_ok=True)
    pointer = base / "current-run.txt"
    if fresh or not pointer.exists():
        pointer.write_text(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), encoding="utf-8")
    folder = base / pointer.read_text(encoding="utf-8").strip()
    folder.mkdir(exist_ok=True)
    board_file = folder / "board-order.json"
    if board_file.exists():
        boards = json.loads(board_file.read_text(encoding="utf-8"))
    else:
        boards = load_boards()
        board_file.write_text(json.dumps(boards), encoding="utf-8")

    records, manifest, salaried, excluded = [], [], [], []
    used = {}
    salary_companies = set()
    salaried_ids = set()
    raw_count = 0
    reached = False
    with requests.Session() as session:
        session.headers.update({"User-Agent": "STAT386-Academic-Job-Data-Project/1.0", "Accept": "application/json"})
        for position, board in enumerate(boards, start=1):
            path = folder / f"{board}.json"
            if board in EXCLUDED_BOARDS:
                # An audit found this duplicate employer after its exploratory fetch.
                # Preserve that history but exclude its roles and never request it again.
                previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                excluded.append({"board": board, "reason": EXCLUDED_BOARDS[board],
                                 "attempted_ids": previous.get("attempted_ids", []),
                                 "descriptions_saved": len(previous.get("records", [])),
                                 "metadata_posts": previous.get("metadata_posts", 0)})
                raw_count += previous.get("metadata_posts", 0)
                continue
            if path.exists():
                cache = json.loads(path.read_text(encoding="utf-8"))
            else:
                endpoint = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
                listing = get_json(session, endpoint)
                if listing is None:
                    cache = {"board": board, "company": board, "company_key": company_key(board),
                             "status": "404", "metadata_posts": 0, "planned_ids": [], "attempted_ids": [], "records": []}
                else:
                    jobs = listing.get("jobs", [])
                    names = [plain_text(job["company_name"]) for job in jobs if job.get("company_name")]
                    name = pd.Series(names).value_counts().index[0] if names else board
                    key = company_key(name)
                    if board in COMPANY_ALIASES:
                        name, key = COMPANY_ALIASES[board]["company"], COMPANY_ALIASES[board]["company_key"]
                    candidates, seen = [], set()
                    for job in jobs:
                        title = plain_text(job.get("title"))
                        group = classify_title(title)
                        research = re.search(r"\b(?:applied|research) scientist\b", title, re.I)
                        if group is None and not research:
                            continue
                        if classify_seniority(title) is None:
                            continue
                        role = job.get("internal_job_id") or job["id"]
                        if role not in seen:
                            candidates.append(job)
                            seen.add(role)
                    selected = choose_roles(candidates, max(0, MAX_ROLES - used.get(key, 0)))
                    cache = {"board": board, "company": name, "company_key": key,
                             "status": "ok", "metadata_posts": len(jobs),
                             "candidate_roles": len(candidates), "planned_ids": [job["id"] for job in selected],
                             "attempted_ids": [], "records": [], "failures": []}
                # Save the chosen IDs before fetching details. Resume cannot choose five more.
                path.write_text(json.dumps(cache), encoding="utf-8")
            # Reconcile saved employer labels too, so a newly recognized alias
            # shares the existing allowance instead of getting five more slots.
            key = company_key(cache["company"])
            if board in COMPANY_ALIASES:
                key = COMPANY_ALIASES[board]["company_key"]
            cache["company_key"] = key
            for entry in cache["records"]:
                entry["company_key"] = key
            path.write_text(json.dumps(cache), encoding="utf-8")
            used[key] = used.get(key, 0) + len(cache["planned_ids"])
            if used[key] > MAX_ROLES:
                raise ValueError(f"Five-role collection budget exceeded for {cache['company']}.")
            for job_id in cache["planned_ids"]:
                if job_id in cache["attempted_ids"]:
                    continue
                # Failed requests also consume a slot; they are not replaced by extra roles.
                cache["attempted_ids"].append(job_id)
                path.write_text(json.dumps(cache), encoding="utf-8")
                detail_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?pay_transparency=true"
                try:
                    detail = get_json(session, detail_url)
                except Exception as error:
                    cache["failures"].append({"id": job_id, "reason": str(error)})
                    path.write_text(json.dumps(cache), encoding="utf-8")
                    raise
                if detail is not None:
                    cache["records"].append({"company": cache["company"], "company_key": key, "board": board,
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "job": detail})
                else:
                    cache["failures"].append({"id": job_id, "reason": "404"})
                path.write_text(json.dumps(cache), encoding="utf-8")
            records.extend(cache["records"])
            raw_count += cache["metadata_posts"]
            manifest.append({k: v for k, v in cache.items() if k != "records"})
            if cache["records"]:
                try:
                    part, _, _ = clean_snapshot({"source": "Greenhouse Job Board API", "records": cache["records"]})
                except ValueError:
                    part = pd.DataFrame()
                if not part.empty:
                    part = part.loc[part["salary_posted"] == 1]
                    part = part.loc[~part["role_id"].isin(salaried_ids)]
                    salaried_ids.update(part["role_id"])
                    salaried.extend(part.to_dict(orient="records"))
                    salary_companies.update(part["company_key"])
            reached = len(salaried) >= TARGET_ROLES and len(salary_companies) >= MIN_COMPANIES
            progress = {"boards_visited": position, "directory_boards": len(boards), "metadata_posts": raw_count,
                        "detail_requests": sum(len(item["attempted_ids"]) for item in manifest)
                                           + sum(len(item["attempted_ids"]) for item in excluded),
                        "excluded_duplicate_board_attempts": sum(len(item["attempted_ids"]) for item in excluded),
                        "descriptions_saved": len(records), "salaried_roles": len(salaried),
                        "salaried_companies": len(salary_companies), "target_reached": reached}
            (base / "progress.json").write_text(json.dumps(progress, indent=2), encoding="utf-8")
            print(f"{position}/{len(boards)} {cache['company']}: {len(cache['records'])} descriptions; "
                  f"{len(salaried)} salaried roles / {len(salary_companies)} companies", flush=True)
            if reached:
                break
    snapshot = {"source": "Greenhouse Job Board API", "records": records, "requests": manifest,
                "excluded_boards": excluded,
                "collection_complete": reached, "target_reached": reached, "progress": progress,
                "raw_post_count": raw_count, "max_roles_per_company": MAX_ROLES,
                "sampling_seed": SEED, "directory_url": DIRECTORY_URL, "activity_url": ACTIVITY_URL,
                "directory_boards": len(boards), "collected_at_utc": datetime.now(timezone.utc).isoformat()}
    RAW_PATH.parent.mkdir(exist_ok=True)
    RAW_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    if not reached:
        raise ValueError("The directory was exhausted before both salary targets were met. The prior CSV was preserved.")
    return snapshot



# 5. Turn saved JSON records into one cleaned DataFrame

def clean_snapshot(snapshot):
    if snapshot.get("source") != "Greenhouse Job Board API":
        raise ValueError("The current snapshot is not Greenhouse data. Run project.py --collect first.")
    rows, audit = [], []
    aliases = COMPANY_ALIASES
    seen_ids = set()
    counts = {"raw_results": len(snapshot["records"]), "duplicate_post_ids_removed": 0,
              "missing_ids_removed": 0, "unmatched_titles_removed": 0,
              "non_english_removed": 0, "non_senior_removed": 0}
    counts["metadata_post_entries_inspected"] = snapshot.get("raw_post_count", counts["raw_results"])
    counts["metadata_unmatched_titles"] = snapshot.get("unmatched_titles_removed", 0)
    counts["metadata_non_senior_titles"] = snapshot.get("non_senior_removed", 0)
    for entry in snapshot["records"]:
        job = entry["job"]
        entry = dict(entry)
        entry["company_key"] = company_key(entry["company"])
        if entry["board"] in aliases:
            entry = dict(entry)
            entry["company"] = aliases[entry["board"]]["company"]
            entry["company_key"] = aliases[entry["board"]]["company_key"]
        if not job.get("id"):
            counts["missing_ids_removed"] += 1
            continue
        job_id = f"{entry['board']}:{job['id']}"
        if job_id in seen_ids:
            counts["duplicate_post_ids_removed"] += 1
            continue
        seen_ids.add(job_id)
        title = plain_text(job.get("title"))
        description = plain_text(job.get("content"))
        group = classify_title(title, description)
        if group is None:
            counts["unmatched_titles_removed"] += 1
            continue
        seniority = classify_seniority(title)
        if seniority is None:
            counts["non_senior_removed"] += 1
            continue
        language = job.get("language") or "unknown"
        if language != "unknown" and not language.lower().startswith("en"):
            counts["non_english_removed"] += 1
            continue
        flags = skill_mentions(description)
        if not description:
            flags = dict.fromkeys(flags)
        ranges = posted_pay(job, description)
        location = plain_text((job.get("location") or {}).get("name"))
        usable, annual_basis = annual_usd_ranges(ranges, location, description)
        low = min(item["min"] for item in usable) if usable else None
        high = max(item["max"] for item in usable) if usable else None
        salary_midpoint = (low + high) / 2 if usable else None
        primary = usable[0] if usable else (ranges[0] if ranges else {})
        internal_id = job.get("internal_job_id")
        employer = entry.get("company_key", company_key(entry["company"]))
        role_id = f"{employer}:{internal_id}" if internal_id is not None else job_id
        location = plain_text((job.get("location") or {}).get("name"))
        family = "|".join([entry["board"], title.casefold(), description.casefold()])
        rows.append({
            "job_id": job_id, "role_id": role_id, "greenhouse_post_id": job["id"],
            "title": title, "company": entry["company"], "board": entry["board"],
            "company_key": entry.get("company_key", entry["company"].casefold()),
            "location": location, "job_group": group, "seniority": seniority, "language": language,
            "departments": "; ".join(item["name"] for item in job.get("departments", [])),
            "updated_at": job.get("updated_at"), "first_published": job.get("first_published"),
            "source_url": job.get("absolute_url"),
            "salary_posted": int(bool(ranges)),
            "salary_min": primary.get("min"), "salary_max": primary.get("max"),
            "salary_currency": primary.get("currency"), "salary_period": primary.get("period"),
            "salary_method": primary.get("method"), "salary_kind": primary.get("kind"),
            "posted_range_count": len(ranges), "posted_ranges": json.dumps(ranges),
            "salary_min_usd": low, "salary_max_usd": high,
            "annual_salary_midpoint_usd": salary_midpoint,
            "salary_range_count": len(usable),
            "annual_pay_basis": annual_basis,
            "annual_pay_inference_rule": (
                "USD; US location; unspecified period; no nonannual pay wording; "
                f"both bounds between {INFER_ANNUAL_MIN} and {INFER_ANNUAL_MAX}"
                if annual_basis == "inferred" else None),
            "salary_status": "annual_usd_available" if usable else "posted_not_comparable" if ranges else "not_posted_or_not_detected",
            "description_characters": len(description),
            "description_available": int(bool(description)),
            "posting_family_id": hashlib.sha256(family.encode("utf-8")).hexdigest()[:16],
            "source": "Greenhouse Job Board API", "collected_at_utc": entry["retrieved_at_utc"],
            **flags,
        })
        audit.append({"job_id": job_id, "title": title, "source_url": job.get("absolute_url"),
                      "description": description, "salary_candidates": json.dumps(ranges), **flags})
    data = pd.DataFrame(rows)
    if data.empty:
        raise ValueError("No relevant jobs were found.")
    # Several location-specific posts can refer to the same internal role.
    data["post_count_for_role"] = data.groupby("role_id")["job_id"].transform("size")
    locations = data.groupby("role_id")["location"].agg(lambda values: "; ".join(sorted(set(values))))
    data["all_locations"] = data["role_id"].map(locations)
    before = len(data)
    data = data.sort_values("description_characters", ascending=False, kind="stable").drop_duplicates("role_id")
    counts["repeated_role_posts_removed"] = before - len(data)
    data = data.sort_values(["company", "title", "job_id"]).reset_index(drop=True)
    # Boards sharing a normalized employer identity count as one company.
    labels = data.groupby("company_key")["company"].first().to_dict()
    labels.update({"doordash": "DoorDash", "fanatics": "Fanatics",
                   "spacex": "SpaceX", "wpp": "WPP"})
    data["company"] = data["company_key"].map(labels)
    data["possible_repost"] = data.duplicated(["title", "company", "location"], keep=False).astype(int)
    data["posting_family_size"] = data.groupby("posting_family_id")["job_id"].transform("size")
    counts.update({"final_rows": len(data), "features": len(data.columns),
                   "employers": int(data["company"].nunique()),
                   "posting_families": int(data["posting_family_id"].nunique()),
                   "collection": {key: value for key, value in snapshot.items() if key != "records"}})
    return data, pd.DataFrame(audit), counts

# 6. Validate, summarize, and plot with pandas methods

def validate_data(jobs):
    """Fail clearly if the data no longer meet the assignment or the sampling plan."""
    if len(jobs) < TARGET_ROLES or jobs.shape[1] < 5:
        raise ValueError("This study requires at least 300 salaried roles and five variables.")
    if not jobs["job_id"].is_unique or not jobs["role_id"].is_unique:
        raise ValueError("Repeated job or role IDs remain.")
    if jobs["company_key"].nunique() < MIN_COMPANIES:
        raise ValueError("This study requires more than 100 companies.")
    if jobs.groupby("company_key").size().max() > MAX_ROLES:
        raise ValueError("A company has more than five roles.")
    if not jobs["salary_posted"].eq(1).all():
        raise ValueError("Every role in the main dataset must disclose numeric pay.")
    if jobs["seniority"].isna().any():
        raise ValueError("Every retained role needs a seniority category.")


def normal_curve_from_range(lower, upper, grid):
    """Model advertised bounds as mean minus/plus two standard deviations."""
    if not (math.isfinite(lower) and math.isfinite(upper) and 0 < lower < upper):
        raise ValueError("A range curve needs two finite, positive, different bounds.")
    mean = (lower + upper) / 2
    standard_deviation = (upper - lower) / 4
    density = []
    for x in grid:
        distance = (x - mean) / standard_deviation
        density.append(math.exp(-0.5 * distance ** 2)
                       / (standard_deviation * math.sqrt(2 * math.pi)))
    return density


def plot_pay_distributions(jobs):
    """Show separate range-mixture plots, including labeled annual-pay inferences."""
    order = ["Machine learning / AI", "Data science", "Data / business analytics",
             "Data engineering", "Analytics engineering / BI", "Applied / quantitative science"]
    comparable = jobs.dropna(subset=["salary_min_usd", "salary_max_usd"]).copy()
    valid = (comparable["salary_min_usd"].map(math.isfinite)
             & comparable["salary_max_usd"].map(math.isfinite)
             & comparable["salary_min_usd"].gt(0)
             & comparable["salary_max_usd"].gt(comparable["salary_min_usd"])
             & comparable["annual_pay_basis"].isin(["confirmed", "inferred"]))
    comparable = comparable.loc[valid]
    comparable["range_mean"] = (comparable["salary_min_usd"] + comparable["salary_max_usd"]) / 2
    comparable["range_sd"] = (comparable["salary_max_usd"] - comparable["salary_min_usd"]) / 4
    families = [name for name in order if comparable["job_group"].eq(name).any()]
    far_tail = (comparable["range_mean"] + 4 * comparable["range_sd"]).max()
    right_edge = math.ceil(far_tail / 100000) * 100 if len(comparable) else 500
    grid = list(range(0, int(right_edge) + 1))
    rows = max(1, math.ceil(len(families) / 2))
    fig, axes = plt.subplots(rows, 2, figsize=(12, 3 * rows + 2), sharex=True, sharey=True, squeeze=False)
    summary, legend_handles = [], {}
    maximum_density = 0
    for family, ax in zip(families, axes.flat):
        group = comparable.loc[comparable["job_group"] == family]
        confirmed_count = int(group["annual_pay_basis"].eq("confirmed").sum())
        inferred_count = int(group["annual_pay_basis"].eq("inferred").sum())
        mean = float(group["range_mean"].mean())
        summary.append({"job_group": family, "roles": len(group),
                        "confirmed_roles": confirmed_count, "inferred_roles": inferred_count,
                        "employers": int(group["company_key"].nunique()),
                        "mean_midpoint_usd": mean,
                        "median_midpoint_usd": float(group["range_mean"].median()),
                        "curve_shown": True})
        all_curves = []
        for _, posting in group.iterrows():
            curve = normal_curve_from_range(posting["salary_min_usd"] / 1000,
                                            posting["salary_max_usd"] / 1000, grid)
            all_curves.append(curve)
        combined = [sum(points) / len(all_curves) for points in zip(*all_curves)]
        line, = ax.plot(grid, combined, color="#286f82", linewidth=2.2)
        legend_handles.setdefault("Confirmed + inferred annual pay", line)
        ax.fill_between(grid, combined, color="#286f82", alpha=0.12)
        maximum_density = max(maximum_density, max(combined))
        line = ax.axvline(mean / 1000, color="#b37b16", linestyle="--", linewidth=1.5)
        legend_handles.setdefault("Mean range midpoint", line)
        ax.set_title(f"{family}\nn={len(group)}: {confirmed_count} confirmed, {inferred_count} inferred", fontsize=11)
        ax.text(0.97, 0.86, f"Combined mean: ${mean / 1000:,.0f}k", transform=ax.transAxes,
                ha="right", fontsize=10, color="#286f82")
        ax.grid(axis="x", alpha=0.15)
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)
    for index, ax in enumerate(axes.flat):
        if index >= len(families):
            fig.delaxes(ax)  # Do not display a panel for an incomplete/empty family.
            continue
        ax.set_xlim(0, right_edge)
        ax.set_ylim(0, max(maximum_density * 1.2, 0.001))
        ax.set_xticks(range(0, int(right_edge) + 1, 100))
        ax.tick_params(axis="x", labelbottom=True)
    if not families:
        fig.text(0.5, 0.5, "No complete annual USD ranges are available", ha="center")
    fig.suptitle("Range-based pay distributions by senior role family", fontsize=17, y=0.98)
    fig.text(0.5, 0.94, "Each posting: mean = midpoint; SD = (upper - lower) / 4", ha="center", fontsize=11)
    if legend_handles:
        fig.legend(list(legend_handles.values()), list(legend_handles),
                   loc="upper center", bbox_to_anchor=(0.5, 0.92), ncol=2, frameon=False)
    fig.supxlabel("Annual USD pay ($1,000s)", y=0.075)
    fig.supylabel("Modelled density (same scale in every panel)", x=0.015)
    fig.text(0.03, 0.035, "Inferred: explicit USD + US location + USD 25k-1m bounds + unspecified period, with no conflicting pay-period wording.", fontsize=9)
    fig.text(0.03, 0.012, "Equal weight per posting. Bounds model mean +/- 2 SD; normal tails extend beyond them. This is an assumption, not observed earnings.", fontsize=9)
    fig.tight_layout(rect=(0.035, 0.10, 1, 0.88), h_pad=2)
    fig.savefig(OUTPUT / "salary_distributions.png", dpi=150)
    plt.close(fig)
    return summary


def analyze_jobs(jobs):
    OUTPUT.mkdir(exist_ok=True)
    skills = []
    for column in jobs.columns:
        if column.startswith("mentions_"):
            skills.append(column)
    described = jobs.loc[jobs["description_available"] == 1].copy()
    if described.empty:
        raise ValueError("Skill analysis requires descriptions.")

    # The mean of a 0/1 indicator is the fraction of roles mentioning that skill.
    role_rates = described[skills].mean() * 100
    company_rates = described.groupby("company_key")[skills].mean().mean() * 100
    frequency = pd.DataFrame({"Each role equal": role_rates,
                              "Each company equal": company_rates})
    frequency = frequency.sort_values("Each role equal")
    labels = []
    for name in frequency.index:
        labels.append(name.replace("mentions_", "").replace("_", " ").upper())
    frequency.index = labels
    ax = frequency.plot.barh(figsize=(9, 6), color=["#286f82", "#d7a342"])
    ax.set_title("Senior data and AI skill mentions: maximum five roles per company")
    ax.set_xlabel("Mention rate (%)")
    ax.set_ylabel("")
    plt.figtext(0.01, 0.01, "Source: public Greenhouse boards. Mentions are not verified requirements.", fontsize=8)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.savefig(OUTPUT / "skill_frequency.png", dpi=150)
    plt.close()

    salary_by_role = plot_pay_distributions(jobs)

    by_group = described.groupby("job_group")[skills].mean() * 100
    company_group_rates = described.groupby(["job_group", "company_key"])[skills].mean()
    company_group_rates = company_group_rates.groupby("job_group").mean() * 100
    salary = jobs["annual_salary_midpoint_usd"].dropna()
    salary_by_skill = []
    for skill in skills:
        for mentioned in [0, 1]:
            group = described.loc[described[skill] == mentioned]
            pay = group["annual_salary_midpoint_usd"].dropna()
            median = float(pay.median()) if len(pay) else None
            salary_by_skill.append({"skill": skill, "mentioned": mentioned,
                                    "roles": len(group), "salary_n": len(pay), "median_midpoint": median})
    results = {
        "roles": len(jobs), "companies": jobs["company_key"].nunique(), "variables": jobs.shape[1],
        "maximum_roles_per_company": jobs.groupby("company_key").size().max(),
        "role_counts": jobs["job_group"].value_counts().to_dict(),
        "seniority_counts": jobs["seniority"].value_counts().to_dict(),
        "company_counts": jobs["company"].value_counts().to_dict(),
        "common_titles": jobs["title"].value_counts().to_dict(),
        "skill_counts": described[skills].sum().to_dict(),
        "role_weighted_skill_percent": role_rates.to_dict(),
        "company_equal_skill_percent": company_rates.to_dict(),
        "skill_percent_by_role": by_group.to_dict(orient="index"),
        "company_equal_skill_percent_by_role": company_group_rates.to_dict(orient="index"),
        "salary_currency_counts": jobs["salary_currency"].value_counts(dropna=False).to_dict(),
        "salary_period_counts": jobs["salary_period"].value_counts(dropna=False).to_dict(),
        "salary_method_counts": jobs["salary_method"].value_counts().to_dict(),
        "annual_usd_salary_count": len(salary),
        "confirmed_annual_usd_count": int(jobs["annual_pay_basis"].eq("confirmed").sum()),
        "inferred_annual_usd_count": int(jobs["annual_pay_basis"].eq("inferred").sum()),
        "salary_employers": jobs.loc[jobs["annual_salary_midpoint_usd"].notna(), "company_key"].nunique(),
        "salary_midpoint_summary": salary.describe().to_dict(),
        "salary_by_role": salary_by_role,
        "salary_density_model": {"type": "equal_weight_normal_mixture",
                                 "mean": "(lower + upper) / 2",
                                 "standard_deviation": "(upper - lower) / 4",
                                 "range_interpretation": "mean plus or minus two standard deviations",
                                 "minimum_components": 1,
                                 "eligible_roles": sum(item["roles"] for item in salary_by_role)},
        "annual_pay_inference": {"currency": "explicit USD only", "location": "US locations only",
                                 "minimum_lower_bound": INFER_ANNUAL_MIN,
                                 "maximum_upper_bound": INFER_ANNUAL_MAX,
                                 "exclude": "explicit nonannual periods, conflicting period wording, total compensation, incomplete bounds",
                                 "preference": "use confirmed annual ranges before inferred ranges"},
        "salary_by_skill": salary_by_skill,
        "missing_values": jobs.isna().sum().to_dict(),
    }
    # Convert NumPy scalar values through pandas before saving ordinary JSON.
    text = pd.Series(results).to_json(indent=2, double_precision=15)
    (OUTPUT / "results.json").write_text(text, encoding="utf-8")
    print(f"Validated {len(jobs)} senior roles from {jobs['company_key'].nunique()} companies.")
    print("Maximum roles per company:", jobs.groupby("company_key").size().max())
    print("\nRole counts:\n", jobs["job_group"].value_counts().to_string())
    print("\nSkill percentages:\n", frequency.sort_values("Each role equal", ascending=False).round(1).to_string())
    confirmed_count = int(jobs["annual_pay_basis"].eq("confirmed").sum())
    inferred_count = int(jobs["annual_pay_basis"].eq("inferred").sum())
    print(f"\nAnnual USD ranges: {len(salary)} ({confirmed_count} confirmed, {inferred_count} inferred)")
    print("All summaries: output/results.json. Figures: output/*.png.")
    return results


# 7. Main function that brings all of the above together into a function
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--collect", action="store_true", help="Resume the public salary search.")
    options.add_argument("--rebuild", action="store_true", help="Clean the saved raw snapshot without network requests.")
    parser.add_argument("--fresh", action="store_true", help="Start a new salary search instead of resuming.")
    args = parser.parse_args()
    if args.fresh and not args.collect:
        parser.error("--fresh must be used together with --collect.")
    if args.collect or args.rebuild:
        if args.collect:
            snapshot = collect_jobs(fresh=args.fresh)
        else:
            snapshot = json.loads(RAW_PATH.read_text(encoding="utf-8"))
            if not snapshot.get("collection_complete", True):
                raise ValueError("The saved collection was interrupted. Keep the previous CSV until collection completes.")
        jobs, _, cleaning_counts = clean_snapshot(snapshot)
        jobs = select_salaried_sample(jobs)
        validate_data(jobs)
        jobs.to_csv(DATA_PATH, index=False)
    else:
        jobs = pd.read_csv(DATA_PATH, dtype={"job_id": str, "role_id": str})
        if "salary_posted" not in jobs.columns:
            progress_path = ROOT / ".project-cache/salary-search/progress.json"
            status = ""
            if progress_path.exists():
                progress = json.loads(progress_path.read_text(encoding="utf-8"))
                status = (f"Saved search progress: {progress['salaried_roles']} pay-disclosing roles "
                          f"across {progress['salaried_companies']} companies.\n")
            parser.exit(status=1, message=(
                "Data update pending: jobs.csv still uses the earlier study's format.\n"
                "The expanded CSV will replace it after collection reaches 300 salary-disclosing "
                "roles across at least 101 companies.\n" + status
                + "If collection is already running, let it finish. Otherwise resume with:\n"
                "  uv run python project.py --collect\n"
                "Your installed packages are not the problem; no saved data was changed.\n"))
        if "annual_pay_basis" not in jobs.columns:
            parser.exit(status=1, message=(
                "This CSV predates the annual-pay inference update. Use the current bundled jobs.csv, "
                "or rebuild from your saved raw snapshot:\n  uv run python project.py --rebuild\n"))
        validate_data(jobs)
    analyze_jobs(jobs)


if __name__ == "__main__":
    main()
