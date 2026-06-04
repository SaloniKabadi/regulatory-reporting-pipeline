"""build_dashboard.py - Generate a self-contained interactive HTML dashboard.

Reads from data/reporting.db (created by ingest.py) and writes
docs/index.html so the dashboard can be served via GitHub Pages.

The dashboard mirrors the structure described in the Power BI step of the
guide: KPI cards on top, then charts for portfolio default rate, risk-band
exposure, and a scatter of avg loan size vs default rate.
"""

import logging
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s"
)
log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(REPO_ROOT, "sql")
DB_PATH = os.path.join(REPO_ROOT, "data", "reporting.db")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

# Bank-y palette: navy / teal / amber / red — same vibe as the Excel headers.
NAVY = "#1e3a5f"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
RED = "#ef4444"
GREEN = "#10b981"
SLATE = "#64748b"
RISK_COLORS = {"Low Risk": GREEN, "Medium Risk": AMBER, "High Risk": RED}


def _run_sql(engine, sql_path: str) -> pd.DataFrame:
    with open(sql_path, "r") as f:
        query = f.read()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def _kpi_card(label: str, value: str, sublabel: str = "") -> str:
    return f"""
    <div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sublabel}</div>
    </div>
    """


def _chart_default_by_loan_type(risk: pd.DataFrame) -> str:
    fig = go.Figure(
        go.Bar(
            x=risk["loan_type"],
            y=risk["default_rate_pct"],
            marker_color=[NAVY, TEAL],
            text=risk["default_rate_pct"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Default rate: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Default rate by loan tenor",
        yaxis_title="Default rate (%)",
        xaxis_title="",
        template="plotly_white",
        height=380,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart_default_by_type")


def _chart_exposure_donut(seg: pd.DataFrame) -> str:
    fig = go.Figure(
        go.Pie(
            labels=seg["risk_band"],
            values=seg["exposure_mn"],
            hole=0.55,
            marker=dict(colors=[RISK_COLORS.get(b, SLATE) for b in seg["risk_band"]]),
            hovertemplate="<b>%{label}</b><br>Exposure: $%{value:.1f}M<br>%{percent}<extra></extra>",
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        title="Portfolio exposure by risk band",
        template="plotly_white",
        height=380,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart_exposure_donut")


def _chart_default_by_band(seg: pd.DataFrame) -> str:
    seg_sorted = seg.sort_values("actual_default_rate")
    fig = go.Figure(
        go.Bar(
            x=seg_sorted["actual_default_rate"],
            y=seg_sorted["risk_band"],
            orientation="h",
            marker_color=[RISK_COLORS.get(b, SLATE) for b in seg_sorted["risk_band"]],
            text=seg_sorted["actual_default_rate"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Default rate: %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Actual default rate by risk band",
        xaxis_title="Default rate (%)",
        yaxis_title="",
        template="plotly_white",
        height=380,
        margin=dict(l=80, r=40, t=60, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart_default_by_band")


def _chart_loan_vs_default(seg: pd.DataFrame) -> str:
    fig = go.Figure(
        go.Scatter(
            x=seg["avg_loan_size"],
            y=seg["actual_default_rate"],
            mode="markers+text",
            marker=dict(
                size=seg["customer_count"] / 500,
                color=[RISK_COLORS.get(b, SLATE) for b in seg["risk_band"]],
                line=dict(width=2, color="white"),
            ),
            text=seg["risk_band"],
            textposition="top center",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Avg loan: $%{x:,.0f}<br>"
                "Default rate: %{y:.2f}%<br>"
                "Customers: %{marker.size:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Avg loan size vs default rate (bubble = customer count)",
        xaxis_title="Avg loan size ($)",
        yaxis_title="Default rate (%)",
        template="plotly_white",
        height=420,
        margin=dict(l=60, r=40, t=60, b=50),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="chart_loan_vs_default")


def build():
    if not os.path.exists(DB_PATH):
        log.error(f"Database not found at {DB_PATH}. Run pipeline/run_pipeline.py first.")
        sys.exit(1)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    risk = _run_sql(engine, os.path.join(SQL_DIR, "risk_summary.sql"))
    seg = _run_sql(engine, os.path.join(SQL_DIR, "segment_report.sql"))

    with engine.connect() as conn:
        total_rows = conn.execute(text("SELECT COUNT(*) FROM loan_applications")).scalar()

    # KPI numbers
    total_accounts = int(risk["total_accounts"].sum())
    total_exposure = float(risk["total_exposure_mn"].sum())
    total_npa = float(risk["npa_exposure_mn"].sum())
    npa_ratio = (total_npa / total_exposure * 100) if total_exposure else 0
    avg_default_rate = float(risk["default_rate_pct"].mean())

    kpis = (
        _kpi_card("Total accounts", f"{total_accounts:,}", "loans in portfolio")
        + _kpi_card("Total exposure", f"${total_exposure:,.0f}M", "outstanding principal")
        + _kpi_card("NPA ratio", f"{npa_ratio:.2f}%", "non-performing exposure")
        + _kpi_card("Avg default rate", f"{avg_default_rate:.2f}%", "across loan types")
    )

    chart_default = _chart_default_by_loan_type(risk)
    chart_donut = _chart_exposure_donut(seg)
    chart_band = _chart_default_by_band(seg)
    chart_scatter = _chart_loan_vs_default(seg)

    # Tables — render the raw data so the dashboard tells the same story as Excel
    risk_table = risk.to_html(index=False, classes="data-table", border=0, float_format="%.2f")
    seg_table = seg.to_html(index=False, classes="data-table", border=0, float_format="%.2f")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Regulatory Reporting Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --navy: {NAVY};
    --teal: {TEAL};
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #0f172a;
    --muted: #64748b;
    --border: #e2e8f0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
  }}
  header {{
    background: var(--navy);
    color: white;
    padding: 28px 40px;
  }}
  header h1 {{
    margin: 0 0 4px 0;
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }}
  header p {{
    margin: 0;
    opacity: 0.75;
    font-size: 13px;
  }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    background: rgba(45, 212, 191, 0.18);
    color: var(--teal);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  main {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 32px 40px 60px;
  }}
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
  }}
  .kpi-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 8px;
  }}
  .kpi-value {{
    font-size: 28px;
    font-weight: 600;
    color: var(--navy);
    margin-bottom: 4px;
  }}
  .kpi-sub {{
    font-size: 12px;
    color: var(--muted);
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px;
  }}
  .card.full {{ grid-column: 1 / -1; }}
  section h2 {{
    font-size: 15px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin: 28px 0 12px 0;
  }}
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  .data-table th {{
    background: var(--navy);
    color: white;
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
  }}
  .data-table td {{
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
  }}
  .data-table tr:hover td {{ background: #f1f5f9; }}
  footer {{
    text-align: center;
    padding: 24px;
    color: var(--muted);
    font-size: 12px;
  }}
  footer a {{ color: var(--navy); }}
  @media (max-width: 900px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; }}
    main {{ padding: 24px 20px 40px; }}
    header {{ padding: 24px 20px; }}
  }}
</style>
</head>
<body>
<header>
  <span class="badge">PROJECT_01 · DATA PIPELINE</span>
  <h1>Automated Regulatory Reporting Pipeline</h1>
  <p>Lending Club 2018 Q4 · {total_accounts:,} loan records · generated {generated_at}</p>
</header>

<main>
  <div class="kpi-row">
    {kpis}
  </div>

  <section>
    <h2>Portfolio Overview</h2>
    <div class="grid-2">
      <div class="card">{chart_default}</div>
      <div class="card">{chart_donut}</div>
    </div>
    <div class="card full" style="padding: 16px;">
      <h3 style="margin: 4px 0 12px 0; font-size: 14px;">Risk summary by loan type</h3>
      {risk_table}
    </div>
  </section>

  <section>
    <h2>Risk Segment Deep Dive</h2>
    <div class="grid-2">
      <div class="card">{chart_band}</div>
      <div class="card">{chart_scatter}</div>
    </div>
    <div class="card full" style="padding: 16px;">
      <h3 style="margin: 4px 0 12px 0; font-size: 14px;">Risk band breakdown</h3>
      {seg_table}
    </div>
  </section>
</main>

<footer>
  <strong>Pipeline:</strong> CSV → SQLite → SQL → Python → Excel → Dashboard ·
  <a href="https://github.com/SaloniKabadi/regulatory-reporting-pipeline">View source on GitHub</a>
</footer>
</body>
</html>
"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w") as f:
        f.write(html)

    log.info(f"Dashboard written: {out_path}")
    log.info(f"Open with: open {out_path}")


if __name__ == "__main__":
    build()
