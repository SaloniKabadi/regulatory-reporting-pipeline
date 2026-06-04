"""ingest.py — Load Lending Club CSV into SQLite.

Mirrors a bank ETL ingest layer: same logic against Oracle/Postgres in production,
just swap the SQLAlchemy connection string.
"""

import logging
import os
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


# Loan statuses we treat as "defaulted" for regulatory NPA reporting.
# Charged Off + 31+ days late mirrors the RBI 90-day NPA definition closely enough
# for a public-data simulation.
DEFAULT_STATUSES = {
    "Charged Off",
    "Default",
    "Late (31-120 days)",
}

# Reporting-relevant columns only. Lending Club ships ~145 columns; we keep
# the ones a risk team actually uses, exactly like a real ETL would.
REPORTING_COLUMNS = [
    "id",
    "loan_amnt",
    "funded_amnt",
    "term",
    "int_rate",
    "installment",
    "grade",
    "sub_grade",
    "emp_length",
    "home_ownership",
    "annual_inc",
    "verification_status",
    "issue_d",
    "loan_status",
    "purpose",
    "addr_state",
    "dti",
]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize messy Lending Club fields into analysis-ready types."""
    # term: " 36 months" -> 36
    df["term"] = (
        df["term"].astype(str).str.extract(r"(\d+)").astype("Int64")
    )

    # int_rate: " 23.40%" -> 23.40
    df["int_rate"] = (
        df["int_rate"].astype(str).str.replace("%", "", regex=False).str.strip()
    )
    df["int_rate"] = pd.to_numeric(df["int_rate"], errors="coerce")

    # Drop the prospectus footer rows (the last 2 rows are total-funded summaries
    # and have no loan_amnt). Lending Club anonymizes `id` so we anchor on loan_amnt.
    df = df.dropna(subset=["loan_amnt"]).copy()

    # TARGET flag: 1 = defaulted, 0 = performing.
    df["TARGET"] = df["loan_status"].isin(DEFAULT_STATUSES).astype(int)

    # contract_type: bucket term into "Short Term" / "Long Term" so the
    # report reads like the Home Credit "NAME_CONTRACT_TYPE" split.
    df["contract_type"] = df["term"].map(
        {36: "Short Term Loan", 60: "Long Term Loan"}
    )

    return df


def ingest_data(
    csv_path: str = "data/LoanStats_2018Q4.csv",
    db_path: str = "data/reporting.db",
):
    """Load CSV -> SQLite. Returns the SQLAlchemy engine for downstream use."""
    log.info("Ingestion started")

    # skiprows=1 skips the Lending Club prospectus disclaimer line.
    df = pd.read_csv(
        csv_path,
        skiprows=1,
        usecols=REPORTING_COLUMNS,
        low_memory=False,
    )
    log.info(f"Loaded {len(df):,} rows, {df.shape[1]} columns")

    df = _clean(df)
    log.info(f"After cleaning: {len(df):,} rows")

    # Data-quality snapshot: log any columns with nulls
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        log.info(f"Null counts:\n{nulls}")

    # Tag the batch with reporting month — simulates a monthly run
    df["REPORT_MONTH"] = datetime.now().strftime("%Y-%m")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    df.to_sql("loan_applications", engine, if_exists="replace", index=False)

    log.info(f"Loaded into {db_path} - table: loan_applications")
    return engine


if __name__ == "__main__":
    ingest_data()
