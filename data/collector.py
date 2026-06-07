import argparse
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import requests
import duckdb

from config import DATA_DIR, DB_PATH, LEAGUE_CODES, SEASONS

BASE_URL = "https://www.football-data.co.uk/mmz4281"

CSV_COLUMNS = [
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "Referee",
    "HS",
    "AS",
    "HST",
    "AST",
    "HF",
    "AF",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
    "BWH",
    "BWD",
    "BWA",
    "PSH",
    "PSD",
    "PSA",
    "WHH",
    "WHD",
    "WHA",
    "VCH",
    "VCD",
    "VCA",
    "Bb1X2",
    "BbMxH",
    "BbAvH",
    "BbMxD",
    "BbAvD",
    "BbMxA",
    "BbAvA",
    "BbOU",
    "BbMx>2.5",
    "BbAv>2.5",
    "BbMx<2.5",
    "BbAv<2.5",
    "BbAH",
    "BbAHh",
    "BbMxAHH",
    "BbAvAHH",
    "BbMxAHA",
    "BbAvAHA",
]


def ensure_paths() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_csv(season: str, league_code: str) -> Path:
    season_dir = DATA_DIR / season
    season_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{league_code}.csv"
    target_path = season_dir / file_name
    if target_path.exists():
        return target_path

    url = f"{BASE_URL}/{season}/{file_name}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    target_path.write_bytes(response.content)
    return target_path


def load_csv(path: Path, league_code: str, season: str) -> pd.DataFrame:
    df = pd.read_csv(path, dayfirst=True, parse_dates=["Date"], encoding="latin1", on_bad_lines="skip")
    if df.empty:
        return df

    columns = {"Date": "date", "HomeTeam": "home_team", "AwayTeam": "away_team", "FTHG": "home_goals", "FTAG": "away_goals", "FTR": "result"}
    df = df.rename(columns=columns)
    keep = [c for c in ["date", "home_team", "away_team", "home_goals", "away_goals", "HS", "AS", "HST", "AST", "BbAv>2.5", "BbOU"] if c in df.columns]
    df = df[keep]
    df = df.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"])
    df["competition"] = LEAGUE_CODES.get(league_code, league_code)
    df["season"] = season
    df["total_goals"] = df["home_goals"] + df["away_goals"]
    if "BbAv>2.5" in df.columns:
        df["odds_over_2_5"] = pd.to_numeric(df["BbAv>2.5"], errors="coerce")
    else:
        df["odds_over_2_5"] = pd.NA

    df = df.sort_values("date").reset_index(drop=True)
    # rename shot columns if present
    if "HS" in df.columns:
        df = df.rename(columns={"HS": "home_shots", "AS": "away_shots", "HST": "home_sot", "AST": "away_sot"})

    out_cols = ["date", "competition", "season", "home_team", "away_team", "home_goals", "away_goals", "total_goals", "odds_over_2_5"]
    for col in ["home_shots", "away_shots", "home_sot", "away_sot"]:
        if col in df.columns:
            out_cols.append(col)

    return df[out_cols]


def build_match_database() -> None:
    ensure_paths()
    records: List[pd.DataFrame] = []
    for season in SEASONS:
        for league_code in LEAGUE_CODES:
            try:
                csv_path = download_csv(season, league_code)
                df = load_csv(csv_path, league_code, season)
                if not df.empty:
                    records.append(df)
            except Exception as exc:
                print(f"Skipping {league_code} {season}: {exc}")

    if not records:
        raise RuntimeError("No datasets were loaded. Check internet connectivity and league metadata.")

    all_matches = pd.concat(records, ignore_index=True)
    con = duckdb.connect(DB_PATH)
    con.register("all_matches", all_matches)
    con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM all_matches")
    con.execute("COPY matches TO '" + str(DATA_DIR / "matches.parquet") + "' (FORMAT PARQUET)")
    con.close()
    print(f"Built database with {len(all_matches)} matches at {DB_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and build football match data for over 2.5 prediction.")
    parser.add_argument("--build-db", action="store_true", help="Download league CSVs and build the match database.")
    args = parser.parse_args()

    if args.build_db:
        build_match_database()


if __name__ == "__main__":
    main()
