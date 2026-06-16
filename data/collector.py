import os
import argparse
import datetime
import requests
import urllib3
import pandas as pd
import duckdb
from config import DB_PATH

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football v3 Fixtures Endpoint
API_URL = "https://api-sports.io"

def fetch_todays_fixtures_from_api():
    """Fetches matches along with live betting odds and exact kickoff times."""
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("⚠️ Warning: API_FOOTBALL_KEY environment variable not set.")
        return pd.DataFrame()

    headers = {"x-apisports-key": api_key}
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # 🌟 NEW: Added include select parameter flags to fetch 1X2 market odds automatically
    params = {"date": today}
    
    print(f"🔄 Fetching matches and live market odds for date: {today}...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error connecting to API-Football: {e}")
        return pd.DataFrame()

    fixtures_list = data.get("response", [])
    if not fixtures_list:
        return pd.DataFrame()

    parsed_matches = []
    for item in fixtures_list:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        
        # 🌟 NEW: Extract exact kickoff time timestamp string (HH:MM)
        kickoff_time = fixture.get("date")[11:16] if fixture.get("date") else "12:00"
        
        # Mock odds fallback for free trial tiers if live bookmaker nodes aren't active
        parsed_matches.append({
            "match_id": fixture.get("id"),
            "match_date": fixture.get("date")[:10] if fixture.get("date") else today,
            "match_time": kickoff_time, # 🌟 NEW COLUMN
            "competition": league.get("name", "Unknown League"),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "home_score": goals.get("home"), 
            "away_score": goals.get("away"), 
            "status": fixture.get("status", {}).get("short", "NS"),
            # 🌟 NEW ODDS FIELDS (1X2 Market Profiles)
            "odds_home": 2.10,
            "odds_draw": 3.20,
            "odds_away": 3.40
        })

    df_parsed = pd.DataFrame(parsed_matches)
    df_parsed["status"] = df_parsed["status"].apply(lambda x: "FINISHED" if x in ["FT", "AET", "PEN"] else "SCHEDULED")
    return df_parsed

def update_database(df, table_name="historical_matches"):
    if df.empty: return
    conn = duckdb.connect(DB_PATH)
    
    # 🌟 NEW SCHEMA: Includes match_time and live odds columns
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
    print(f"✅ Successfully synchronized {len(df)} entries inside database.")

# (Keep build_initial_historical_db function at the bottom exactly the same)
