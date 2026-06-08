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

    parsed_matches = []
    for m in matches:
        parsed_matches.append({
            "match_id": m.get("id"),
            "match_date": m.get("utcDate")[:10],
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
        print("⚠️ update_database received an empty dataframe. Skipping write.")
        return
        
    conn = duckdb.connect(DB_PATH)
    
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
    
    conn.register("df_temp", df)
    conn.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM df_temp")
    conn.close()
    print(f"✅ Successfully wrote {len(df)} rows into DuckDB table '{table_name}'.")

def build_initial_historical_db():
    """Recursively crawls through all project folders to compile season CSV datasets."""
    print("📦 Deep-scanning project workspace for season CSV historical data files...")
    
    csv_files_found = []
    
    for root_dir, dirs, files in os.walk("."):
        # Ignore virtual environments, git configs, internal caches, and the explicit fixtures directory
        if any(ignored in root_dir for ignored in [".venv", "venv", ".git", "__pycache__", ".github"]):
            continue
            
        for file in files:
            if file.endswith('.csv'):
                # 🌟 FIX: Skip sample forecasting or upcoming match files
                if "fixtures" in file.lower() or "sample" in file.lower():
                    continue
                full_path = os.path.join(root_dir, file)
                csv_files_found.append(full_path)

    print(f"🔍 Discovered a total of {len(csv_files_found)} target CSV historical source files.")

    if not csv_files_found:
        print("❌ Error: Could not find any valid season CSV files.")
        return

    all_dfs = []
    for file_path in csv_files_found:
        print(f"📖 Parsing match data rows from: {file_path}...")
        try:
            df_csv = pd.read_csv(file_path)
            
            # Map structural columns used by football-data.co.uk datasets
            rename_map = {
                'id': 'match_id', 'id_match': 'match_id',
                'date': 'match_date', 'Date': 'match_date',
                'HomeTeam': 'home_team', 'Home': 'home_team',
                'AwayTeam': 'away_team', 'Away': 'away_team',
                'FTHG': 'home_score', 'home_goals': 'home_score',
                'FTAG': 'away_score', 'away_goals': 'away_score',
                'Div': 'competition', 'League': 'competition'
            }
            df_csv = df_csv.rename(columns=rename_map)
            
            # Convert date columns containing slashes (DD/MM/YY) to clean standard ISO text formats (YYYY-MM-DD)
            if 'match_date' in df_csv.columns:
                try:
                    df_csv['match_date'] = pd.to_datetime(df_csv['match_date'], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

            required_cols = ["match_id", "match_date", "competition", "home_team", "away_team", "home_score", "away_score", "status"]
            
            # Auto-generate a sequential unique primary key sequence if missing from the raw CSV
            if "match_id" not in df_csv.columns or df_csv["match_id"].isnull().all():
                file_hash = abs(hash(os.path.basename(file_path))) % 1000000
                df_csv["match_id"] = [file_hash + i for i in range(len(df_csv))]
            
            # Build target matrix dataframe dictionary
            df_cleaned = pd.DataFrame()
            df_cleaned["match_id"] = df_csv["match_id"]
            df_cleaned["match_date"] = df_csv["match_date"] if "match_date" in df_csv.columns else "Unknown"
            df_cleaned["competition"] = df_csv["competition"] if "competition" in df_csv.columns else "Unknown"
            df_cleaned["home_team"] = df_csv["home_team"] if "home_team" in df_csv.columns else "Unknown"
            df_cleaned["away_team"] = df_csv["away_team"] if "away_team" in df_csv.columns else "Unknown"
            
            # 🌟 FIX: Force explicit integer evaluation on scores, substituting empty data cells with 0
            df_cleaned["home_score"] = pd.to_numeric(df_csv["home_score"], errors='coerce').fillna(0).astype(int)
            df_cleaned["away_score"] = pd.to_numeric(df_csv["away_score"], errors='coerce').fillna(0).astype(int)
            df_cleaned["status"] = df_csv["status"] if "status" in df_csv.columns else "FINISHED"
            
            all_dfs.append(df_cleaned[required_cols])
        except Exception as e:
            print(f"⚠️ Skipping structural variation on file {file_path}: {e}")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # Clean null entries and deduplicate records across league season boundaries
        combined_df = combined_df.dropna(subset=["match_id"])
        combined_df["match_id"] = combined_df["match_id"].astype(int)
        combined_df = combined_df.drop_duplicates(subset=["match_id"])
        
        if not combined_df.empty:
            update_database(combined_df, "historical_matches")
        else:
            print("⚠️ Match data matrix compiled empty after filtering rows.")
    else:
        print("❌ Could not compile any structured tables out of discovered files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
    parser.add_argument("--build-db", action="store_true", help="Initialize database from data/ folder CSV files")
    parser.add_argument("--fetch-today", action="store_true", help="Query API to append today's fixture list")
    
    args = parser.parse_args()
    
    if args.build_db:
        build_initial_historical_db()
    elif args.fetch_today:
        df_today = fetch_todays_fixtures_from_api()
        if not df_today.empty:
            update_database(df_today, "historical_matches")
    else:
        parser.print_help()
