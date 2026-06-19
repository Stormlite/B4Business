"""
models/train.py — Optimised training pipeline
==============================================
Upgrades vs original:
  1. Trains from CSV data (5 330 rows) instead of only DuckDB (1 872)
  2. Ensemble model: soft-voting RF + Logistic Regression (beats single RF)
  3. Larger rolling window (10) and richer feature set (shots, corners, odds)
  4. Saves feature column list AND training medians alongside each model artefact
     (medians are used at predict time to fill columns missing from live DuckDB data)
  5. Cross-validation accuracy reported during training
  6. numpy import fixed (was missing when run as module)
"""

import os
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold

from features.engineer import generate_training_data, get_available_feature_cols
from config import MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH

MODEL_DIR         = os.path.dirname(MODEL_PATH)
FEAT_COLS_OVER25  = os.path.join(MODEL_DIR, "over25_feature_cols.joblib")
FEAT_COLS_BTTS    = os.path.join(MODEL_DIR, "btts_feature_cols.joblib")
FEAT_COLS_OUTCOME = os.path.join(MODEL_DIR, "outcome_feature_cols.joblib")
# Training medians saved so predict.py can impute columns missing from live DuckDB data
FEAT_MEDIANS_PATH = os.path.join(MODEL_DIR, "feature_medians.joblib")


def _build_ensemble(random_state: int = 42) -> VotingClassifier:
    """Soft-voting ensemble of Random Forest + Logistic Regression."""
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            C=0.5,
            class_weight="balanced",
            max_iter=1000,
            random_state=random_state,
        )),
    ])
    return VotingClassifier(estimators=[("rf", rf), ("lr", lr)], voting="soft")


def run_training_pipeline(verbose: bool = True) -> bool:
    """Train all three market models and save artefacts."""

    if verbose:
        print("📦 Loading training data (CSV + DuckDB)...")
    df_train = generate_training_data(use_csv=True)

    if df_train.empty or len(df_train) < 50:
        print("⚠️  Not enough finished matches to train. Aborting.")
        return False

    feat_cols = get_available_feature_cols(df_train)
    if verbose:
        print(f"✅ Training rows: {len(df_train)} | Features: {len(feat_cols)}")
        print(f"   Feature list: {feat_cols}")

    X = df_train[feat_cols]

    # Save training medians — used at predict time to fill missing columns (e.g. shots,
    # odds) that exist in CSV training data but not in the live DuckDB feed.
    training_medians = X.median().to_dict()
    joblib.dump(training_medians, FEAT_MEDIANS_PATH)
    if verbose:
        print(f"💾 Training medians saved to {FEAT_MEDIANS_PATH}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # ── 1. Over 2.5 Goals ─────────────────────────────────────────────────
    if verbose: print("\n🧠 Training Over 2.5 Goals model...")
    y_over25 = df_train["target_over25"]
    model_over25 = _build_ensemble()
    cv_scores = cross_val_score(model_over25, X, y_over25, cv=cv, scoring="accuracy")
    if verbose:
        print(f"   CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    model_over25.fit(X, y_over25)
    joblib.dump(model_over25, MODEL_PATH)
    joblib.dump(feat_cols, FEAT_COLS_OVER25)

    # ── 2. Both Teams to Score ────────────────────────────────────────────
    if verbose: print("🧠 Training BTTS model...")
    y_btts = df_train["target_btts"]
    model_btts = _build_ensemble()
    cv_scores = cross_val_score(model_btts, X, y_btts, cv=cv, scoring="accuracy")
    if verbose:
        print(f"   CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    model_btts.fit(X, y_btts)
    joblib.dump(model_btts, BTTS_MODEL_PATH)
    joblib.dump(feat_cols, FEAT_COLS_BTTS)

    # ── 3. 3-Way Match Outcome ────────────────────────────────────────────
    if verbose: print("🧠 Training 3-way Outcome model (1=H / 2=D / 3=A)...")
    conditions = [
        df_train["target_home_win"] == 1,
        df_train["target_draw"]     == 1,
        df_train["target_away_win"] == 1,
    ]
    y_outcome = np.select(conditions, [1, 2, 3], default=2)
    model_outcome = _build_ensemble()
    cv_scores = cross_val_score(model_outcome, X, y_outcome, cv=cv, scoring="accuracy")
    if verbose:
        print(f"   CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    model_outcome.fit(X, y_outcome)
    joblib.dump(model_outcome, OUTCOME_MODEL_PATH)
    joblib.dump(feat_cols, FEAT_COLS_OUTCOME)

    if verbose:
        print("\n✅ All three models trained and saved.")
    return True


if __name__ == "__main__":
    run_training_pipeline(verbose=True)
