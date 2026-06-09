import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import datetime
import pandas as pd
import duckdb
from models.predict import score_todays_fixtures
from config import DB_PATH

st.set_page_config(page_title="Over2.5 & BTTS | Analytics Dashboard", page_icon="⚽", layout="wide")

# Custom Styles
st.markdown("""
    <style>
    .main-title { font-size: 2.6rem !important; font-weight: 800 !important; color: #1E293B; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1.1rem !important; color: #64748B; margin-bottom: 1.5rem; }
    .kpi-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 1.25rem; border-radius: 0.75rem; text-align: center; }
    .kpi-val { font-size: 1.75rem !important; font-weight: 700 !important; color: #0F172A; }
    .kpi-lbl { font-size: 0.85rem !important; color: #64748B; text-transform: uppercase; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚽ Over2.5 & BTTS Predictive Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Multi-market machine learning dashboard tracking goals and team form variables in real-time.</div>', unsafe_allow_html=True)

today_date = datetime.date.today().strftime("%Y-%m-%d")

# --- 🌟 HISTORICAL ACCURACY CHART ENGINE ---
st.subheader("📈 Historical League Goal Trends (Rolling Analytics)")
conn = duckdb.connect(DB_PATH)
try:
    # Query database to build monthly trend breakdown
    trend_df = conn.execute("""
        SELECT 
            SUBSTR(match_date, 1, 7) as month,
            AVG(CASE WHEN (home_score + away_score) > 2.5 THEN 1.0 ELSE 0.0 END) * 100 as over_25_rate,
            AVG(CASE WHEN home_score > 0 AND away_score > 0 THEN 1.0 ELSE 0.0 END) * 100 as btts_rate
        FROM historical_matches 
        WHERE status='FINISHED' AND match_date != 'Unknown' AND match_date IS NOT NULL
        GROUP BY month ORDER BY month ASC
    """).df()
    
    if not trend_df.empty:
        # Format for Streamlit Native Line Charting
        chart_data = trend_df.set_index('month')
        chart_data.columns = ['Over 2.5 Goals %', 'BTTS %']
        st.line_chart(chart_data)
    else:
        st.info("Insufficient finished data rows to chart trends yet.")
except Exception as e:
    st.caption(f"Historical trend chart loading: Database initializing... ({e})")
finally:
    conn.close()

st.write("---")

# --- CORE INFERENCE SLATE CONTAINER ---
st.subheader(f"📅 Live Predictive Ratings for Today: `{today_date}`")

with st.spinner("Executing mathematical array inferences against live data feeds..."):
    try:
        df_predictions = score_todays_fixtures()
        
        if not df_predictions.empty:
            # KPI Cards
            total_fixtures = len(df_predictions)
            o25_picks = len(df_predictions[df_predictions["over_2_5_probability"] >= 0.75])
            btts_picks = len(df_predictions[df_predictions["btts_probability"] >= 0.75])

            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{total_fixtures}</div><div class="kpi-lbl">Total Fixtures Slate</div></div>', unsafe_allow_html=True)
            with kpi2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{o25_picks}</div><div class="kpi-lbl">High Over 2.5 Picks (≥75%)</div></div>', unsafe_allow_html=True)
            with kpi3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{btts_picks}</div><div class="kpi-lbl">High BTTS Picks (≥75%)</div></div>', unsafe_allow_html=True)
            
            st.write("")
            
            # Interactive Filter Elements
            all_teams = sorted(list(set(df_predictions["home_team"].tolist() + df_predictions["away_team"].tolist())))
            selected_teams = st.multiselect("🔍 Filter specific team profiles:", options=all_teams, placeholder="Search team names...")
            
            df_filtered = df_predictions.copy()
            if selected_teams:
                df_filtered = df_filtered[df_filtered["home_team"].isin(selected_teams) | df_filtered["away_team"].isin(selected_teams)]

            # Presentation Format Layout Configuration
            df_display = pd.DataFrame()
            df_display["Home Team"] = df_filtered["home_team"]
            df_display["Away Team"] = df_filtered["away_team"]
            df_display["Over 2.5 Prob"] = df_filtered["over_2_5_probability"].map(lambda x: f"{x * 100:.1f}%")
            df_display["Over 2.5 Verdict"] = df_filtered["over_2_5_verdict"].map(lambda x: "🔥 Yes" if x == 1 else "🛑 Under")
            df_display["BTTS Prob"] = df_filtered["btts_probability"].map(lambda x: f"{x * 100:.1f}%")
            df_display["BTTS Verdict"] = df_filtered["btts_verdict"].map(lambda x: "🔥 Yes" if x == 1 else "🛑 No")

            # Dual Market Visual Highlights Styles
            def style_multi_market_table(row):
                styles = [''] * len(row)
                try:
                    o25_val = float(row["Over 2.5 Prob"].replace('%', ''))
                    btts_val = float(row["BTTS Prob"].replace('%', ''))
                    
                    # If both high value features align, give row deep emerald highlight accent
                    if o25_val >= 75.0 and btts_val >= 75.0:
                        return ['background-color: #D1E7DD; color: #0F5132; font-weight: bold; font-size:15px;'] * len(row)
                    
                    # Individual Highlight Conditions
                    if o25_val >= 75.0:
                        styles[2] = 'background-color: #E6F4EA; color: #137333; font-weight: bold;'
                        styles[3] = 'background-color: #E6F4EA; color: #137333; font-weight: bold;'
                    if btts_val >= 75.0:
                        styles[4] = 'background-color: #E8F0FE; color: #1A73E8; font-weight: bold;'
                        styles[5] = 'background-color: #E8F0FE; color: #1A73E8; font-weight: bold;'
                except ValueError:
                    pass
                return styles

            styled_grid = df_display.style.apply(style_multi_market_table, axis=1)
            st.dataframe(styled_grid, use_container_width=True, hide_index=True)
            
            csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Export Dual-Market Prediction Matrix (CSV)", data=csv_bytes, file_name=f"predictions_{today_date}.csv", mime="text/csv")
        else:
            st.info("ℹ️ No active scheduled fixtures discovered for today.")
    except Exception as e:
        st.error(f"❌ Core Application Interface Error: {e}")

# Expandable Nerdy Toggle Content Blueprint
st.write("---")
with st.expander("🤓 View Multi-Market Model Variables & Architecture Details"):
    st.markdown("""
    **Dual Classification Node Specifications:**
    - **Model Alpha (Over 2.5):** Scikit-Learn `RandomForestClassifier` targeting total match goals count arrays > 2.5.
    - **Model Beta (BTTS):** Scikit-Learn `RandomForestClassifier` targeting matches where both `home_score > 0` and `away_score > 0`.
    - **Feature Arrays Loaded:** Base goal rolling statistics combined with the new `combined_btts_trend` team tracking vector.
    """)

with st.sidebar:
    st.header("⚙️ Multi-Model Telemetry")
    st.success("● Over 2.5 Model: Online")
    st.success("● BTTS Model: Online")
