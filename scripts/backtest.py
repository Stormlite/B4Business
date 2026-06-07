import argparse
from pathlib import Path

import duckdb
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score

from config import DB_PATH, MODEL_PATH
from features.engineer import build_features, select_feature_matrix


def load_matches() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH)
    df = con.execute("SELECT * FROM matches ORDER BY date").df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def evaluate_model(model, df: pd.DataFrame) -> None:
    features = build_features(df)
    X, y = select_feature_matrix(features)
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    acc = accuracy_score(y, y_pred)
    brier = brier_score_loss(y, y_prob)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)

    print(f"Historical evaluation on full dataset")
    print(f"Accuracy: {acc:.4f}")
    print(f"Brier score: {brier:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")


def backtest_by_date(model, df: pd.DataFrame) -> None:
    df = df.sort_values("date").reset_index(drop=True)
    features = build_features(df)
    X, y = select_feature_matrix(features)
    y_prob = model.predict_proba(X)[:, 1]
    preds = (y_prob >= 0.5).astype(int)
    features = features.assign(pred=preds, prob=y_prob)

    daily = features.groupby(features["date"].dt.date).apply(
        lambda g: pd.Series(
            {
                "accuracy": accuracy_score(g["over_2_5"], g["pred"]),
                "precision": precision_score(g["over_2_5"], g["pred"], zero_division=0),
                "recall": recall_score(g["over_2_5"], g["pred"], zero_division=0),
                "matches": len(g),
            }
        )
    )

    print("Per-day grouped performance")
    print(daily.describe().loc[["mean", "std", "min", "max"]])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run historical backtesting for the over 2.5 goals model.")
    parser.add_argument("--backtest", action="store_true", help="Run full dataset evaluation and date-level backtest.")
    parser.add_argument("--sample-days", type=int, default=30, help="Number of days to sample for date-based backtesting.")
    args = parser.parse_args()

    if args.backtest:
        model = joblib.load(MODEL_PATH)
        matches = load_matches()
        evaluate_model(model, matches)
        backtest_by_date(model, matches)


if __name__ == "__main__":
    main()
