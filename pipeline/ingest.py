"""Load Lending Club CSV into SQLite.

Same idea works against Postgres or Oracle, just change the SQLAlchemy URL.
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


# Statuses we count as defaulted for NPA reporting.
# RBI's strict NPA definition is 90+ days past due, but Lending Club's
# "Late (31-120 days)" bucket overlaps with that. Close enough for a sim.
DEFAULT_STATUSES = {
    "Charged Off",
    "Default",
    "Late (31-120 days)",
}

# Subset of columns we actually need. The full file has ~145, but loading
# all of them takes forever and we don't use most of them.
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
    """Fix the messy types coming out of the raw CSV."""
    # term comes in as " 36 months" / " 60 months". Pull the integer out.
    df["term"] = (
        df["term"].astype(str).str.extract(r"(\d+)").astype("Int64")
    )

    # int_rate is a string like " 23.40%". Strip the % and cast.
    df["int_rate"] = (
        df["int_rate"].astype(str).str.replace("%", "", regex=False).str.strip()
    )
    df["int_rate"] = pd.to_numeric(df["int_rate"], errors="coerce")

    # The CSV ends with two summary rows (no loan_amnt) that aren't real loans.
    # `id` is anonymised in this dump so we can't anchor on it. Use loan_amnt.
    df = df.dropna(subset=["loan_amnt"]).copy()

    # Defaulted = 1, performing = 0. Single number is easier to SUM/AVG later.
    df["TARGET"] = df["loan_status"].isin(DEFAULT_STATUSES).astype(int)

    # Bucket 36mo as short term and 60mo as long term so the report has
    # a more business-friendly grouping than just a number.
    df["contract_type"] = df["term"].map(
        {36: "Short Term Loan", 60: "Long Term Loan"}
    )

    return df


def ingest_data(
    csv_path: str = "data/LoanStats_2018Q4.csv",
    db_path: str = "data/reporting.db",
):
    """Read the CSV, clean it, write to SQLite. Returns the engine."""
    log.info("Ingestion started")

    # First line of the file is the LC prospectus disclaimer, not a header.
    df = pd.read_csv(
        csv_path,
        skiprows=1,
        usecols=REPORTING_COLUMNS,
        low_memory=False,
    )
    log.info(f"Loaded {len(df):,} rows, {df.shape[1]} columns")

    df = _clean(df)
    log.info(f"After cleaning: {len(df):,} rows")

    # Quick null audit so anything weird shows up in the logs.
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        log.info(f"Null counts:\n{nulls}")

    # Stamp the batch with reporting month. Useful when there are
    # multiple monthly snapshots in the same DB (future extension).
    df["REPORT_MONTH"] = datetime.now().strftime("%Y-%m")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    df.to_sql("loan_applications", engine, if_exists="replace", index=False)

    log.info(f"Loaded into {db_path} - table: loan_applications")
    return engine


if __name__ == "__main__":
    ingest_data()
