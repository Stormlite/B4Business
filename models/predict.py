import argparse
import io
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

from config import DB_PATH, MODEL_PATH
from features.engineer import build_features, prepare_fixture_features, select_feature_matrix


def load_model():
    return joblib.load(MODEL_PATH)


def load_match_history() -> pd.DataFrame:
    import duckdb

    con = duckdb.connect(DB_PATH)
    df = con.execute("SELECT * FROM matches ORDER BY date").df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_fixtures(path: Path | str | io.IOBase) -> pd.DataFrame:
    if hasattr(path, "read"):
        df = pd.read_csv(path, parse_dates=["date"])
    else:
        path = Path(path)
        df = pd.read_csv(path, parse_dates=["date"]) if path.suffix == ".csv" else pd.read_csv(path, parse_dates=["date"])
    if "competition" not in df.columns:
        df["competition"] = "Unknown"
    return df[["date", "competition", "home_team", "away_team"]].copy()


def predict_for_date(model, history: pd.DataFrame, fixtures: pd.DataFrame, date: datetime) -> pd.DataFrame:
    target_fixtures = fixtures[fixtures["date"] == date].copy()
    if target_fixtures.empty:
        raise ValueError(f"No fixtures found for {date.date()}")

    fixture_features = prepare_fixture_features(target_fixtures, history)
    X, _ = select_feature_matrix(fixture_features)
    probabilities = model.predict_proba(X)[:, 1]
    results = target_fixtures.copy()
    results["over_2_5_probability"] = probabilities
    results["prediction"] = (results["over_2_5_probability"] >= 0.5).astype(int)
    return results.sort_values("over_2_5_probability", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict over 2.5 goals for a given fixtures file and date.")
    parser.add_argument("--date", required=True, help="Prediction date in YYYY-MM-DD format.")
    parser.add_argument("--fixtures", required=True, help="CSV file containing upcoming fixtures.")
    parser.add_argument("--output", default="predictions.csv", help="Output CSV file.")
    args = parser.parse_args()

    model = load_model()
    history = load_match_history()
    fixtures = load_fixtures(Path(args.fixtures))
    date = datetime.fromisoformat(args.date)
    predictions = predict_for_date(model, history, fixtures, date)
    predictions.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output}")
    print(predictions.to_string(index=False))


if __name__ == "__main__":
    main()
