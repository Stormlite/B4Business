import os
import argparse
import datetime
import requests
import urllib3
import pandas as pd
import duckdb
from config import DB_PATH

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football Base URL
API_URL = "https://api-sports.io"

def fetch_live_market_odds():
    """Fetches real-world scheduled soccer matches and live bookmaker odds using your verified format."""
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        print("⚠️ Warning: THE_ODDS_API_KEY not set. Using default baseline odds matrix.")
        return {}

    # 🌟 FIXED: Using your exact verified Tennis structure format
    SPORT = "upcoming"
    REGION = "eu"
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={api_key}&regions={REGION}&markets=h2h"
    
    print("📡 Querying The Odds API V4 for upcoming live soccer pricing feeds...")
    try:
        response = requests.get(url, timeout=12)
        if response.status_code != 200:
            print(f"⚠️ Odds API Error Status: {response.status_code}")
            return {}
            
        data = response.json()
        odds_map = {}
        
        for match in data:
            # 🌟 FIXED: Drop entries that do not map down to soccer match events
            if "soccer" not in match.get("sport_key", "").lower():
                continue
                
            home_team = match.get("home_team")
            away_team = match.get("away_team")
            odds_home, odds_draw, odds_away = 2.10, 3.20, 3.40 # Default baseline fallbacks
            
            # 🌟 FIXED: Map specifically through your targeted reliable bookies
            if match.get("bookmakers"):
                for b in match["bookmakers"]:
                    if b["key"] in ["sportybet", "onexbet", "bet365", "betway"]:
                        for m in b.get("markets", []):
                            if m["key"] == "h2h":
                                for out in m.get("outcomes", []):
                                    if out["name"] == home_team: odds_home = out["price"]
                                    if out["name"] == away_team: odds_away = out["price"]
                                    if out["name"] == "Draw": odds_draw = out["price"]
                        break # Successfully extracted prices, move to the next fixture
            
            norm_key = f"{str(home_team).lower()} vs {str(away_team).lower()}"
            odds_map[norm_key] = {"H": odds_home, "D": odds_draw, "A": odds_away}
            
        return odds_map
    except Exception as e:
        print(f"❌ Failed to query live bookmaker odds: {e}")
        return {}

def fetch_todays_fixtures_from_api():
    """Fetches ALL real-world fixtures globally along with live integrated V4 odds mappings."""
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("⚠️ Warning: API_FOOTBALL_KEY environment variable not set.")
        return pd.DataFrame()

    headers = {"x-apisports-key": api_key}
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Pre-fetch the live odds map using our fixed tennis-style method
    live_odds_feed = fetch_live_market_odds()
    
    # Query only by date to pull ALL global matches concurrently in 1 request
    params = {"date": today}
    print(f"🔄 Requesting ALL global fixtures from API-Football for date: {today}...")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=15, allow_redirects=False)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error connecting to API-Football global endpoint: {e}")
        return pd.DataFrame()

    fixtures_list = data.get("response", [])
    if not fixtures_list:
        print(f"ℹ️ No active scheduled matches found globally for date: {today}")
        return pd.DataFrame()

    parsed_matches = []
    for item in fixtures_list:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        
        home_name = teams.get("home", {}).get("name")
        away_name = teams.get("away", {}).get("name")
        kickoff_time = fixture.get("date")[11:16] if fixture.get("date") else "15:00"
        
        # Default fallback values
        odds_h, odds_d, odds_a = 2.10, 3.20, 3.40
        lookup_key = f"{str(home_name).lower()} vs {str(away_name).lower()}"
        
        # Join data using name alignment checks
        matched_odds = live_odds_feed.get(lookup_key)
        if not matched_odds:
            # Fuzzy substring fallback verification
            for key, odds in live_odds_feed.items():
                if str(home_name).lower() in key or str(away_name).lower() in key:
                    matched_odds = odds
                    break
        
        if matched_odds:
            odds_h = matched_odds["H"]
            odds_d = matched_odds["D"]
            odds_a = matched_odds["A"]

        parsed_matches.append({
            "match_id": fixture.get("id"),
            "match_date": fixture.get("date")[:10] if fixture.get("date") else today,
            "match_time": kickoff_time,
            "competition": league.get("name", "Unknown League"),
            "home_team": home_name,
            "away_team": away_name,
            "home_score": goals.get("home"), 
            "away_score": goals.get("away"), 
            "status": fixture.get("status", {}).get("short", "NS"),
            "odds_home": odds_h,
            "odds_draw": odds_d,
            "odds_away": odds_a
        })

    df_parsed = pd.DataFrame(parsed_matches)
    df_parsed["status"] = df_parsed["status"].apply(lambda x: "FINISHED" if x in ["FT", "AET", "PEN"] else "SCHEDULED")
    return df_parsed

def update_database(df, table_name="historical_matches"):
    if df.empty: return
    conn = duckdb.connect(DB_PATH)
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
    print(f"✅ Successfully wrote {len(df)} rows into DuckDB.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
    parser.add_argument("--build-db", action="store_true")
    parser.add_argument("--fetch-today", action="store_true")
    args = parser.parse_args()
    if args.build_db:
        pass
    elif args.fetch_today:
        df_today = fetch_todays_fixtures_from_api()
        if not df_today.empty: 
            update_database(df_today, "historical_matches")
