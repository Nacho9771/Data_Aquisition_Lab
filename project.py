"""STAT 386: senior data careers across employers.

Default: analyze the saved jobs.csv without contacting any websites.
--rebuild: recreate jobs.csv from the private saved raw snapshot.
--collect: deliberately start a fresh public collection, capped at five roles/company.

The code follows the class sequence: collect -> clean -> validate -> summarize -> plot.
"""

import argparse
from datetime import datetime, timezone
from html import unescape
import hashlib
import json
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
# This is data, not 382 different scraping rules. All boards use the same API.
# Source: moonie0201/ats-directory (CC0), companies.jsonl,
# Git blob bf25fe8e74b67ccba6598b27d1b51199ae0114e1. The source cohort is incomplete.
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

BOARDS = """
10alabs 10beauty 1800contacts 2k 2u 3redpartners
60decibelsinc 8451 8451university 9thwayinsignia a3c41b8b71eff8c4 abacusinsights
abelsontaylor accenturefederalservices accuweather acluinternships acuitymd ada18
adcouncil addepar1 adelphirealworld adswerveinc advancedspace advancedtechnologyservices
aevexaerospace affirm affirmedrxpbc agoda agwestfarmcredit aircapture
airtable alamarbiosciences alarmcom alku allcareers aloyoga
alpaca alphaawmnaearlycareers alphafmcroles alphasense alphataraxia altaresourcetechnologiesinc
altentechnologyusa amarok americaninstitutesforresearch amplitude ampsortation anaplan
andurilindustries anthropic antora aperaaiinc aperiatechnologies apexcompanies
appian applovin apptronik aquaticcapitalmanagement arcanaanalytics arcboatcompany
arcesiumllc archer56 arenaclub arevonenergyimpltest argmax arizeai
armada artefactlinkedin arvinas ashfieldadvisory assetliving assuredguaranty
assystinc asteraearlycareer2026 asteralabs astranis atek athinkingape
atlassand atomicmachines attentionarc attentive auctane audaxgroup
authenticbrandsgroup avepoint avidxchangeinc avride awetomaton axios
axle axon axontalentcommunity axq axs axsometherapeutics
axuall aypapower babelstreet bamboohr17 bandwidth betterhelpcom
bevicareers bgeinc billiontoone birdygrey blackedgecapital blacksky
blockchain bloombergdotorg bloomreach bluelabsanalyticsinc blueskyinnovators bluestaq
botauto bottomlinetechnologies boxinc bpcs bracebridgecapital breezeairways
breezecash brevium brightai bti36021 bugcrowd businessolverinvitationonly
butternutbox buyersedgeplatformrecruiting cadwell calyxo candidly canonical
capco capitalontap captivation carbonchain carefeed carta
cartesiansystems caseguard catapultsports cc celigo cellsignalingtechnology79
celonis censys centriaautism chanzuckerberginitiative charlesriverassociates charterup
checkr chicagotrading chicagotradingcampus chime chowbus civisanalytics
clarityinnovates clear clearwayjobs clinicalarchitecture clockworksystems cloudflare
cmt cobaltio cognitiv coherehealth colabsoftware commerceiq
commvault compeerfinancial comstock concentric connectder connerstrongbuckelew
constantcontact constellationsoftwareinc constructionresources consumerreports convene cooksys
correlationone cortland cottinghambutlerinsuranceservicesinc coursera cpisecurity creatorsworkhere
creditunionofcolorado cresta cribl criticalmass crunchyroll css
cssmerge ctccampusboard customcomputerspecialists darkwolfsolutions datasystemsanalystsinc dbeconorthamerica
ddome debtbook deepmind defenseunicorns designmehair detroitlions
devrev dhpace dialpad didi digs diligentcorporation
diligentrobotics dlhcorporation docugami doordashusa dorsia doublegood
doubleverify doximity drivewealth drweng drwuniversityjobs duettoresearch
dunnhumby dv01 dvtrading earnin echodynecorp edgewoodpartnersinsurancecenter
edmentum efficientcomputer eikontherapeutics elevationscreditunion elwoodtechnologies emergingtalent
energyhub energysolutions engineersgate enigmaio ennoblecare enova
ensco ensemble epickids eudia eulerity eventsandinterns
everlaw evolver excelsportsmanagement exoduspoint expertnetwork ezcaterinc
faire fairlife fanaticscollectibles fashionnova fccincinnati federato
figma figure figureai financialtechnologypartners fiveringsllc flagshippioneeringinc
flex flexport flighthub flip flowtraders focusfinancialpartners
focuspartnerswealth foleyhoag forbes formic forteracorporation forwardnetworks
fosphamarketing fourhands fourkites freedomconsulting freeformfuturecorp fsastorecom
fschumacherco fspco-op012325 furtherearlycareer gaintheory galaxydigitalservices gallup
gametimeunited gardacp garnerhealth gcmgrosvenor gelbergroup gelberhandshake
generalatlantic generalmatter genevatrading genscript geotab getbuilt
gingerlabsinc ginkgobioworks gitlab gleanwork globalizationpartners glossgenius
glydways gofundme goldenpetbrands goodwaygroup goremutualinsurance gotion
gradial grafanalabs graphcore grassrootsanalytics greenhouse greenworkssunriseglobalmarketing
growthloop grvty gsdm guidepoint guidepointsecurity gusto
haizelabs hankooktireamericacorp harbingermotors harborglobal hasbro haven
headlandstechnologiesllc heartflowinc hellbenderinc heraldapi heygen hiddenlayer
higherlogic hivefinancialsystems homesolutions honehealth horacemannservicecorporation horizonindustrieslimited
horizonsurgicalsystems hudl humansignal hyannisportresearch icapitalnetwork idmeuniversityrecruiting
ieqcapital immersive impact impinjexternal impiricus incidentiq
industrialelectricmanufacturing inflectionai inizio innodatainc inspiremedicalsystemsinc instabase
instalilyai instawork instead insurify integra integrainterns
internshiplist2000 intersystems interwellhealth interworks intrinsicrobotics inversionspace
ionq iovancebiotherapeutics ispottv itslogisticsllc ivalua ivxhealth
janestreet jencapinc jobsatphamily jobsmckinneycom
""".split()

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
    # Greenhouse sometimes encodes tags as &lt;p&gt;, so decode before stripping.
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
    if re.search(r"\b(?:product\s+(?:manager|management|strategy)|project manager|business manager|solutions manager|sales engineer)\b", title, re.I):
        return None
    ml = re.search(r"\b(?:machine[ -]learning|deep learning|ML|AI|LLM|NLP|MLOps|computer vision|natural language)\b", title, re.I)
    technical = re.search(r"\b(?:engineer\w*|scientist\w*|research\w*|architect\w*)\b", title, re.I)
    management = re.search(r"\b(?:manager|director|head|lead)\b", title, re.I)
    commercial = re.search(r"\b(?:sales|partnerships?|client|marketing|accounts?|GTM|capacity)\b|business development", title, re.I)
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

# 3. Salary parsing. Keep uncertainty missing instead of guessing.

def number(value):
    try:
        result = float(value)
        return result if 0 < result < float("inf") else None
    except (TypeError, ValueError):
        return None

def salary_ranges(text):
    """Keep explicitly USD, explicitly annual dollar ranges. Never annualize hourly pay."""
    pattern = r"(?:\$\s*|USD\s+)([\d,]+(?:\.\d{1,2})?)\s*(?:[-–—]|to)\s*\$?\s*([\d,]+(?:\.\d{1,2})?)"
    ranges = []
    for match in re.finditer(pattern, text, re.I):
        low, high = [number(part.replace(",", "")) for part in match.groups()]
        before = text[max(0, match.start() - 450):match.start()]
        after = text[match.end():match.end() + 180]
        local = before + match.group() + after
        suffix = re.match(r"\s*(USD|CAD|AUD|SGD)\b", after, re.I)
        currency = suffix.group(1).upper() if suffix else None
        if currency is None and re.search(r"\bUSD\b|U\.S\. dollars|US dollars", local, re.I):
            currency = "USD"
        annual = bool(re.search(
            r"\bannual(?:ized)?\s+(?:(?:base|cash|gross|total)\s+)?(?:salary|pay|compensation)"
            r"|\bper year\b|\byearly\b|/year|\bper annum\b", local, re.I))
        hourly = bool(re.search(r"\bper hour\b|\bhourly\b|/hour", before[-80:] + after[:60], re.I))
        if low is not None and high is not None and high >= low:
            ranges.append({"low": low, "high": high, "currency": currency,
                           "annual": annual and not hourly, "context": local})
    return ranges

# 4. Collect only selected role details, preserving raw responses for later cleaning.

def company_key(name):
    """Make small differences in employer labels share the same five-role allowance."""
    name = re.sub(r"^(?:careers at|careers|jobs at)\s+", "", name.strip(), flags=re.I)
    name = re.sub(r"\b(?:incorporated|inc|llc|ltd|limited|corporation|corp)\.?$", "", name, flags=re.I)
    return re.sub(r"\W+", "", name.casefold())


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
    response.raise_for_status()  # Stop on access blocks or other failed responses.
    return response.json()


def collect_jobs():
    """Read title lists, then request at most five full descriptions per company."""
    records = []
    manifest = []
    used = {}
    raw_count = 0
    with requests.Session() as session:
        session.headers.update({"User-Agent": "STAT386-Academic-Job-Data-Project/1.0"})
        for position, board in enumerate(BOARDS, start=1):
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            listing = get_json(session, url)  # No content=true: only title-list metadata.
            if listing is None:
                manifest.append({"board": board, "status": "404", "detail_requests": 0})
                continue
            jobs = listing.get("jobs", [])
            raw_count += len(jobs)
            names = []
            for job in jobs:
                if job.get("company_name"):
                    names.append(plain_text(job["company_name"]))
            name = pd.Series(names).value_counts().index[0] if names else board
            key = company_key(name)
            if board in COMPANY_ALIASES:
                name = COMPANY_ALIASES[board]["company"]
                key = COMPANY_ALIASES[board]["company_key"]
            candidates = []
            seen = set()
            for job in jobs:
                title = plain_text(job.get("title"))
                group = classify_title(title)
                research = re.search(r"\b(?:applied|research) scientist\b", title, re.I)
                if group is None and not research:
                    continue
                if classify_seniority(title) is None:
                    continue
                role_id = job.get("internal_job_id") or job["id"]
                if role_id not in seen:
                    candidates.append(job)
                    seen.add(role_id)
            remaining = max(0, MAX_ROLES - used.get(key, 0))
            selected = choose_roles(candidates, remaining)
            used[key] = used.get(key, 0) + len(selected)
            for job in selected:
                detail = get_json(session, f"{url}/{job['id']}")
                if detail is not None:
                    records.append({"company": name, "company_key": key, "board": board,
                                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                                    "job": detail})
            manifest.append({"board": board, "company": name, "company_key": key,
                             "status": "ok", "jobs": len(jobs), "detail_requests": len(selected)})
            snapshot = {"source": "Greenhouse Job Board API", "records": records,
                        "collection_complete": False,
                        "raw_post_count": raw_count, "requests": manifest,
                        "max_roles_per_company": MAX_ROLES, "sampling_seed": SEED,
                        "collected_at_utc": datetime.now(timezone.utc).isoformat()}
            RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
            RAW_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            print(f"{position}/{len(BOARDS)} {name}: requested {len(selected)} descriptions")
    if not records:
        raise ValueError("No role descriptions were collected.")
    snapshot["collection_complete"] = True
    RAW_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return snapshot


# 5. Turn saved JSON records into one cleaned DataFrame.

def clean_snapshot(snapshot):
    if snapshot.get("source") != "Greenhouse Job Board API":
        raise ValueError("The current snapshot is not Greenhouse data. Run collect_jobs.py first.")
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
        ranges = salary_ranges(description)
        # An annual upper bound below $1,000 is treated as an implausible placeholder.
        usable = [item for item in ranges if item["currency"] == "USD" and item["annual"] and item["high"] >= 1000]
        low = min(item["low"] for item in usable) if usable else None
        high = max(item["high"] for item in usable) if usable else None
        salary_midpoint = (low + high) / 2 if usable else None
        internal_id = job.get("internal_job_id")
        role_id = f"{entry['board']}:{internal_id}" if internal_id is not None else job_id
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
            "salary_min_usd": low, "salary_max_usd": high,
            "annual_salary_midpoint_usd": salary_midpoint,
            "salary_range_count": len(usable),
            "salary_status": "annual_usd_available" if usable else "not_comparable_or_missing",
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
    labels = data.groupby("company_key")["company"].first()
    data["company"] = data["company_key"].map(labels)
    data["possible_repost"] = data.duplicated(["title", "company", "location"], keep=False).astype(int)
    data["posting_family_size"] = data.groupby("posting_family_id")["job_id"].transform("size")
    counts.update({"final_rows": len(data), "features": len(data.columns),
                   "employers": int(data["company"].nunique()),
                   "posting_families": int(data["posting_family_id"].nunique()),
                   "collection": {key: value for key, value in snapshot.items() if key != "records"}})
    return data, pd.DataFrame(audit), counts

# 6. Validate, summarize, and plot with pandas methods used in Labs 3-5.

def validate_data(jobs):
    """Fail clearly if the data no longer meet the assignment or the sampling plan."""
    if len(jobs) < 200 or jobs.shape[1] < 5:
        raise ValueError("The assignment requires at least 200 rows and five variables.")
    if not jobs["job_id"].is_unique or not jobs["role_id"].is_unique:
        raise ValueError("Repeated job or role IDs remain.")
    if jobs["company_key"].nunique() <= 100:
        raise ValueError("This study requires more than 100 companies.")
    if jobs.groupby("company_key").size().max() > MAX_ROLES:
        raise ValueError("A company has more than five roles.")
    if jobs["seniority"].isna().any():
        raise ValueError("Every retained role needs a seniority category.")


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

    coverage = jobs.groupby(["job_group", "salary_status"]).size().unstack(fill_value=0)
    coverage = coverage.reindex(columns=["annual_usd_available", "not_comparable_or_missing"], fill_value=0)
    coverage.columns = ["Annual USD range extracted", "Missing or not comparable"]
    ax = coverage.plot.barh(stacked=True, figsize=(11, 6), color=["#286f82", "#d7a342"])
    ax.set_title("Only explicitly annual USD ranges enter the pay summary")
    ax.set_xlabel("Number of roles")
    ax.set_ylabel("")
    plt.figtext(0.01, 0.01, "Source: public Greenhouse boards. No hourly pay is annualized.", fontsize=8)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.savefig(OUTPUT / "salary_coverage.png", dpi=150)
    plt.close()

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
        "annual_usd_salary_count": len(salary),
        "salary_employers": jobs.loc[jobs["annual_salary_midpoint_usd"].notna(), "company_key"].nunique(),
        "salary_midpoint_summary": salary.describe().to_dict(),
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
    print(f"\nComparable annual USD ranges: {len(salary)}")
    print("All summaries: output/results.json. Figures: output/*.png.")
    return results


# 7. Read this first to see how the functions fit together.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--collect", action="store_true", help="Start a new public collection.")
    options.add_argument("--rebuild", action="store_true", help="Clean the saved raw snapshot without network requests.")
    args = parser.parse_args()
    if args.collect or args.rebuild:
        if args.collect:
            if RAW_PATH.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                RAW_PATH.rename(RAW_PATH.with_name(f"raw_jobs_{stamp}.json"))
            snapshot = collect_jobs()
        else:
            snapshot = json.loads(RAW_PATH.read_text(encoding="utf-8"))
            if not snapshot.get("collection_complete", True):
                raise ValueError("The saved collection was interrupted. Keep the previous CSV until collection completes.")
        jobs, _, cleaning_counts = clean_snapshot(snapshot)
        validate_data(jobs)
        jobs.to_csv(DATA_PATH, index=False)
    else:
        jobs = pd.read_csv(DATA_PATH, dtype={"job_id": str, "role_id": str})
        validate_data(jobs)
    analyze_jobs(jobs)


if __name__ == "__main__":
    main()
