import os
import joblib
import pandas as pd
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH, BTTS_MODEL_PATH

def score_todays_fixtures():
    """Generates automated dual-market prediction arrays for matches scheduled today."""
    # Verify that BOTH model binaries exist before running calculations
    if not os.path.exists(MODEL_PATH) or not os.path.exists(BTTS_MODEL_PATH):
        print("⚠️ Missing model artifacts. Ensure both joblib files exist.")
        return pd.DataFrame()

    # Load both machine learning model weights
    model_over25 = joblib.load(MODEL_PATH)
    model_btts = joblib.load(BTTS_MODEL_PATH)
    
    # Query today's engineered match vectors
    df_today = generate_feature_pipeline(extract_live_today_only=True)
    
    if df_today is None or df_today.empty:
        return pd.DataFrame()
        
    # Define our input metrics
    feature_cols = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage'
    ]
    
    X_live = df_today[feature_cols]
    
    # Calculate target probabilities and verdicts for Over 2.5 Goals
    prob_over25 = model_over25.predict_proba(X_live)[:, 1]
    pred_over25 = model_over25.predict(X_live)
    
    # Calculate target probabilities and verdicts for Both Teams to Score (BTTS)
    prob_btts = model_btts.predict_proba(X_live)[:, 1]
    pred_btts = model_btts.predict(X_live)
    
    # Compile everything into a structured output dataframe for app.py
    df_output = pd.DataFrame({
        "home_team": df_today["home_team"],
        "away_team": df_today["away_team"],
        "over_2_5_probability": prob_over25.round(4),
        "over_2_5_verdict": pred_over25,
        "btts_probability": prob_btts.round(4),
        "btts_verdict": pred_btts
    })
    
    # Rank matches from highest likelihood of goals to lowest
    return df_output.sort_values(by="over_2_5_probability", ascending=False)
