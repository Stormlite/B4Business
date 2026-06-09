# # import streamlit as st
# # import datetime
# # import pandas as pd
# # from models.predict import score_todays_fixtures

# # # --- PAGE SETUP & UI COSMETICS ---
# # st.set_page_config(
# #     page_title="Football Over 2.5 Goals Predictor", 
# #     page_icon="⚽", 
# #     layout="wide"
# # )

# # # Render main web application headers
# # st.title("⚽ Live Football Over 2.5 Goals Predictor")
# # st.markdown("""
# # This web application displays automated, live probabilities that scheduled football fixtures will cross **Over 2.5 total match goals**. 
# # The system runs completely serverless, refreshing game lists and retraining parameters daily using cloud automation workflows.
# # """)

# # st.write("---")

# # # --- CORE BACKEND EXECUTION ENGINE ---
# # # Track real-time calendar date context variables
# # today_date = datetime.date.today().strftime("%Y-%m-%d")

# # # Create two visual columns for layout organization
# # col_info, col_spacer = st.columns([2, 1])

# # with col_info:
# #     st.subheader(f"📅 Showing Live Match Predictions for Today: `{today_date}`")

# # # Fetch and execute inference metrics from our pipeline using safe loading elements
# # with st.spinner("Analyzing active real-world fixtures and processing model math..."):
# #     try:
# #         # Pull live rankings compiled from models/predict.py
# #         df_predictions = score_todays_fixtures()
        
# #         if not df_predictions.empty:
# #             # Format numbers visually for easier readability
# #             df_display = df_predictions.copy()
# #             df_display["over_2_5_probability"] = df_display["over_2_5_probability"].map(lambda x: f"{x * 100:.2f}%")
# #             df_display["prediction"] = df_display["prediction"].map(lambda x: "🔥 Yes (Over 2.5)" if x == 1 else "🛑 No (Under 2.5)")
            
# #             # Rename column headers for clean display
# #             df_display.columns = ["Home Team", "Away Team", "Over 2.5 Probability", "Model Verdict"]
            
# #             # Render interactive styled data grid view across the interface
# #             st.dataframe(df_display, use_container_width=True)
            
# #             st.write("") # Margin buffer spacer
            
# #             # Recreate export CSV capability using automated data downloads
# #             csv_data = df_predictions.to_csv(index=False).encode('utf-8')
# #             st.download_button(
# #                 label="📥 Download Today's Predictions as CSV",
# #                 data=csv_data,
# #                 file_name=f"predictions_{today_date}.csv",
# #                 mime="text/csv",
# #                 use_container_width=False
# #             )
            
# #         else:
# #             st.info("ℹ️ No scheduled fixtures available for today's monitored competitions. Check back tomorrow morning!")
            
# #     except Exception as e:
# #         st.error(f"❌ An error occurred while parsing predictions: {e}")
# #         st.info("💡 Ensure your GitHub Action pipeline has run successfully at least once to create the core model and database files.")

# # # --- SIDEBAR INFORMATION FOOTER PANEL ---
# # with st.sidebar:
# #     st.header("⚙️ Operational Status")
# #     st.success("✅ System Status: Active")
# #     st.info(f"🕒 Current Web Server Date: {today_date}")
    
# #     st.write("---")
# #     st.markdown("""
# #     ### 🛠️ Architecture
# #     - **Hosting:** Streamlit Community Cloud
# #     - **Database Engine:** DuckDB
# #     - **Automation Engine:** GitHub Actions (`cron` scheduling)
# #     - **API Provider:** Football-Data.org
# #     """)
# #     st.caption("Model parameters are automatically retrained daily to account for changing team form and league trends.")


# import sys
# import os

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import streamlit as st
# import datetime
# import pandas as pd
# from models.predict import score_todays_fixtures

# st.set_page_config(page_title="Football Over 2.5 Goals Predictor", page_icon="⚽", layout="wide")

# st.title("⚽ Live Football Over 2.5 Goals Predictor")
# st.markdown("This interface displays probabilities that scheduled football fixtures will cross **Over 2.5 total match goals**.")

# st.write("---")
# today_date = datetime.date.today().strftime("%Y-%m-%d")

# with st.spinner("Analyzing active real-world fixtures and processing model math..."):
#     try:
#         df_predictions = score_todays_fixtures()
        
#         if not df_predictions.empty:
#             # 🌟 UPGRADE 1: Interactive Multi-Select Filter Sidebar Menu Control Layout
#             all_teams = sorted(list(set(df_predictions["home_team"].tolist() + df_predictions["away_team"].tolist())))
#             selected_teams = st.multiselect("🔍 Filter specific team cards out of today's slate:", options=all_teams)
            
#             df_filtered = df_predictions.copy()
#             if selected_teams:
#                 df_filtered = df_filtered[
#                     df_filtered["home_team"].isin(selected_teams) | df_filtered["away_team"].isin(selected_teams)
#                 ]

#             # Formats displays columns 
#             df_display = df_filtered.copy()
#             df_display["over_2_5_probability"] = df_display["over_2_5_probability"].map(lambda x: f"{x * 100:.2f}%")
#             df_display["prediction"] = df_display["prediction"].map(lambda x: "🔥 Yes (Over 2.5)" if x == 1 else "🛑 No (Under 2.5)")
#             df_display.columns = ["Home Team", "Away Team", "Over 2.5 Probability", "Model Verdict"]

#             # 🌟 UPGRADE 2: Color Highlight High-Value Targets Green (>75%)
#             def highlight_picks(row):
#                 try:
#                     prob_val = float(row["Over 2.5 Probability"].replace('%', ''))
#                     if prob_val >= 75.0:
#                         return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
#                 except ValueError:
#                     pass
#                 return [''] * len(row)

#             styled_df = df_display.style.apply(highlight_picks, axis=1)
#             st.dataframe(styled_df, use_container_width=True)
            
#             csv_data = df_filtered.to_csv(index=False).encode('utf-8')
#             st.download_button(label="📥 Download Filtered Selections as CSV", data=csv_data, file_name=f"predictions_{today_date}.csv", mime="text/csv")
#         else:
#             st.info("ℹ️ No scheduled fixtures available for today.")
#     except Exception as e:
#         st.error(f"❌ An error occurred while parsing predictions: {e}")

# with st.sidebar:
#     st.header("⚙️ Operational Status")
#     st.success("✅ System Status: Active")
#     st.info(f"🕒 Server Date: {today_date}")

import sys
import os

# Ensure root paths load accurately in cloud environments
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import datetime
import pandas as pd
from models.predict import score_todays_fixtures

# --- 🎨 PRODUCTION BRANDING & STYLING ---
st.set_page_config(
    page_title="Over2.5 | Predictive Analytics Dashboard", 
    page_icon="⚽", 
    layout="wide"
)

# Premium dark/light unified component styling blocks
st.markdown("""
    <style>
    .main-title { font-size: 2.6rem !important; font-weight: 800 !important; color: #1E293B; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1.1rem !important; color: #64748B; margin-bottom: 2rem; }
    .kpi-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 1.25rem; border-radius: 0.75rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .kpi-val { font-size: 1.75rem !important; font-weight: 700 !important; color: #0F172A; }
    .kpi-lbl { font-size: 0.85rem !important; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 🚀 HEADER ARCHITECTURE ---
st.markdown('<div class="main-title">⚽ Over2.5 Predictive Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Production-grade automated forecasting machine learning models evaluating over/under goal metrics for today\'s fixtures.</div>', unsafe_allow_html=True)

today_date = datetime.date.today().strftime("%Y-%m-%d")

# --- ⚡ CORE DATA PARSING ENGINE ---
with st.spinner("Executing mathematical array inferences against live data feeds..."):
    try:
        df_predictions = score_todays_fixtures()
        
        if not df_predictions.empty:
            # 📊 KPI SCORECARD METRIC ROW
            total_fixtures = len(df_predictions)
            high_conf_picks = len(df_predictions[df_predictions["over_2_5_probability"] >= 0.75])
            avg_prob = df_predictions["over_2_5_probability"].mean() * 100

            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{total_fixtures}</div><div class="kpi-lbl">Fixtures Monitored</div></div>', unsafe_allow_html=True)
            with kpi2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{high_conf_picks}</div><div class="kpi-lbl">High Confidence Selections (≥75%)</div></div>', unsafe_allow_html=True)
            with kpi3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-val">{avg_prob:.1f}%</div><div class="kpi-lbl">Average Over 2.5 Slate Weight</div></div>', unsafe_allow_html=True)
            
            st.write("")
            st.write("")

            # 🔍 INTERACTIVE FILTER CONTROLS
            all_teams = sorted(list(set(df_predictions["home_team"].tolist() + df_predictions["away_team"].tolist())))
            
            f_col1, f_col2 = st.columns([3, 1])
            with f_col1:
                selected_teams = st.multiselect("🔍 Filter specific team profiles:", options=all_teams, placeholder="Search team names...")
            with f_col2:
                # Filter rows using an interactive confidence slider block
                min_prob = st.slider("📈 Minimum Probability Threshold:", min_value=0, max_value=100, value=0, step=5)

            # Apply UI data selection overrides dynamically
            df_filtered = df_predictions.copy()
            if selected_teams:
                df_filtered = df_filtered[df_filtered["home_team"].isin(selected_teams) | df_filtered["away_team"].isin(selected_teams)]
            df_filtered = df_filtered[df_filtered["over_2_5_probability"] >= (min_prob / 100)]

            # 🛠️ DATA PRESENTATION & CONDITIONAL DESIGN STRINGS
            df_display = df_filtered.copy()
            df_display["over_2_5_probability"] = df_display["over_2_5_probability"].map(lambda x: f"{x * 100:.2f}%")
            df_display["prediction"] = df_display["prediction"].map(lambda x: "🔥 Yes (Over 2.5)" if x == 1 else "🛑 No (Under 2.5)")
            df_display.columns = ["Home Team", "Away Team", "Over 2.5 Probability", "Model Verdict"]

            # High value targets are styled with premium soft emerald green tints
            def style_production_table(row):
                try:
                    prob_float = float(row["Over 2.5 Probability"].replace('%', ''))
                    if prob_float >= 75.0:
                        return ['background-color: #E6F4EA; color: #137333; font-weight: 700; border-left: 4px solid #137333;'] * len(row)
                    elif prob_float <= 35.0:
                        return ['background-color: #FCE8E6; color: #C5221F;'] * len(row)
                except ValueError:
                    pass
                return [''] * len(row)

            # Render data matrix view
            if not df_display.empty:
                styled_grid = df_display.style.apply(style_production_table, axis=1)
                st.dataframe(styled_grid, use_container_width=True, hide_index=True)
                
                # Clean file export options
                csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Filtered Forecast Matrix (CSV)", 
                    data=csv_bytes, 
                    file_name=f"over25_predictions_{today_date}.csv", 
                    mime="text/csv"
                )
            else:
                st.info("No fixtures match your slider or search token criteria.")

        else:
            st.info("ℹ️ No active scheduled fixtures discovered for today's tracked competitions. Check back tomorrow morning!")
            
    except Exception as e:
        st.error(f"❌ Core Application Interface Error: {e}")

# --- 🤓 THE "NERDY DETAILS" ACCORDION TOGGLE ---
st.write("---")
with st.expander("🤓 View Nerdy Details, Model Parameters, and Operational Context"):
    st.markdown("### 🛠️ Architecture Blueprint & Data Engineering Profile")
    st.write(f"Current Local Execution Date: `{today_date}`")
    
    n_col1, n_col2 = st.columns(2)
    with n_col1:
        st.markdown("""
        **Data Processing Infrastructure:**
        - **Ingestion Engine:** API-Football v3 REST Protocols
        - **Analytical Processing Core:** DuckDB Storage Engine
        - **Orchestration:** Serverless GitHub Actions `cron` scheduling engine running daily at 04:00 UTC.
        - **Pipeline Targets:** Pulls real-time rosters, updates historical records, and automates model file writebacks.
        """)
    with n_col2:
        st.markdown("""
        **Machine Learning Framework Details:**
        - **Classification Model:** Scikit-Learn `RandomForestClassifier`
        - **Hyperparameter Profiles:** 100 Trees, Balanced Class Weights, Maximum Tree Depth: 6.
        - **Engineered Dimensions Vector:**
          1. `home_rolling_scored` | 2. `home_rolling_conceded`
          3. `away_rolling_scored` | 4. `away_rolling_conceded`
          5. `combined_rolling_scoring_power` | 6. `combined_rolling_defensive_leakage`
        """)
        
    st.markdown("### 🔔 Connected Integration Services")
    st.info("💬 **Twilio Messaging Node:** Active — Daily alerts push automated high-confidence selections directly to your WhatsApp terminal if probabilities exceed the 75% valuation floor.")

# --- SIDEBAR OPERATIONAL TELEMETRY ---
with st.sidebar:
    st.header("⚙️ System Telemetry")
    st.success("● Cloud Core: Operational")
    st.caption("The predictive array models retrain and optimize automatically every 24 hours to balance dynamic variations in team form metrics.")
