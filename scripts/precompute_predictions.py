"""scripts/precompute_predictions.py — saves today+tomorrow's scored
predictions to DuckDB during the pipeline run, so the Streamlit app can read
them back near-instantly instead of recomputing the full pipeline (rolling
stats over the whole match history) on every page load.
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import score_todays_fixtures, save_predictions

def precompute():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    for target_date in [today, tomorrow]:
        date_str = target_date.strftime("%Y-%m-%d")
        print(f"🔄 Precomputing predictions for {date_str}...")
        df = score_todays_fixtures(target_date=date_str)
        if df.empty:
            print(f"ℹ️  No fixtures/predictions for {date_str} — nothing to save.")
            continue
        save_predictions(df, date_str)

if __name__ == "__main__":
    precompute()
