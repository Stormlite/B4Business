from __future__ import annotations

from datetime import datetime
from typing import List

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "home_last3_goals_scored",
    "home_last3_goals_conceded",
    "home_last3_goal_diff",
    "home_last3_total_goals",
    "home_last5_over25_rate",
    "home_rest_days",
    "home_last3_shots",
    "home_last3_sot",
    "home_last3_shot_accuracy",
    "home_last3_sot_rate",
    "away_last3_goals_scored",
    "away_last3_goals_conceded",
    "away_last3_goal_diff",
    "away_last3_total_goals",
    "away_last5_over25_rate",
    "away_rest_days",
    "away_last3_shots",
    "away_last3_sot",
    "away_last3_shot_accuracy",
    "away_last3_sot_rate",
    "home_last5_total_goals",
    "away_last5_total_goals",
    "home_last5_total_goals_diff",
    "home_last5_over25_rate_diff",
    "home_last3_total_goals_diff",
    "home_last3_shots_diff",
    "home_last3_sot_diff",
    "home_last3_shot_accuracy_diff",
    "home_last3_sot_rate_diff",
    "home_rest_days_diff",
    "competition_mean_goals",
    "competition_over25_rate",
    "home_attack_strength",
    "home_defense_strength",
    "away_attack_strength",
    "away_defense_strength",
    "home_attack_vs_away_defense",
    "away_attack_vs_home_defense",
    "h2h_last5_over25_rate",
    "home_is_favorite",
]


def add_match_outcomes(matches: pd.DataFrame) -> pd.DataFrame:
    df = matches.copy()
    df["over_2_5"] = (df["total_goals"] > 2.5).astype(int)
    return df


def build_team_history(matches: pd.DataFrame) -> pd.DataFrame:
    df = matches.sort_values("date").copy()
    team_records = []
    for team in pd.unique(pd.concat([df["home_team"], df["away_team"]])):
        team_matches = df[(df["home_team"] == team) | (df["away_team"] == team)].copy()
        team_matches = team_matches.sort_values("date")
        team_matches["is_home"] = team_matches["home_team"] == team
        team_matches["goals_scored"] = np.where(team_matches["is_home"], team_matches["home_goals"], team_matches["away_goals"])
        team_matches["goals_conceded"] = np.where(team_matches["is_home"], team_matches["away_goals"], team_matches["home_goals"])
        team_matches["total_goals"] = team_matches["goals_scored"] + team_matches["goals_conceded"]
        # shots and shots-on-target per team (if provided in original dataset)
        if "home_shots" in team_matches.columns and "away_shots" in team_matches.columns:
            team_matches["shots_for"] = np.where(team_matches["is_home"], team_matches["home_shots"], team_matches["away_shots"])
        else:
            team_matches["shots_for"] = 0

        if "home_sot" in team_matches.columns and "away_sot" in team_matches.columns:
            team_matches["sot_for"] = np.where(team_matches["is_home"], team_matches["home_sot"], team_matches["away_sot"])
        else:
            team_matches["sot_for"] = 0
        team_records.append(team_matches)
    return pd.concat(team_records, ignore_index=True)


def rolling_stats(series: pd.Series, window: int) -> pd.Series:
    return series.shift(1).rolling(window, min_periods=1).mean()


def compute_rest_days(df: pd.DataFrame) -> pd.Series:
    df = df.sort_values("date")
    rest = df["date"].diff().dt.days
    rest = rest.shift(1).fillna(7).clip(lower=1)
    return rest


def build_features(matches: pd.DataFrame, reference_date: datetime | None = None) -> pd.DataFrame:
    df = add_match_outcomes(matches)
    df = df.sort_values("date").reset_index(drop=True)
    home_history = build_team_history(df)
    away_history = home_history.copy()

    home_agg = []
    away_agg = []
    for index, row in df.iterrows():
        team = row["home_team"]
        history = home_history[(home_history["home_team"] == team) | (home_history["away_team"] == team)]
        team_history = history[history["date"] < row["date"]]
        team_history = team_history.sort_values("date")
        home_last3_goals = rolling_stats(team_history["goals_scored"], 3).iloc[-1] if not team_history.empty else 0.0
        home_last3_conceded = rolling_stats(team_history["goals_conceded"], 3).iloc[-1] if not team_history.empty else 0.0
        home_last3_shots = rolling_stats(team_history["shots_for"], 3).iloc[-1] if ("shots_for" in team_history.columns and not team_history.empty) else 0.0
        home_last3_sot = rolling_stats(team_history["sot_for"], 3).iloc[-1] if ("sot_for" in team_history.columns and not team_history.empty) else 0.0
        home_last3_total_goals = rolling_stats(team_history["total_goals"], 3).iloc[-1] if not team_history.empty else 0.0
        home_last5_total_goals = rolling_stats(team_history["total_goals"], 5).iloc[-1] if not team_history.empty else 0.0
        home_last5_over25_rate = rolling_stats(team_history["total_goals"].gt(2.5).astype(int), 5).iloc[-1] if not team_history.empty else 0.0
        home_rest_days = compute_rest_days(team_history).iloc[-1] if len(team_history) >= 1 else 7
        home_last3_shot_accuracy = home_last3_goals / home_last3_shots if home_last3_shots > 0 else 0.0
        home_last3_sot_rate = home_last3_sot / home_last3_shots if home_last3_shots > 0 else 0.0
        home_agg.append({
            "home_last3_goals_scored": home_last3_goals,
            "home_last3_goals_conceded": home_last3_conceded,
            "home_last3_goal_diff": home_last3_goals - home_last3_conceded,
            "home_last3_total_goals": home_last3_total_goals,
            "home_last5_total_goals": home_last5_total_goals,
            "home_last5_over25_rate": home_last5_over25_rate,
            "home_rest_days": home_rest_days,
            "home_last3_shots": home_last3_shots,
            "home_last3_sot": home_last3_sot,
            "home_last3_shot_accuracy": home_last3_shot_accuracy,
            "home_last3_sot_rate": home_last3_sot_rate,
        })

        team = row["away_team"]
        history = away_history[(away_history["home_team"] == team) | (away_history["away_team"] == team)]
        team_history = history[history["date"] < row["date"]]
        team_history = team_history.sort_values("date")
        away_last3_goals = rolling_stats(team_history["goals_scored"], 3).iloc[-1] if not team_history.empty else 0.0
        away_last3_conceded = rolling_stats(team_history["goals_conceded"], 3).iloc[-1] if not team_history.empty else 0.0
        away_last3_shots = rolling_stats(team_history["shots_for"], 3).iloc[-1] if ("shots_for" in team_history.columns and not team_history.empty) else 0.0
        away_last3_sot = rolling_stats(team_history["sot_for"], 3).iloc[-1] if ("sot_for" in team_history.columns and not team_history.empty) else 0.0
        away_last3_total_goals = rolling_stats(team_history["total_goals"], 3).iloc[-1] if not team_history.empty else 0.0
        away_last5_total_goals = rolling_stats(team_history["total_goals"], 5).iloc[-1] if not team_history.empty else 0.0
        away_last5_over25_rate = rolling_stats(team_history["total_goals"].gt(2.5).astype(int), 5).iloc[-1] if not team_history.empty else 0.0
        away_rest_days = compute_rest_days(team_history).iloc[-1] if len(team_history) >= 1 else 7
        away_last3_shot_accuracy = away_last3_goals / away_last3_shots if away_last3_shots > 0 else 0.0
        away_last3_sot_rate = away_last3_sot / away_last3_shots if away_last3_shots > 0 else 0.0
        away_agg.append({
            "away_last3_goals_scored": away_last3_goals,
            "away_last3_goals_conceded": away_last3_conceded,
            "away_last3_goal_diff": away_last3_goals - away_last3_conceded,
            "away_last3_total_goals": away_last3_total_goals,
            "away_last5_total_goals": away_last5_total_goals,
            "away_last5_over25_rate": away_last5_over25_rate,
            "away_rest_days": away_rest_days,
            "away_last3_shots": away_last3_shots,
            "away_last3_sot": away_last3_sot,
            "away_last3_shot_accuracy": away_last3_shot_accuracy,
            "away_last3_sot_rate": away_last3_sot_rate,
        })

    home_features = pd.DataFrame(home_agg)
    away_features = pd.DataFrame(away_agg)
    features = pd.concat([df.reset_index(drop=True), home_features, away_features], axis=1)
    features = features.sort_values("date").reset_index(drop=True)

    features["competition_mean_goals"] = features.groupby("competition")["total_goals"].transform(
        lambda s: s.expanding().mean().shift(1)
    )
    features["competition_mean_goals"] = features["competition_mean_goals"].fillna(features["total_goals"].mean())
    features["competition_over25_rate"] = features.groupby("competition")["over_2_5"].transform(
        lambda s: s.expanding().mean().shift(1)
    )
    features["competition_over25_rate"] = features["competition_over25_rate"].fillna(features["over_2_5"].mean())

    features["home_attack_strength"] = np.where(
        features["home_last3_goals_scored"] > 0,
        features["home_last3_goals_scored"] / features["competition_mean_goals"],
        0.0,
    )
    features["home_defense_strength"] = np.where(
        features["home_last3_goals_conceded"] > 0,
        features["home_last3_goals_conceded"] / features["competition_mean_goals"],
        0.0,
    )
    features["away_attack_strength"] = np.where(
        features["away_last3_goals_scored"] > 0,
        features["away_last3_goals_scored"] / features["competition_mean_goals"],
        0.0,
    )
    features["away_defense_strength"] = np.where(
        features["away_last3_goals_conceded"] > 0,
        features["away_last3_goals_conceded"] / features["competition_mean_goals"],
        0.0,
    )
    features["home_last5_total_goals_diff"] = features["home_last5_total_goals"] - features["away_last5_total_goals"]
    features["home_last5_over25_rate_diff"] = features["home_last5_over25_rate"] - features["away_last5_over25_rate"]
    features["home_last3_total_goals_diff"] = features["home_last3_total_goals"] - features["away_last3_total_goals"]
    features["home_last3_shots_diff"] = features["home_last3_shots"] - features["away_last3_shots"]
    features["home_last3_sot_diff"] = features["home_last3_sot"] - features["away_last3_sot"]
    features["home_last3_shot_accuracy_diff"] = features["home_last3_shot_accuracy"] - features["away_last3_shot_accuracy"]
    features["home_last3_sot_rate_diff"] = features["home_last3_sot_rate"] - features["away_last3_sot_rate"]
    features["home_rest_days_diff"] = features["home_rest_days"] - features["away_rest_days"]
    features["home_attack_vs_away_defense"] = np.where(
        features["away_last3_goals_conceded"] > 0,
        features["home_last3_goals_scored"] / (features["away_last3_goals_conceded"] + 1e-6),
        0.0,
    )
    features["away_attack_vs_home_defense"] = np.where(
        features["home_last3_goals_conceded"] > 0,
        features["away_last3_goals_scored"] / (features["home_last3_goals_conceded"] + 1e-6),
        0.0,
    )

    features["h2h_last5_over25_rate"] = 0.0
    for idx, row in features.iterrows():
        mask = (
            ((features["home_team"] == row["home_team"]) & (features["away_team"] == row["away_team"]))
            | ((features["home_team"] == row["away_team"]) & (features["away_team"] == row["home_team"]))
        )
        previous = features[mask & (features["date"] < row["date"])].sort_values("date")
        previous = previous.tail(5)
        if not previous.empty:
            features.at[idx, "h2h_last5_over25_rate"] = previous["total_goals"].gt(2.5).astype(int).mean()

    features["home_is_favorite"] = 0.0
    if "odds_over_2_5" in features.columns:
        features["home_is_favorite"] = np.where(features["odds_over_2_5"].notna() & (features["odds_over_2_5"] < 2.0), 1.0, 0.0)

    features[FEATURE_COLUMNS] = features[FEATURE_COLUMNS].fillna(0.0)
    return features


def select_feature_matrix(features: pd.DataFrame, feature_names: list[str] | None = None) -> tuple[pd.DataFrame, pd.Series]:
    # Allow selecting a custom ordered list of feature names (used at prediction time)
    if feature_names is None:
        feature_names = FEATURE_COLUMNS

    X = features.copy()
    # Ensure all requested features exist; if not, create them filled with 0.0
    for fn in feature_names:
        if fn not in X.columns:
            X[fn] = 0.0

    X = X[feature_names].copy()
    y = features["over_2_5"].astype(int) if "over_2_5" in features.columns else pd.Series([0] * len(X))
    return X, y


def compute_team_history(history: pd.DataFrame, team: str) -> pd.DataFrame:
    team_history = history[(history["home_team"] == team) | (history["away_team"] == team)].copy()
    team_history = team_history.sort_values("date")
    team_history["is_home"] = team_history["home_team"] == team
    team_history["goals_scored"] = np.where(team_history["is_home"], team_history["home_goals"], team_history["away_goals"])
    team_history["goals_conceded"] = np.where(team_history["is_home"], team_history["away_goals"], team_history["home_goals"])
    team_history["total_goals"] = team_history["goals_scored"] + team_history["goals_conceded"]
    # include shots and sot per team if available
    if "home_shots" in team_history.columns and "away_shots" in team_history.columns:
        team_history["shots_for"] = np.where(team_history["is_home"], team_history["home_shots"], team_history["away_shots"])
    else:
        team_history["shots_for"] = 0

    if "home_sot" in team_history.columns and "away_sot" in team_history.columns:
        team_history["sot_for"] = np.where(team_history["is_home"], team_history["home_sot"], team_history["away_sot"])
    else:
        team_history["sot_for"] = 0
    return team_history


def fixture_team_features(team_history: pd.DataFrame, fixture_date: datetime) -> dict[str, float]:
    subset = team_history[team_history["date"] < fixture_date]
    if subset.empty:
        return {
            "last3_goals_scored": 0.0,
            "last3_goals_conceded": 0.0,
            "last3_goal_diff": 0.0,
            "last3_total_goals": 0.0,
            "last5_total_goals": 0.0,
            "last5_over25_rate": 0.0,
            "rest_days": 7.0,
            "last3_shots": 0.0,
            "last3_sot": 0.0,
            "last3_shot_accuracy": 0.0,
            "last3_sot_rate": 0.0,
        }

    last3_goals = rolling_stats(subset["goals_scored"], 3).iloc[-1]
    last3_conceded = rolling_stats(subset["goals_conceded"], 3).iloc[-1]
    last3_shots = rolling_stats(subset["shots_for"], 3).iloc[-1] if "shots_for" in subset.columns else 0.0
    last3_sot = rolling_stats(subset["sot_for"], 3).iloc[-1] if "sot_for" in subset.columns else 0.0
    return {
        "last3_goals_scored": last3_goals,
        "last3_goals_conceded": last3_conceded,
        "last3_goal_diff": last3_goals - last3_conceded,
        "last3_total_goals": rolling_stats(subset["total_goals"], 3).iloc[-1],
        "last5_total_goals": rolling_stats(subset["total_goals"], 5).iloc[-1],
        "last5_over25_rate": rolling_stats(subset["total_goals"].gt(2.5).astype(int), 5).iloc[-1],
        "rest_days": compute_rest_days(subset).iloc[-1] if len(subset) >= 1 else 7.0,
        "last3_shots": last3_shots,
        "last3_sot": last3_sot,
        "last3_shot_accuracy": last3_goals / last3_shots if last3_shots > 0 else 0.0,
        "last3_sot_rate": last3_sot / last3_shots if last3_shots > 0 else 0.0,
    }


def prepare_fixture_features(fixtures: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    fixtures = fixtures.copy()
    fixtures["date"] = pd.to_datetime(fixtures["date"])
    fixtures["competition"] = fixtures.get("competition", "Unknown")
    fixtures = fixtures.sort_values("date").reset_index(drop=True)
    fixtures_features = []

    league_mean = history.groupby("competition")["total_goals"].mean()
    league_over25 = history.groupby("competition")["total_goals"].apply(
        lambda s: (s > 2.5).astype(int).mean()
    )

    for _, fixture in fixtures.iterrows():
        home_history = compute_team_history(history, fixture["home_team"])
        away_history = compute_team_history(history, fixture["away_team"])
        home_stats = fixture_team_features(home_history, fixture["date"])
        away_stats = fixture_team_features(away_history, fixture["date"])

        over_25_rate = home_stats["last5_over25_rate"] * 0.5 + away_stats["last5_over25_rate"] * 0.5
        h2h_rate = 0.0
        mask = (
            ((history["home_team"] == fixture["home_team"]) & (history["away_team"] == fixture["away_team"]))
            | ((history["home_team"] == fixture["away_team"]) & (history["away_team"] == fixture["home_team"]))
        )
        h2h_matches = history[mask].sort_values("date").tail(5)
        if not h2h_matches.empty:
            h2h_rate = (h2h_matches["total_goals"] > 2.5).astype(int).mean()

        league_avg = float(league_mean.get(fixture["competition"], history["total_goals"].mean()))
        home_attack_strength = home_stats["last3_goals_scored"] / league_avg if league_avg > 0 else 0.0
        away_defense_strength = away_stats["last3_goals_conceded"] / league_avg if league_avg > 0 else 0.0

        fixtures_features.append({
            "date": fixture["date"],
            "competition": fixture["competition"],
            "home_team": fixture["home_team"],
            "away_team": fixture["away_team"],
            "home_last3_goals_scored": home_stats["last3_goals_scored"],
            "home_last3_goals_conceded": home_stats["last3_goals_conceded"],
            "home_last3_goal_diff": home_stats["last3_goal_diff"],
            "home_last3_total_goals": home_stats["last3_total_goals"],
            "home_last5_over25_rate": home_stats["last5_over25_rate"],
            "home_rest_days": home_stats["rest_days"],
            "home_last3_shots": home_stats["last3_shots"],
            "home_last3_sot": home_stats["last3_sot"],
            "home_last3_shot_accuracy": home_stats["last3_shot_accuracy"],
            "home_last3_sot_rate": home_stats["last3_sot_rate"],
            "away_last3_goals_scored": away_stats["last3_goals_scored"],
            "away_last3_goals_conceded": away_stats["last3_goals_conceded"],
            "away_last3_goal_diff": away_stats["last3_goal_diff"],
            "away_last3_total_goals": away_stats["last3_total_goals"],
            "away_last5_over25_rate": away_stats["last5_over25_rate"],
            "away_rest_days": away_stats["rest_days"],
            "away_last3_shots": away_stats["last3_shots"],
            "away_last3_sot": away_stats["last3_sot"],
            "away_last3_shot_accuracy": away_stats["last3_shot_accuracy"],
            "away_last3_sot_rate": away_stats["last3_sot_rate"],
            "home_last5_total_goals": home_stats["last5_total_goals"],
            "away_last5_total_goals": away_stats["last5_total_goals"],
            "home_last5_total_goals_diff": home_stats["last5_total_goals"] - away_stats["last5_total_goals"],
            "home_last5_over25_rate_diff": home_stats["last5_over25_rate"] - away_stats["last5_over25_rate"],
            "home_last3_total_goals_diff": home_stats["last3_total_goals"] - away_stats["last3_total_goals"],
            "home_last3_shots_diff": home_stats["last3_shots"] - away_stats["last3_shots"],
            "home_last3_sot_diff": home_stats["last3_sot"] - away_stats["last3_sot"],
            "home_last3_shot_accuracy_diff": home_stats["last3_shot_accuracy"] - away_stats["last3_shot_accuracy"],
            "home_last3_sot_rate_diff": home_stats["last3_sot_rate"] - away_stats["last3_sot_rate"],
            "home_rest_days_diff": home_stats["rest_days"] - away_stats["rest_days"],
            "home_attack_strength": home_attack_strength,
            "home_defense_strength": home_stats["last3_goals_conceded"] / league_avg if league_avg > 0 else 0.0,
            "away_attack_strength": away_stats["last3_goals_scored"] / league_avg if league_avg > 0 else 0.0,
            "away_defense_strength": away_defense_strength,
            "competition_mean_goals": league_avg,
            "competition_over25_rate": float(league_over25.get(fixture["competition"], (history["total_goals"] > 2.5).astype(int).mean())),
            "home_attack_vs_away_defense": home_stats["last3_goals_scored"] / (away_stats["last3_goals_conceded"] + 1e-6) if away_stats["last3_goals_conceded"] > 0 else 0.0,
            "away_attack_vs_home_defense": away_stats["last3_goals_scored"] / (home_stats["last3_goals_conceded"] + 1e-6) if home_stats["last3_goals_conceded"] > 0 else 0.0,
            "h2h_last5_over25_rate": h2h_rate,
            "home_is_favorite": 0.0,
            "over_2_5": 0,
        })

    fixture_df = pd.DataFrame(fixtures_features)
    fixture_df[FEATURE_COLUMNS] = fixture_df[FEATURE_COLUMNS].fillna(0.0)
    return fixture_df
