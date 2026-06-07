import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from models.predict import load_fixtures, load_model, load_match_history, predict_for_date


@st.cache_data
def get_model():
    return load_model()


@st.cache_data
def get_history():
    return load_match_history()


def load_uploaded_fixtures(uploaded_file):
    if uploaded_file is None:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)
    return load_fixtures(tmp_path)


def main():
    st.title("Football Over 2.5 Goals Predictor")
    st.write(
        "Upload a fixtures CSV, choose a match date, and view predicted over-2.5 probabilities ranked from highest to lowest."
    )

    model = get_model()
    history = get_history()

    uploaded_file = st.file_uploader("Upload fixture CSV", type=["csv"])
    fixtures = None
    if uploaded_file is not None:
        try:
            fixtures = load_uploaded_fixtures(uploaded_file)
        except Exception as exc:
            st.error(f"Unable to load fixtures: {exc}")
            return

    if fixtures is None:
        st.info("Please upload a fixture CSV with columns: date, competition, home_team, away_team.")
        return

    fixtures["date"] = pd.to_datetime(fixtures["date"]).dt.date
    unique_dates = sorted(fixtures["date"].unique())
    if not unique_dates:
        st.error("No valid fixture dates found in the uploaded file.")
        return

    selected_date = st.selectbox("Select fixture date", unique_dates, index=0)
    st.write(f"Showing predictions for {selected_date}")

    try:
        predictions = predict_for_date(model, history, fixtures, selected_date)
    except Exception as exc:
        st.error(f"Prediction failed: {exc}")
        return

    st.markdown("### Top predicted matches")
    st.dataframe(predictions["home_team away_team over_2_5_probability prediction".split()], use_container_width=True)

    st.markdown("### Download results")
    csv = predictions.to_csv(index=False)
    st.download_button(
        label="Download predictions as CSV",
        data=csv,
        file_name=f"over25_predictions_{selected_date}.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.write("Model trained on historical football fixtures from the local dataset.")


if __name__ == "__main__":
    main()
