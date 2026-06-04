# Automated Regulatory Reporting Pipeline

End-to-end ETL pipeline simulating a bank's month-end risk reporting cycle on
**128,412 real loan records** from Lending Club (2018 Q4).

**Stack:** Python · SQL · SQLite · SQLAlchemy · pandas · APScheduler · XlsxWriter · Power BI

## Architecture

```
   INGEST            TRANSFORM          AUTOMATE         EXPORT           DASHBOARD
CSV → SQLite   ->   SQL queries   ->   Python script  -> Excel report ->  Power BI
```

## What this project demonstrates

- **Data ingestion** — 128k+ rows loaded from CSV into SQLite via SQLAlchemy
- **SQL transformation** — NPA ratio + risk-band segmentation using CTEs
- **Python orchestration** — single `run_pipeline.py` runs ingest -> SQL -> Excel
- **Scheduling** — APScheduler cron job for monthly auto-runs
- **Reporting** — formatted multi-sheet Excel (navy headers, frozen panes, number formats)
- **Dashboard** — Power BI consuming the Excel output

## Dataset

[Lending Club 2018 Q4 loan data](https://www.kaggle.com/datasets/wordsforthewise/lending-club)
— public, ~128k loan records with default status, grades (A-G), interest rates,
employment, income, state, purpose. Lending Club's `grade` field maps cleanly to
CIBIL-style bureau bands used in Indian retail banking.

> The original guide uses Home Credit Default Risk (Kaggle, gated). Lending Club
> is the same shape of problem on a public mirror — credit applications + default
> labels — so all the regulatory-reporting framing carries over.

## Folder structure

```
regulatory-reporting-pipeline/
├── data/
│   └── LoanStats_2018Q4.csv           # downloaded, gitignored
├── sql/
│   ├── risk_summary.sql               # NPA report by loan type
│   └── segment_report.sql             # risk band segmentation
├── pipeline/
│   ├── ingest.py                      # CSV -> SQLite
│   ├── run_pipeline.py                # main orchestrator
│   └── scheduler.py                   # APScheduler cron
├── output/
│   └── monthly_report_YYYYMM.xlsx     # auto-generated, gitignored
├── powerbi/
│   └── dashboard.pbix
├── assets/                            # screenshots for this README
├── .gitignore
├── README.md
└── requirements.txt
```

## How to run

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/regulatory-reporting-pipeline.git
cd regulatory-reporting-pipeline

# 2. Set up env
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Download dataset
#    https://www.kaggle.com/datasets/wordsforthewise/lending-club
#    Place LoanStats_2018Q4.csv in ./data/

# 4. Run the pipeline
python pipeline/run_pipeline.py

# 5. (Optional) Run the scheduler
python pipeline/scheduler.py
```

## Sample output

After running, `output/monthly_report_YYYYMM.xlsx` contains three sheets:

**Risk_Summary** — default rate and NPA exposure by loan tenor

| loan_type       | total_accounts | defaulted | default_rate_% | exposure_mn | npa_ratio_% |
|-----------------|----------------|-----------|----------------|-------------|-------------|
| Long Term Loan  | 40,233         | 7,124     | 17.71          | 879.93      | 17.78       |
| Short Term Loan | 88,179         | 10,034    | 11.38          | 1,170.98    | 11.91       |

**Risk_Segments** — segmentation by Lending Club grade (CIBIL analogue)

| risk_band   | customers | default_rate_% | exposure_mn | avg_int_rate |
|-------------|-----------|----------------|-------------|--------------|
| High Risk   | 6,450     | 27.60          | 91.55       | 25.50        |
| Medium Risk | 48,090    | 18.65          | 762.95      | 16.73        |
| Low Risk    | 73,872    | 8.68           | 1,196.41    | 9.35         |

The default rate gradient validates that the grade-based segmentation is
statistically meaningful — exactly the kind of check a risk team performs
on bureau-score-derived bands.

## Build progress

- [x] 00 · Setup
- [x] 01 · Data
- [x] 02 · SQL Layer
- [x] 03 · Python Pipeline
- [x] 04 · Automation (scheduler ready)
- [ ] 05 · Power BI dashboard
- [ ] 06 · GitHub & README polish

## Resume bullet

> Built an end-to-end automated regulatory reporting pipeline using Python, SQL,
> and Power BI — covering data ingestion into SQLite, SQL-based NPA and risk-segment
> transformation, APScheduler-based monthly automation, and stakeholder-ready
> formatted Excel + dashboard output on **128k+ Lending Club loan records**.

## Resume keywords

ETL · Automation · DAX · SQL · Python · Power BI · Regulatory Reporting · NPA · Risk Segmentation
