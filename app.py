import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import math
import streamlit as st
import datetime
import pandas as pd
import joblib
from models.predict import score_todays_fixtures
from config import MODEL_PATH

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="B4Business · Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme tokens (Material Design 3 — tonal color roles + elevation) ──────────
# "Light" (design concept: Matchday — warm pitch-day) and "Dark" (design
# concept: Night Match — stadium-under-lights). Both share the same role
# structure (primary/secondary/tertiary containers, surface tiers, outline)
# so every downstream component only ever references roles, never raw hex —
# swapping THEMES[name] is the entire re-skin.
THEMES = {
    "Light": {
        "mode": "light",
        "primary": "#1B5E3F", "primary_container": "#D7F0DE", "on_primary_container": "#0A3320",
        "secondary": "#C97A0E", "secondary_container": "#FCEACB", "on_secondary_container": "#593F06",
        "tertiary": "#4C5FD1", "tertiary_container": "#E1E4FB", "on_tertiary_container": "#1F2A6B",
        "surface": "#FAFAF7", "surface_container": "#FFFFFF", "surface_container_high": "#F1F3EE",
        "on_surface": "#1A1C1A", "on_surface_variant": "#494A45", "outline": "#E1E4DC",
        "error": "#8C1D18", "error_container": "#F9DEDC",
        "display_font": "'Space Grotesk'", "mono_font": "'Roboto Mono'",
        "shadow_1": "0 1px 2px rgba(20,24,20,0.06), 0 1px 3px rgba(20,24,20,0.08)",
        "shadow_2": "0 2px 6px rgba(20,24,20,0.08), 0 4px 12px rgba(20,24,20,0.06)",
        "card_border": "none", "bg_glow": "none",
    },
    "Dark": {
        "mode": "dark",
        "primary": "#7FE3B4", "primary_container": "#0F3D2B", "on_primary_container": "#A8F5CC",
        "secondary": "#FFC94A", "secondary_container": "#4A3600", "on_secondary_container": "#FFDD8A",
        "tertiary": "#A6B4FF", "tertiary_container": "#2A2F63", "on_tertiary_container": "#C9D1FF",
        "surface": "#0E1210", "surface_container": "#171B18", "surface_container_high": "#1F2420",
        "on_surface": "#E5E8E2", "on_surface_variant": "#9CA39A", "outline": "#2B302B",
        "error": "#FFB4A9", "error_container": "#4A2B22",
        "display_font": "'Sora'", "mono_font": "'JetBrains Mono'",
        "shadow_1": "none", "shadow_2": "none",
        "card_border": "1px solid var(--outline)",
        "bg_glow": "radial-gradient(circle at 20% 0%, rgba(127,227,180,0.06), transparent 40%)",
    },
}

if "theme" not in st.session_state:
    st.session_state.theme = "Light"

# ── Theme + Day toggles ─────────────────────────────────────────────────────
# Wider left column for Day, narrow right column for the Light/Dark toggle —
# CSS below right-aligns its contents so it sits flush top-right.
col_day, col_theme = st.columns([4, 1])
with col_day:
    day_choice = st.radio(
        "Day", ["Today", "Tomorrow"], horizontal=True, label_visibility="collapsed", key="day_toggle"
    )
with col_theme:
    theme_choice = st.radio(
        "Theme", list(THEMES.keys()), horizontal=True, label_visibility="collapsed", key="theme"
    )

T = THEMES[theme_choice]

# ── Global CSS — every rule below references T[...] tokens, never raw hex ────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Sora:wght@500;600;700&family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@500;700&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
    --primary: {T['primary']};
    --primary-container: {T['primary_container']};
    --on-primary-container: {T['on_primary_container']};
    --secondary: {T['secondary']};
    --secondary-container: {T['secondary_container']};
    --on-secondary-container: {T['on_secondary_container']};
    --tertiary: {T['tertiary']};
    --tertiary-container: {T['tertiary_container']};
    --on-tertiary-container: {T['on_tertiary_container']};
    --surface: {T['surface']};
    --surface-container: {T['surface_container']};
    --surface-container-high: {T['surface_container_high']};
    --on-surface: {T['on_surface']};
    --on-surface-variant: {T['on_surface_variant']};
    --outline: {T['outline']};
    --error: {T['error']};
    --error-container: {T['error_container']};
}}

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

/* ── Re-skin Streamlit's own chrome, not just custom divs ───────────────── */
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background: var(--surface);
    background-image: {T['bg_glow']};
}}
.main .block-container {{ max-width: 900px; padding-top: 1.5rem; }}
[data-testid="stMarkdownContainer"] p, .stMarkdown, label, .stCaption {{ color: var(--on-surface); }}
[data-testid="stExpander"] {{
    background: var(--surface-container); border: {T['card_border']}; border-radius: 16px;
    box-shadow: {T['shadow_1']};
}}
hr {{ border-color: var(--outline); }}

/* Segmented-control styling for st.radio (used for Day and Theme toggles) */
[data-testid="stRadio"] > div {{
    background: var(--surface-container-high); border-radius: 999px; padding: 4px;
    display: inline-flex; gap: 2px; border: {T['card_border']};
}}
[data-testid="stRadio"] label {{
    background: transparent; border-radius: 999px; padding: 7px 16px !important;
    transition: all .15s; cursor: pointer;
}}
[data-testid="stRadio"] label:has(input:checked) {{
    background: var(--surface-container); box-shadow: {T['shadow_1']};
}}
[data-testid="stRadio"] label:has(input:checked) p {{ color: var(--primary) !important; font-weight: 700; }}
[data-testid="stRadio"] label p {{ font-family: 'Inter'; font-weight: 600; font-size: 0.85rem; color: var(--on-surface-variant); }}
[data-testid="stRadio"] input {{ display: none; }}
[data-testid="stRadio"] label > div:first-child {{ display: none; }}  /* hide native radio dot */

/* Push the Light/Dark toggle (2nd column in the top row) flush right */
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stRadio"] {{
    display: flex; justify-content: flex-end;
}}

/* Header */
.b4b-header {{ padding: 6px 2px 20px; }}
.b4b-header h1 {{
    font-family: {T['display_font']}; color: var(--on-surface); font-size: 1.8rem;
    font-weight: 700; margin: 4px 0 2px; letter-spacing: -0.01em;
}}
.b4b-header p {{ color: var(--on-surface-variant); font-size: 0.88rem; margin: 0; }}
.b4b-badge {{
    display: inline-flex; align-items: center; gap: 7px;
    background: var(--primary-container); color: var(--on-primary-container);
    font-size: 0.74rem; font-weight: 700; padding: 6px 13px; border-radius: 999px;
}}
.b4b-badge .dot {{ width: 7px; height: 7px; border-radius: 50%; background: var(--primary); }}

/* Stat / KPI cards */
.kpi-row {{ display: flex; gap: 14px; margin-bottom: 24px; }}
.kpi-card {{
    flex: 1; background: var(--surface-container); border: {T['card_border']};
    border-radius: 16px; padding: 18px 20px; box-shadow: {T['shadow_1']};
}}
.kpi-card .val {{ font-family: {T['display_font']}; font-size: 1.9rem; font-weight: 700; color: var(--primary); line-height: 1; }}
.kpi-card .lbl {{ font-size: 0.74rem; color: var(--on-surface-variant); font-weight: 600;
                  text-transform: uppercase; letter-spacing: 0.05em; margin-top: 6px; }}
.kpi-card .sub {{ font-size: 0.74rem; color: var(--on-surface-variant); opacity: .75; margin-top: 2px; }}

/* Pick cards */
.pick-card {{
    background: var(--surface-container); border: {T['card_border']};
    border-radius: 22px; padding: 18px 20px 16px; margin-bottom: 14px;
    box-shadow: {T['shadow_2']}; position: relative; overflow: hidden;
}}
.pick-card.warn::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background: var(--secondary); }}
.pick-card:not(.warn)::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background: var(--primary); }}
.pick-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.pick-card .match {{ font-family: {T['display_font']}; font-size: 1.05rem; font-weight: 600; color: var(--on-surface); }}
.pick-card .meta  {{ font-size: 0.8rem; color: var(--on-surface-variant); margin-top: 4px; }}
.pick-card .meta .odds {{ font-family: {T['mono_font']}; font-weight: 500; }}
.pick-card .pills {{ display: flex; gap: 7px; margin-top: 12px; flex-wrap: wrap; }}

.pill {{ display: inline-block; padding: 6px 12px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; }}
.pill-green  {{ background: var(--primary-container);   color: var(--on-primary-container); }}
.pill-teal   {{ background: var(--primary-container);   color: var(--on-primary-container); }}
.pill-blue   {{ background: var(--secondary-container);  color: var(--on-secondary-container); }}
.pill-purple {{ background: var(--tertiary-container);   color: var(--on-tertiary-container); }}
.pill-gray   {{ background: var(--error-container);      color: var(--error); }}

/* Confidence ring */
.ring {{ width: 46px; height: 46px; flex-shrink: 0; }}
.ring text {{ font-family: {T['mono_font']}; font-weight: 700; font-size: 11px; fill: var(--on-surface); }}

/* Section titles */
.section-title {{
    font-family: {T['display_font']}; font-size: 0.95rem; font-weight: 600;
    color: var(--on-surface); margin: 26px 0 12px;
}}

/* Fixtures table */
.table-card {{
    background: var(--surface-container); border: {T['card_border']}; border-radius: 16px;
    box-shadow: {T['shadow_1']}; overflow: hidden; margin-top: 4px;
}}
.table-scroll {{ max-height: 520px; overflow-y: auto; }}
.b4b-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.b4b-table th {{
    position: sticky; top: 0; text-align: left; font-weight: 600; color: var(--on-surface-variant);
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.03em;
    padding: 12px 14px; border-bottom: 1px solid var(--outline); background: var(--surface-container);
}}
.b4b-table td {{ padding: 10px 14px; border-bottom: 1px solid var(--outline); color: var(--on-surface); }}
.b4b-table tr:last-child td {{ border-bottom: none; }}
.b4b-table tr:hover td {{ background: var(--surface-container-high); }}
.b4b-table td.num {{ font-family: {T['mono_font']}; font-weight: 500; }}

/* Footer */
.b4b-footer {{
    text-align: center; color: var(--on-surface-variant); font-size: 0.75rem;
    margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--outline);
}}
</style>
""", unsafe_allow_html=True)


def confidence_ring(conf_pct: float, high_threshold: float = 60) -> str:
    """Inline SVG ring — Material-style circular confidence indicator."""
    conf_pct = max(0, min(100, conf_pct))
    r = 18
    circumference = 2 * math.pi * r
    offset = circumference * (1 - conf_pct / 100)
    color = "var(--primary)" if conf_pct > high_threshold else "var(--secondary)"
    return f"""<svg class="ring" viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="{r}" stroke="var(--outline)" stroke-width="4" fill="none"/>
      <circle cx="22" cy="22" r="{r}" stroke="{color}" stroke-width="4" fill="none"
              stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}"
              stroke-linecap="round" transform="rotate(-90 22 22)"/>
      <text x="22" y="26" text-anchor="middle">{conf_pct:.0f}%</text>
    </svg>"""


# ── Header ────────────────────────────────────────────────────────────────────
view_date = datetime.date.today() if day_choice == "Today" else datetime.date.today() + datetime.timedelta(days=1)
view_date_str = view_date.strftime("%Y-%m-%d")
today = view_date.strftime("%A, %d %B %Y")

st.markdown(f"""
<div class="b4b-header">
  <div class="b4b-badge"><span class="dot"></span>{"Live" if day_choice == "Today" else "Preview"} · {today}</div>
  <h1>⚽ B4Business Football Analytics</h1>
  <p>Machine-learning predictions for {"today's" if day_choice == "Today" else "tomorrow's"} fixtures · Over 2.5 · Over 0.5 · BTTS · 1X2</p>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading predictions..."):
    try:
        df = score_todays_fixtures(target_date=view_date_str)
    except Exception as e:
        st.error(f"❌ Could not load predictions: {e}")
        st.stop()

if df is None or df.empty:
    if day_choice == "Today":
        st.info("ℹ️ No fixtures found for today. Check back later, or make sure your data pipeline has run.")
    else:
        st.info("ℹ️ Tomorrow's fixtures aren't available yet — they're normally pre-fetched by "
                "the daily pipeline run. Check back after it's run today.")
    st.stop()

# ── Sort control ──────────────────────────────────────────────────────────────
col_sort, col_filter = st.columns([1, 1])
with col_sort:
    sort_by = st.radio(
        "Sort by",
        ["🔥 Highest Confidence", "⏰ Kick-off Time"],
        horizontal=True,
        label_visibility="collapsed",
    )
with col_filter:
    min_prob = st.slider("Min Over 2.5 probability", 0, 100, 0, 5, format="%d%%",
                         label_visibility="collapsed")

# Apply sort & filter
if "Kick-off" in sort_by and "match_time" in df.columns:
    df = df.sort_values("match_time", ascending=True)
else:
    df = df.sort_values("over_2_5_probability", ascending=False)

df_filtered = df[df["over_2_5_probability"] >= min_prob / 100]

# ── KPI row ───────────────────────────────────────────────────────────────────
total     = len(df_filtered)
high_conf = int(df_filtered.get("high_conf_pick", pd.Series([False]*len(df_filtered))).sum()) \
            if "high_conf_pick" in df_filtered.columns else \
            int((df_filtered["over_2_5_probability"] >= 0.62).sum())
avg_o25   = df_filtered["over_2_5_probability"].mean() * 100

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="val">{total}</div>
      <div class="lbl">Fixtures {day_choice}</div>
      <div class="sub">across all tracked leagues</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="val">{high_conf}</div>
      <div class="lbl">High-Confidence Picks</div>
      <div class="sub">≥62% model probability</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="val">{avg_o25:.1f}%</div>
      <div class="lbl">Avg Over 2.5 Probability</div>
      <div class="sub">across the slate</div>
    </div>""", unsafe_allow_html=True)

# ── High-confidence picks ─────────────────────────────────────────────────────
hc_col = "high_conf_pick" if "high_conf_pick" in df_filtered.columns else None
if hc_col:
    df_hc = df_filtered[df_filtered[hc_col] == True]
else:
    df_hc = df_filtered[df_filtered["over_2_5_probability"] >= 0.62]

if not df_hc.empty:
    st.markdown('<div class="section-title">⭐ High-Confidence Selections</div>', unsafe_allow_html=True)
    for _, row in df_hc.iterrows():
        o25   = row["over_2_5_probability"] * 100
        o05   = row.get("over_0_5_probability", float("nan")) * 100
        btts  = row.get("btts_probability", 0) * 100
        hw    = row.get("prob_home_win", 0) * 100
        dw    = row.get("prob_draw", 0) * 100
        aw    = row.get("prob_away_win", 0) * 100
        time_ = row.get("match_time", "—")
        oddsH = row.get("odds_home", 0)
        oddsD = row.get("odds_draw", 0)
        oddsA = row.get("odds_away", 0)
        odds_str = f"{oddsH:.2f} / {oddsD:.2f} / {oddsA:.2f}" if oddsH else "—"
        has_odds = row.get("has_market_odds", True)  # default True for older cached predictions
        conf  = row.get("over25_confidence", abs(row["over_2_5_probability"] - 0.5)) * 200

        st.markdown(f"""
        <div class="pick-card {'warn' if not has_odds else ''}">
          <div class="pick-top">
            <div>
              <div class="match">{row['home_team']} <span style="color:var(--on-surface-variant);font-weight:400">vs</span> {row['away_team']}</div>
              <div class="meta">⏰ {time_} &nbsp;·&nbsp; Odds <span class="odds">{odds_str}</span></div>
            </div>
            {confidence_ring(conf)}
          </div>
          <div class="pills">
            <span class="pill pill-green">Over 2.5 &nbsp; {o25:.1f}%</span>
            {f'<span class="pill pill-teal">Over 0.5 &nbsp; {o05:.1f}%</span>' if o05 == o05 else ''}
            <span class="pill pill-blue">BTTS &nbsp; {btts:.1f}%</span>
            <span class="pill pill-purple">1X2 &nbsp; {hw:.0f}% / {dw:.0f}% / {aw:.0f}%</span>
            {'' if has_odds else '<span class="pill pill-gray">⚠️ No market odds — 1X2 less reliable</span>'}
          </div>
        </div>
        """, unsafe_allow_html=True)

# ── Full fixture table ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 All Fixtures</div>', unsafe_allow_html=True)

table = pd.DataFrame()
table["Time"]      = df_filtered.get("match_time", "—")
table["Home"]      = df_filtered["home_team"]
table["Away"]      = df_filtered["away_team"]
table["Over 2.5"]  = (df_filtered["over_2_5_probability"] * 100).map("{:.1f}%".format)
if "over_0_5_probability" in df_filtered.columns:
    table["Over 0.5"] = (df_filtered["over_0_5_probability"] * 100).map(
        lambda v: "—" if pd.isna(v) else f"{v:.1f}%"
    )
table["BTTS"]      = (df_filtered.get("btts_probability", 0) * 100).map("{:.1f}%".format)
table["1X2 (H/D/A)"] = df_filtered.apply(
    lambda r: f"{r.get('prob_home_win',0)*100:.0f}% / {r.get('prob_draw',0)*100:.0f}% / {r.get('prob_away_win',0)*100:.0f}%",
    axis=1
)
if "odds_home" in df_filtered.columns:
    table["Odds (1/X/2)"] = df_filtered.apply(
        lambda r: f"{r.get('odds_home',0):.2f} / {r.get('odds_draw',0):.2f} / {r.get('odds_away',0):.2f}"
                  if r.get("has_market_odds", True) else "⚠️ Not available",
        axis=1
    )
if hc_col:
    table["⭐"] = df_filtered["high_conf_pick"].map({True: "✅", False: ""})

# Custom HTML table (rather than st.dataframe) so it actually follows the
# theme — Streamlit's native dataframe component has its own fixed internal
# styling that CSS variables can't reach. Wrapped in a scroll container so
# it stays usable with 100+ fixtures, same as st.dataframe would.
def _cell(col, val):
    numeric_cols = {"Over 2.5", "Over 0.5", "BTTS", "1X2 (H/D/A)", "Odds (1/X/2)"}
    cls = ' class="num"' if col in numeric_cols else ""
    return f"<td{cls}>{val}</td>"

rows_html = "".join(
    "<tr>" + "".join(_cell(c, row[c]) for c in table.columns) + "</tr>"
    for _, row in table.iterrows()
)
header_html = "".join(f"<th>{c}</th>" for c in table.columns)
st.markdown(f"""
<div class="table-card"><div class="table-scroll">
<table class="b4b-table"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>
</div></div>
""", unsafe_allow_html=True)

# ── Export ────────────────────────────────────────────────────────────────────
csv_out = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Download predictions (CSV)",
    data=csv_out,
    file_name=f"b4business_{datetime.date.today()}.csv",
    mime="text/csv",
)

# ── Nerd stuff toggle ─────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🤓 Nerd Stuff — Model Details & Confidence Tiers"):

    st.markdown("#### How the model works")
    st.markdown("""
    The prediction engine is a **soft-voting ensemble** of a Random Forest (300 trees)
    and a Logistic Regression, trained on **5,119 finished matches** across 3 seasons
    (Bundesliga, Premier League, La Liga, Serie A, Ligue 1).

    **23 features per match, including:**
    - 🔁 10-game rolling averages: goals scored/conceded, shots on target, corners
    - 📈 Per-team historical Over 2.5 & BTTS rates
    - 💹 Bookmaker-implied probabilities for Over 2.5 (Avg odds + B365)
    - 🏟️ League encoding (some leagues score more than others)
    """)

    st.markdown("#### Confidence-tier accuracy (cross-validated, no data leakage)")
    tier_data = pd.DataFrame({
        "Model confidence": ["≥55%", "≥60%", "≥65%", "≥70%"],
        "Accuracy":         ["61.1%", "64.8%", "68.8%", "72.9%"],
        "% of games":       ["68%", "37%", "18%", "6%"],
        "Games in sample":  ["3,485", "1,891", "908", "329"],
    })
    st.table(tier_data)
    st.caption("Overall CV accuracy: **58.1%** · AUC-ROC: **0.615** · Brier score: **0.24**")

    st.markdown("#### Top feature importances (RF component)")
    feat_imp = pd.DataFrame({
        "Feature":    ["ip_avg_over25", "ip_avg_draw", "ip_b365_over25", "ip_avg_home",
                       "shot_ratio", "comb_shots_ot", "a_roll_corners",
                       "comb_scoring", "h_roll_corners", "h_roll_shots_ot"],
        "Importance": [0.0949, 0.0809, 0.0754, 0.0587,
                       0.0531, 0.0511, 0.0484,
                       0.0458, 0.0445, 0.0432],
    })
    st.bar_chart(feat_imp.set_index("Feature"))

    st.markdown("#### Tech stack")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        | Layer | Tool |
        |---|---|
        | Data store | DuckDB |
        | Feature pipeline | pandas / numpy |
        | Models | scikit-learn |
        | Fixture data | API-Football v3 |
        """)
    with col2:
        st.markdown("""
        | Layer | Tool |
        |---|---|
        | Odds data | The Odds API v4 |
        | Training data | football-data.co.uk CSVs |
        | Dashboard | Streamlit |
        | Deployment | Streamlit Cloud |
        """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="b4b-footer">
  B4Business Football Analytics · Predictions are probabilistic estimates only ·
  Not financial or betting advice
</div>
""", unsafe_allow_html=True)
