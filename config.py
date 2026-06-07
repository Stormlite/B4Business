from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "models"
DB_PATH = DATA_DIR / "matches.duckdb"
MODEL_PATH = MODEL_DIR / "over25_model.joblib"
SCALER_PATH = MODEL_DIR / "scaler.joblib"
# Optional: a public URL where a pre-built model can be downloaded at runtime
# If you deploy the app and don't commit the model artifact, set this to a stable URL
# or provide the URL via the MODEL_DOWNLOAD_URL environment variable.
MODEL_DOWNLOAD_URL = None

# Folder where you can place multiple fixtures CSV files. The CLI and utilities
# will look here if you pass a directory as the fixtures argument.
FIXTURES_DIR = DATA_DIR / "fixtures"

LEAGUE_CODES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "I1": "Serie A",
    "F1": "Ligue 1",
}

SEASONS = ["2223", "2324", "2425"]
