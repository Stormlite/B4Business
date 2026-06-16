import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH

def run_training_pipeline():
    print("🏋️ Extracting historical features from database...")
    df_train = generate_feature_pipeline(extract_live_today_only=False)
    
    if df_train.empty or len(df_train) < 10:
        print("⚠️ Not enough completed matches found to execute training.")
        return False

    feature_cols = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage',
        'combined_btts_trend'
    ]
    X = df_train[feature_cols]
    
    # 1. Over 2.5 Goals
    print("🧠 Training Over 2.5 Goals Predictor...")
    model_over25 = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
    model_over25.fit(X, df_train['target_over25'])
    joblib.dump(model_over25, MODEL_PATH)
    
    # 2. Both Teams to Score (BTTS)
    print("🧠 Training Both Teams to Score (BTTS) Predictor...")
    model_btts = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
    model_btts.fit(X, df_train['target_btts'])
    joblib.dump(model_btts, BTTS_MODEL_PATH)
    
    # 🌟 NEW: Multi-Class 3-Way Outcome Model Training (1=Home Win, 2=Draw, 3=Away Win)
    print("🧠 Training 3-Way Match Outcome Predictor...")
    conditions = [
        df_train['target_home_win'] == 1,
        df_train['target_draw'] == 1,
        df_train['target_away_win'] == 1
    ]
    choices = [1, 2, 3]
    y_outcome = np.select(conditions, choices, default=2)
    
    model_outcome = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
    model_outcome.fit(X, y_outcome)
    joblib.dump(model_outcome, OUTCOME_MODEL_PATH)
    
    print("📦 Multi-market machine learning retraining complete.")
    return True

if __name__ == "__main__":
    import numpy as np
    run_training_pipeline()
