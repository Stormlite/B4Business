import os
import argparse
import joblib
from sklearn.ensemble import RandomForestClassifier
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH

def run_training_pipeline():
    """Extracts historical datasets and trains both Over 2.5 and BTTS models."""
    print("🏋️ Extracting dynamic historical features from database...")
    df_train = generate_feature_pipeline(extract_live_today_only=False)
    
    if df_train.empty or len(df_train) < 10:
        print("⚠️ Not enough completed matches found in database to safely train.")
        return False

    feature_cols = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage',
        'combined_btts_trend'
    ]
    
    X = df_train[feature_cols]
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    # 🌟 MODEL 1: Train Over 2.5 Goals Predictor
    print("🎯 Training Over 2.5 Classifier...")
    y_o25 = df_train['target_over25']
    model_o25 = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
    model_o25.fit(X, y_o25)
    joblib.dump(model_o25, MODEL_PATH)
    print(f"✅ Over 2.5 Model saved at: {MODEL_PATH}")
    
    # 🌟 MODEL 2: Train BTTS Predictor
    print("🎯 Training Both Teams To Score (BTTS) Classifier...")
    y_btts = df_train['target_btts']
    model_btts = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
    model_btts.fit(X, y_btts)
    
    # Derive BTTS save path relative to central config path
    btts_path = os.path.join(os.path.dirname(MODEL_PATH), "btts_model.joblib")
    joblib.dump(model_btts, btts_path)
    print(f"✅ BTTS Model saved at: {btts_path}")
    
    print("📦 Automated daily multi-model retraining complete!")
    return True

if __name__ == "__main__":
    run_training_pipeline()
