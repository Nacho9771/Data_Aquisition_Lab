# Senior data careers across 152 companies

STAT 386 Data Acquisition Blog project. The saved dataset contains **380 senior
roles from 152 companies**, with **no more than five roles per company** and 42
variables. Nothing has been pushed, published, or submitted to Canvas.

## The four main files

| File | What to use it for |
| --- | --- |
| `project.py` | All Python: collection, cleaning, validation, summaries, and figures |
| `blog.qmd` | Editable Quarto blog post |
| `jobs.csv` | The collected and cleaned dataset; one row per retained internal role |
| `README.md` | Instructions, methods, course references, and data definitions |

`pyproject.toml` and `uv.lock` record the Python environment. `blog.html` is the
rendered review copy. The `output` folder is generated: two PNG figures and one
JSON file containing the statistical summaries. You do not need to edit those
generated files by hand.

The previous multi-file version and class materials are preserved privately under
the ignored `.canvas-local` directory. Raw responses live in the ignored
`.project-cache` directory. Neither private directory belongs in a public repository.

## Run the saved project

From this folder in your terminal:

```powershell
uv sync --locked
uv run python project.py
quarto render blog.qmd --to html
```

The default Python command reads `jobs.csv`, checks the data, prints summaries,
and makes the two figures. It does **not** contact Greenhouse. Open `blog.html`
to review the rendered post. Quarto is installed separately from the Python packages.

To recreate the CSV from the saved private raw JSON on this computer:

```powershell
uv run python project.py --rebuild
```

To deliberately collect a new snapshot:

```powershell
uv run python project.py --collect
```

That last command makes live requests and can take a while. It backs up the previous
raw file, reads the configured boards, and requests at most five full descriptions
per normalized employer. It uses a three-second delay, a timeout, and no automatic
retries. Access blocks, rate limits, and other request errors stop collection.
Interrupted raw collections are marked incomplete so they cannot silently replace
the finished CSV. New live results will change as vacancies change.
After a new collection, update the numerical claims in `blog.qmd` to match the
new `output/results.json` before publishing the post.

The supplied CSV is sufficient to reproduce the published findings. The download
bundle does not contain private raw responses; on another computer, `--rebuild`
requires your own saved raw collection.

## Read the code in this order

Start with `main()` at the bottom. It chooses between reading the existing CSV,
cleaning the saved raw data, and starting a new collection.

Then work through the numbered sections:

1. **Settings:** the five-role cap, random seed, request delay, and board identifiers.
2. **Text helpers:** clean markup, identify seniority and role families, find skill names.
3. **Salary parsing:** accept only interpretable annual USD ranges.
4. **Collection:** read title lists, select candidates, and retrieve their descriptions.
5. **Cleaning:** make a list of row dictionaries, convert it to a DataFrame, and deduplicate.
6. **Validation and EDA:** check the sample, calculate grouped summaries, and save plots.
7. **Main:** run those steps in the intended order.

The long board list is input data, not hundreds of different scraping rules.
`posting_family_id` is just a stable fingerprint for identifying repeated text;
it does not affect the main skill rankings. The salary and R-language patterns
are the most specialized parts and have comments explaining their purpose.

## How this follows STAT 386

The course materials were used as a guide to methods and organization, not as a
source of job data or answers copied into this project.

| Course material reviewed | Connection to this code |
| --- | --- |
| [Lab 3: pandas exploration](https://github.com/Stat386-Fall-2026/Lab_3/blob/main/lab_3.qmd) | `read_csv`, filtering, sorting, `value_counts`, summaries, derived variables |
| [Lab 4: pandas patterns](https://github.com/Stat386-Fall-2026/Lab_4/blob/main/lab_4.qmd) | `groupby`, grouped means, text indicators, counts versus rates, pandas plots |
| [Lab 5: cleaning pipelines](https://github.com/Stat386-Fall-2026/Lab_5/blob/main/lab_5.qmd) | Reusable functions, explicit regex rules, duplicate handling, preserved missing values, validation |
| [Lab 6: web collection](https://github.com/Stat386-Fall-2026/Lab_6/blob/main/lab_6.qmd) | Bounded requests, timeouts, source records, separate raw and processed data, offline rendering |
| [Regex follow-along](https://github.com/tjkerby/regex-lecture/blob/main/follow-along.qmd) | Word boundaries, alternatives, extraction, testing misleading partial matches |
| [pandas foundations](https://github.com/tjkerby/stat-386-pandas-foundations) and [advanced pandas](https://github.com/tjkerby/stat-386-pandas-questions) | Question-driven summaries and figures generated before rendering Quarto |
| [Data acquisition slides in Canvas](https://byu.instructure.com/courses/38551/files/14105481) | HTTP/JSON, sequential polite requests, saved responses, request and population limits |
| [Course syllabus](https://byu.instructure.com/courses/38551/assignments/syllabus) | Verify AI suggestions and be able to explain the final decisions |

The five-role sampling rule, employer-name correction, and conservative salary
parser are project-specific additions. They should not be described as exact
copies of an in-class exercise. The current script's three-second delay follows
the acquisition slides' starting guidance; the saved earlier collection used a
half-second pause. No recollection was needed for this simplification.

Useful checks for understanding: Why does the mean of a 0/1 skill indicator equal
a mention rate? Why does equal-company weighting use two grouped means? Why does
a missing salary remain missing? Which line limits the number of detail requests?

## Methods and limits

The original live collection was made November 5, 2026, America/Denver. A
[CC0 public directory](https://github.com/moonie0201/ats-directory) supplied 382
candidate board identifiers. The pinned source was `companies.jsonl`, Git blob
`bf25fe8e74b67ccba6598b27d1b51199ae0114e1`. The list is incomplete and alphabetically
limited. All job data came directly from the
[Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html).

Of 382 boards, 374 returned title lists containing 23,951 metadata entries.
The collector retrieved 418 full descriptions under the cap. Final title/content
checks excluded 36 descriptions, and explicit language checks excluded two more,
leaving 380 roles. The retained families are AI/ML (170), data engineering (68),
data/business analytics (53), data science (49), applied/quantitative science (22),
and analytics engineering/BI (18).

Seniority requires Senior/Sr., Staff, Principal, Lead, Distinguished, or relevant
management/leadership wording. Junior, internship, and unmarked titles are excluded.
Commercial AI roles and generic product/project management are outside this study.
The API header “LinkedIn Job Wrapping” is corrected to Artefact based on that
board's own company introduction.

All returned locations were eligible. The cap limits concentration; it does not
make the directory a random or representative employer sample. Equal-company
rates average skill indicators within each company and then average those rates.
They are not the percentage of companies requiring a skill.

Skill flags measure mentions, including possible boilerplate and alternative or
preferred tools. They do not establish proficiency requirements. Missing descriptions
produce missing flags. R matching excludes identifiers, R&D, R&R, and currency
prefixes. Excel uses contextual patterns to avoid matching the verb “excel.”

Only 15 roles from seven companies have extractable annual USD pay under the
conservative rule. Hourly pay and unspecified currencies/periods are not guessed.
An annual upper bound below $1,000 is excluded as implausible; one source had $1–$2.
Multiple qualifying ranges become an advertised envelope. Its midpoint is not actual
pay. No skill has ten usable salaries in both comparison groups, so the post makes
no salary-premium claim.

## Data dictionary

| Variables | Meaning |
| --- | --- |
| `job_id`, `role_id`, `greenhouse_post_id` | Board/post identifier, board/internal-role identifier, source post number |
| `title`, `company`, `board`, `company_key` | Published title and employer identity; normalized key shares the five-role allowance |
| `location`, `all_locations`, `departments` | Location and department metadata among collected records |
| `job_group`, `seniority`, `language` | Role family, title-based seniority tier, source language |
| `updated_at`, `first_published`, `collected_at_utc` | Source and retrieval timestamps |
| `source`, `source_url` | Greenhouse attribution and retained public posting link |
| `salary_min_usd`, `salary_max_usd`, `annual_salary_midpoint_usd` | Annual USD envelope and midpoint, missing if not comparable |
| `salary_range_count`, `salary_status` | Count of qualifying ranges and extraction status |
| `description_characters`, `description_available` | Cleaned text length and availability indicator |
| `mentions_python`, `mentions_sql`, `mentions_r` | Language mentions |
| `mentions_pytorch`, `mentions_tensorflow` | Framework mentions |
| `mentions_aws`, `mentions_azure`, `mentions_gcp`, `mentions_cloud` | Platform mentions and broader cloud indicator |
| `mentions_spark`, `mentions_excel`, `mentions_tableau`, `mentions_power_bi` | Other tracked tools |
| `post_count_for_role`, `possible_repost`, `posting_family_id`, `posting_family_size` | Duplicate diagnostics among collected records |

## Review and publication

The intended code repository is
[Data_Aquisition_Lab](https://github.com/Nacho9771/Data_Aquisition_Lab). The blog
must ultimately be added to the separate
[existing blog repository](https://github.com/Nacho9771/cgordon0.github.io), preserving
the earlier tutorial. After review, copy this post there as `data-acquisition.qmd`,
preserving the existing tutorial's `blog.qmd`. Copy the two generated figures and
adjust their paths, then add the new post to the site's render list and navigation. No second website
is needed. Actual GitHub pushes, publication, and Canvas submission remain pending.

The small derived CSV excludes full advertisement narratives and applicant data.
Review source terms and instructor guidance before releasing data. Public access
does not grant an unrestricted license to republish advertisements. Keep all raw
responses, credentials, course downloads, and private review archives out of Git.

Canvas's recorded due date is November 6 at 11:59 p.m. Mountain time, although the
assignment description says November 10. Use the earlier date for planning.

## AI assistance and verification

Codex assisted with acquisition code, analysis, drafting, and this consolidation.
The combined script was checked against the saved raw snapshot and the previous
dataset and summaries. Connor's review and ability to explain the code remain
important parts of the course's stated approach to AI collaboration.
