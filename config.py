from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "models"
DB_PATH = DATA_DIR / "matches.duckdb"
MODEL_PATH = MODEL_DIR / "over25_model.joblib"
SCALER_PATH = MODEL_DIR / "scaler.joblib"

LEAGUE_CODES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "I1": "Serie A",
    "F1": "Ligue 1",
}

SEASONS = ["2223", "2324", "2425"]
