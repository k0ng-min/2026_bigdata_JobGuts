# JOBGUTS

> **Technology-combination analysis for Korean IT job postings**
> Turning job-posting skill requirements into clear, evidence-based learning signals.

[![Course](https://img.shields.io/badge/Course-Introduction%20to%20Big%20Data-1f6feb?style=for-the-badge)](#) [![Progress](https://img.shields.io/badge/Progress-Week%2010%20complete-1a7f37?style=for-the-badge)](#weekly-progress) [![Status](https://img.shields.io/badge/Status-In%20development-f59e0b?style=for-the-badge)](#)

## At a glance

| Item | Details |
| --- | --- |
| **Project** | Analysis of technology combinations in Korean IT job postings |
| **Core method** | Technology-name normalization, Apriori frequent-itemset mining, and association rules |
| **Data source** | [young-cc/korean-it-recruit-dataset](https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset) on Hugging Face |
| **Current milestone** | Week 10 - data collection and preprocessing complete |
| **Repository report** | [Week 10 interim report](reports/week-10-interim-report.pdf) |

## Project overview

JOBGUTS analyzes technologies that are mentioned together in Korean IT job postings. Each posting is modeled as a transaction and each required technology as an item. The project standardizes inconsistent technology labels (for example, `JS`, `JavaScript`, and the Korean spelling for JavaScript) before applying Apriori and association-rule mining.

The planned service will present role-specific technology combinations, personalized related-skill recommendations, a technology relationship graph, and supporting job-posting excerpts with confidence and interest values.

The analysis focuses on two questions:

1. **What changes after technology-name normalization?** We compare frequent technology combinations and top association-rule rankings before and after normalization under the same conditions.
2. **Which rules are genuinely informative?** We compare confidence with interest to reduce the misleading effect of broadly required technologies and surface more meaningful co-occurrence patterns.

> **Interpretation principle:** An association rule represents technologies mentioned together in a job posting. It does not establish a learning sequence, a causal relationship, or a guarantee of employment.

## Team

| Member | Student ID | Role |
| --- | --- | --- |
| Donggyun Seo | 2021270664 | Team Lead |
| Kyungseon Kim | 2022270656 | Team Member |
| Biho Jeong | 2022270622 | Team Member |
| Kyungmin Seol | 2022270643 | Team Member |

## Weekly progress

<details open>
<summary><strong>Week 10 - Data collection and preprocessing</strong> ✅</summary>

<br>

**Outcome:** The reproducible data-collection and preprocessing pipeline is complete. The full report is available in [`reports/week-10-interim-report.pdf`](reports/week-10-interim-report.pdf).

| Area | Completed work |
| --- | --- |
| Source selection | Fixed a single JSON release, `master_merged_v5.json`, to prevent duplicate counting across dataset versions. |
| Schema validation | Defined the use of posting identifiers, company/title metadata, full text, technology fields, experience level, and location. |
| Data quality | Removed required-field missing values and very short texts; deduplicated by `source + job_id` and then by normalized company, title, and full text. |
| Technology evidence | Compared `final_techs` and `hard_skills` against samples of `raw_text` and selected the field with stronger text-level support. |
| Job groups | Classified postings into Backend, Frontend, Fullstack, Data/AI, and Other; Fullstack is retained separately to avoid blurring Backend/Frontend comparisons. |
| Experience groups | Kept entry-level / no-experience-required and 1-3-year experience postings as separate cohorts; ambiguous or conflicting cases are isolated for review. |
| Deliverables | `data/processed/cleaned_jobs.parquet` and `data/processed/review_needed.csv` are generated locally by the pipeline and intentionally excluded from Git. |

**Implemented pipeline**

```text
Selected raw JSON
  -> required-field and text-quality checks
  -> duplicate removal
  -> technology-field validation against raw text
  -> job-group and experience-group classification
  -> cleaned dataset + review queue
```

**Key implementation files**

| File | Purpose |
| --- | --- |
| [`src/download_raw.py`](src/download_raw.py) | Downloads the selected dataset release into `data/raw/`. |
| [`src/preprocess.py`](src/preprocess.py) | Runs validation, deduplication, technology-field selection, grouping, and output generation. |
| [`src/test_preprocess_smoke.py`](src/test_preprocess_smoke.py) | Covers the core job, experience, and technology-pattern rules. |
| [`src/verify_outputs.py`](src/verify_outputs.py) | Verifies generated output integrity and prints samples. |
</details>

<details>
<summary><strong>Week 11 - Technology normalization and Apriori analysis</strong> 🗓️</summary>

<br>

Planned work:

- Build `src/normalize.py` with a canonical technology dictionary.
- Normalize case variants, abbreviations, and Korean/English equivalents while keeping distinct ecosystems separate (for example, Java vs. JavaScript, React vs. React Native, and Spring vs. Spring Boot).
- Isolate unverified or ambiguous labels instead of forcing a mapping.
- Build `src/apriori_analysis.py`; model one posting as one basket, remove duplicate technologies within each basket, and explore itemsets up to three technologies.
- Report support, confidence, and interest, flagging rules with insufficient data.
- Run controlled comparisons for normalization before/after, confidence vs. interest, and job/experience cohorts.
</details>

<details>
<summary><strong>Week 12 - Results validation and insight design</strong> 🗓️</summary>

<br>

Planned work: validate rule stability and cohort differences, review representative job-posting evidence, and design clear result views for technology combinations and rule metrics.
</details>

<details>
<summary><strong>Week 13 - Service integration and refinement</strong> 🗓️</summary>

<br>

Planned work: integrate the analysis outputs into the service experience, refine relationship visualizations and recommendations, and test user-facing explanations for clarity and responsible interpretation.
</details>

<details>
<summary><strong>Week 14 - Final evaluation and presentation</strong> 🗓️</summary>

<br>

Planned work: finalize the end-to-end evaluation, document limitations and findings, prepare the final presentation, and package reproducible project materials.
</details>

## Analysis design

| Comparison | Validation goal | Controlled condition |
| --- | --- | --- |
| Before vs. after normalization | Measure the change in unique technology labels, frequent combinations, and rule rankings. | Same posting set, technology field, and minimum support. |
| Confidence vs. interest | Identify rules whose high confidence is mainly caused by a broadly occurring consequent. | Show the consequent's overall posting rate alongside both metrics. |
| Cohort comparisons | Compare Backend vs. Frontend and entry-level/no-experience-required vs. 1-3-year experience cohorts. | Calculate support, confidence, and interest within each cohort. |

## Getting started

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt

# Download the selected raw data, then build local outputs.
python src/download_raw.py
python src/preprocess.py

# Optional validation after preprocessing.
python src/test_preprocess_smoke.py
python src/verify_outputs.py
```

## Repository layout

```text
.
├── reports/
│   └── week-10-interim-report.pdf
├── src/
│   ├── download_raw.py
│   ├── preprocess.py
│   ├── test_preprocess_smoke.py
│   └── verify_outputs.py
├── requirements.txt
└── README.md
```

## Data and privacy

Raw data, generated datasets, and analysis outputs are excluded from version control because they are large and reproducible from the pipeline. Secrets, environment files, and Streamlit secrets are also excluded.

---

<sub>Original project proposal content has been retained and expanded in English. Last updated for the Week 10 interim milestone.</sub>
