# import argparse
# from datetime import datetime
# from pathlib import Path
# from typing import List

# import pandas as pd
# import requests
# import duckdb

# from config import DATA_DIR, DB_PATH, LEAGUE_CODES, SEASONS

# BASE_URL = "https://www.football-data.co.uk/mmz4281"

# CSV_COLUMNS = [
#     "Date",
#     "HomeTeam",
#     "AwayTeam",
#     "FTHG",
#     "FTAG",
#     "FTR",
#     "HTHG",
#     "HTAG",
#     "HTR",
#     "Referee",
#     "HS",
#     "AS",
#     "HST",
#     "AST",
#     "HF",
#     "AF",
#     "HC",
#     "AC",
#     "HY",
#     "AY",
#     "HR",
#     "AR",
#     "BWH",
#     "BWD",
#     "BWA",
#     "PSH",
#     "PSD",
#     "PSA",
#     "WHH",
#     "WHD",
#     "WHA",
#     "VCH",
#     "VCD",
#     "VCA",
#     "Bb1X2",
#     "BbMxH",
#     "BbAvH",
#     "BbMxD",
#     "BbAvD",
#     "BbMxA",
#     "BbAvA",
#     "BbOU",
#     "BbMx>2.5",
#     "BbAv>2.5",
#     "BbMx<2.5",
#     "BbAv<2.5",
#     "BbAH",
#     "BbAHh",
#     "BbMxAHH",
#     "BbAvAHH",
#     "BbMxAHA",
#     "BbAvAHA",
# ]


# def ensure_paths() -> None:
#     DATA_DIR.mkdir(parents=True, exist_ok=True)


# def download_csv(season: str, league_code: str) -> Path:
#     season_dir = DATA_DIR / season
#     season_dir.mkdir(parents=True, exist_ok=True)
#     file_name = f"{league_code}.csv"
#     target_path = season_dir / file_name
#     if target_path.exists():
#         return target_path

#     url = f"{BASE_URL}/{season}/{file_name}"
#     response = requests.get(url, timeout=20)
#     response.raise_for_status()
#     target_path.write_bytes(response.content)
#     return target_path


# def load_csv(path: Path, league_code: str, season: str) -> pd.DataFrame:
#     df = pd.read_csv(path, dayfirst=True, parse_dates=["Date"], encoding="latin1", on_bad_lines="skip")
#     if df.empty:
#         return df

#     columns = {"Date": "date", "HomeTeam": "home_team", "AwayTeam": "away_team", "FTHG": "home_goals", "FTAG": "away_goals", "FTR": "result"}
#     df = df.rename(columns=columns)
#     keep = [c for c in ["date", "home_team", "away_team", "home_goals", "away_goals", "HS", "AS", "HST", "AST", "BbAv>2.5", "BbOU"] if c in df.columns]
#     df = df[keep]
#     df = df.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"])
#     df["competition"] = LEAGUE_CODES.get(league_code, league_code)
#     df["season"] = season
#     df["total_goals"] = df["home_goals"] + df["away_goals"]
#     if "BbAv>2.5" in df.columns:
#         df["odds_over_2_5"] = pd.to_numeric(df["BbAv>2.5"], errors="coerce")
#     else:
#         df["odds_over_2_5"] = pd.NA

#     df = df.sort_values("date").reset_index(drop=True)
#     # rename shot columns if present
#     if "HS" in df.columns:
#         df = df.rename(columns={"HS": "home_shots", "AS": "away_shots", "HST": "home_sot", "AST": "away_sot"})

#     out_cols = ["date", "competition", "season", "home_team", "away_team", "home_goals", "away_goals", "total_goals", "odds_over_2_5"]
#     for col in ["home_shots", "away_shots", "home_sot", "away_sot"]:
#         if col in df.columns:
#             out_cols.append(col)

#     return df[out_cols]


# def build_match_database() -> None:
#     ensure_paths()
#     records: List[pd.DataFrame] = []
#     for season in SEASONS:
#         for league_code in LEAGUE_CODES:
#             try:
#                 csv_path = download_csv(season, league_code)
#                 df = load_csv(csv_path, league_code, season)
#                 if not df.empty:
#                     records.append(df)
#             except Exception as exc:
#                 print(f"Skipping {league_code} {season}: {exc}")

#     if not records:
#         raise RuntimeError("No datasets were loaded. Check internet connectivity and league metadata.")

#     all_matches = pd.concat(records, ignore_index=True)
#     con = duckdb.connect(DB_PATH)
#     con.register("all_matches", all_matches)
#     con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM all_matches")
#     con.execute("COPY matches TO '" + str(DATA_DIR / "matches.parquet") + "' (FORMAT PARQUET)")
#     con.close()
#     print(f"Built database with {len(all_matches)} matches at {DB_PATH}")


# def main() -> None:
#     parser = argparse.ArgumentParser(description="Download and build football match data for over 2.5 prediction.")
#     parser.add_argument("--build-db", action="store_true", help="Download league CSVs and build the match database.")
#     args = parser.parse_args()

#     if args.build_db:
#         build_match_database()


# if __name__ == "__main__":
#     main()


import os
import argparse
import datetime
import requests
import pandas as pd
import duckdb
from config import DB_PATH  # Pulls the central db path from your config.py

API_URL = "https://football-data.org"

def fetch_todays_fixtures_from_api():
    """Fetches real-world fixtures happening today using the API token."""
    api_key = os.getenv("FOOTBALL_API_APIKEY")
    if not api_key:
        print("⚠️ Warning: FOOTBALL_API_APIKEY environment variable not set.")
        return pd.DataFrame()

    headers = {"X-Auth-Token": api_key}
    
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    params = {
        "dateFrom": today,
        "dateTo": today
    }
    
    print(f"🔄 Fetching real-world fixtures for date: {today}...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error connecting to Football-Data API: {e}")
        return pd.DataFrame()

    matches = data.get("matches", [])
    if not matches:
        print("ℹ️ No matches found scheduled for today.")
        return pd.DataFrame()

    # Parse JSON properties safely into flat rows
    parsed_matches = []
    for m in matches:
        parsed_matches.append({
            "match_id": m.get("id"),
            "match_date": m.get("utcDate")[:10], # Extract YYYY-MM-DD
            "competition": m.get("competition", {}).get("name"),
            "home_team": m.get("homeTeam", {}).get("name"),
            "away_team": m.get("awayTeam", {}).get("name"),
            "home_score": m.get("score", {}).get("fullTime", {}).get("home"),
            "away_score": m.get("score", {}).get("fullTime", {}).get("away"),
            "status": m.get("status")
        })

    return pd.DataFrame(parsed_matches)

def update_database(df, table_name="historical_matches"):
    """Saves or updates rows inside the DuckDB file."""
    if df.empty:
        return
        
    conn = duckdb.connect(DB_PATH)
    
    # Create the target table if it does not already exist
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            match_id INTEGER PRIMARY KEY,
            match_date VARCHAR,
            competition VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            home_score INTEGER,
            away_score INTEGER,
            status VARCHAR
        )
    """)
    
    # Register the dataframe locally into DuckDB context
    conn.register("df_temp", df)
    
    # Use an upsert syntax (INSERT OR REPLACE) to prevent duplicate entries
    conn.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM df_temp")
    conn.close()
    print(f"✅ Successfully wrote {len(df)} rows into DuckDB table '{table_name}'.")

def build_initial_historical_db():
    """Fallback mechanism to load initial history from your existing CSV paths."""
    print("📦 Building initial match database using available CSV sources...")
    # Target your existing CSV setup inside data/ folder
    csv_dir = "data/"
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print("❌ No baseline historical CSV files found in data/ directory to initialize.")
        return

    all_dfs = []
    for file in csv_files:
        path = os.path.join(csv_dir, file)
        try:
            df_csv = pd.read_csv(path)
            # Ensure basic column compliance
            required_cols = ["match_id", "match_date", "competition", "home_team", "away_team", "home_score", "away_score", "status"]
            # Fill missing optional columns if needed
            for col in required_cols:
                if col not in df_csv.columns:
                    df_csv[col] = None
            all_dfs.append(df_csv[required_cols])
        except Exception as e:
            print(f"Skipping corrupt or mismatched file {file}: {e}")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["match_id"])
        update_database(combined_df, "historical_matches")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
    parser.add_argument("--build-db", action="store_true", help="Initialize database from data/ folder CSV files")
    parser.add_argument("--fetch-today", action="store_true", help="Query API to append today's fixture list")
    
    args = parser.parse_args()
    
    if args.build-db:
        build_initial_historical_db()
    elif args.fetch-today:
        df_today = fetch_todays_fixtures_from_api()
        if not df_today.empty:
            # We save live fixtures either to historical_matches or a staging table
            update_database(df_today, "historical_matches")
    else:
        parser.print_help()
