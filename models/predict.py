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
from config import MODEL_PATH, OVER05_MODEL_PATH, CORNERS_MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH, DB_PATH

MODEL_DIR         = os.path.dirname(MODEL_PATH)
FEAT_COLS_OVER25  = os.path.join(MODEL_DIR, "over25_feature_cols.joblib")
FEAT_COLS_OVER05  = os.path.join(MODEL_DIR, "over05_feature_cols.joblib")
FEAT_COLS_CORNERS = os.path.join(MODEL_DIR, "corners_feature_cols.joblib")
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
    # Corners is also a newer market — same optional-load pattern as Over 0.5,
    # plus this one can genuinely be missing training data for a given run
    # if too few rows had corner data (see train.py's guard).
    model_corners = joblib.load(CORNERS_MODEL_PATH) if os.path.exists(CORNERS_MODEL_PATH) else None

    feat_over25  = joblib.load(FEAT_COLS_OVER25)  if os.path.exists(FEAT_COLS_OVER25)  else None
    feat_over05  = joblib.load(FEAT_COLS_OVER05)  if os.path.exists(FEAT_COLS_OVER05)  else None
    feat_corners = joblib.load(FEAT_COLS_CORNERS) if os.path.exists(FEAT_COLS_CORNERS) else None
    feat_btts    = joblib.load(FEAT_COLS_BTTS)    if os.path.exists(FEAT_COLS_BTTS)    else None
    feat_outcome = joblib.load(FEAT_COLS_OUTCOME) if os.path.exists(FEAT_COLS_OUTCOME) else None

    medians = _load_medians()

    df_today = generate_feature_pipeline(extract_live_today_only=True, target_date=target_date)
    if df_today.empty:
        return pd.DataFrame()

    live_cols    = get_available_feature_cols(df_today)
    feat_over25  = feat_over25  or live_cols
    feat_over05  = feat_over05  or live_cols
    feat_corners = feat_corners or live_cols
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

    if model_corners is not None:
        X_corners    = _build_feature_matrix(df_today, feat_corners, medians)
        prob_corners = model_corners.predict_proba(X_corners)[:, 1]
    else:
        prob_corners = np.full(len(df_today), np.nan)

    confidence = np.abs(prob_over25 - 0.5)

    df_output = pd.DataFrame({
        "match_id":             df_today["match_id"],
        "home_team":            df_today["home_team"],
        "away_team":            df_today["away_team"],
        "over_2_5_probability": prob_over25.round(4),
        "over_0_5_probability": np.round(prob_over05, 4),
        "corners_probability":  np.round(prob_corners, 4),
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


PREDICTIONS_TABLE = "daily_predictions"


def save_predictions(df: pd.DataFrame, target_date: str):
    """
    Persists scored predictions for a date into a dedicated DuckDB table, so
    the Streamlit app can read them back near-instantly instead of re-running
    the full pipeline (rolling stats over the whole match history, model
    inference) on every page load. Called from the pipeline run, after
    retraining — this is the same computation notify.py already does for its
    own WhatsApp message, just now saved for the app to reuse too.
    """
    if df is None or df.empty:
        return
    conn = duckdb.connect(DB_PATH)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {PREDICTIONS_TABLE} (
            match_id INTEGER,
            match_date VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            match_time VARCHAR,
            over_2_5_probability DOUBLE,
            over_0_5_probability DOUBLE,
            corners_probability DOUBLE,
            btts_probability DOUBLE,
            prob_home_win DOUBLE,
            prob_draw DOUBLE,
            prob_away_win DOUBLE,
            over25_confidence DOUBLE,
            high_conf_pick BOOLEAN,
            has_market_odds BOOLEAN,
            odds_home REAL,
            odds_draw REAL,
            odds_away REAL,
            computed_at TIMESTAMP,
            PRIMARY KEY (match_id)
        )
    """)
    to_save = df.copy()
    to_save["match_date"] = target_date
    to_save["computed_at"] = pd.Timestamp.now()
    cols = ["match_id", "match_date", "home_team", "away_team", "match_time",
            "over_2_5_probability", "over_0_5_probability", "corners_probability",
            "btts_probability", "prob_home_win", "prob_draw", "prob_away_win",
            "over25_confidence", "high_conf_pick", "has_market_odds",
            "odds_home", "odds_draw", "odds_away", "computed_at"]
    for c in cols:
        if c not in to_save.columns:
            to_save[c] = None
    to_save = to_save[cols]

    # Clear any previous predictions for this date first — fixture counts and
    # match_ids can shift between runs (postponements, new fixtures added),
    # so a plain upsert could leave stale rows behind. Then insert fresh.
    conn.register("df_temp", to_save)
    conn.execute(f"DELETE FROM {PREDICTIONS_TABLE} WHERE match_date = ?", [target_date])
    conn.execute(f"INSERT INTO {PREDICTIONS_TABLE} SELECT * FROM df_temp")
    conn.close()
    print(f"✅ Saved {len(to_save)} precomputed predictions for {target_date}.")


def load_precomputed_predictions(target_date: str) -> pd.DataFrame:
    """
    Reads back predictions saved by save_predictions(), if present. Returns
    an empty DataFrame if the table doesn't exist yet or has no rows for
    this date — callers should fall back to score_todays_fixtures() (a live
    computation) in that case, so this never blocks a fresh deployment or a
    date the pipeline hasn't precomputed for.
    """
    try:
        conn = duckdb.connect(DB_PATH)
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        if PREDICTIONS_TABLE not in tables:
            conn.close()
            return pd.DataFrame()
        df = conn.execute(
            f"SELECT * FROM {PREDICTIONS_TABLE} WHERE match_date = ?", [target_date]
        ).df()
        conn.close()
        if df.empty:
            return df
        return df.sort_values("over_2_5_probability", ascending=False)
    except Exception as e:
        print(f"⚠️  Could not load precomputed predictions: {e}")
        return pd.DataFrame()
