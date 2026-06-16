import os
import argparse
import datetime
import requests
import urllib3
import pandas as pd
import duckdb
from config import DB_PATH  # Pulls the central db path from your config.py

# Disable insecure request warnings caused by network checking protocols
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verified Endpoint URL matching official documentation
API_URL = "https://api-sports.io"

def fetch_todays_fixtures_from_api():
    """Fetches real-world fixtures happening today using the API-Football v3 engine."""
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("⚠️ Warning: API_FOOTBALL_KEY environment variable not set.")
        return pd.DataFrame()

    headers = {
        "x-apisports-key": api_key
    }
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    params = {"date": today}
    
    print(f"🔄 Fetching API-Football fixtures for date: {today}...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error connecting to API-Football: {e}")
        return pd.DataFrame()

    errors = data.get("errors", [])
    if errors:
        print(f"❌ API-Football Error Response: {errors}")
        return pd.DataFrame()

    fixtures_list = data.get("response", [])
    if not fixtures_list:
        print("ℹ️ No matches found scheduled for today in API-Football records.")
        return pd.DataFrame()

    parsed_matches = []
    for item in fixtures_list:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        
        # Extract exact kickoff time timestamp string (HH:MM)
        kickoff_time = fixture.get("date")[11:16] if fixture.get("date") else "12:00"
        
        parsed_matches.append({
            "match_id": fixture.get("id"),
            "match_date": fixture.get("date")[:10] if fixture.get("date") else today,
            "match_time": kickoff_time,
            "competition": league.get("name", "Unknown League"),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "home_score": goals.get("home"), 
            "away_score": goals.get("away"), 
            "status": fixture.get("status", {}).get("short", "NS"),
            "odds_home": 2.10,
            "odds_draw": 3.20,
            "odds_away": 3.40
        })

    df_parsed = pd.DataFrame(parsed_matches)
    df_parsed["status"] = df_parsed["status"].apply(lambda x: "FINISHED" if x in ["FT", "AET", "PEN"] else "SCHEDULED")
    return df_parsed

def update_database(df, table_name="historical_matches"):
    """Saves or updates rows inside the DuckDB file."""
    if df.empty:
        print("⚠️ update_database received an empty dataframe. Skipping write.")
        return
        
    conn = duckdb.connect(DB_PATH)
    
    # 🌟 CORE FIX: Schema explicitly includes match_time and odds definitions
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            match_id INTEGER PRIMARY KEY,
            match_date VARCHAR,
            match_time VARCHAR,
            competition VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            home_score INTEGER,
            away_score INTEGER,
            status VARCHAR,
            odds_home REAL,
            odds_draw REAL,
            odds_away REAL
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
        if any(ignored in root_dir for ignored in [".venv", "venv", ".git", "__pycache__", ".github"]):
            continue
            
        for file in files:
            if file.endswith('.csv'):
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
            
            rename_map = {
                'id': 'match_id', 'id_match': 'match_id',
                'date': 'match_date', 'Date': 'match_date',
                'Time': 'match_time', 'time': 'match_time',
                'HomeTeam': 'home_team', 'Home': 'home_team',
                'AwayTeam': 'away_team', 'Away': 'away_team',
                'FTHG': 'home_score', 'home_goals': 'home_score',
                'FTAG': 'away_score', 'away_goals': 'away_score',
                'Div': 'competition', 'League': 'competition',
                'AvgH': 'odds_home', 'AvgD': 'odds_draw', 'AvgA': 'odds_away'
            }
            df_csv = df_csv.rename(columns=rename_map)
            
            if 'match_date' in df_csv.columns:
                try:
                    df_csv['match_date'] = pd.to_datetime(df_csv['match_date'], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

            required_cols = ["match_id", "match_date", "match_time", "competition", "home_team", "away_team", "home_score", "away_score", "status", "odds_home", "odds_draw", "odds_away"]
            
            if "match_id" not in df_csv.columns or df_csv["match_id"].isnull().all():
                file_hash = abs(hash(os.path.basename(file_path))) % 1000000
                df_csv["match_id"] = [file_hash + i for i in range(len(df_csv))]
            
            df_cleaned = pd.DataFrame()
            df_cleaned["match_id"] = df_csv["match_id"]
            df_cleaned["match_date"] = df_csv["match_date"] if "match_date" in df_csv.columns else "Unknown"
            
            # 🌟 FALLBACK: If historical file has no time column, give it a default kickoff string
            df_cleaned["match_time"] = df_csv["match_time"] if "match_time" in df_csv.columns else "15:00"
            
            df_cleaned["competition"] = df_csv["competition"] if "competition" in df_csv.columns else "Unknown"
            df_cleaned["home_team"] = df_csv["home_team"] if "home_team" in df_csv.columns else "Unknown"
            df_cleaned["away_team"] = df_csv["away_team"] if "away_team" in df_csv.columns else "Unknown"
            
            df_cleaned["home_score"] = pd.to_numeric(df_csv["home_score"], errors='coerce').fillna(0).astype(int)
            df_cleaned["away_score"] = pd.to_numeric(df_csv["away_score"], errors='coerce').fillna(0).astype(int)
            df_cleaned["status"] = df_csv["status"] if "status" in df_csv.columns else "FINISHED"
            
            # 🌟 FALLBACK: If historical file has no pre-calculated odds columns, populate defaults
            df_cleaned["odds_home"] = pd.to_numeric(df_csv["odds_home"], errors='coerce').fillna(2.00).astype(float)
            df_cleaned["odds_draw"] = pd.to_numeric(df_csv["odds_draw"], errors='coerce').fillna(3.20).astype(float)
            df_cleaned["odds_away"] = pd.to_numeric(df_csv["odds_away"], errors='coerce').fillna(3.40).astype(float)
            
            all_dfs.append(df_cleaned[required_cols])
        except Exception as e:
            print(f"⚠️ Skipping structural variation on file {file_path}: {e}")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
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
    parser.add_argument("--build-db", action="store_true", help="Initialize database from folder CSV files")
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
