"""
features/engineer.py — Optimised feature pipeline
================================================
Key upgrades vs original:
  1. Loads from local CSV files (5 330 rows) rather than only DuckDB (1 872)
  2. Rolling window extended to 10 games (empirically better)
  3. Shots-on-target, corners, BTTS rate, and per-team Over-2.5 rate added
  4. Pre-match Avg>2.5 / B365>2.5 market-odds features (when present)
  5. League encoding (some leagues are inherently higher-scoring)
  6. DuckDB path kept for live-prediction integration
"""

import os
import pandas as pd
import numpy as np
import duckdb

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "matches.duckdb")

# ── CSV files shipped in the repo ───────────────────────────────────────────
_CSV_SEASONS = ["2223", "2324", "2425"]
_CSV_LEAGUES  = ["E0.csv", "D1.csv", "SP1.csv", "I1.csv", "F1.csv"]
_DATA_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

ROLLING_WINDOW = 10        # games to look back for rolling stats
MIN_PERIODS    = 3         # minimum games before a rolling stat is valid

# Feature columns the models will actually use (in order)
FEATURE_COLS = [
    # Rolling goal averages (home / away)
    "h_roll_scored",   "h_roll_conceded",
    "a_roll_scored",   "a_roll_conceded",
    # Combined scoring
    "comb_scoring",    "comb_conceded",
    # Shots on target
    "h_roll_shots_ot", "a_roll_shots_ot", "comb_shots_ot",
    # Corners
    "h_roll_corners",  "a_roll_corners",
    # Per-team market trends
    "h_roll_over25",   "a_roll_over25",   "comb_over25",
    "h_roll_btts",     "a_roll_btts",
    # Composite signals
    "home_adv_score",  "shot_ratio",
    # League context
    "league_enc",
]

# These are added only when pre-match odds are in the data (training CSV path)
ODDS_FEATURE_COLS = [
    "ip_avg_over25",
    "ip_b365_over25",
    "ip_avg_home",
    "ip_avg_draw",
]


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_csv_data() -> pd.DataFrame:
    """
    Loads all local CSV season files and returns a clean DataFrame.
    Columns normalised to match the rest of the pipeline.
    """
    frames = []
    for season in _CSV_SEASONS:
        for fname in _CSV_LEAGUES:
            path = os.path.join(_DATA_DIR, season, fname)
            if not os.path.exists(path):
                continue
            try:
                df = pd.read_csv(path)
                df["season"] = season
                frames.append(df)
            except Exception as e:
                print(f"⚠️  Could not read {path}: {e}")

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)

    # Drop rows without final scores
    raw = raw.dropna(subset=["FTHG", "FTAG"])

    # Normalise column names to shared schema
    col_map = {
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "FTHG": "home_score",   "FTAG": "away_score",
        "Div":  "competition",
    }
    raw = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})
    raw = raw.reset_index(drop=True)

    # Build all new columns in one assignment to avoid fragmentation warnings
    match_date = pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce")
    home_score = raw["home_score"]
    away_score = raw["away_score"]
    total      = home_score + away_score
    new_cols = pd.DataFrame({
        "match_date":     match_date,
        "status":         "FINISHED",
        "match_id":       -(np.arange(len(raw)) + 1),
        "total_goals":    total,
        "target_over25":  (total > 2.5).astype(int),
        "target_over05":  (total > 0.5).astype(int),
        "target_btts":    ((home_score > 0) & (away_score > 0)).astype(int),
        "target_home_win": (home_score > away_score).astype(int),
        "target_draw":     (home_score == away_score).astype(int),
        "target_away_win": (home_score < away_score).astype(int),
    })
    raw = pd.concat([raw, new_cols], axis=1)

    return raw.sort_values("match_date").reset_index(drop=True)


def load_raw_data_from_db() -> pd.DataFrame:
    """Loads matches from DuckDB (used for live prediction path)."""
    conn = duckdb.connect(DB_PATH)
    query = """
        SELECT
            match_id, match_date, competition, home_team, away_team,
            CAST(home_score AS REAL) AS home_score,
            CAST(away_score AS REAL) AS away_score,
            status,
            CAST(odds_home AS REAL) AS odds_home,
            CAST(odds_draw AS REAL) AS odds_draw,
            CAST(odds_away AS REAL) AS odds_away
        FROM historical_matches
        ORDER BY match_date ASC
    """
    df = conn.execute(query).df()
    conn.close()

    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df["total_goals"]    = df["home_score"] + df["away_score"]
    df["target_over25"]  = np.where(df["total_goals"] > 2.5, 1, 0)
    df["target_over05"]  = np.where(df["total_goals"] > 0.5, 1, 0)
    df["target_btts"]    = np.where((df["home_score"] > 0) & (df["away_score"] > 0), 1, 0)
    df["target_home_win"] = np.where(df["home_score"] > df["away_score"], 1, 0)
    df["target_draw"]     = np.where(df["home_score"] == df["away_score"], 1, 0)
    df["target_away_win"] = np.where(df["home_score"] < df["away_score"], 1, 0)

    return df


def _build_rolling_stats(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    """
    Computes per-team rolling averages without data leakage.
    Uses shift(1) so each game only sees the team's *previous* matches.
    """
    df = df.copy().sort_values("match_date").reset_index(drop=True)
    df["_idx"] = df.index

    # Determine which columns are available
    shots_available   = "HS" in df.columns and "AS" in df.columns
    shots_ot_avail    = "HST" in df.columns and "AST" in df.columns
    corners_avail     = "HC" in df.columns and "AC" in df.columns

    def _side(team_col, sc, cc, sh, st, co, is_home_val):
        cols = ["_idx", "match_date", team_col, sc, cc]
        renames = {"_idx": "_idx", "match_date": "date", team_col: "team", sc: "scored", cc: "conceded"}
        extras = {}
        if shots_available:
            cols.append(sh); renames[sh] = "shots"
        if shots_ot_avail:
            cols.append(st); renames[st] = "shots_ot"
        if corners_avail:
            cols.append(co); renames[co] = "corners"
        tmp = df[cols].copy().rename(columns=renames)
        tmp["is_home"] = is_home_val
        return tmp

    home_side = _side("home_team", "home_score", "away_score",
                      "HS", "HST", "HC", 1)
    away_side = _side("away_team", "away_score", "home_score",
                      "AS", "AST", "AC", 0)
    hist = pd.concat([home_side, away_side]).sort_values(["team", "date"]).reset_index(drop=True)

    # Rolling averages with leakage-free shift
    def _roll(series):
        return series.shift(1).rolling(window, min_periods=MIN_PERIODS).mean()

    for col in ["scored", "conceded"]:
        hist[f"roll_{col}"] = hist.groupby("team")[col].transform(_roll)

    if shots_available:
        hist["roll_shots"] = hist.groupby("team")["shots"].transform(_roll)
    if shots_ot_avail:
        hist["roll_shots_ot"] = hist.groupby("team")["shots_ot"].transform(_roll)
    if corners_avail:
        hist["roll_corners"] = hist.groupby("team")["corners"].transform(_roll)

    hist["over25_ind"] = ((hist["scored"] + hist["conceded"]) > 2.5).astype(int)
    hist["btts_ind"]   = ((hist["scored"] > 0) & (hist["conceded"] > 0)).astype(int)
    hist["roll_over25"] = hist.groupby("team")["over25_ind"].transform(_roll)
    hist["roll_btts"]   = hist.groupby("team")["btts_ind"].transform(_roll)

    roll_cols = [c for c in ["roll_scored", "roll_conceded", "roll_shots",
                              "roll_shots_ot", "roll_corners", "roll_over25", "roll_btts"]
                 if c in hist.columns]

    h_stats = hist[hist.is_home == 1][["_idx"] + roll_cols].copy()
    h_stats.columns = ["_idx"] + ["h_" + c for c in roll_cols]

    a_stats = hist[hist.is_home == 0][["_idx"] + roll_cols].copy()
    a_stats.columns = ["_idx"] + ["a_" + c for c in roll_cols]

    df = df.merge(h_stats, on="_idx", how="left").merge(a_stats, on="_idx", how="left")

    # Composite features
    df["comb_scoring"]  = df.get("h_roll_scored", 0) + df.get("a_roll_scored", 0)
    df["comb_conceded"] = df.get("h_roll_conceded", 0) + df.get("a_roll_conceded", 0)
    df["home_adv_score"] = df.get("h_roll_scored", 0) - df.get("a_roll_scored", 0)

    if "h_roll_shots_ot" in df.columns and "a_roll_shots_ot" in df.columns:
        df["comb_shots_ot"] = df["h_roll_shots_ot"] + df["a_roll_shots_ot"]
        df["shot_ratio"]    = df["h_roll_shots_ot"] / (df["a_roll_shots_ot"] + 0.01)
    else:
        df["comb_shots_ot"] = np.nan
        df["shot_ratio"]    = np.nan

    if "h_roll_corners" in df.columns and "a_roll_corners" in df.columns:
        pass  # already present
    else:
        df["h_roll_corners"] = np.nan
        df["a_roll_corners"] = np.nan

    if "h_roll_over25" in df.columns and "a_roll_over25" in df.columns:
        df["comb_over25"] = (df["h_roll_over25"] + df["a_roll_over25"]) / 2
    else:
        df["comb_over25"] = np.nan

    if "h_roll_shots" not in df.columns:
        df["h_roll_shots"] = np.nan
        df["a_roll_shots"] = np.nan

    # League encoding (ordinal, sorted alphabetically for reproducibility)
    if "competition" in df.columns:
        league_order = sorted(df["competition"].dropna().unique())
        league_map   = {v: i for i, v in enumerate(league_order)}
        df["league_enc"] = df["competition"].map(league_map).fillna(-1).astype(int)
    else:
        df["league_enc"] = 0

    # Market-implied Over 2.5 probabilities (CSV training data only)
    if "Avg>2.5" in df.columns:
        df["ip_avg_over25"] = 1.0 / df["Avg>2.5"].replace(0, np.nan)
    if "B365>2.5" in df.columns:
        df["ip_b365_over25"] = 1.0 / df["B365>2.5"].replace(0, np.nan)
    for odds_h, odds_d, odds_a, pfx in [
        ("AvgH",  "AvgD",  "AvgA",  "avg"),
        ("B365H", "B365D", "B365A", "b365"),
        # Live DuckDB schema uses different column names for the same thing
        # (match-winner decimal odds) — without this, ip_avg_home/ip_avg_draw
        # were only ever computed for CSV training data, never for live
        # fixtures, even though real odds were being collected into
        # odds_home/odds_draw/odds_away all along. Live predictions were
        # silently falling back to a constant training-median value for the
        # single most important outcome-model feature (~17% importance),
        # which biased live 1X2 predictions toward the home team (the
        # majority class in training) regardless of the actual matchup.
        ("odds_home", "odds_draw", "odds_away", "avg"),
    ]:
        if all(c in df.columns for c in [odds_h, odds_d, odds_a]):
            margin = (1 / df[odds_h].replace(0, np.nan)
                    + 1 / df[odds_d].replace(0, np.nan)
                    + 1 / df[odds_a].replace(0, np.nan))
            df[f"ip_{pfx}_home"] = (1 / df[odds_h].replace(0, np.nan)) / margin
            df[f"ip_{pfx}_draw"] = (1 / df[odds_d].replace(0, np.nan)) / margin

    df.drop(columns=["_idx"], inplace=True, errors="ignore")
    return df


def get_available_feature_cols(df: pd.DataFrame) -> list:
    """Returns the subset of FEATURE_COLS + ODDS_FEATURE_COLS actually in df."""
    all_possible = FEATURE_COLS + ODDS_FEATURE_COLS
    return [c for c in all_possible if c in df.columns]


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline entry points
# ─────────────────────────────────────────────────────────────────────────────

def generate_training_data(use_csv: bool = True) -> pd.DataFrame:
    """
    Returns finished-match rows with features for model training.

    Parameters
    ----------
    use_csv : bool
        True  → load from local CSV files (recommended; 5 330 rows, richer features)
        False → load from DuckDB only (1 872 rows)
    """
    if use_csv:
        df_raw = load_csv_data()
        if df_raw.empty:
            print("⚠️  No CSV data found, falling back to DuckDB.")
            df_raw = load_raw_data_from_db()
    else:
        df_raw = load_raw_data_from_db()

    if df_raw.empty:
        return pd.DataFrame()

    df = _build_rolling_stats(df_raw)
    df = df[df["status"] == "FINISHED"]

    feat_cols = get_available_feature_cols(df)
    target_cols = [
        "target_over25", "target_over05", "target_btts",
        "target_home_win", "target_draw", "target_away_win",
    ]
    keep = ["match_id", "match_date", "competition", "home_team", "away_team"]

    return df[keep + feat_cols + target_cols].dropna(subset=feat_cols[:4])


def generate_feature_pipeline(extract_live_today_only: bool = False) -> pd.DataFrame:
    """
    Legacy-compatible entry point (called by models/predict.py).
    For live predictions, pulls from DuckDB; for training, uses CSV data.
    """
    if extract_live_today_only:
        df_raw = load_raw_data_from_db()
        if df_raw.empty:
            return pd.DataFrame()
        df = _build_rolling_stats(df_raw)
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        df_today = df[df["match_date"].dt.strftime("%Y-%m-%d") == today_str]
        feat_cols = get_available_feature_cols(df_today)
        id_cols = ["match_id", "match_date", "home_team", "away_team"]
        return df_today[id_cols + feat_cols]

    # Training path — prefer CSV
    return generate_training_data(use_csv=True)


# ─────────────────────────────────────────────────────────────────────────────
# Backwards-compat aliases (so existing scripts still import)
# ─────────────────────────────────────────────────────────────────────────────
calculate_rolling_stats = _build_rolling_stats
