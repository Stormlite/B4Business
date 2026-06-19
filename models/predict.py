"""
models/predict.py — Live prediction scorer
==========================================
Upgrades vs original:
  - Loads saved feature-column list from training so predict always
    uses the exact same features the model was trained on
  - Adds a `confidence` column and `high_conf` flag for selective betting
  - Falls back gracefully when feature list artefact is missing
"""

import os
import joblib
import pandas as pd
import duckdb

from features.engineer import (
    generate_feature_pipeline,
    get_available_feature_cols,
    FEATURE_COLS,
    ODDS_FEATURE_COLS,
)
from config import MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH, DB_PATH

MODEL_DIR = os.path.dirname(MODEL_PATH)
FEAT_COLS_OVER25  = os.path.join(MODEL_DIR, "over25_feature_cols.joblib")
FEAT_COLS_BTTS    = os.path.join(MODEL_DIR, "btts_feature_cols.joblib")
FEAT_COLS_OUTCOME = os.path.join(MODEL_DIR, "outcome_feature_cols.joblib")

# Minimum model probability to be flagged as a "high-confidence" pick
HIGH_CONF_THRESHOLD = 0.62


def _load_feat_cols(path: str, df: pd.DataFrame) -> list:
    """Load saved feature columns; fall back to inferring from df if missing."""
    if os.path.exists(path):
        cols = joblib.load(path)
        # Keep only columns that exist in live data (odds cols may not be present)
        return [c for c in cols if c in df.columns]
    # Fallback: infer from current data
    return get_available_feature_cols(df)


def score_todays_fixtures() -> pd.DataFrame:
    """
    Loads saved models and returns a scored DataFrame for today's fixtures.
    Returns an empty DataFrame if models or data are missing.
    """
    required = [MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH]
    if not all(os.path.exists(p) for p in required):
        print("⚠️  Model artefacts missing — run `python models/train.py` first.")
        return pd.DataFrame()

    model_over25  = joblib.load(MODEL_PATH)
    model_btts    = joblib.load(BTTS_MODEL_PATH)
    model_outcome = joblib.load(OUTCOME_MODEL_PATH)

    df_today = generate_feature_pipeline(extract_live_today_only=True)
    if df_today.empty:
        return pd.DataFrame()

    feat_over25  = _load_feat_cols(FEAT_COLS_OVER25,  df_today)
    feat_btts    = _load_feat_cols(FEAT_COLS_BTTS,    df_today)
    feat_outcome = _load_feat_cols(FEAT_COLS_OUTCOME, df_today)

    # Subset to common available columns (robustness if live data lacks odds cols)
    def _predict(model, feat_cols):
        X = df_today[feat_cols].fillna(df_today[feat_cols].median())
        return model.predict_proba(X)

    prob_over25_mat = _predict(model_over25, feat_over25)
    prob_btts_mat   = _predict(model_btts,   feat_btts)
    prob_outcome    = _predict(model_outcome, feat_outcome)

    prob_over25 = prob_over25_mat[:, 1]
    prob_btts   = prob_btts_mat[:, 1]

    # Confidence = how far from 0.5 the model is
    confidence  = (prob_over25 - 0.5).abs() if hasattr(prob_over25, "abs") else abs(prob_over25 - 0.5)
    confidence  = abs(prob_over25 - 0.5)

    df_output = pd.DataFrame({
        "match_id":           df_today["match_id"],
        "home_team":          df_today["home_team"],
        "away_team":          df_today["away_team"],
        "over_2_5_probability": prob_over25.round(4),
        "btts_probability":     prob_btts.round(4),
        "prob_home_win":        prob_outcome[:, 0].round(4),
        "prob_draw":            prob_outcome[:, 1].round(4),
        "prob_away_win":        prob_outcome[:, 2].round(4),
        "over25_confidence":    confidence.round(4),
        "high_conf_pick":       (prob_over25 >= HIGH_CONF_THRESHOLD) | (prob_over25 <= (1 - HIGH_CONF_THRESHOLD)),
    })

    # Merge kickoff times and bookmaker odds from DuckDB
    try:
        conn    = duckdb.connect(DB_PATH)
        df_meta = conn.execute(
            "SELECT match_id, match_time, odds_home, odds_draw, odds_away FROM historical_matches"
        ).df()
        conn.close()
        df_output = df_output.merge(df_meta, on="match_id", how="left")
    except Exception as e:
        print(f"⚠️  Could not merge odds metadata: {e}")

    return df_output.sort_values("over_2_5_probability", ascending=False)
