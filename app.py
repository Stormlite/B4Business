import sys
import os

# Force Python to recognize the project root directory for module resolution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import datetime
import pandas as pd
from models.predict import score_todays_fixtures

# --- PAGE SETUP & UI COSMETICS ---
st.set_page_config(
    page_title="Football Over 2.5 Goals Predictor", 
    page_icon="⚽", 
    layout="wide"
)

# Render main web application headers
st.title("⚽ Live Football Over 2.5 Goals Predictor")
st.markdown("""
This web application displays automated, live probabilities that scheduled football fixtures will cross **Over 2.5 total match goals**. 
The system runs completely serverless, refreshing game lists and retraining parameters daily using cloud automation workflows.
""")

st.write("---")

# --- CORE BACKEND EXECUTION ENGINE ---
# Track real-time calendar date context variables
today_date = datetime.date.today().strftime("%Y-%m-%d")

# Create two visual columns for layout organization
col_info, col_spacer = st.columns([2, 1])

with col_info:
    st.subheader(f"📅 Showing Live Match Predictions for Today: `{today_date}`")

# Fetch and execute inference metrics from our pipeline using safe loading elements
with st.spinner("Analyzing active real-world fixtures and processing model math..."):
    try:
        # Pull live rankings compiled from models/predict.py
        df_predictions = score_todays_fixtures()
        
        if not df_predictions.empty:
            # Format numbers visually for easier readability
            df_display = df_predictions.copy()
            df_display["over_2_5_probability"] = df_display["over_2_5_probability"].map(lambda x: f"{x * 100:.2f}%")
            df_display["prediction"] = df_display["prediction"].map(lambda x: "🔥 Yes (Over 2.5)" if x == 1 else "🛑 No (Under 2.5)")
            
            # Rename column headers for clean display
            df_display.columns = ["Home Team", "Away Team", "Over 2.5 Probability", "Model Verdict"]
            
            # Render interactive styled data grid view across the interface
            st.dataframe(df_display, use_container_width=True)
            
            st.write("") # Margin buffer spacer
            
            # Recreate export CSV capability using automated data downloads
            csv_data = df_predictions.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Today's Predictions as CSV",
                data=csv_data,
                file_name=f"predictions_{today_date}.csv",
                mime="text/csv",
                use_container_width=False
            )
            
        else:
            st.info("ℹ️ No scheduled fixtures available for today's monitored competitions. Check back tomorrow morning!")
            
    except Exception as e:
        st.error(f"❌ An error occurred while parsing predictions: {e}")
        st.info("💡 Ensure your GitHub Action pipeline has run successfully at least once to create the core model and database files.")

# --- SIDEBAR INFORMATION FOOTER PANEL ---
with st.sidebar:
    st.header("⚙️ Operational Status")
    st.success("✅ System Status: Active")
    st.info(f"🕒 Current Web Server Date: {today_date}")
    
    st.write("---")
    st.markdown("""
    ### 🛠️ Architecture
    - **Hosting:** Streamlit Community Cloud
    - **Database Engine:** DuckDB
    - **Automation Engine:** GitHub Actions (`cron` scheduling)
    - **API Provider:** Football-Data.org
    """)
    st.caption("Model parameters are automatically retrained daily to account for changing team form and league trends.")
