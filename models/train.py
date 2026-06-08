# import argparse
# from datetime import datetime
# from pathlib import Path

# import duckdb
# import joblib
# import numpy as np
# import pandas as pd
# from sklearn.metrics import accuracy_score, brier_score_loss, classification_report
# from sklearn.pipeline import Pipeline
# from sklearn.preprocessing import StandardScaler
# from xgboost import XGBClassifier

# from config import DB_PATH, MODEL_DIR, MODEL_PATH
# from features.engineer import build_features, select_feature_matrix

# MODEL_DIR.mkdir(parents=True, exist_ok=True)


# def load_matches() -> pd.DataFrame:
#     con = duckdb.connect(DB_PATH)
#     df = con.execute("SELECT * FROM matches ORDER BY date").df()
#     con.close()
#     df["date"] = pd.to_datetime(df["date"])
#     return df


# def time_series_split(df: pd.DataFrame, test_size: float = 0.2):
#     cutoff = int(len(df) * (1.0 - test_size))
#     train = df.iloc[:cutoff]
#     test = df.iloc[cutoff:]
#     return train, test


# def train_model(fast: bool = False) -> None:
#     df = load_matches()
#     features = build_features(df)
#     X, y = select_feature_matrix(features)

#     train_df, test_df = time_series_split(features, test_size=0.15)
#     X_train, y_train = select_feature_matrix(train_df)
#     X_test, y_test = select_feature_matrix(test_df)

#     parser = None
#     # Allow a fast training mode for quick iterations
#     # Compute class imbalance
#     neg = (y_train == 0).sum()
#     pos = (y_train == 1).sum()
#     scale_pos_weight = float(neg / pos) if pos > 0 else 1.0

#     clf = XGBClassifier(
#         n_estimators=300 if not fast else 100,
#         max_depth=6,
#         learning_rate=0.05 if not fast else 0.1,
#         subsample=0.8,
#         colsample_bytree=0.8,
#         use_label_encoder=False,
#         eval_metric="logloss",
#         scale_pos_weight=scale_pos_weight,
#         random_state=42,
#         verbosity=0,
#     )
#     pipeline = Pipeline([("scaler", StandardScaler()), ("clf", clf)])

#     print("Starting training pipeline.fit()...")
#     pipeline.fit(X_train, y_train)
#     print("Training complete — evaluating...")
#     y_pred = pipeline.predict(X_test)
#     # some classifiers may not implement predict_proba; handle gracefully
#     try:
#         y_prob = pipeline.predict_proba(X_test)[:, 1]
#     except Exception:
#         y_prob = (y_pred).astype(float)

#     acc = accuracy_score(y_test, y_pred)
#     brier = brier_score_loss(y_test, y_prob)
#     report = classification_report(y_test, y_pred, digits=4)
#     prob_min, prob_max, prob_mean, prob_median = float(y_prob.min()), float(y_prob.max()), float(y_prob.mean()), float(np.median(y_prob))
#     positive_ratio = float((y_pred == 1).mean())

#     joblib.dump(pipeline, MODEL_PATH)

#     print(f"Model saved to {MODEL_PATH}")
#     print(f"Accuracy: {acc:.4f}")
#     print(f"Brier score: {brier:.4f}")
#     print(f"Predicted positive ratio: {positive_ratio:.4f}")
#     print(f"Probability min/max/mean/median: {prob_min:.4f}/{prob_max:.4f}/{prob_mean:.4f}/{prob_median:.4f}")
#     print("Classification report:")
#     print(report)


# def main() -> None:
#     parser = argparse.ArgumentParser(description="Train the over 2.5 goals model.")
#     parser.add_argument("--train", action="store_true", help="Train the model using the match database.")
#     parser.add_argument("--fast", action="store_true", help="Run a fast baseline training (XGBoost small).")
#     args = parser.parse_args()

#     if args.train:
#         train_model(fast=args.fast)


# if __name__ == "__main__":
#     main()

import os
import argparse
import joblib
from sklearn.ensemble import RandomForestClassifier
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH

def run_training_pipeline():
    """Extracts historical datasets from DuckDB and trains a time-aware model."""
    print("🏋️ Extracting dynamic historical features from database...")
    df_train = generate_feature_pipeline(extract_live_today_only=False)
    
    if df_train.empty or len(df_train) < 10:
        print("⚠️ Not enough completed matches found in database to safely train a model. (Minimum required: 10 rows).")
        return False

    # Define the predictive inputs
    feature_cols = [
        'home_rolling_scored', 
        'home_rolling_conceded', 
        'away_rolling_scored', 
        'away_rolling_conceded',
        'combined_rolling_scoring_power',
        'combined_rolling_defensive_leakage'
    ]
    
    X = df_train[feature_cols]
    y = df_train['target_over25']
    
    print(f"📊 Training dataset contains {len(df_train)} rows across {len(feature_cols)} engineered parameters.")
    
    # Initialize a balanced, robust Random Forest Classifier
    model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=6, 
        random_state=42,
        class_weight='balanced'
    )
    
    model.fit(X, y)
    
    # Ensure directory path structure exists
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    # Save the trained model artifact to your path definition
    joblib.dump(model, MODEL_PATH)
    print(f"📦 Automated daily retraining complete. Model stored successfully at: {MODEL_PATH}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Training Execution CLI")
    parser.add_argument("--train", action="store_true", help="Execute model retraining optimization pipeline")
    args = parser.parse_args()
    
    if args.train:
        run_training_pipeline()
    else:
        # Default fallback to run training if triggered without tags by the workflow
        run_training_pipeline()
