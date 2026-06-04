# LoanLens — Portfolio Risk Console

A small ETL and reporting project I put together to mimic what a bank's
regulatory reporting team actually does each month-end. It pulls raw
loan data into SQLite, runs SQL transforms, exports a formatted Excel
for stakeholders, and serves an interactive dashboard for anyone who'd
rather click than open Excel.

**Live dashboard:** https://salonikabadi.github.io/regulatory-reporting-pipeline/

**Stack:** Python 3.9, SQLAlchemy, pandas, SQLite, APScheduler, XlsxWriter, Plotly.

---

## Why I built this

Most of my Python/SQL practice has been in notebooks, which is fine for
learning but doesn't really resemble what regulated lenders do day to
day. Banks run roughly the same loop every month: pull the latest data,
recompute the same handful of metrics, format the result, ship it to
the regulator and senior management.

The interesting parts of that loop aren't in tutorials. Real CSVs have
weird column quirks. The scheduler matters. Excel formatting matters
more than you'd think. And the SQL has to map cleanly onto a regulatory
definition (NPA, in this case), not just compute "something useful".

So I rebuilt the loop end-to-end on public Lending Club data (128k
loans from 2018 Q4). I tried to keep the architecture realistic enough
that the same code could move to production without much rework:
SQLAlchemy so the same Python works against Postgres, SQL files on
disk so a SQL-only analyst can read or change them without touching
Python, APScheduler for the cron piece.

---

## What it does

```
   INGEST            TRANSFORM          AUTOMATE         EXPORT          DASHBOARD
CSV  →  SQLite  →   SQL queries  →   Python script  →  Excel report  →  Plotly HTML
```

1. `ingest.py` reads the raw LC csv, fixes the obvious type mess
   (interest rates as `" 23.40%"` strings, term as `" 36 months"`),
   maps `loan_status` to a defaulted flag, and writes to SQLite.
2. Two SQL files do the actual analytics. `risk_summary.sql` produces
   an NPA-style summary by tenor, `segment_report.sql` does a
   risk-band cut by LC grade.
3. `run_pipeline.py` is the orchestrator. Ingest, then SQL, then
   Excel. The Excel has navy headers, frozen panes, three sheets
   (summary, segments, metadata).
4. `scheduler.py` is an APScheduler cron set to fire on the 1st of
   every month at 06:00.
5. `build_dashboard.py` renders an interactive HTML dashboard from
   the same SQLite file. Published via GitHub Pages so the link works
   for anyone.

---

## Sample output

Numbers from a recent run on the 2018 Q4 file (128,412 loans):

| loan tenor      | accounts | defaulted | default rate | exposure | NPA ratio |
|-----------------|---------:|----------:|-------------:|---------:|----------:|
| Long Term Loan  |   40,233 |     7,124 |       17.71% | $880M    |    17.78% |
| Short Term Loan |   88,179 |    10,034 |       11.38% | $1,171M  |    11.91% |

Long-tenor loans default at about 1.5x the rate of short-tenor. The
usual relationship, but worth confirming on your own data before you
quote it to anyone.

| risk band   | customers | default rate | avg loan | avg rate |
|-------------|----------:|-------------:|---------:|---------:|
| High Risk   |     6,450 |       27.60% |  $14,193 |   25.50% |
| Medium Risk |    48,090 |       18.65% |  $15,865 |   16.73% |
| Low Risk    |    73,872 |        8.68% |  $16,196 |    9.35% |

The default-rate gradient lines up with the grade-based bands, which
is the kind of basic check you'd run before trusting the grade for
anything downstream.

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

## Running it locally

```bash
git clone https://github.com/SaloniKabadi/regulatory-reporting-pipeline.git
cd regulatory-reporting-pipeline

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Grab the dataset (Kaggle account required, ~22MB zip)
# https://www.kaggle.com/datasets/wordsforthewise/lending-club
# Unzip LoanStats_2018Q4.csv into ./data/

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

- Proper pytest coverage around the cleaning logic in `ingest.py`.
  Right now I've eyeballed the outputs and that's not enough for
  anything real.
- A `delta` table so consecutive monthly snapshots stack instead of
  overwriting. Useful for trend analysis.
- Swap SQLite for Postgres in a docker-compose so the
  connection-string story isn't just hypothetical.
- Email the formatted xlsx via SMTP after each run.

---

## Notes and honest disclaimers

- LC's `id` column is anonymised in the 2018 file, so I anchor the
  dropna on `loan_amnt` instead. Two summary rows at the bottom of
  the CSV get filtered out as a side effect.
- The "NPA" framing maps roughly onto LC's late-payment buckets but
  isn't a strict RBI definition. On real bank data you'd derive NPA
  straight from days-past-due.
- The dashboard is Plotly on GitHub Pages, not Power BI. Same idea,
  different tooling. I went this route so the dashboard is reachable
  by anyone with a browser, no Microsoft licence required.
