"""scripts/run_local_prediction.py — run predictions locally and print results"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
from models.predict import score_todays_fixtures

def main():
    print(f"⚽ Running predictions for {datetime.date.today()}...")
    df = score_todays_fixtures()
    if df is None or df.empty:
        print("ℹ️  No fixtures found for today.")
        return
    print(f"✅ {len(df)} fixtures scored.\n")
    print(df[["home_team","away_team","over_2_5_probability","btts_probability",
              "high_conf_pick"]].to_string(index=False))
    out = "predictions_sample.csv"
    df.to_csv(out, index=False)
    print(f"\n📥 Saved to {out}")

if __name__ == "__main__":
    main()
