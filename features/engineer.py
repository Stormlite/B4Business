import pandas as pd
import numpy as np
import duckdb
from config import DB_PATH

def load_raw_data_from_db():
    """Queries all matches from DuckDB ordered chronologically."""
    conn = duckdb.connect(DB_PATH)
    query = """
        SELECT 
            match_id, match_date, competition, home_team, away_team,
            CAST(home_score AS REAL) as home_score,
            CAST(away_score AS REAL) as away_score, status
        FROM historical_matches
        ORDER BY match_date ASC
    """
    df = conn.execute(query).df()
    conn.close()
    
    df['total_goals'] = df['home_score'] + df['away_score']
    
    # Core Targets
    df['target_over25'] = np.where(df['total_goals'] > 2.5, 1, 0)
    df['target_btts'] = np.where((df['home_score'] > 0) & (df['away_score'] > 0), 1, 0)
    
    # 🌟 NEW: 3-Way Match Outcome Targets
    df['target_home_win'] = np.where(df['home_score'] > df['away_score'], 1, 0)
    df['target_draw'] = np.where(df['home_score'] == df['away_score'], 1, 0)
    df['target_away_win'] = np.where(df['home_score'] < df['away_score'], 1, 0)
    
    return df

def calculate_rolling_stats(df, window=5):
    """Calculates team metrics using shifting rolling windows to prevent data leakage."""
    df = df.sort_values('match_date').reset_index(drop=True)
    
    home_side = df[['match_id', 'match_date', 'home_team', 'home_score', 'away_score']].rename(
        columns={'home_team': 'team', 'home_score': 'goals_scored', 'away_score': 'goals_conceded'}
    )
    home_side['is_home'] = 1
    
    away_side = df[['match_id', 'match_date', 'away_team', 'away_score', 'home_score']].rename(
        columns={'away_team': 'team', 'away_score': 'goals_scored', 'home_score': 'goals_conceded'}
    )
    away_side['is_home'] = 0
    
    team_history = pd.concat([home_side, away_side], axis=0).sort_values(['team', 'match_date'])
    
    team_history['rolling_scored'] = team_history.groupby('team')['goals_scored'].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).mean()
    )
    team_history['rolling_conceded'] = team_history.groupby('team')['goals_conceded'].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).mean()
    )
    
    team_history['rolling_scored'] = team_history['rolling_scored'].fillna(1.2)
    team_history['rolling_conceded'] = team_history['rolling_conceded'].fillna(1.2)
    
    home_stats = team_history[team_history['is_home'] == 1][['match_id', 'rolling_scored', 'rolling_conceded']].rename(
        columns={'rolling_scored': 'home_rolling_scored', 'rolling_conceded': 'home_rolling_conceded'}
    )
    away_stats = team_history[team_history['is_home'] == 0][['match_id', 'rolling_scored', 'rolling_conceded']].rename(
        columns={'rolling_scored': 'away_rolling_scored', 'rolling_conceded': 'away_rolling_conceded'}
    )
    
    df = df.merge(home_stats, on='match_id', how='left')
    df = df.merge(away_stats, on='match_id', how='left')
    
    df['combined_rolling_scoring_power'] = df['home_rolling_scored'] + df['away_rolling_scored']
    df['combined_rolling_defensive_leakage'] = df['home_rolling_conceded'] + df['away_rolling_conceded']
    df['combined_btts_trend'] = (df['home_rolling_scored'] * 0.5) + (df['away_rolling_scored'] * 0.5)
    
    return df

def generate_feature_pipeline(extract_live_today_only=False):
    """Returns data split into historical training variables or today's prediction rows."""
    df_raw = load_raw_data_from_db()
    if df_raw.empty:
        return pd.DataFrame()
        
    df_features = calculate_rolling_stats(df_raw)
    
    feature_columns = [
        'home_rolling_scored', 'home_rolling_conceded', 
        'away_rolling_scored', 'away_rolling_conceded',
        'combined_rolling_scoring_power', 'combined_rolling_defensive_leakage',
        'combined_btts_trend'
    ]
    
    if extract_live_today_only:
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        df_today = df_features[df_features['match_date'] == today_str]
        return df_today[['match_id', 'match_date', 'home_team', 'away_team'] + feature_columns]
        
    # 🌟 NEW: Include 3-way match outcome targets in training output arrays
    df_train = df_features[df_features['status'] == 'FINISHED'].dropna(subset=['target_over25', 'target_btts'])
    return df_train[['match_id', 'match_date', 'target_over25', 'target_btts', 'target_home_win', 'target_draw', 'target_away_win'] + feature_columns]
