"""
scripts/eval_model.py — Model evaluation with confidence-tier reporting
======================================================================
Run:  python scripts/eval_model.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, brier_score_loss, precision_score,
    recall_score, roc_auc_score,
)

from features.engineer import generate_training_data, get_available_feature_cols
from config import MODEL_PATH

def evaluate():
    print("📊 Loading training data...")
    df = generate_training_data(use_csv=True)
    if df.empty:
        print("❌ No data found."); return

    feat_cols = get_available_feature_cols(df)
    X = df[feat_cols]
    y = df["target_over25"]

    print(f"   Rows: {len(df)} | Features: {len(feat_cols)}")
    print(f"   Over-2.5 base rate: {y.mean():.3f}\n")

    model = joblib.load(MODEL_PATH)
    cv    = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Cross-validated probabilities (no data leakage)
    probs = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    preds = (probs >= 0.5).astype(int)

    print("─── Overall Performance ────────────────────────────────")
    print(f"  Accuracy  : {accuracy_score(y, preds):.4f}")
    print(f"  AUC-ROC   : {roc_auc_score(y, probs):.4f}")
    print(f"  Brier     : {brier_score_loss(y, probs):.4f}")
    print(f"  Precision : {precision_score(y, preds, zero_division=0):.4f}")
    print(f"  Recall    : {recall_score(y, preds, zero_division=0):.4f}")

    print("\n─── Confidence-Tier Accuracy (key for selective betting) ──")
    for thresh in [0.55, 0.60, 0.65, 0.70]:
        mask = (probs >= thresh) | (probs <= (1 - thresh))
        if mask.sum() < 30:
            continue
        tier_acc = accuracy_score(y.values[mask], (probs[mask] >= 0.5).astype(int))
        tier_pct = mask.mean() * 100
        print(f"  ≥{int(thresh*100)}% confidence: {tier_acc:.4f} acc  "
              f"on {mask.sum()} games ({tier_pct:.1f}% of all fixtures)")

    print("\n─── Feature Importances (from RF component) ──────────────")
    # Extract RF from ensemble if possible
    try:
        rf = dict(model.named_estimators_)["rf"]
        importances = sorted(
            zip(feat_cols, rf.feature_importances_), key=lambda x: -x[1]
        )
        for name, imp in importances[:10]:
            print(f"  {name:30s}  {imp:.4f}")
    except Exception:
        print("  (Could not extract feature importances from this model type)")

if __name__ == "__main__":
    evaluate()
