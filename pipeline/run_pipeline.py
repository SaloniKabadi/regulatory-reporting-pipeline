"""run_pipeline.py - Main orchestrator.

Calls ingest -> runs SQL reports -> exports formatted multi-sheet Excel.
Same pattern banks use for month-end regulatory reporting.
"""

import logging
import os
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import text

# Allow imports from the pipeline/ folder when run from repo root or from inside it.
sys.path.append(os.path.dirname(__file__))
from ingest import ingest_data  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)
log = logging.getLogger(__name__)

# Paths are relative to repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(REPO_ROOT, "sql")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")
DATA_CSV = os.path.join(REPO_ROOT, "data", "LoanStats_2018Q4.csv")


def run_sql_file(engine, sql_path: str) -> pd.DataFrame:
    """Read a .sql file and execute it, returning a DataFrame."""
    with open(sql_path, "r") as f:
        query = f.read()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def export_to_excel(dfs: dict, output_path: str) -> None:
    """Write multiple DataFrames to a formatted Excel - each as a separate sheet."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        wb = writer.book

        hdr = wb.add_format(
            {
                "bold": True,
                "bg_color": "#1e3a5f",
                "font_color": "#ffffff",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        num_fmt = wb.add_format({"num_format": "#,##0.00"})

        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]

            for col_idx, col_name in enumerate(df.columns):
                ws.write(0, col_idx, col_name, hdr)
                # Auto-width based on header length, with a sensible minimum
                width = max(len(str(col_name)) + 4, 18)
                # Apply number format to numeric columns only
                if pd.api.types.is_numeric_dtype(df[col_name]):
                    ws.set_column(col_idx, col_idx, width, num_fmt)
                else:
                    ws.set_column(col_idx, col_idx, width)

            ws.freeze_panes(1, 0)  # Lock the header row when scrolling

    log.info(f"Report saved: {output_path}")


def main():
    log.info("======= PIPELINE START =======")

    # 1. Ingest
    engine = ingest_data(csv_path=DATA_CSV)

    # Total rows for the metadata sheet
    with engine.connect() as conn:
        total_rows = conn.execute(
            text("SELECT COUNT(*) FROM loan_applications")
        ).scalar()

    # 2. Run SQL reports
    reports = {
        "Risk_Summary": run_sql_file(engine, os.path.join(SQL_DIR, "risk_summary.sql")),
        "Risk_Segments": run_sql_file(
            engine, os.path.join(SQL_DIR, "segment_report.sql")
        ),
        "Metadata": pd.DataFrame(
            [
                {
                    "report_run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "report_month": datetime.now().strftime("%B %Y"),
                    "pipeline_version": "1.0.0",
                    "source_table": "loan_applications",
                    "source_dataset": "Lending Club 2018 Q4",
                    "rows_processed": total_rows,
                }
            ]
        ),
    }

    # 3. Export
    fname = os.path.join(
        OUTPUT_DIR, f"monthly_report_{datetime.now():%Y%m}.xlsx"
    )
    export_to_excel(reports, fname)

    log.info("======= PIPELINE COMPLETE =======")


if __name__ == "__main__":
    main()
