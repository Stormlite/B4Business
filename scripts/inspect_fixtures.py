"""scripts/inspect_fixtures.py — inspect what's in the DuckDB and CSV data files"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb, pandas as pd
from config import DB_PATH
from features.engineer import load_csv_data

print("── DuckDB historical_matches ────────────────────────────")
conn = duckdb.connect(DB_PATH)
df_db = conn.execute("SELECT * FROM historical_matches LIMIT 5").df()
total = conn.execute("SELECT COUNT(*) FROM historical_matches").fetchone()[0]
conn.close()
print(f"Total rows: {total}")
print(df_db.to_string(index=False))

print("\n── CSV season files ─────────────────────────────────────")
df_csv = load_csv_data()
print(f"Total rows: {len(df_csv)}")
print("Columns:", df_csv.columns.tolist()[:15], "...")
print("Competitions:", df_csv["competition"].unique()[:10])
print(df_csv[["match_date","competition","home_team","away_team","home_score","away_score"]].head().to_string(index=False))
