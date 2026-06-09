import os
import joblib
import pandas as pd
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH

def score_todays_fixtures():
    """Generates automated prediction vectors for matches scheduled today across multiple markets."""
    btts_path = os.path.join(os.path.dirname(MODEL_PATH), "btts_model.joblib")
    
    if not os.path.exists(MODEL_PATH) or not os.path.exists(btts_path):
        return pd.DataFrame()

    # Load both models
    model_o25 = joblib.load(MODEL_PATH)
    model_btts = joblib.load(btts_path)
    
    df_today = generate_feature_pipeline(extract_live_today_only=True)
    if df_today.empty:
        return pd.DataFrame()
        
    feature_cols = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage',
        'combined_btts_trend'
    ]
    
    X_live = df_today[feature_cols]
    
    # Generate Dual Predictions
    prob_o25 = model_o25.predict_proba(X_live)[:, 1]
    pred_o25 = model_o25.predict(X_live)
    
    prob_btts = model_btts.predict_proba(X_live)[:, 1]
    pred_btts = model_btts.predict(X_live)
    
    df_output = pd.DataFrame({
        "home_team": df_today["home_team"],
        "away_team": df_today["away_team"],
        "over_2_5_probability": prob_o25.round(4),
        "over_2_5_verdict": pred_o25,
        "btts_probability": prob_btts.round(4),
        "btts_verdict": pred_btts
    })
    
    return df_output.sort_values(by="over_2_5_probability", ascending=False)
