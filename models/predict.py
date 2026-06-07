import argparse
import io
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import requests
import os

from config import DB_PATH, MODEL_PATH, MODEL_DOWNLOAD_URL, FIXTURES_DIR
from features.engineer import build_features, prepare_fixture_features, select_feature_matrix


def _download_file(url: str, dest: Path, timeout: int = 30) -> None:
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def load_model():
    # Primary: load from local path
    if Path(MODEL_PATH).exists():
        return joblib.load(MODEL_PATH)

    # Secondary: try environment variable override
    env_url = os.environ.get("MODEL_DOWNLOAD_URL")
    url = env_url or MODEL_DOWNLOAD_URL
    if url:
        try:
            _download_file(url, Path(MODEL_PATH))
            return joblib.load(MODEL_PATH)
        except Exception as exc:
            raise RuntimeError(f"Model not found locally and download failed: {exc}") from exc

    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Train locally or set MODEL_DOWNLOAD_URL to download a pre-built model.")


def load_match_history() -> pd.DataFrame:
    import duckdb

    con = duckdb.connect(DB_PATH)
    df = con.execute("SELECT * FROM matches ORDER BY date").df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_fixtures(path: Path | str | io.IOBase) -> pd.DataFrame:
    # Support passing a directory containing multiple fixture CSVs — they will be concatenated
    def _normalize_df(df: pd.DataFrame, inferred_competition: str | None = None) -> pd.DataFrame:
        # Normalize column names: lowercase, strip, replace spaces with underscores
        df = df.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Common name mappings
        col_map = {}
        if "date" not in df.columns:
            # try common alternatives
            for alt in ("date", "match_date", "kickoff", "kickoff_time", "datetime"):
                if alt in df.columns:
                    col_map[alt] = "date"
                    break
        if "home_team" not in df.columns:
            for alt in ("home_team", "hometeam", "home", "home_team_name", "home_team_name"):
                if alt in df.columns:
                    col_map[alt] = "home_team"
                    break
        if "away_team" not in df.columns:
            for alt in ("away_team", "awayteam", "away", "away_team_name", "away_team_name"):
                if alt in df.columns:
                    col_map[alt] = "away_team"
                    break
        if "competition" not in df.columns and inferred_competition:
            df["competition"] = inferred_competition

        if col_map:
            df = df.rename(columns=col_map)

        # parse date robustly
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

        # ensure required columns exist
        for req in ("date", "home_team", "away_team"):
            if req not in df.columns:
                raise ValueError(f"Required fixture column '{req}' not found after normalization. Available: {list(df.columns)}")

        # Fill missing competition
        if "competition" not in df.columns:
            df["competition"] = inferred_competition or "Unknown"

        return df[["date", "competition", "home_team", "away_team"]].copy()

    if hasattr(path, "read"):
        df = pd.read_csv(path)
        return _normalize_df(df)
    else:
        path = Path(path)
        if path.is_dir():
            files = sorted(path.glob("*.csv"))
            if not files:
                raise FileNotFoundError(f"No CSV fixtures found in directory: {path}")
            parts: list[pd.DataFrame] = []
            for p in files:
                inferred = p.stem.split("-")[0].replace("_", " ").title()
                df_i = pd.read_csv(p)
                try:
                    parts.append(_normalize_df(df_i, inferred_competition=inferred))
                except Exception:
                    # try again without inferred competition if normalization fails
                    parts.append(_normalize_df(df_i, inferred_competition=None))
            df = pd.concat(parts, ignore_index=True)
            return df
        else:
            df = pd.read_csv(path)
            inferred = path.stem.split("-")[0].replace("_", " ").title()
            return _normalize_df(df, inferred_competition=inferred)


def predict_for_date(model, history: pd.DataFrame, fixtures: pd.DataFrame, date: datetime) -> pd.DataFrame:
    target_fixtures = fixtures[fixtures["date"] == date].copy()
    if target_fixtures.empty:
        raise ValueError(f"No fixtures found for {date.date()}")

    fixture_features = prepare_fixture_features(target_fixtures, history)
    X, _ = select_feature_matrix(fixture_features)
    probabilities = model.predict_proba(X)[:, 1]
    results = target_fixtures.copy()
    results["over_2_5_probability"] = probabilities
    results["prediction"] = (results["over_2_5_probability"] >= 0.5).astype(int)
    return results.sort_values("over_2_5_probability", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict over 2.5 goals for a given fixtures file and date.")
    parser.add_argument("--date", required=True, help="Prediction date in YYYY-MM-DD format.")
    parser.add_argument("--fixtures", required=True, help="CSV file containing upcoming fixtures.")
    parser.add_argument("--output", default="predictions.csv", help="Output CSV file.")
    args = parser.parse_args()

    model = load_model()
    history = load_match_history()
    fixtures = load_fixtures(Path(args.fixtures))
    date = datetime.fromisoformat(args.date)
    predictions = predict_for_date(model, history, fixtures, date)
    predictions.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output}")
    print(predictions.to_string(index=False))


if __name__ == "__main__":
    main()
