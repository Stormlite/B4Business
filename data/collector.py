# # import os
# # import argparse
# # import datetime
# # import requests
# # import urllib3
# # import pandas as pd
# # import duckdb
# # from config import DB_PATH

# # urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # # API-Football Base URL
# # API_URL = "https://v3.football.api-sports.io/fixtures"

# # def fetch_live_market_odds():
# #     """Fetches real-world scheduled soccer matches and live bookmaker odds using your verified format."""
# #     api_key = os.getenv("THE_ODDS_API_KEY")
# #     if not api_key:
# #         print("⚠️ Warning: THE_ODDS_API_KEY not set. Using default baseline odds matrix.")
# #         return {}

# #     # 🌟 FIXED: Using your exact verified Tennis structure format
# #     SPORT = "upcoming"
# #     REGION = "eu"
# #     url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={api_key}&regions={REGION}&markets=h2h"
    
# #     print("📡 Querying The Odds API V4 for upcoming live soccer pricing feeds...")
# #     try:
# #         response = requests.get(url, timeout=12)
# #         if response.status_code != 200:
# #             print(f"⚠️ Odds API Error Status: {response.status_code}")
# #             return {}
            
# #         data = response.json()
# #         odds_map = {}
        
# #         for match in data:
# #             # 🌟 FIXED: Drop entries that do not map down to soccer match events
# #             if "soccer" not in match.get("sport_key", "").lower():
# #                 continue
                
# #             home_team = match.get("home_team")
# #             away_team = match.get("away_team")
# #             odds_home, odds_draw, odds_away = 2.10, 3.20, 3.40 # Default baseline fallbacks
            
# #             # 🌟 FIXED: Map specifically through your targeted reliable bookies
# #             if match.get("bookmakers"):
# #                 for b in match["bookmakers"]:
# #                     if b["key"] in ["sportybet", "onexbet", "bet365", "betway"]:
# #                         for m in b.get("markets", []):
# #                             if m["key"] == "h2h":
# #                                 for out in m.get("outcomes", []):
# #                                     if out["name"] == home_team: odds_home = out["price"]
# #                                     if out["name"] == away_team: odds_away = out["price"]
# #                                     if out["name"] == "Draw": odds_draw = out["price"]
# #                         break # Successfully extracted prices, move to the next fixture
            
# #             norm_key = f"{str(home_team).lower()} vs {str(away_team).lower()}"
# #             odds_map[norm_key] = {"H": odds_home, "D": odds_draw, "A": odds_away}
            
# #         return odds_map
# #     except Exception as e:
# #         print(f"❌ Failed to query live bookmaker odds: {e}")
# #         return {}

# # def fetch_todays_fixtures_from_api():
# #     """Fetches ALL real-world fixtures globally along with live integrated V4 odds mappings."""
# #     api_key = os.getenv("API_FOOTBALL_KEY")
# #     if not api_key:
# #         print("⚠️ Warning: API_FOOTBALL_KEY environment variable not set.")
# #         return pd.DataFrame()

# #     headers = {"x-apisports-key": api_key}
# #     today = datetime.date.today().strftime("%Y-%m-%d")
    
# #     # Pre-fetch the live odds map using our fixed tennis-style method
# #     live_odds_feed = fetch_live_market_odds()
    
# #     # Query only by date to pull ALL global matches concurrently in 1 request
# #     params = {"date": today}
# #     print(f"🔄 Requesting ALL global fixtures from API-Football for date: {today}...")
# #     try:
# #         response = requests.get(API_URL, headers=headers, params=params, timeout=15, allow_redirects=False)
# #         response.raise_for_status()
# #         data = response.json()
# #     except Exception as e:
# #         print(f"❌ Error connecting to API-Football global endpoint: {e}")
# #         return pd.DataFrame()

# #     fixtures_list = data.get("response", [])
# #     if not fixtures_list:
# #         print(f"ℹ️ No active scheduled matches found globally for date: {today}")
# #         return pd.DataFrame()

# #     parsed_matches = []
# #     for item in fixtures_list:
# #         fixture = item.get("fixture", {})
# #         league = item.get("league", {})
# #         teams = item.get("teams", {})
# #         goals = item.get("goals", {})
        
# #         home_name = teams.get("home", {}).get("name")
# #         away_name = teams.get("away", {}).get("name")
# #         kickoff_time = fixture.get("date")[11:16] if fixture.get("date") else "15:00"
        
# #         # Default fallback values
# #         odds_h, odds_d, odds_a = 2.10, 3.20, 3.40
# #         lookup_key = f"{str(home_name).lower()} vs {str(away_name).lower()}"
        
# #         # Join data using name alignment checks
# #         matched_odds = live_odds_feed.get(lookup_key)
# #         if not matched_odds:
# #             # Fuzzy substring fallback verification
# #             for key, odds in live_odds_feed.items():
# #                 if str(home_name).lower() in key or str(away_name).lower() in key:
# #                     matched_odds = odds
# #                     break
        
# #         if matched_odds:
# #             odds_h = matched_odds["H"]
# #             odds_d = matched_odds["D"]
# #             odds_a = matched_odds["A"]

# #         parsed_matches.append({
# #             "match_id": fixture.get("id"),
# #             "match_date": fixture.get("date")[:10] if fixture.get("date") else today,
# #             "match_time": kickoff_time,
# #             "competition": league.get("name", "Unknown League"),
# #             "home_team": home_name,
# #             "away_team": away_name,
# #             "home_score": goals.get("home"), 
# #             "away_score": goals.get("away"), 
# #             "status": fixture.get("status", {}).get("short", "NS"),
# #             "odds_home": odds_h,
# #             "odds_draw": odds_d,
# #             "odds_away": odds_a
# #         })

# #     df_parsed = pd.DataFrame(parsed_matches)
# #     df_parsed["status"] = df_parsed["status"].apply(lambda x: "FINISHED" if x in ["FT", "AET", "PEN"] else "SCHEDULED")
# #     return df_parsed

# # def update_database(df, table_name="historical_matches"):
# #     if df.empty: return
# #     conn = duckdb.connect(DB_PATH)
# #     conn.execute(f"""
# #         CREATE TABLE IF NOT EXISTS {table_name} (
# #             match_id INTEGER PRIMARY KEY,
# #             match_date VARCHAR,
# #             match_time VARCHAR,
# #             competition VARCHAR,
# #             home_team VARCHAR,
# #             away_team VARCHAR,
# #             home_score INTEGER,
# #             away_score INTEGER,
# #             status VARCHAR,
# #             odds_home REAL,
# #             odds_draw REAL,
# #             odds_away REAL
# #         )
# #     """)
# #     conn.register("df_temp", df)
# #     conn.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM df_temp")
# #     conn.close()
# #     print(f"✅ Successfully wrote {len(df)} rows into DuckDB.")

# # if __name__ == "__main__":
# #     parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
# #     parser.add_argument("--build-db", action="store_true")
# #     parser.add_argument("--fetch-today", action="store_true")
# #     args = parser.parse_args()
# #     if args.build_db:
# #         pass
# #     elif args.fetch_today:
# #         df_today = fetch_todays_fixtures_from_api()
# #         if not df_today.empty: 
# #             update_database(df_today, "historical_matches")


# import os
# import argparse
# import datetime
# import requests
# import urllib3
# import pandas as pd
# import duckdb
# from config import DB_PATH

# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # 🌟 FIXED: Verified, explicit base URL endpoint definitions
# API_URL = "https://api-sports.io"

# def fetch_live_market_odds():
#     """Fetches real-world scheduled soccer matches and live bookmaker odds using your verified format."""
#     api_key = os.getenv("THE_ODDS_API_KEY")
#     if not api_key:
#         print("⚠️ Warning: THE_ODDS_API_KEY not set. Using default baseline odds matrix.")
#         return {}

#     SPORT = "upcoming"
#     REGION = "eu,us,uk,au"
#     url = f"https://the-odds-api.com/{SPORT}/odds/?apiKey={api_key}&regions={REGION}&markets=h2h"
    
#     print("📡 Querying The Odds API V4 for upcoming live soccer pricing feeds...")
#     try:
#         response = requests.get(url, timeout=12)
#         if response.status_code != 200:
#             print(f"⚠️ Odds API Error Status: {response.status_code}")
#             return {}
            
#         data = response.json()
#         odds_map = {}
        
#         for match in data:
#             if "soccer" not in match.get("sport_key", "").lower():
#                 continue
                
#             home_team = match.get("home_team")
#             away_team = match.get("away_team")
#             odds_home, odds_draw, odds_away = 2.10, 3.20, 3.40
            
#             if match.get("bookmakers"):
#                 for b in match["bookmakers"]:
#                     if b["key"] in ["sportybet", "onexbet", "bet365", "betway"]:
#                         for m in b.get("markets", []):
#                             if m["key"] == "h2h":
#                                 for out in m.get("outcomes", []):
#                                     if out["name"] == home_team: odds_home = out["price"]
#                                     if out["name"] == away_team: odds_away = out["price"]
#                                     if out["name"] == "Draw": odds_draw = out["price"]
#                         break
            
#             norm_key = f"{str(home_team).lower()} vs {str(away_team).lower()}"
#             odds_map[norm_key] = {"H": odds_home, "D": odds_draw, "A": odds_away}
            
#         return odds_map
#     except Exception as e:
#         print(f"❌ Failed to query live bookmaker odds: {e}")
#         return {}

# def fetch_todays_fixtures_from_api():
#     """Fetches ALL real-world fixtures globally along with live integrated V4 odds mappings."""
#     api_key = os.getenv("API_FOOTBALL_KEY")
#     if not api_key:
#         print("⚠️ Warning: API_FOOTBALL_KEY environment variable not set.")
#         return pd.DataFrame()

#     # API-Football authenticates via the x-apisports-key header parameter
#     headers = {"x-apisports-key": api_key}
#     today = datetime.date.today().strftime("%Y-%m-%d")
    
#     live_odds_feed = fetch_live_market_odds()
    
#     params = {"date": today}
#     print(f"🔄 Requesting ALL global fixtures from API-Football for date: {today}...")
#     try:
#         # 🌟 FIXED: Changed hardcoded text to use the API_URL variable definition directly
#         response = requests.get(API_URL, headers=headers, params=params, timeout=15, allow_redirects=False)
#         response.raise_for_status()
#         data = response.json()
#     except Exception as e:
#         print(f"❌ Error connecting to API-Football global endpoint: {e}")
#         return pd.DataFrame()

#     fixtures_list = data.get("response", [])
#     if not fixtures_list:
#         print(f"ℹ️ No active scheduled matches found globally for date: {today}")
#         return pd.DataFrame()

#     parsed_matches = []
#     for item in fixtures_list:
#         fixture = item.get("fixture", {})
#         league = item.get("league", {})
#         teams = item.get("teams", {})
#         goals = item.get("goals", {})
        
#         home_name = teams.get("home", {}).get("name")
#         away_name = teams.get("away", {}).get("name")
#         kickoff_time = fixture.get("date")[11:16] if fixture.get("date") else "15:00"
        
#         odds_h, odds_d, odds_a = 2.10, 3.20, 3.40
#         lookup_key = f"{str(home_name).lower()} vs {str(away_name).lower()}"
        
#         matched_odds = live_odds_feed.get(lookup_key)
#         if not matched_odds:
#             for key, odds in live_odds_feed.items():
#                 if str(home_name).lower() in key or str(away_name).lower() in key:
#                     matched_odds = odds
#                     break
        
#         if matched_odds:
#             odds_h = matched_odds["H"]
#             odds_d = matched_odds["D"]
#             odds_a = matched_odds["A"]

#         parsed_matches.append({
#             "match_id": fixture.get("id"),
#             "match_date": fixture.get("date")[:10] if fixture.get("date") else today,
#             "match_time": kickoff_time,
#             "competition": league.get("name", "Unknown League"),
#             "home_team": home_name,
#             "away_team": away_name,
#             "home_score": goals.get("home"), 
#             "away_score": goals.get("away"), 
#             "status": fixture.get("status", {}).get("short", "NS"),
#             "odds_home": odds_h,
#             "odds_draw": odds_d,
#             "odds_away": odds_a
#         })

#     df_parsed = pd.DataFrame(parsed_matches)
#     df_parsed["status"] = df_parsed["status"].apply(lambda x: "FINISHED" if x in ["FT", "AET", "PEN"] else "SCHEDULED")
#     return df_parsed

# def update_database(df, table_name="historical_matches"):
#     if df.empty: return
#     conn = duckdb.connect(DB_PATH)
#     conn.execute(f"""
#         CREATE TABLE IF NOT EXISTS {table_name} (
#             match_id INTEGER PRIMARY KEY,
#             match_date VARCHAR,
#             match_time VARCHAR,
#             competition VARCHAR,
#             home_team VARCHAR,
#             away_team VARCHAR,
#             home_score INTEGER,
#             away_score INTEGER,
#             status VARCHAR,
#             odds_home REAL,
#             odds_draw REAL,
#             odds_away REAL
#         )
#     """)
#     conn.register("df_temp", df)
#     conn.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM df_temp")
#     conn.close()
#     print(f"✅ Successfully wrote {len(df)} rows into DuckDB.")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
#     parser.add_argument("--build-db", action="store_true")
#     parser.add_argument("--fetch-today", action="store_true")
#     args = parser.parse_args()
#     if args.build_db:
#         pass
#     elif args.fetch_today:
#         df_today = fetch_todays_fixtures_from_api()
#         if not df_today.empty: 
#             update_database(df_today, "historical_matches")

import os
import argparse
import datetime
import time
import requests
import urllib3
import pandas as pd
import duckdb

# Attempt to import DB_PATH from config; fall back gracefully if not present
try:
    from config import DB_PATH
except ImportError:
    DB_PATH = "football.db"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ✅ FIXED: Correct versioned base URL for API-Football v3
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

# ✅ FIXED: Correct base URL for The Odds API v4
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"


def fetch_live_market_odds():
    """
    Fetches live/upcoming soccer odds from The Odds API v4.
    Correct endpoint: GET /v4/sports/{sport}/odds
    Docs: https://the-odds-api.com/liveapi/guides/v4/
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        print("⚠️  Warning: THE_ODDS_API_KEY not set. Using default baseline odds.")
        return {}

    # Use the generic 'soccer' sport group — covers all soccer competitions
    sport = "soccer"

    # ✅ FIXED: Correct V4 URL format
    url = f"{ODDS_API_BASE_URL}/sports/{sport}/odds"

    params = {
        "apiKey": api_key,          # ✅ goes as query param, not in the path
        "regions": "eu,us,uk,au",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }

    print("📡 Querying The Odds API v4 for upcoming soccer odds...")
    try:
        response = requests.get(url, params=params, timeout=12)

        if response.status_code == 401:
            print("❌ Odds API: Invalid or missing API key.")
            return {}
        if response.status_code == 422:
            print("❌ Odds API: Unprocessable request — check sport key or params.")
            return {}
        if response.status_code != 200:
            print(f"⚠️  Odds API error {response.status_code}: {response.text[:200]}")
            return {}

        data = response.json()
        odds_map = {}

        for match in data:
            home_team = match.get("home_team")
            away_team = match.get("away_team")
            # No hardcoded fallback here — 2.10/3.20/3.40 is itself a
            # home-favoring set of odds, so injecting it for every unmatched
            # fixture was silently biasing predictions toward the home team.
            # None propagates through as "no odds available" and the model's
            # per-column training-median fallback (a neutral, data-derived
            # value) kicks in instead — see features/engineer.py.
            odds_home, odds_draw, odds_away = None, None, None

            for bookmaker in match.get("bookmakers", []):
                if bookmaker["key"] in ["sportybet", "onexbet", "bet365", "betway"]:
                    for market in bookmaker.get("markets", []):
                        if market["key"] == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome["name"] == home_team:
                                    odds_home = outcome["price"]
                                elif outcome["name"] == away_team:
                                    odds_away = outcome["price"]
                                elif outcome["name"] == "Draw":
                                    odds_draw = outcome["price"]
                    break  # stop after first matching bookmaker

            norm_key = f"{str(home_team).lower()} vs {str(away_team).lower()}"
            odds_map[norm_key] = {"H": odds_home, "D": odds_draw, "A": odds_away}

        print(f"✅ Fetched odds for {len(odds_map)} soccer matches.")
        return odds_map

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error querying Odds API: {e}")
        return {}


def fetch_fixtures_for_date(target_date: str = None):
    """
    Fetches fixtures for a given date from API-Football v3 (defaults to today).
    Correct endpoint: GET /fixtures?date=YYYY-MM-DD
    Docs: https://www.api-football.com/documentation-v3#tag/Fixtures
    """
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("⚠️  Warning: API_FOOTBALL_KEY environment variable not set.")
        return pd.DataFrame()

    # ✅ FIXED: Auth goes in the header (not a query param)
    headers = {"x-apisports-key": api_key}

    target_date = target_date or datetime.date.today().strftime("%Y-%m-%d")
    live_odds_feed = fetch_live_market_odds()

    # ✅ FIXED: Correct endpoint path appended to the base URL
    url = f"{API_FOOTBALL_BASE_URL}/fixtures"
    params = {"date": target_date}

    print(f"🔄 Requesting fixtures from API-Football for date: {target_date}...")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code == 401:
            print("❌ API-Football: Unauthorized — check your API key.")
            return pd.DataFrame()
        if response.status_code != 200:
            print(f"⚠️  API-Football error {response.status_code}: {response.text[:200]}")
            return pd.DataFrame()

        data = response.json()

        # API-Football wraps errors inside a 200 response sometimes
        if data.get("errors"):
            print(f"❌ API-Football API error: {data['errors']}")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to API-Football: {e}")
        return pd.DataFrame()

    fixtures_list = data.get("response", [])
    if not fixtures_list:
        print(f"ℹ️  No fixtures found for date: {target_date}")
        return pd.DataFrame()

    parsed_matches = []
    for item in fixtures_list:
        fixture = item.get("fixture", {})
        league  = item.get("league", {})
        teams   = item.get("teams", {})
        goals   = item.get("goals", {})
        score   = item.get("score", {})
        halftime = score.get("halftime", {})

        home_name    = teams.get("home", {}).get("name")
        away_name    = teams.get("away", {}).get("name")
        home_id      = teams.get("home", {}).get("id")
        away_id      = teams.get("away", {}).get("id")
        fixture_date = fixture.get("date", "")
        kickoff_time = fixture_date[11:16] if len(fixture_date) >= 16 else "15:00"

        # Odds lookup — exact match first, then fuzzy. No hardcoded default:
        # an unmatched fixture stores NULL odds rather than a fake
        # home-favoring price, so the model treats it as genuinely missing
        # data (falls back to its neutral training median) instead of being
        # steered toward the home team by a fabricated number.
        odds_h, odds_d, odds_a = None, None, None
        lookup_key = f"{str(home_name).lower()} vs {str(away_name).lower()}"
        matched_odds = live_odds_feed.get(lookup_key)

        if not matched_odds:
            for key, odds in live_odds_feed.items():
                if str(home_name).lower() in key or str(away_name).lower() in key:
                    matched_odds = odds
                    break

        if matched_odds:
            odds_h = matched_odds["H"]
            odds_d = matched_odds["D"]
            odds_a = matched_odds["A"]

        status_short = fixture.get("status", {}).get("short", "NS")
        status = "FINISHED" if status_short in ["FT", "AET", "PEN"] else "SCHEDULED"

        parsed_matches.append({
            "match_id":      fixture.get("id"),
            "match_date":    fixture_date[:10] if fixture_date else target_date,
            "match_time":    kickoff_time,
            "competition":   league.get("name", "Unknown League"),
            "home_team":     home_name,
            "away_team":     away_name,
            "home_team_id":  home_id,
            "away_team_id":  away_id,
            "home_score":    goals.get("home"),
            "away_score":    goals.get("away"),
            "home_ht_score": halftime.get("home"),
            "away_ht_score": halftime.get("away"),
            "status":        status,
            "odds_home":     odds_h,
            "odds_draw":     odds_d,
            "odds_away":     odds_a,
        })

    df = pd.DataFrame(parsed_matches)
    print(f"✅ Parsed {len(df)} fixtures for {target_date}.")
    return df


# Backward-compatible alias — some callers may still reference the old name.
def fetch_todays_fixtures_from_api():
    return fetch_fixtures_for_date()


def backfill_match_statistics(days_back: int = 3, limit: int = 50):
    """
    Backfills shots / shots-on-target / corners for recently finished matches
    collected via API-Football, using GET /fixtures/statistics?fixture={id}.
    Docs: https://www.api-football.com/documentation-v3#tag/Fixtures

    Only targets rows with match_id > 0 (real API-Football fixture IDs — CSV-
    sourced historical rows use negative placeholder IDs, see load_csv_data)
    that are FINISHED and still missing statistics, so re-running this is
    idempotent and cheap on API quota.

    NOTE: written against the documented API-Football v3 response shape
    (confirmed field names: "Total Shots", "Shots on Goal", "Corner Kicks")
    but NOT tested against a live call — api-sports.io is not reachable from
    the sandbox this was developed in. Verify the parsing below against a
    real response (e.g. one finished fixture) before trusting it at scale.
    """
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("⚠️  Warning: API_FOOTBALL_KEY environment variable not set.")
        return

    headers = {"x-apisports-key": api_key}
    conn = duckdb.connect(DB_PATH)

    # DuckDB has no ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so check first.
    existing_cols = {row[0] for row in conn.execute("DESCRIBE historical_matches").fetchall()}
    for col in ["home_shots", "away_shots", "home_shots_ot", "away_shots_ot",
                "home_corners", "away_corners"]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE historical_matches ADD COLUMN {col} INTEGER")

    targets = conn.execute(f"""
        SELECT match_id, home_team, away_team FROM historical_matches
        WHERE status = 'FINISHED'
          AND match_id > 0
          AND home_shots IS NULL
          AND match_date >= CAST((CURRENT_DATE - INTERVAL {days_back} DAY) AS VARCHAR)
        LIMIT {limit}
    """).fetchall()

    if not targets:
        print("ℹ️  No recently finished matches need statistics backfill.")
        conn.close()
        return

    print(f"🔄 Backfilling statistics for {len(targets)} finished matches...")
    url = f"{API_FOOTBALL_BASE_URL}/fixtures/statistics"
    updated = 0

    # Confirmed via API-Football's own rate-limit docs: free tier is 10
    # requests/minute (separate from a 100/day cap). 1.5s pacing was ~40
    # req/min — 4x over — which is exactly why every call in the previous
    # run hit a 429 even after retrying once. 6.5s gives a small safety
    # margin under the true 6s-per-request minimum for 10/min.
    MIN_INTERVAL = 6.5

    for fixture_id, home_team, away_team in targets:
        try:
            response = requests.get(url, headers=headers, params={"fixture": fixture_id}, timeout=12)

            retry_count = 0
            while response.status_code == 429 and retry_count < 2:
                # Prefer the server's own Retry-After header when present —
                # more reliable than guessing a fixed backoff.
                wait = int(response.headers.get("Retry-After", 15))
                print(f"⏳ Rate limited on fixture {fixture_id}, waiting {wait}s and retrying "
                      f"(attempt {retry_count + 1}/2)...")
                time.sleep(wait)
                response = requests.get(url, headers=headers, params={"fixture": fixture_id}, timeout=12)
                retry_count += 1

            if response.status_code != 200:
                print(f"⚠️  Statistics fetch failed for fixture {fixture_id}: {response.status_code}")
                continue

            blocks = response.json().get("response", [])
            if len(blocks) != 2:
                # Not yet populated by the API, or an unsupported competition — skip, retry next run.
                continue

            # Match by team name rather than assume response order is home-first.
            by_name = {}
            for block in blocks:
                stats = {s["type"]: s["value"] for s in block.get("statistics", [])}
                by_name[str(block.get("team", {}).get("name", "")).lower()] = {
                    "shots":    stats.get("Total Shots") or 0,
                    "shots_ot": stats.get("Shots on Goal") or 0,
                    "corners":  stats.get("Corner Kicks") or 0,
                }

            home_stats = by_name.get(str(home_team).lower())
            away_stats = by_name.get(str(away_team).lower())
            if not home_stats or not away_stats:
                print(f"⚠️  Fixture {fixture_id}: team name mismatch between DB and statistics response, skipping.")
                continue

            conn.execute("""
                UPDATE historical_matches
                SET home_shots = ?, away_shots = ?,
                    home_shots_ot = ?, away_shots_ot = ?,
                    home_corners = ?, away_corners = ?
                WHERE match_id = ?
            """, [
                home_stats["shots"], away_stats["shots"],
                home_stats["shots_ot"], away_stats["shots_ot"],
                home_stats["corners"], away_stats["corners"],
                fixture_id,
            ])
            updated += 1

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching statistics for fixture {fixture_id}: {e}")
            continue
        finally:
            # Proactive pacing between every request (success, skip, or
            # exception) — see MIN_INTERVAL comment above for the math.
            time.sleep(MIN_INTERVAL)

    conn.close()
    print(f"✅ Backfilled statistics for {updated}/{len(targets)} matches.")


def update_database(df, table_name="historical_matches"):
    """Upserts fixture data into DuckDB."""
    if df.empty:
        print("⚠️  No data to write.")
        return

    conn = duckdb.connect(DB_PATH)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            match_id   INTEGER PRIMARY KEY,
            match_date VARCHAR,
            match_time VARCHAR,
            competition VARCHAR,
            home_team  VARCHAR,
            away_team  VARCHAR,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            home_ht_score INTEGER,
            away_ht_score INTEGER,
            status     VARCHAR,
            odds_home  REAL,
            odds_draw  REAL,
            odds_away  REAL,
            home_shots    INTEGER,
            away_shots    INTEGER,
            home_shots_ot INTEGER,
            away_shots_ot INTEGER,
            home_corners  INTEGER,
            away_corners  INTEGER
        )
    """)
    # Migration for DBs that already exist from before these 4 columns were
    # added (same ALTER-if-missing pattern used for the statistics backfill).
    existing_cols = {row[0] for row in conn.execute(f"DESCRIBE {table_name}").fetchall()}
    for col, coltype in [("home_team_id", "INTEGER"), ("away_team_id", "INTEGER"),
                          ("home_ht_score", "INTEGER"), ("away_ht_score", "INTEGER")]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {coltype}")
    conn.register("df_temp", df)

    # Explicit column list + ON CONFLICT upsert instead of "INSERT OR REPLACE
    # ... SELECT *". Two bugs that fixes:
    #   1. SELECT * requires df_temp's column count to exactly match the
    #      table's — broke the moment backfill_match_statistics() ALTERed the
    #      table to 18 columns while a plain fetch only ever provides 12.
    #   2. INSERT OR REPLACE fully replaces the row. Re-fetching an existing
    #      match_id (e.g. status flipping to FINISHED) would have silently
    #      wiped any already-backfilled shots/corners data back to NULL,
    #      since this fetch never provides those columns. The upsert below
    #      only ever touches the 12 columns it actually has data for.
    fetch_cols = ["match_id", "match_date", "match_time", "competition",
                  "home_team", "away_team", "home_team_id", "away_team_id",
                  "home_score", "away_score", "home_ht_score", "away_ht_score",
                  "status", "odds_home", "odds_draw", "odds_away"]
    col_list = ", ".join(fetch_cols)
    update_set = ", ".join(f"{c} = excluded.{c}" for c in fetch_cols if c != "match_id")

    conn.execute(f"""
        INSERT INTO {table_name} ({col_list})
        SELECT {col_list} FROM df_temp
        ON CONFLICT (match_id) DO UPDATE SET {update_set}
    """)
    conn.close()
    print(f"✅ Wrote {len(df)} rows into DuckDB table '{table_name}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Predictor Data Pipeline CLI")
    parser.add_argument("--build-db",     action="store_true", help="Initialize the database schema")
    parser.add_argument("--fetch-today",  action="store_true", help="Fetch today's fixtures and store them")
    parser.add_argument("--backfill-stats", action="store_true",
                         help="Backfill shots/shots-on-target/corners for recently finished matches")
    args = parser.parse_args()

    if args.build_db:
        conn = duckdb.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_matches (
                match_id   INTEGER PRIMARY KEY,
                match_date VARCHAR,
                match_time VARCHAR,
                competition VARCHAR,
                home_team  VARCHAR,
                away_team  VARCHAR,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_score INTEGER,
                away_score INTEGER,
                home_ht_score INTEGER,
                away_ht_score INTEGER,
                status     VARCHAR,
                odds_home  REAL,
                odds_draw  REAL,
                odds_away  REAL,
                home_shots    INTEGER,
                away_shots    INTEGER,
                home_shots_ot INTEGER,
                away_shots_ot INTEGER,
                home_corners  INTEGER,
                away_corners  INTEGER
            )
        """)
        conn.close()
        print("✅ Database schema initialized.")

    elif args.fetch_today:
        # Fetch tomorrow's fixtures too, not just today's. This pre-loads the
        # data the "Tomorrow" toggle needs, and — more importantly — means
        # tomorrow's fixtures are already sitting in the DB *before* midnight
        # hits, closing the gap where the app showed nothing/stale data
        # between 00:00 and whenever the (delayed) scheduled run actually
        # executes for "today" the next calendar day.
        df_today = fetch_fixtures_for_date()
        if not df_today.empty:
            update_database(df_today, "historical_matches")

        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        df_tomorrow = fetch_fixtures_for_date(tomorrow)
        if not df_tomorrow.empty:
            update_database(df_tomorrow, "historical_matches")

    elif args.backfill_stats:
        backfill_match_statistics()
