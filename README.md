# Data Aquisition Blog: Observation of Data Science and ML Positions

STAT 386 Data Acquisition Blog. 300 distinct roles from 102 companies, all with detected numeric advertised pay, 53 variables, and at most five retained roles per normalized company. **Nothing has been pushed, published, or submitted.**

## Essential files

| File | Purpose |
|------------------------------------|------------------------------------|
| `project.py` | All Python collection, cleaning, checks, summaries, and figures |
| `blog.qmd` | Editable Quarto post |
| `jobs.csv` | Finished 300-role dataset |
| `README.md` | Instructions, methods, and data dictionary |

`pyproject.toml` and `uv.lock` record the Python environment. `blog.html` is the self-contained review copy. `output/` contains two generated PNG figures and `results.json`; recreate these with the Python script before rendering Quarto. Private raw data, previous versions, and course downloads stay in ignored `.project-cache/` and `.canvas-local/` folders. Never upload those folders or credentials.

## Run the saved project

``` powershell
uv sync --locked
uv run python project.py
quarto render blog.qmd --to html
```

The default Python command reads the supplied CSV, validates it, and recreates all summaries and figures **without contacting Greenhouse**. Quarto is installed separately. Open `blog.html` to review the post. The download ZIP contains the four essential files, both Python environment files, `.python-version`, `.gitignore`, and the standalone HTML preview.

To clean the saved private raw snapshot again on this computer:

``` powershell
uv run python project.py --rebuild
```

To resume the cached live salary search, or start a separate fresh search:

``` powershell
uv run python project.py --collect
uv run python project.py --collect --fresh
```

Live collection can take substantial time. The fixed board order and selected IDs are saved before detail requests. At most five attempts per normalized company are allowed in the sampling cohort, including failures and nonqualifying descriptions; restarting never replaces them with extra roles. Requests are sequential with a three-second pause, timeouts, and no automatic retries. Access errors and rate limits stop the run. An unfinished search does not replace the finished CSV. Review any failure before resuming. A finished cached search needs no further job requests.

The ZIP does not contain private raw responses: `--rebuild` on another computer requires its own raw collection. The supplied CSV reproduces the analysis directly. New collection results will change with vacancies. Update the blog's numerical claims from `output/results.json` after changing the data.

## Read the code

Start with `main()` at the bottom, then follow the numbered sections: settings, text helpers, pay parsing, collection, cleaning, validation/EDA, and the entry point. The code uses functions, loops, lists/dictionaries, requests/JSON, regular expressions, pandas filters/grouped summaries, and pandas/matplotlib plots. Caching and request accounting protect the company cap across interruptions.

## How this follows STAT 386

The course materials were used as a guide to methods and organization, not as a source of job data or answers copied into this project.

| Course material reviewed | Connection to this code |
|------------------------------------|------------------------------------|
| [Lab 3: pandas exploration](https://github.com/Stat386-Fall-2026/Lab_3/blob/main/lab_3.qmd) | `read_csv`, filtering, sorting, `value_counts`, summaries, derived variables |
| [Lab 4: pandas patterns](https://github.com/Stat386-Fall-2026/Lab_4/blob/main/lab_4.qmd) | `groupby`, grouped means, text indicators, counts versus rates, pandas plots |
| [Lab 5: cleaning pipelines](https://github.com/Stat386-Fall-2026/Lab_5/blob/main/lab_5.qmd) | Reusable functions, explicit regex rules, duplicate handling, preserved missing values, validation |
| [Lab 6: web collection](https://github.com/Stat386-Fall-2026/Lab_6/blob/main/lab_6.qmd) | Bounded requests, timeouts, source records, separate raw and processed data, offline rendering |
| [Regex follow-along](https://github.com/tjkerby/regex-lecture/blob/main/follow-along.qmd) | Word boundaries, alternatives, extraction, testing misleading partial matches |
| [pandas foundations](https://github.com/tjkerby/stat-386-pandas-foundations) and [advanced pandas](https://github.com/tjkerby/stat-386-pandas-questions) | Question-driven summaries and figures generated before rendering Quarto |
| [Data acquisition slides in Canvas](https://byu.instructure.com/courses/38551/files/14105481) | HTTP/JSON, sequential polite requests, saved responses, request and population limits |
| [Course syllabus](https://byu.instructure.com/courses/38551/assignments/syllabus) | Verify AI suggestions and be able to explain the final decisions |

The company cap and pay parser are project-specific decisions. The expanded live collection uses a three-second pause between sequential requests.

Useful checks for understanding: Why does the mean of a 0/1 skill indicator equal a mention rate? Why does equal-company weighting use two grouped means? Why does a missing salary remain missing? Which line limits the number of detail requests?

## Methods and limits

All job data were freshly obtained through the [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html). Public job reads require no API key. Candidate identifiers came from the [LastRound AI ATS company directory](https://github.com/fyrosofttech/lastroundai-hiring-data/tree/main/ats-directory), licensed CC BY 4.0, pinned at commit `2816bfadd65b7bbec23701dd036bcc7496c729db`. Credit: LastRound AI and its [salary-transparency study](https://lastroundai.com/blog/salary-transparency-study-2026). The script filters that directory to 4,966 Greenhouse boards. Historical live-board counts from [open-ats-feed](https://github.com/veresk06/open-ats-feed) guide visit order, with seed 386 breaking ties. These are discovery sources, not substitutes for freshly requested job descriptions. Cached copies preserve the actual discovery inputs used here. This prioritizes historically active boards.

**Request-history exceptions:** xai (5 attempts); wpp (5 attempts); fanaticscollectibles (3 attempts); vmlenterprisesolutions (4 attempts). The `xai` board identifies itself as SpaceXSI and its descriptions identify SpaceX. WPP Media identifies itself as WPP's operating unit. Fanatics Collectibles names Commerce and Collectibles as parts of the same Fanatics platform. These later boards were recognized as overlapping employers after their initial fetches. They are excluded entirely from the dataset, their historical requests are recorded separately in `excluded_boards`, and future runs skip them. The primary sampling manifest respects five attempts per normalized employer. The combined exploratory history includes these documented exceptions to the intended cap; it must not be described as obeying the cap without exception. The final CSV has no more than five roles per retained employer. VML/WPP Enterprise Solutions is also excluded after its published name revealed the WPP connection. Known DoorDash, Fanatics, SpaceX and WPP regional/unit names share a brand key and remaining request allowance, including when resuming cached boards. Other employer identities use normalized published names; this is not a complete corporate-ownership database.

The search visited 278 boards and inspected 87,943 metadata entries. It attempted 617 descriptions and retained 596 responses in the primary cleaning cohort; the excluded duplicate board remains separately cached. Final title, content, language, duplicate, and pay checks found 303 eligible pay-disclosing roles across 102 companies. One role per contributing company is retained first, then remaining slots are filled reproducibly to 300. Company size in the final data ranges from one to 5 roles.

Seniority requires explicit Senior/Sr., Staff, Principal, Lead, Distinguished, or relevant management/leadership wording. Junior/internship and unmarked titles are excluded. Families cover AI/ML, data science, data/business analytics, data engineering, analytics engineering/BI, and applied/quantitative science. Commercial AI and generic product/project management are excluded. Research scientists require machine-learning or data-science description evidence. Explicit non-English language records are excluded; unspecified language is retained. All locations are eligible. The Artefact board header is corrected using its own introduction. Role-family selection cycles alphabetically through available families before taking additional roles from a family. When more than five families are available, the five-request limit means not every family can be represented at that employer.

Skills are text mentions, not verified requirements. Boilerplate and preferred tools can count. R excludes R&D, R&R, R\$ and identifier patterns; Excel uses contextual wording to avoid the verb. Equal-company rates average within-company rates, then give those companies equal weight. They are not employer-requirement prevalence.

Pay extraction prefers Greenhouse `pay_input_ranges` requested with `pay_transparency=true`; documented cents are divided by 100. Labeled currency ranges in descriptions provide a fallback. Numeric employer pay may have an unknown period or currency: reported values are retained unchanged. A dollar sign alone does not establish USD. No currency conversion or hourly annualization is used. An explicit annual range with an upper bound below 1,000 is excluded as implausible. Structured fields with one bound can establish disclosure, but not an annual midpoint.

Primary currency counts: USD: 206, unspecified_dollar: 79, CAD: 13, EUR: 2. Primary period counts: unspecified: 217, year: 80, month: 2, hour: 1. There are 145 usable annual USD roles from 51 employers: 35 confirmed annual roles and 110 annual-pay inferences. Confirmed annual ranges are preferred; only when none are available does the script consider inference. Inference requires explicit USD, a recognizable US location, an unspecified period, two positive bounds between \$25,000 and \$1,000,000, and no conflicting hourly/daily/weekly/monthly pay wording. These thresholds are exploratory plausibility limits, not proof of an annual period. Generic remote locations and identified foreign/mixed locations do not qualify. Total-compensation ranges and incomplete or zero-width ranges are excluded. The reported `salary_period` remains unchanged; `annual_pay_basis` and `annual_pay_inference_rule` record the derived assumption separately. Multiple qualifying ranges become a low-to-high advertised envelope. Its midpoint is not observed earnings. No causal or salary-premium claim is made. Other posted pay stays in the dataset with its explicit attributes. Scopely's Senior Data Scientist, Marketing posting supplies structured annual USD bounds of \$17,100–\$253,000. These unusually broad employer-provided values are retained as reported, not silently repaired or treated as verified earnings.

This is a purposive, salary-conditioned Greenhouse sample. Platform coverage, activity ordering, pay disclosure, title/language rules and the cap all affect it. It is not representative of all employers or senior salaries, and cannot estimate market-wide pay-disclosure rates. Automatic text extraction can miss formats.

## Pay distribution figure

`output/skill_frequency.png` compares skill mentions, and `output/salary_distributions.png` shows separate range-based normal mixtures by role family. `output/results.json` includes `salary_by_role`: role counts, employer counts, mean and median midpoints, confirmed/inferred counts, and whether a curve is shown. `annual_pay_inference` records the inference rule and bounds in that JSON file.

The plot groups related titles into role families. Average pay means the unweighted mean of posting range midpoints, not the average of observed employee salaries. Multiple qualifying regional ranges first form one envelope for a posting.

Each eligible posting supplies one normal curve with mean `(lower + upper) / 2` and standard deviation `(upper - lower) / 4`. The posted bounds therefore represent mean plus/minus two standard deviations, enclosing about 95% of the assumed curve. Normal tails extend beyond the advertised range. Curves are averaged with equal weight per posting within each family. This is a modelling assumption, not an empirical distribution of earnings or a confidence interval. Separate panels share dollar and density scales, show the number of confirmed and inferred observations, and mark the combined mean with an orange dashed line. The figure only shows a curve for families with at least 10 comparable postings. Families with 1–9 comparable postings still appear in the salary summaries.

## Data dictionary

| Variables | Meaning |
|------------------------------------|------------------------------------|
| `job_id`, `role_id`, `greenhouse_post_id` | Board/post identifier, employer/internal-role identifier, source post number |
| `title`, `company`, `board`, `company_key` | Published title and employer identity; normalized key shares the five-role allowance |
| `location`, `all_locations`, `departments` | Location and department metadata among collected records |
| `job_group`, `seniority`, `language` | Role family, title-based seniority tier, source language |
| `updated_at`, `first_published`, `collected_at_utc` | Source and retrieval timestamps |
| `source`, `source_url` | Greenhouse attribution and retained public posting link |
| `salary_posted`, `salary_min`, `salary_max`, `salary_currency`, `salary_period` | Detected numeric pay, primary range bounds, explicit currency and period (unknown remains unknown) |
| `salary_method`, `salary_kind`, `posted_range_count`, `posted_ranges` | Extraction method, pay definition, count and JSON representation of all detected ranges |
| `annual_pay_basis`, `annual_pay_inference_rule` | Confirmed, inferred, or not comparable; the exact rule used when annual pay is inferred |
| `salary_min_usd`, `salary_max_usd`, `annual_salary_midpoint_usd` | Annual USD envelope and midpoint, missing if not comparable |
| `salary_range_count`, `salary_status` | Count of qualifying ranges and extraction status |
| `description_characters`, `description_available` | Cleaned text length and availability indicator |
| `mentions_python`, `mentions_sql`, `mentions_r` | Language mentions |
| `mentions_pytorch`, `mentions_tensorflow` | Framework mentions |
| `mentions_aws`, `mentions_azure`, `mentions_gcp`, `mentions_cloud` | Platform mentions and broader cloud indicator |
| `mentions_spark`, `mentions_excel`, `mentions_tableau`, `mentions_power_bi` | Other tracked tools |
| `post_count_for_role`, `possible_repost`, `posting_family_id`, `posting_family_size` | Duplicate diagnostics among collected records |
