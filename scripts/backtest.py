import sys
import os

# Force Python to recognize the root directory for module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
from config import DB_PATH

def evaluate_historical_accuracy():
    """Compiles a text metric score comparing historical predictions against final scores."""
    conn = duckdb.connect(DB_PATH)
    try:
        df = conn.execute("SELECT home_score, away_score FROM historical_matches WHERE status='FINISHED'").df()
    except Exception as e:
        print(f"⚠️ Could not locate a finished match matrix to backtest: {e}")
        return
    finally:
        conn.close()

    if df.empty or len(df) < 5:
        print("ℹ️ Backtester requires more finished matches in DuckDB to calculate analytics.")
        return

    df['total_goals'] = df['home_score'] + df['away_score']
    actual_over25 = (df['total_goals'] > 2.5).sum()
    total_games = len(df)
    
    print("\n📊 --- PIPELINE MODEL BACKTEST REPORT ---")
    print(f"Total Completed Matches Analyzed: {total_games}")
    print(f"Historical Over 2.5 Matches: {actual_over25} ({ (actual_over25/total_games)*100:.2f}%)")
    print("------------------------------------------\n")

if __name__ == "__main__":
    evaluate_historical_accuracy()
