# LoanLens — Portfolio Risk Console

A small ETL + reporting project I built to mimic what a bank's regulatory
reporting team actually does each month-end. It ingests raw loan data,
runs SQL transforms, exports a formatted Excel for stakeholders, and serves
an interactive dashboard for anyone who'd rather click than open Excel.

**Live dashboard:** https://salonikabadi.github.io/regulatory-reporting-pipeline/

**Stack:** Python 3.9 · SQLAlchemy · pandas · SQLite · APScheduler · XlsxWriter · Plotly

---

## Why this project

I wanted to put together something that wasn't just a notebook with a
pandas tutorial in it. Banks (and any regulated lender, really) run the
same loop every month: pull the latest data, recompute the same handful
of metrics, format the result, send it to the regulator and senior
management. The interesting parts are the parts you don't get from a
DataCamp course — column quirks in real CSVs, scheduling, making the
output look professional, designing SQL that maps cleanly to a
regulatory definition like NPA.

So I rebuilt that loop end-to-end on public Lending Club data
(128k loans from 2018 Q4) and tried to keep the architecture honest:
SQLAlchemy so the same Python works against Postgres in production,
SQL files on disk so a SQL-only analyst can read or edit them without
touching Python, APScheduler for the cron piece.

---

## What it does

```
   INGEST            TRANSFORM          AUTOMATE         EXPORT           DASHBOARD
CSV → SQLite   ->   SQL queries   ->   Python script  -> Excel report ->  Plotly HTML
```

1. `ingest.py` reads the raw LC csv, cleans the obvious type issues
   (interest rates as `" 23.40%"` strings, term as `" 36 months"`),
   maps `loan_status` to a defaulted flag, writes to SQLite.
2. Two SQL files do the actual analytics. `risk_summary.sql` produces an
   NPA-style summary by tenor, `segment_report.sql` does a risk-band cut
   based on LC grade.
3. `run_pipeline.py` orchestrates ingest → SQL → Excel. The Excel has
   navy headers, frozen panes, three sheets (summary, segments,
   metadata).
4. `scheduler.py` is an APScheduler cron set to fire on the 1st of every
   month at 06:00.
5. `build_dashboard.py` renders an interactive HTML dashboard from the
   same SQLite file. It's published via GitHub Pages and rebuilds
   whenever I push.

---

## Sample output

Numbers from my last run on the 2018 Q4 file (128,412 loans):

| loan tenor      | accounts | defaulted | default rate | exposure | NPA ratio |
|-----------------|---------:|----------:|-------------:|---------:|----------:|
| Long Term Loan  |   40,233 |     7,124 |       17.71% | $880M    |    17.78% |
| Short Term Loan |   88,179 |    10,034 |       11.38% | $1,171M  |    11.91% |

Long-tenor loans default at roughly 1.5x the rate of short-tenor — the
classic relationship you'd expect a credit risk team to surface and
explain.

| risk band   | customers | default rate | avg loan | avg rate |
|-------------|----------:|-------------:|---------:|---------:|
| High Risk   |     6,450 |       27.60% |  $14,193 |   25.50% |
| Medium Risk |    48,090 |       18.65% |  $15,865 |   16.73% |
| Low Risk    |    73,872 |        8.68% |  $16,196 |    9.35% |

The default-rate gradient validates the grade-based bands as a useful
risk signal — exactly the sanity check a risk team would run before
trusting the grade for pricing or capital allocation.

---

## Folder layout

```
regulatory-reporting-pipeline/
├── data/
│   └── LoanStats_2018Q4.csv         # gitignored, ~99MB
├── sql/
│   ├── risk_summary.sql             # NPA cut by loan type
│   └── segment_report.sql           # risk-band cut by grade
├── pipeline/
│   ├── ingest.py
│   ├── run_pipeline.py              # main entry point
│   ├── build_dashboard.py           # writes docs/index.html
│   └── scheduler.py
├── output/
│   ├── monthly_report_YYYYMM.xlsx   # archived, gitignored
│   └── monthly_report_latest.xlsx   # stable filename for BI consumers
├── docs/
│   └── index.html                   # what GitHub Pages serves
├── README.md
├── requirements.txt
└── .gitignore
```

---

## How to run it locally

```bash
git clone https://github.com/SaloniKabadi/regulatory-reporting-pipeline.git
cd regulatory-reporting-pipeline

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# grab the dataset (Kaggle account required, ~22MB zip)
# https://www.kaggle.com/datasets/wordsforthewise/lending-club
# unzip LoanStats_2018Q4.csv into ./data/

python pipeline/run_pipeline.py       # produces output/*.xlsx + reporting.db
python pipeline/build_dashboard.py    # produces docs/index.html
open docs/index.html                  # macOS, or just double-click
```

To start the scheduler instead:

```bash
python pipeline/scheduler.py
```

---

## Things I'd add next

- Proper unit tests around the cleaning logic in `ingest.py`. Right now
  I've eyeballed the outputs but I'd want pytest fixtures over a small
  sample CSV before I'd trust this in any real environment.
- A `delta` table so consecutive monthly snapshots stack instead of
  overwriting. Useful for trend analysis.
- Swap SQLite for Postgres in a docker-compose so the connection-string
  story isn't just hypothetical.
- Email the formatted xlsx via SMTP after each run.

---

## Notes / honest disclaimers

- LC's `id` column is anonymised in this 2018 file, so I anchor the
  dropna on `loan_amnt` instead. Two summary rows at the bottom of the
  CSV get filtered out as a side effect.
- The "NPA" framing maps roughly onto LC's late-payment buckets but
  isn't a strict RBI definition. On real bank data you'd derive NPA
  from days-past-due directly.
- The dashboard is Plotly-on-GitHub-Pages, not Power BI. Same idea,
  different tooling. I went this route so the dashboard is reachable
  by anyone with a browser, no Microsoft licence required.
