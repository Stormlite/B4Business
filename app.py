# import sys
# import os

# # Ensure root paths load accurately in cloud environments
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import streamlit as st
# import datetime
# import pandas as pd
# import duckdb
# from models.predict import score_todays_fixtures
# from config import DB_PATH

# # --- 🎨 PRODUCTION BRANDING & STYLING ---
# st.set_page_config(
#     page_title="Over2.5 | Predictive Analytics Dashboard", 
#     page_icon="⚽", 
#     layout="wide"
# )

# st.markdown("""
#     <style>
#     .main-title { font-size: 2.6rem !important; font-weight: 800 !important; color: #1E293B; margin-bottom: 0.5rem; }
#     .subtitle { font-size: 1.1rem !important; color: #64748B; margin-bottom: 2rem; }
#     .kpi-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 1.25rem; border-radius: 0.75rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
#     .kpi-val { font-size: 1.75rem !important; font-weight: 700 !important; color: #0F172A; }
#     .kpi-lbl { font-size: 0.85rem !important; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
#     </style>
# """, unsafe_allow_html=True)

# st.markdown('<div class="main-title">⚽ Over2.5 & BTTS Predictive Analytics</div>', unsafe_allow_html=True)
# st.markdown('<div class="subtitle">Production-grade automated forecasting machine learning models evaluating over/under goal metrics for today\'s fixtures.</div>', unsafe_allow_html=True)

# # 🌟 AUTOMATED SYSTEM DATE OVERVIEW
# today_date = datetime.date.today().strftime("%Y-%m-%d")

# # --- 📈 LINE GRAPH ACCURACY PERFORMANCE CHART ---
# st.subheader("📈 Model Accuracy Performance Timeline")
# conn = duckdb.connect(DB_PATH)
# try:
#     df_chart = conn.execute("SELECT * FROM model_accuracy_history ORDER BY year_month ASC").df()
#     if not df_chart.empty:
#         df_chart = df_chart.set_index("year_month")
#         df_chart.columns = ["Over 2.5 Goals Accuracy (%)", "BTTS Accuracy (%)"]
#         st.line_chart(df_chart)
#     else:
#         st.info("Historical accuracy dataset is initializing. Chart populates after morning data syncs.")
# except Exception:
#     st.info("Accuracy timeline tracking map loaded. Visualizes following initial automated run.")
# finally:
#     conn.close()

# st.write("---")

# # --- ⚡ CORE DATA PARSING ENGINE ---
# with st.spinner("Executing mathematical array inferences against live data feeds..."):
#     try:
#         df_predictions = score_todays_fixtures()
        
#         if df_predictions is not None and not df_predictions.empty:
#             total_fixtures = len(df_predictions)
#             high_conf_picks = len(df_predictions[(df_predictions["over_2_5_probability"] >= 0.75) | (df_predictions["btts_probability"] >= 0.75)])
#             avg_prob = df_predictions["over_2_5_probability"].mean() * 100

#             kpi1, kpi2, kpi3 = st.columns(3)
#             with kpi1:
#                 st.markdown(f'<div class="kpi-card"><div class="kpi-val">{total_fixtures}</div><div class="kpi-lbl">Fixtures Monitored</div></div>', unsafe_allow_html=True)
#             with kpi2:
#                 st.markdown(f'<div class="kpi-card"><div class="kpi-val">{high_conf_picks}</div><div class="kpi-lbl">High Confidence Selections (≥75%)</div></div>', unsafe_allow_html=True)
#             with kpi3:
#                 st.markdown(f'<div class="kpi-card"><div class="kpi-val">{avg_prob:.1f}%</div><div class="kpi-lbl">Average Over 2.5 Slate Weight</div></div>', unsafe_allow_html=True)
            
#             st.write("")
#             st.write("")

#             # 🔍 INTERACTIVE FILTER CONTROLS
#             all_teams = sorted(list(set(df_predictions["home_team"].tolist() + df_predictions["away_team"].tolist())))
            
#             f_col1, f_col2 = st.columns(2)
#             with f_col1:
#                 selected_teams = st.multiselect("🔍 Filter specific team profiles:", options=all_teams, placeholder="Search team names...")
#             with f_col2:
#                 # 🌟 FIX: Min value default set to 0, ensuring ALL games show upon interface load
#                 min_prob = st.slider("📈 Minimum Probability Threshold (Over 2.5 or BTTS):", min_value=0, max_value=100, value=0, step=5)

#             # Apply user filter choices dynamically
#             df_filtered = df_predictions.copy()
#             if selected_teams:
#                 df_filtered = df_filtered[df_filtered["home_team"].isin(selected_teams) | df_filtered["away_team"].isin(selected_teams)]
            
#             df_filtered = df_filtered[
#                 (df_filtered["over_2_5_probability"] >= (min_prob / 100)) | 
#                 (df_filtered["btts_probability"] >= (min_prob / 100))
#             ]

#             # 🛠️ DATA PRESENTATION LAYOUT
#             df_display = df_filtered.copy()
#             df_display["over_2_5_probability"] = (df_display["over_2_5_probability"] * 100).map(lambda x: f"{x:.2f}%")
#             df_display["over_2_5_verdict"] = df_display["over_2_5_verdict"].map(lambda x: "🔥 Yes" if x == 1 else "🛑 No")
#             df_display["btts_probability"] = (df_display["btts_probability"] * 100).map(lambda x: f"{x:.2f}%")
#             df_display["btts_verdict"] = df_display["btts_verdict"].map(lambda x: "🔥 Yes" if x == 1 else "🛑 No")
            
#             df_display.columns = ["Home Team", "Away Team", "Over 2.5 Prob", "Over 2.5 Verdict", "BTTS Prob", "BTTS Verdict"]

#             # Conditional table formatting function for production display
#             def style_production_table(row):
#                 try:
#                     o25_val = float(row["Over 2.5 Prob"].replace('%', ''))
#                     btts_val = float(row["BTTS Prob"].replace('%', ''))
#                     if o25_val >= 75.0 or btts_val >= 75.0:
#                         return ['background-color: #E6F4EA; color: #137333; font-weight: 700;'] * len(row)
#                 except ValueError:
#                     pass
#                 return [''] * len(row)

#             if not df_display.empty:
#                 styled_grid = df_display.style.apply(style_production_table, axis=1)
#                 st.dataframe(styled_grid, use_container_width=True, hide_index=True)
                
#                 csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
#                 st.download_button(label="📥 Export Full Selection Matrix (CSV)", data=csv_bytes, file_name=f"football_predictions_{today_date}.csv", mime="text/csv")
#             else:
#                 st.info("No games match the slider value criteria chosen.")
#         else:
#             st.info("ℹ️ No active scheduled fixtures discovered for today's tracked competitions. Check back tomorrow morning!")
            
#     except Exception as e:
#         st.error(f"❌ Core Application Interface Error: {e}")

# # --- 🤓 THE "NERDY DETAILS" ACCORDION TOGGLE ---
# st.write("---")
# with st.expander("🤓 View Nerdy Details, Model Parameters, and Operational Context"):
#     st.markdown("### 🛠️ Architecture Blueprint & Data Engineering Profile")
#     st.write(f"Current Local Execution Date: `{today_date}`")
#     st.markdown("""
#     **Data & Analytics Summary Stack:**
#     - **Ingestion Source Engine:** API-Football v3 REST Protocols
#     - **Database Core:** DuckDB Storage Layer
#     - **Classification Model Infrastructure:** Twin Scikit-Learn `RandomForestClassifier` modules scoring Over 2.5 & BTTS targets independently.
#     """)


import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import datetime
import pandas as pd
from models.predict import score_todays_fixtures

st.set_page_config(page_title="Pro Analytics Dashboard", page_icon="⚽", layout="wide")

st.markdown('<h1 style="color:#0F172A;">⚽ Elite Multi-Market Analytics Station</h1>', unsafe_allow_html=True)

# 🌟 NEW UPGRADE: UI CONTROL PANEL WITH CHRONOLOGICAL SORTING
sort_option = st.radio("排序 / **Sort Display Rows By:**", options=["🔥 Highest Goal Probability", "⏰ Chronological Kickoff Time"], horizontal=True)

with st.spinner("Processing live array matrices..."):
    try:
        df_predictions = score_todays_fixtures()
        
        if df_predictions is not None and not df_predictions.empty:
            
            # Apply Sorting Toggles dynamically
            if "Kickoff Time" in sort_option:
                df_predictions = df_predictions.sort_values(by="match_time", ascending=True)
            else:
                df_predictions = df_predictions.sort_values(by="over_2_5_probability", ascending=False)
                
            df_display = pd.DataFrame()
            df_display["Time ⏰"] = df_predictions["match_time"]
            df_display["Home Team"] = df_predictions["home_team"]
            df_display["Away Team"] = df_predictions["away_team"]
            
            # Goal Probabilities
            df_display["Over 2.5 %"] = (df_predictions["over_2_5_probability"] * 100).map(lambda x: f"{x:.1f}%")
            df_display["BTTS %"] = (df_predictions["btts_probability"] * 100).map(lambda x: f"{x:.1f}%")
            
            # 🌟 NEW outcome predictions
            df_display["1X2 Probs (H / D / A)"] = df_predictions.apply(
                lambda r: f"{r['prob_home_win']*100:.0f}% / {r['prob_draw']*100:.0f}% / {r['prob_away_win']*100:.0f}%", axis=1
            )
            
            # 🌟 NEW live market odds strings
            df_display["Live Odds (1 / X / 2)"] = df_predictions.apply(
                lambda r: f"{r['odds_home']:.2f} / {r['odds_draw']:.2f} / {r['odds_away']:.2f}", axis=1
            )
            
            # 🌟 NEW SportyBet Over 0.5 Smart Slip Guide Target Column
            df_display["SportyBet Code Recommendation"] = "✅ Over 0.5 (Active)"
            
            # Render Table View with styling
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # 🌟 NEW SportyBet Quick Slip Accordion View
            with st.expander("🎫 View Verified SportyBet Over 0.5 Accumulator Slip Summary"):
                st.markdown("### 📋 Copy-Paste Accumulator Roster Selection Details")
                st.caption("To prevent account bans from web firewall bots, copy these exact text strings directly into your SportyBet search card panel safely:")
                for _, row in df_display.iterrows():
                    st.text(f"⚽ {row['Home Team']} vs {row['Away Team']} ➡️ Market Selection: Over 0.5 Goals")
                    
        else:
            st.info("No fixtures available for today.")
    except Exception as e:
        st.error(f"UI Interface Parsing Error: {e}")
