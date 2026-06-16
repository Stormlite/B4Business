import os
import joblib
import pandas as pd
import duckdb
from features.engineer import generate_feature_pipeline
from config import MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH, DB_PATH

def score_todays_fixtures():
    if not all(os.path.exists(p) for p in [MODEL_PATH, BTTS_MODEL_PATH, OUTCOME_MODEL_PATH]):
        return pd.DataFrame()

    model_over25 = joblib.load(MODEL_PATH)
    model_btts = joblib.load(BTTS_MODEL_PATH)
    model_outcome = joblib.load(OUTCOME_MODEL_PATH)
    
    df_today = generate_feature_pipeline(extract_live_today_only=True)
    if df_today.empty: return pd.DataFrame()
        
    feature_cols = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage',
        'combined_btts_trend'
    ]
    X_live = df_today[feature_cols]
    
    # Basic goal probabilities
    prob_over25 = model_over25.predict_proba(X_live)[:, 1]
    prob_btts = model_btts.predict_proba(X_live)[:, 1]
    
    # 🌟 3-Way Outcome Probabilities Matrix
    prob_outcome = model_outcome.predict_proba(X_live) # Returns 3 columns: [Home, Draw, Away]
    
    df_output = pd.DataFrame({
        "match_id": df_today["match_id"],
        "home_team": df_today["home_team"],
        "away_team": df_today["away_team"],
        "over_2_5_probability": prob_over25.round(4),
        "btts_probability": prob_btts.round(4),
        "prob_home_win": prob_outcome[:, 0].round(4),
        "prob_draw": prob_outcome[:, 1].round(4),
        "prob_away_win": prob_outcome[:, 2].round(4)
    })
    
    # 🌟 Stitch Match Kickoff Times and Betting Odds directly from DuckDB
    conn = duckdb.connect(DB_PATH)
    df_meta = conn.execute("SELECT match_id, match_time, odds_home, odds_draw, odds_away FROM historical_matches").df()
    conn.close()
    
    df_output = df_output.merge(df_meta, on="match_id", how="left")
    return df_output
