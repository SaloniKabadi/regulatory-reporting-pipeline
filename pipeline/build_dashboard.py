"""build_dashboard.py - Generate a self-contained interactive HTML dashboard.

Reads from data/reporting.db (created by ingest.py) and writes
docs/index.html so the dashboard can be served via GitHub Pages.

Dark theme · neon accents · SVG icons · animated counters, particles,
flowing pipeline lines, scanning gradients on cards. No emojis.
"""

import logging
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(REPO_ROOT, "sql")
DB_PATH = os.path.join(REPO_ROOT, "data", "reporting.db")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

TEAL = "#2dd4bf"
EMERALD = "#10b981"
AMBER = "#f59e0b"
RED = "#ef4444"
PURPLE = "#a78bfa"
SLATE = "#64748b"
RISK_COLORS = {"Low Risk": EMERALD, "Medium Risk": AMBER, "High Risk": RED}

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#e2e8f0", size=12),
    title_font=dict(size=14, color="#f1f5f9"),
    margin=dict(l=50, r=30, t=60, b=50),
    xaxis=dict(gridcolor="rgba(148,163,184,0.1)", zerolinecolor="rgba(148,163,184,0.2)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.1)", zerolinecolor="rgba(148,163,184,0.2)"),
    hoverlabel=dict(
        bgcolor="rgba(15,23,42,0.95)",
        bordercolor=TEAL,
        font=dict(color="#f1f5f9", size=12),
    ),
    transition=dict(duration=600, easing="cubic-in-out"),
)

# --- SVG icons (line, 22px viewBox 24) ---
ICON_ACCOUNTS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0Z"/><path d="M3 21v-1a6 6 0 0 1 6-6h6a6 6 0 0 1 6 6v1"/></svg>'
ICON_VAULT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="12" cy="12" r="3.2"/><path d="M12 8.8V12M16 4.5V6M8 4.5V6M16 19.5V21M8 19.5V21"/></svg>'
ICON_ALERT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 21 19.5H3L12 3.5Z"/><path d="M12 10v4M12 17.2v.1"/></svg>'
ICON_TREND_DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m3 7 7 7 4-4 7 7"/><path d="M21 17v-4M21 17h-4"/></svg>'

ICON_INGEST = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>'
ICON_TRANSFORM = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h13l-3-3M20 17H7l3 3"/></svg>'
ICON_AUTOMATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></svg>'
ICON_EXPORT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z"/><path d="M9 13h6M9 17h6M9 9h2"/></svg>'
ICON_DASHBOARD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m7 15 4-6 4 3 5-7"/></svg>'


def _run_sql(engine, sql_path: str) -> pd.DataFrame:
    with open(sql_path, "r") as f:
        query = f.read()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def _kpi_card(label, value, prefix="", suffix="", decimals=0,
              sublabel="", accent=TEAL, icon=""):
    return f"""
    <div class="kpi" style="--accent: {accent}">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value"
           data-target="{value}"
           data-prefix="{prefix}"
           data-suffix="{suffix}"
           data-decimals="{decimals}">{prefix}0{suffix}</div>
      <div class="kpi-sub">{sublabel}</div>
      <div class="kpi-glow"></div>
      <div class="kpi-scan"></div>
    </div>
    """


def _chart_default_by_loan_type(risk, include_js=False):
    fig = go.Figure(go.Bar(
        x=risk["loan_type"], y=risk["default_rate_pct"],
        marker=dict(
            color=risk["default_rate_pct"],
            colorscale=[[0, EMERALD], [0.5, AMBER], [1, RED]],
            line=dict(color="rgba(255,255,255,0.2)", width=1),
        ),
        text=risk["default_rate_pct"].map(lambda v: f"<b>{v:.2f}%</b>"),
        textposition="outside", textfont=dict(color="#f1f5f9", size=14),
        hovertemplate="<b>%{x}</b><br>Default rate: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(title="<b>Default rate by loan tenor</b>",
                      yaxis_title="Default rate (%)", height=380, **DARK_LAYOUT)
    return fig.to_html(full_html=False,
                       include_plotlyjs=("inline" if include_js else False),
                       div_id="chart_default_by_type",
                       config={"displayModeBar": False, "responsive": True})


def _chart_exposure_donut(seg):
    fig = go.Figure(go.Pie(
        labels=seg["risk_band"], values=seg["exposure_mn"], hole=0.65,
        marker=dict(colors=[RISK_COLORS.get(b, SLATE) for b in seg["risk_band"]],
                    line=dict(color="rgba(15,23,42,0.8)", width=3)),
        hovertemplate="<b>%{label}</b><br>Exposure: $%{value:.1f}M<br>%{percent}<extra></extra>",
        textinfo="label+percent", textfont=dict(color="#f1f5f9", size=13),
        pull=[0.04, 0.02, 0], rotation=90,
    ))
    fig.update_layout(
        title="<b>Portfolio exposure by risk band</b>",
        height=380, showlegend=False,
        annotations=[dict(
            text=f"<b>${seg['exposure_mn'].sum():,.0f}M</b><br><span style='font-size:11px;color:#94a3b8'>TOTAL</span>",
            x=0.5, y=0.5, font=dict(size=22, color="#f1f5f9"), showarrow=False,
        )],
        **DARK_LAYOUT,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       div_id="chart_exposure_donut",
                       config={"displayModeBar": False, "responsive": True})


def _chart_default_by_band(seg):
    seg_sorted = seg.sort_values("actual_default_rate")
    fig = go.Figure(go.Bar(
        x=seg_sorted["actual_default_rate"], y=seg_sorted["risk_band"], orientation="h",
        marker=dict(color=[RISK_COLORS.get(b, SLATE) for b in seg_sorted["risk_band"]],
                    line=dict(color="rgba(255,255,255,0.2)", width=1)),
        text=seg_sorted["actual_default_rate"].map(lambda v: f"<b>{v:.1f}%</b>"),
        textposition="outside", textfont=dict(color="#f1f5f9", size=14),
        hovertemplate="<b>%{y}</b><br>Default rate: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(title="<b>Actual default rate by risk band</b>",
                      xaxis_title="Default rate (%)", height=380, **DARK_LAYOUT)
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       div_id="chart_default_by_band",
                       config={"displayModeBar": False, "responsive": True})


def _chart_loan_vs_default(seg):
    fig = go.Figure(go.Scatter(
        x=seg["avg_loan_size"], y=seg["actual_default_rate"], mode="markers+text",
        marker=dict(
            size=seg["customer_count"] / 400,
            color=[RISK_COLORS.get(b, SLATE) for b in seg["risk_band"]],
            line=dict(width=2, color="rgba(255,255,255,0.4)"),
            opacity=0.85, sizemode="diameter", sizemin=20,
        ),
        text=seg["risk_band"], textposition="top center",
        textfont=dict(color="#f1f5f9", size=13),
        hovertemplate=(
            "<b>%{text}</b><br>Avg loan: $%{x:,.0f}<br>"
            "Default rate: %{y:.2f}%<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="<b>Loan size vs default rate (bubble = customer count)</b>",
        xaxis_title="Avg loan size ($)", yaxis_title="Default rate (%)",
        height=420, **DARK_LAYOUT,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       div_id="chart_loan_vs_default",
                       config={"displayModeBar": False, "responsive": True})


def _chart_interest_by_band(seg):
    seg_sorted = seg.sort_values("avg_interest_rate")
    fig = go.Figure(go.Bar(
        x=seg_sorted["risk_band"], y=seg_sorted["avg_interest_rate"],
        marker=dict(color=[RISK_COLORS.get(b, SLATE) for b in seg_sorted["risk_band"]],
                    line=dict(color="rgba(255,255,255,0.2)", width=1)),
        text=seg_sorted["avg_interest_rate"].map(lambda v: f"<b>{v:.2f}%</b>"),
        textposition="outside", textfont=dict(color="#f1f5f9", size=14),
        hovertemplate="<b>%{x}</b><br>Avg rate: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(title="<b>Avg interest rate by risk band — pricing alignment</b>",
                      yaxis_title="Avg interest rate (%)", height=380, **DARK_LAYOUT)
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       div_id="chart_interest_by_band",
                       config={"displayModeBar": False, "responsive": True})


def build():
    if not os.path.exists(DB_PATH):
        log.error(f"Database not found at {DB_PATH}. Run pipeline/run_pipeline.py first.")
        sys.exit(1)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    risk = _run_sql(engine, os.path.join(SQL_DIR, "risk_summary.sql"))
    seg = _run_sql(engine, os.path.join(SQL_DIR, "segment_report.sql"))

    total_accounts = int(risk["total_accounts"].sum())
    total_exposure = float(risk["total_exposure_mn"].sum())
    total_npa = float(risk["npa_exposure_mn"].sum())
    npa_ratio = (total_npa / total_exposure * 100) if total_exposure else 0
    avg_default_rate = float(risk["default_rate_pct"].mean())

    kpis = (
        _kpi_card("Total accounts", total_accounts,
                  sublabel="loans in portfolio", accent=TEAL, icon=ICON_ACCOUNTS)
        + _kpi_card("Total exposure", total_exposure, prefix="$", suffix="M",
                    decimals=0, sublabel="outstanding principal",
                    accent=PURPLE, icon=ICON_VAULT)
        + _kpi_card("NPA ratio", npa_ratio, suffix="%", decimals=2,
                    sublabel="non-performing exposure",
                    accent=AMBER, icon=ICON_ALERT)
        + _kpi_card("Avg default rate", avg_default_rate, suffix="%", decimals=2,
                    sublabel="across loan types",
                    accent=RED, icon=ICON_TREND_DOWN)
    )

    chart_default = _chart_default_by_loan_type(risk, include_js=True)
    chart_donut = _chart_exposure_donut(seg)
    chart_band = _chart_default_by_band(seg)
    chart_scatter = _chart_loan_vs_default(seg)
    chart_interest = _chart_interest_by_band(seg)

    risk_table = risk.to_html(index=False, classes="data-table", border=0, float_format="%.2f")
    seg_table = seg.to_html(index=False, classes="data-table", border=0, float_format="%.2f")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = _render_html(
        kpis=kpis, chart_default=chart_default, chart_donut=chart_donut,
        chart_band=chart_band, chart_scatter=chart_scatter, chart_interest=chart_interest,
        risk_table=risk_table, seg_table=seg_table,
        total_accounts=total_accounts, generated_at=generated_at,
    )

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w") as f:
        f.write(html)
    log.info(f"Dashboard written: {out_path}")


def _render_html(**ctx):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoanLens · Portfolio Risk Console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #050816;
    --card: rgba(15, 23, 42, 0.55);
    --card-border: rgba(45, 212, 191, 0.18);
    --text: #f1f5f9;
    --muted: #94a3b8;
    --teal: #2dd4bf;
    --purple: #a78bfa;
    --amber: #f59e0b;
    --red: #ef4444;
    --green: #10b981;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ height: 100%; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    overflow-x: hidden;
    min-height: 100vh;
    position: relative;
  }}

  /* ===== animated backgrounds ===== */
  body::before {{
    content: "";
    position: fixed; inset: 0;
    background:
      radial-gradient(circle at 15% 20%, rgba(45,212,191,0.14) 0%, transparent 40%),
      radial-gradient(circle at 85% 10%, rgba(167,139,250,0.12) 0%, transparent 40%),
      radial-gradient(circle at 50% 80%, rgba(239,68,68,0.10) 0%, transparent 50%);
    z-index: -3;
    animation: drift 22s ease-in-out infinite;
  }}
  body::after {{
    content: "";
    position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(148,163,184,0.045) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148,163,184,0.045) 1px, transparent 1px);
    background-size: 44px 44px;
    z-index: -2;
    mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    animation: gridShift 18s linear infinite;
  }}
  @keyframes drift {{
    0%, 100% {{ transform: translate(0, 0) scale(1); }}
    50%      {{ transform: translate(2%, -1%) scale(1.05); }}
  }}
  @keyframes gridShift {{
    0%   {{ background-position: 0 0; }}
    100% {{ background-position: 44px 44px; }}
  }}

  /* floating particles canvas-like */
  .particles {{
    position: fixed; inset: 0; z-index: -1; pointer-events: none;
    overflow: hidden;
  }}
  .particle {{
    position: absolute; width: 2px; height: 2px;
    background: var(--teal); border-radius: 50%;
    box-shadow: 0 0 8px var(--teal);
    opacity: 0;
    animation: rise linear infinite;
  }}
  @keyframes rise {{
    0%   {{ transform: translateY(110vh) translateX(0); opacity: 0; }}
    10%  {{ opacity: 0.7; }}
    90%  {{ opacity: 0.4; }}
    100% {{ transform: translateY(-10vh) translateX(40px); opacity: 0; }}
  }}

  /* ===== header ===== */
  header {{
    padding: 56px 48px 24px;
    max-width: 1400px; margin: 0 auto;
    position: relative;
  }}
  .badge {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 14px;
    background: rgba(45, 212, 191, 0.08);
    color: var(--teal);
    border: 1px solid rgba(45, 212, 191, 0.3);
    border-radius: 999px;
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.12em; text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
  }}
  .badge::before {{
    content: ""; width: 6px; height: 6px;
    background: var(--teal); border-radius: 50%;
    box-shadow: 0 0 12px var(--teal);
    animation: pulse 2s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%      {{ opacity: 0.4; transform: scale(0.7); }}
  }}
  h1 {{
    margin-top: 16px;
    font-size: 48px; font-weight: 800;
    letter-spacing: -0.03em; line-height: 1.05;
    background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    opacity: 0; transform: translateY(20px);
    animation: titleIn 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards;
  }}
  h1 .accent {{
    background: linear-gradient(135deg, var(--teal) 0%, var(--purple) 50%, var(--teal) 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s ease-in-out infinite;
  }}
  @keyframes titleIn {{
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes shimmer {{
    0%, 100% {{ background-position: 0% 50%; }}
    50%      {{ background-position: 100% 50%; }}
  }}
  .subtitle {{
    margin-top: 12px;
    color: var(--muted);
    font-size: 15px;
    font-family: 'JetBrains Mono', monospace;
    opacity: 0;
    animation: titleIn 0.9s cubic-bezier(0.16, 1, 0.3, 1) 0.3s forwards;
  }}
  .subtitle .live {{ color: var(--teal); }}
  .blink {{
    display: inline-block; width: 8px; height: 14px;
    background: var(--teal); margin-left: 4px; vertical-align: middle;
    animation: blink 1s steps(2, jump-none) infinite;
  }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}

  /* ===== pipeline flow ===== */
  .pipeline {{
    max-width: 1400px; margin: 36px auto 0;
    padding: 0 48px;
    display: flex; align-items: center; gap: 0;
    flex-wrap: wrap;
  }}
  .pipeline-step {{
    flex: 1; min-width: 150px;
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 16px 18px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
    opacity: 0;
    animation: stepIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }}
  .pipeline-step:nth-child(1) {{ animation-delay: 0.5s; }}
  .pipeline-step:nth-child(3) {{ animation-delay: 0.65s; }}
  .pipeline-step:nth-child(5) {{ animation-delay: 0.80s; }}
  .pipeline-step:nth-child(7) {{ animation-delay: 0.95s; }}
  .pipeline-step:nth-child(9) {{ animation-delay: 1.10s; }}
  @keyframes stepIn {{
    from {{ opacity: 0; transform: translateY(15px) scale(0.95); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  .pipeline-step:hover {{
    transform: translateY(-4px);
    border-color: var(--teal);
    box-shadow: 0 12px 32px rgba(45,212,191,0.18);
  }}
  .pipeline-step .icon {{
    width: 22px; height: 22px;
    color: var(--teal);
    margin-bottom: 8px;
    filter: drop-shadow(0 0 6px rgba(45,212,191,0.5));
  }}
  .pipeline-step .icon svg {{ width: 100%; height: 100%; }}
  .pipeline-step .label {{
    font-size: 11px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.08em;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 2px;
  }}
  .pipeline-step .desc {{
    font-size: 13px; color: var(--text); font-weight: 500;
  }}

  /* flowing dot in arrow */
  .pipeline-arrow {{
    position: relative;
    width: 50px; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(45,212,191,0.4), transparent);
    margin: 0 4px;
  }}
  .pipeline-arrow::before {{
    content: "";
    position: absolute;
    top: 50%; left: 0;
    width: 8px; height: 8px;
    margin-top: -4px;
    background: var(--teal);
    border-radius: 50%;
    box-shadow: 0 0 12px var(--teal), 0 0 24px var(--teal);
    animation: flowDot 2s linear infinite;
  }}
  @keyframes flowDot {{
    0%   {{ left: -4px;  opacity: 0; }}
    10%  {{ opacity: 1; }}
    90%  {{ opacity: 1; }}
    100% {{ left: calc(100% - 4px); opacity: 0; }}
  }}

  /* ===== main ===== */
  main {{ max-width: 1400px; margin: 0 auto; padding: 32px 48px 80px; }}

  /* KPI cards */
  .kpi-row {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;
    margin: 36px 0 40px;
  }}
  .kpi {{
    position: relative;
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 26px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }}
  .kpi:hover {{
    transform: translateY(-6px);
    border-color: var(--accent);
    box-shadow:
      0 20px 50px rgba(0,0,0,0.5),
      0 0 0 1px var(--accent),
      0 0 40px color-mix(in srgb, var(--accent) 30%, transparent);
  }}
  .kpi::before {{
    content: ""; position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    background-size: 200% 100%;
    animation: scanLine 3s ease-in-out infinite;
  }}
  @keyframes scanLine {{
    0%, 100% {{ background-position: 200% 0; }}
    50%      {{ background-position: -200% 0; }}
  }}
  .kpi-glow {{
    position: absolute;
    top: -50%; right: -30%;
    width: 220px; height: 220px;
    background: radial-gradient(circle, var(--accent) 0%, transparent 60%);
    opacity: 0.10;
    border-radius: 50%;
    pointer-events: none;
    transition: opacity 0.4s, transform 0.4s;
  }}
  .kpi:hover .kpi-glow {{
    opacity: 0.22;
    transform: scale(1.2);
  }}
  .kpi-scan {{
    position: absolute; inset: 0;
    background: linear-gradient(110deg, transparent 30%, color-mix(in srgb, var(--accent) 8%, transparent) 50%, transparent 70%);
    transform: translateX(-100%);
    pointer-events: none;
  }}
  .kpi:hover .kpi-scan {{
    animation: shine 1.2s ease-out;
  }}
  @keyframes shine {{
    to {{ transform: translateX(100%); }}
  }}
  .kpi-icon {{
    width: 28px; height: 28px;
    color: var(--accent);
    margin-bottom: 18px;
    filter: drop-shadow(0 0 10px color-mix(in srgb, var(--accent) 50%, transparent));
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }}
  .kpi:hover .kpi-icon {{
    transform: scale(1.15) rotate(-4deg);
  }}
  .kpi-icon svg {{ width: 100%; height: 100%; }}
  .kpi-label {{
    font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.14em;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 14px;
  }}
  .kpi-value {{
    font-size: 38px; font-weight: 700;
    letter-spacing: -0.02em; color: var(--text);
    font-variant-numeric: tabular-nums;
    margin-bottom: 6px;
    background: linear-gradient(135deg, #f1f5f9 0%, color-mix(in srgb, var(--accent) 80%, white) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .kpi-sub {{ font-size: 12px; color: var(--muted); }}

  /* sections */
  section h2 {{
    font-size: 12px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.18em;
    color: var(--teal);
    margin: 44px 0 18px;
    font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; gap: 12px;
  }}
  section h2::before {{
    content: "";
    width: 6px; height: 6px;
    background: var(--teal);
    border-radius: 50%;
    box-shadow: 0 0 12px var(--teal);
    animation: pulse 2s ease-in-out infinite;
  }}
  section h2::after {{
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--card-border), transparent);
  }}

  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .grid-1 {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 14px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    min-height: 410px;
    position: relative;
    overflow: hidden;
  }}
  .card:hover {{
    border-color: rgba(45, 212, 191, 0.4);
    transform: translateY(-3px);
    box-shadow: 0 16px 36px rgba(0,0,0,0.35);
  }}
  .card::before {{
    content: ""; position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(45,212,191,0.04) 0%, transparent 50%);
    pointer-events: none;
  }}
  .plotly-graph-div {{ min-height: 380px !important; }}

  .card.full {{
    grid-column: 1 / -1;
    min-height: 0;
    padding: 26px;
  }}
  .card.full h3 {{
    font-size: 13px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.12em;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
  }}

  /* tables */
  .table-wrap {{ overflow-x: auto; border-radius: 10px; }}
  .data-table {{
    width: 100%; border-collapse: collapse;
    font-size: 13px; font-variant-numeric: tabular-nums;
  }}
  .data-table th {{
    background: rgba(45,212,191,0.06);
    color: var(--teal);
    text-align: left;
    padding: 12px 14px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--card-border);
  }}
  .data-table td {{
    padding: 12px 14px;
    border-bottom: 1px solid rgba(148,163,184,0.08);
    color: var(--text);
    transition: background 0.2s;
  }}
  .data-table tr:last-child td {{ border-bottom: none; }}
  .data-table tr:hover td {{
    background: rgba(45,212,191,0.06);
    color: #f1f5f9;
  }}

  footer {{
    text-align: center;
    padding: 40px 24px;
    color: var(--muted);
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    border-top: 1px solid var(--card-border);
    margin-top: 40px;
  }}
  footer a {{
    color: var(--teal);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s;
  }}
  footer a:hover {{ border-color: var(--teal); }}

  /* fade-in for cards */
  .reveal {{ opacity: 0; transform: translateY(24px); transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1), transform 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
  .reveal.in {{ opacity: 1; transform: translateY(0); }}

  @media (max-width: 1000px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; }}
    .pipeline {{ flex-direction: column; align-items: stretch; }}
    .pipeline-arrow {{ width: 100%; height: 24px;
      background: linear-gradient(180deg, transparent, rgba(45,212,191,0.4), transparent); }}
    .pipeline-arrow::before {{ animation: flowDotV 2s linear infinite; left: 50%; margin-left: -4px; top: 0; }}
    @keyframes flowDotV {{
      0%   {{ top: -4px; opacity: 0; }}
      10%  {{ opacity: 1; }}
      90%  {{ opacity: 1; }}
      100% {{ top: 100%; opacity: 0; }}
    }}
    h1 {{ font-size: 34px; }}
    main, header {{ padding-left: 24px; padding-right: 24px; }}
    .pipeline {{ padding: 0 24px; }}
  }}
</style>
</head>
<body>

<!-- floating particles -->
<div class="particles" id="particles"></div>

<header>
  <span class="badge">LOANLENS · v1.0</span>
  <h1>Portfolio Risk<br><span class="accent">Console</span></h1>
  <p class="subtitle">
    A live regulatory-reporting view of <span class="live">{ctx['total_accounts']:,}</span>
    Lending Club loans · auto-refreshed <span class="live">{ctx['generated_at']}</span><span class="blink"></span>
  </p>
</header>

<div class="pipeline">
  <div class="pipeline-step"><div class="icon">{ICON_INGEST}</div><div class="label">Ingest</div><div class="desc">CSV → SQLite</div></div>
  <div class="pipeline-arrow"></div>
  <div class="pipeline-step"><div class="icon">{ICON_TRANSFORM}</div><div class="label">Transform</div><div class="desc">SQL queries</div></div>
  <div class="pipeline-arrow"></div>
  <div class="pipeline-step"><div class="icon">{ICON_AUTOMATE}</div><div class="label">Automate</div><div class="desc">Python + cron</div></div>
  <div class="pipeline-arrow"></div>
  <div class="pipeline-step"><div class="icon">{ICON_EXPORT}</div><div class="label">Export</div><div class="desc">Excel report</div></div>
  <div class="pipeline-arrow"></div>
  <div class="pipeline-step"><div class="icon">{ICON_DASHBOARD}</div><div class="label">Dashboard</div><div class="desc">This page</div></div>
</div>

<main>
  <div class="kpi-row">
    {ctx['kpis']}
  </div>

  <section>
    <h2>Portfolio Overview</h2>
    <div class="grid-2">
      <div class="card reveal">{ctx['chart_default']}</div>
      <div class="card reveal">{ctx['chart_donut']}</div>
    </div>
    <div class="card full reveal">
      <h3>Risk summary by loan type</h3>
      <div class="table-wrap">{ctx['risk_table']}</div>
    </div>
  </section>

  <section>
    <h2>Risk Segment Deep Dive</h2>
    <div class="grid-2">
      <div class="card reveal">{ctx['chart_band']}</div>
      <div class="card reveal">{ctx['chart_interest']}</div>
    </div>
    <div class="grid-1">
      <div class="card reveal">{ctx['chart_scatter']}</div>
    </div>
    <div class="card full reveal">
      <h3>Risk band breakdown</h3>
      <div class="table-wrap">{ctx['seg_table']}</div>
    </div>
  </section>
</main>

<footer>
  Pipeline: CSV → SQLite → SQL → Python → Excel → Dashboard ·
  <a href="https://github.com/SaloniKabadi/regulatory-reporting-pipeline" target="_blank">view source on GitHub</a>
</footer>

<script>
  // ----- floating particles -----
  (function () {{
    const container = document.getElementById('particles');
    const N = 22;
    for (let i = 0; i < N; i++) {{
      const p = document.createElement('div');
      p.className = 'particle';
      p.style.left = Math.random() * 100 + 'vw';
      p.style.animationDuration = (10 + Math.random() * 14) + 's';
      p.style.animationDelay = (Math.random() * -20) + 's';
      const size = 1 + Math.random() * 2.5;
      p.style.width = size + 'px';
      p.style.height = size + 'px';
      p.style.opacity = (0.3 + Math.random() * 0.5);
      container.appendChild(p);
    }}
  }})();

  // ----- count-up KPIs -----
  function animateValue(el) {{
    const target = parseFloat(el.dataset.target);
    const decimals = parseInt(el.dataset.decimals || "0");
    const prefix = el.dataset.prefix || "";
    const suffix = el.dataset.suffix || "";
    const duration = 1600;
    const start = performance.now();
    function easeOut(t) {{ return 1 - Math.pow(1 - t, 3); }}
    function step(now) {{
      const t = Math.min((now - start) / duration, 1);
      const v = target * easeOut(t);
      el.textContent = prefix + (decimals > 0 ? v.toFixed(decimals) : Math.floor(v).toLocaleString()) + suffix;
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = prefix + (decimals > 0 ? target.toFixed(decimals) : target.toLocaleString()) + suffix;
    }}
    requestAnimationFrame(step);
  }}

  // ----- reveal-on-scroll + count-up trigger -----
  const obs = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        entry.target.classList.add('in');
        const kpi = entry.target.querySelector('.kpi-value[data-target]');
        if (kpi && !kpi.dataset.animated) {{
          kpi.dataset.animated = "1";
          animateValue(kpi);
        }}
        obs.unobserve(entry.target);
      }}
    }});
  }}, {{ threshold: 0.15 }});

  document.querySelectorAll('.kpi, .card').forEach(el => {{
    el.classList.add('reveal');
    obs.observe(el);
  }});

  // ----- subtle parallax tilt on KPIs -----
  document.querySelectorAll('.kpi').forEach(card => {{
    card.addEventListener('mousemove', (e) => {{
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `translateY(-6px) rotateX(${{-y * 4}}deg) rotateY(${{x * 6}}deg)`;
    }});
    card.addEventListener('mouseleave', () => {{
      card.style.transform = '';
    }});
  }});
</script>

</body>
</html>
"""


if __name__ == "__main__":
    build()
