import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st

# Safe imports
try:
    from models.predict import load_fixtures, load_model, load_match_history, predict_for_date
except ImportError as e:
    st.error(f"Failed to import internal modules. Ensure 'models' folder is uploaded to GitHub. Error: {e}")

# Cache model and history loaders safely
@st.cache_resource # Use cache_resource for ML models to avoid serialization bugs
def get_model():
    try:
        return load_model()
    except Exception as e:
        st.error(f"💥 Error loading model. Did you run 'models/train.py' and upload the model files to GitHub? Details: {e}")
        return None

@st.cache_data
def get_history():
    try:
        return load_match_history()
    except Exception as e:
        st.error(f"💥 Error loading match history database. Ensure your data/ directory has been populated. Details: {e}")
        return None

def load_uploaded_fixtures(uploaded_file):
    if uploaded_file is None:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)
    return load_fixtures(tmp_path)


def main():
    st.set_page_config(page_title="Football Over 2.5 Goals Predictor", layout="wide")
    
    st.title("⚽ Football Over 2.5 Goals Predictor")
    st.write(
        "Upload a fixtures CSV, choose a match date, and view predicted over-2.5 probabilities ranked from highest to lowest."
    )

    # 1. Load ML assets safely
    model = get_model()
    history = get_history()

    if model is None or history is None:
        st.warning("⚠️ Application is missing required background ML files. Please check the logs above.")
        return

    # 2. File Upload handling using Session State
    uploaded_file = st.file_uploader("Upload fixture CSV", type=["csv"])
    
    if uploaded_file is not None:
        if "loaded_fixtures" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            try:
                with st.spinner("Processing uploaded fixtures..."):
                    fixtures_df = load_uploaded_fixtures(uploaded_file)
                    # Sync dates to string format to prevent cross-library type mismatches
                    fixtures_df["date"] = pd.to_datetime(fixtures_df["date"]).dt.strftime('%Y-%m-%d')
                    st.session_state["loaded_fixtures"] = fixtures_df
                    st.session_state["file_name"] = uploaded_file.name
            except Exception as exc:
                st.error(f"Unable to load fixtures: {exc}")
                return
    else:
        # Clear state if user removes file
        if "loaded_fixtures" in st.session_state:
            del st.session_state["loaded_fixtures"]

    if "loaded_fixtures" not in st.session_state:
        st.info("💡 Please upload a fixture CSV with columns: `date`, `competition`, `home_team`, `away_team` to begin.")
        return

    fixtures = st.session_state["loaded_fixtures"]
    unique_dates = sorted(fixtures["date"].unique())
    
    if not unique_dates:
        st.error("No valid fixture dates found in the uploaded file. Check your 'date' column format.")
        return

    # 3. Interactive Date Selection
    selected_date_str = st.selectbox("Select fixture date", unique_dates, index=0)
    
    # Crucial Fix: Convert selected date back to the type your predict_for_date function expects
    # If your pipeline expects a datetime object or string, this ensures it matches perfectly.
    try:
        # Check if underlying pipeline needs string or Timestamp (we fall back safely)
        selected_date = pd.to_datetime(selected_date_str).date() 
    except Exception:
        selected_date = selected_date_str

    st.markdown(f"### 📋 Showing predictions for **{selected_date_str}**")

    # 4. Generate Predictions
    try:
        with st.spinner("Calculating historical forms, H2H, and Over 2.5 probabilities..."):
            predictions = predict_for_date(model, history, fixtures, selected_date)
    except Exception as exc:
        st.error(f"❌ Prediction failed: {exc}")
        st.info("This usually happens if team names in your fixture CSV don't perfectly match names in the historical database.")
        return

    # 5. Display Results
    if predictions is not None and not predictions.empty:
        # Check available columns to avoid KeyError if Copilot misnamed columns
        expected_cols = ["home_team", "away_team", "over_2_5_probability", "prediction"]
        available_cols = [col for col in expected_cols if col in predictions.columns]
        
        if not available_cols:
            available_cols = predictions.columns.tolist() # Fallback to all columns if wrong

        st.dataframe(predictions[available_cols], use_container_width=True)

        # 6. Export Results
        csv = predictions.to_csv(index=False)
        st.download_button(
            label="📥 Download predictions as CSV",
            data=csv,
            file_name=f"over25_predictions_{selected_date_str}.csv",
            mime="text/csv",
        )
    else:
        st.warning("No matches found or predictable for this specific date. Check if team names match your database records.")

    st.markdown("---")
    st.caption("Model trained on historical football fixtures from the local dataset.")


if __name__ == "__main__":
    main()