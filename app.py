import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Header */
.b4b-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
    border-radius: 16px;
    padding: 28px 32px 24px;
    margin-bottom: 24px;
}
.b4b-header h1 { color: #F8FAFC; font-size: 1.9rem; font-weight: 800; margin: 0 0 4px; }
.b4b-header p  { color: #94A3B8; font-size: 0.9rem; margin: 0; }
.b4b-badge {
    display: inline-block;
    background: #10B981;
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 2px 10px;
    border-radius: 999px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* KPI cards */
.kpi-row { display: flex; gap: 14px; margin-bottom: 24px; }
.kpi-card {
    flex: 1;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.kpi-card .val { font-size: 2rem; font-weight: 800; color: #0F172A; line-height: 1; }
.kpi-card .lbl { font-size: 0.78rem; color: #64748B; font-weight: 600;
                  text-transform: uppercase; letter-spacing: 0.06em; margin-top: 6px; }
.kpi-card .sub { font-size: 0.75rem; color: #94A3B8; margin-top: 2px; }

/* Pick cards */
.pick-card {
    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
    border: 1.5px solid #6EE7B7;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.pick-card .match  { font-size: 1.05rem; font-weight: 700; color: #064E3B; }
.pick-card .meta   { font-size: 0.82rem; color: #065F46; margin-top: 4px; }
.pick-card .pills  { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}
.pill-green  { background:#D1FAE5; color:#065F46; border:1px solid #6EE7B7; }
.pill-blue   { background:#DBEAFE; color:#1E40AF; border:1px solid #93C5FD; }
.pill-purple { background:#EDE9FE; color:#5B21B6; border:1px solid #C4B5FD; }
.pill-gray   { background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; }
.pill-teal   { background:#CCFBF1; color:#0F766E; border:1px solid #5EEAD4; }

/* Section titles */
.section-title {
    font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #64748B; margin: 24px 0 12px;
}

/* Confidence bar */
.conf-bar-wrap { background:#E2E8F0; border-radius:999px; height:6px; margin-top:6px; }
.conf-bar      { height:6px; border-radius:999px; }

/* Footer */
.b4b-footer {
    text-align: center; color: #94A3B8; font-size: 0.75rem;
    margin-top: 40px; padding-top: 20px; border-top: 1px solid #E2E8F0;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
today = datetime.date.today().strftime("%A, %d %B %Y")
st.markdown(f"""
<div class="b4b-header">
  <div class="b4b-badge">Live · {today}</div>
  <h1>⚽ B4Business Football Analytics</h1>
  <p>Machine-learning predictions for today's fixtures · Over 2.5 · Over 0.5 · BTTS · 1X2</p>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading predictions..."):
    try:
        df = score_todays_fixtures()
    except Exception as e:
        st.error(f"❌ Could not load predictions: {e}")
        st.stop()

if df is None or df.empty:
    st.info("ℹ️ No fixtures found for today. Check back tomorrow, or make sure your data pipeline has run.")
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
      <div class="lbl">Fixtures Today</div>
      <div class="sub">across all tracked leagues</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="val" style="color:#10B981;">{high_conf}</div>
      <div class="lbl">High-Confidence Picks</div>
      <div class="sub">≥62% model probability</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="val">{avg_o25:.1f}%</div>
      <div class="lbl">Avg Over 2.5 Probability</div>
      <div class="sub">across today's slate</div>
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
        bar_color = "#10B981" if conf > 60 else "#F59E0B"

        st.markdown(f"""
        <div class="pick-card">
          <div class="match">{row['home_team']} <span style="color:#94A3B8;font-weight:400">vs</span> {row['away_team']}</div>
          <div class="meta">⏰ {time_} &nbsp;·&nbsp; Odds: {odds_str}</div>
          <div class="pills">
            <span class="pill pill-green">Over 2.5 &nbsp; {o25:.1f}%</span>
            {f'<span class="pill pill-teal">Over 0.5 &nbsp; {o05:.1f}%</span>' if o05 == o05 else ''}
            <span class="pill pill-blue">BTTS &nbsp; {btts:.1f}%</span>
            <span class="pill pill-purple">1X2 &nbsp; {hw:.0f}% / {dw:.0f}% / {aw:.0f}%</span>
            {'' if has_odds else '<span class="pill pill-gray">⚠️ No market odds — 1X2 less reliable</span>'}
          </div>
          <div class="conf-bar-wrap">
            <div class="conf-bar" style="width:{min(conf,100):.0f}%;background:{bar_color};"></div>
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

st.dataframe(table, use_container_width=True, hide_index=True)

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
