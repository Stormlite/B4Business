"""
models/predict.py — Live prediction scorer
==========================================
Key fix: when live DuckDB data is missing columns that the model was trained on
(shots, odds, corners from CSV), we fill them with the training-time medians
saved during model training. NaN values within present columns are also filled
with training medians so the LR component of the ensemble never sees NaN input.
"""

import os
import joblib
import pandas as pd
import numpy as np
import duckdb

from features.engineer import (
    generate_feature_pipeline,
    get_available_feature_cols,
)
from config import MODEL_PATH, OVER05_MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH, DB_PATH

MODEL_DIR         = os.path.dirname(MODEL_PATH)
FEAT_COLS_OVER25  = os.path.join(MODEL_DIR, "over25_feature_cols.joblib")
FEAT_COLS_OVER05  = os.path.join(MODEL_DIR, "over05_feature_cols.joblib")
FEAT_COLS_BTTS    = os.path.join(MODEL_DIR, "btts_feature_cols.joblib")
FEAT_COLS_OUTCOME = os.path.join(MODEL_DIR, "outcome_feature_cols.joblib")
FEAT_MEDIANS_PATH = os.path.join(MODEL_DIR, "feature_medians.joblib")

HIGH_CONF_THRESHOLD = 0.62

# high_conf_pick is deliberately based on the Over 2.5 model only — not Over 0.5.
# Over 0.5 predictions cluster around 90-97% for nearly every match (the market
# is inherently ~94/6 skewed), so a confidence threshold on it would flag almost
# every fixture as "high confidence" and the flag would stop meaning anything.
# Over 2.5 is close to 50/50 league-wide, so crossing 62% there is a real signal.


def _load_medians() -> dict:
    """Load training medians; return empty dict if not yet saved."""
    if os.path.exists(FEAT_MEDIANS_PATH):
        return joblib.load(FEAT_MEDIANS_PATH)
    return {}


def _build_feature_matrix(df: pd.DataFrame, feat_cols: list, medians: dict) -> pd.DataFrame:
    """
    Build a feature matrix that always has every column the model expects.
    - Columns missing from live data → filled with training-time median
    - NaN values within present columns → also filled with training-time median
    This prevents both the sklearn feature-name mismatch AND the NaN error from
    the Logistic Regression component of the ensemble.
    """
    X = pd.DataFrame(index=df.index)
    for col in feat_cols:
        fallback = float(medians.get(col, 0.0))
        if col in df.columns:
            X[col] = df[col].fillna(fallback).values
        else:
            X[col] = fallback
    return X


def score_todays_fixtures(target_date: str = None) -> pd.DataFrame:
    """
    Loads saved models and returns a scored DataFrame for the given date
    (defaults to today). Returns an empty DataFrame if models or data are
    missing. target_date='YYYY-MM-DD' lets the same scorer serve a
    'Tomorrow' view using fixtures pre-fetched a day ahead by collector.py.
    """
    required = [MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH]
    if not all(os.path.exists(p) for p in required):
        print("⚠️  Model artefacts missing — run `python -m models.train` first.")
        return pd.DataFrame()

    model_over25  = joblib.load(MODEL_PATH)
    model_btts    = joblib.load(BTTS_MODEL_PATH)
    model_outcome = joblib.load(OUTCOME_MODEL_PATH)
    # Over 0.5 is a newer market — model may not exist yet on older deployments
    # until the next training run, so it's optional rather than required.
    model_over05  = joblib.load(OVER05_MODEL_PATH) if os.path.exists(OVER05_MODEL_PATH) else None

    feat_over25  = joblib.load(FEAT_COLS_OVER25)  if os.path.exists(FEAT_COLS_OVER25)  else None
    feat_over05  = joblib.load(FEAT_COLS_OVER05)  if os.path.exists(FEAT_COLS_OVER05)  else None
    feat_btts    = joblib.load(FEAT_COLS_BTTS)    if os.path.exists(FEAT_COLS_BTTS)    else None
    feat_outcome = joblib.load(FEAT_COLS_OUTCOME) if os.path.exists(FEAT_COLS_OUTCOME) else None

    medians = _load_medians()

    df_today = generate_feature_pipeline(extract_live_today_only=True, target_date=target_date)
    if df_today.empty:
        return pd.DataFrame()

    live_cols    = get_available_feature_cols(df_today)
    feat_over25  = feat_over25  or live_cols
    feat_over05  = feat_over05  or live_cols
    feat_btts    = feat_btts    or live_cols
    feat_outcome = feat_outcome or live_cols

    X_over25  = _build_feature_matrix(df_today, feat_over25,  medians)
    X_btts    = _build_feature_matrix(df_today, feat_btts,    medians)
    X_outcome = _build_feature_matrix(df_today, feat_outcome, medians)

    prob_over25  = model_over25.predict_proba(X_over25)[:, 1]
    prob_btts    = model_btts.predict_proba(X_btts)[:, 1]
    prob_outcome = model_outcome.predict_proba(X_outcome)

    if model_over05 is not None:
        X_over05    = _build_feature_matrix(df_today, feat_over05, medians)
        prob_over05 = model_over05.predict_proba(X_over05)[:, 1]
    else:
        prob_over05 = np.full(len(df_today), np.nan)

    confidence = np.abs(prob_over25 - 0.5)

    df_output = pd.DataFrame({
        "match_id":             df_today["match_id"],
        "home_team":            df_today["home_team"],
        "away_team":            df_today["away_team"],
        "over_2_5_probability": prob_over25.round(4),
        "over_0_5_probability": np.round(prob_over05, 4),
        "btts_probability":     prob_btts.round(4),
        "prob_home_win":        prob_outcome[:, 0].round(4),
        "prob_draw":            prob_outcome[:, 1].round(4),
        "prob_away_win":        prob_outcome[:, 2].round(4),
        "over25_confidence":    confidence.round(4),
        # Over 2.5 only — see HIGH_CONF_THRESHOLD comment above for why.
        "high_conf_pick":       (prob_over25 >= HIGH_CONF_THRESHOLD) | (prob_over25 <= (1 - HIGH_CONF_THRESHOLD)),
        # True only if real market odds were found for this fixture. When False,
        # the 1X2/outcome probabilities above were computed with a median-imputed
        # odds feature — still a real model output, but without the market's
        # signal, which the outcome model leans on heavily (~30% combined
        # importance). The app should flag this rather than show it silently.
        "has_market_odds":      df_today.get("has_market_odds", pd.Series(False, index=df_today.index)).values,
    })

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
