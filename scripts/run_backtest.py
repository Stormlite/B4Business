import joblib
from pathlib import Path

from config import MODEL_PATH, DB_PATH
from scripts.backtest import load_matches, evaluate_model, backtest_by_date

if __name__ == '__main__':
    model = joblib.load(MODEL_PATH)
    matches = load_matches()
    evaluate_model(model, matches)
    backtest_by_date(model, matches)
