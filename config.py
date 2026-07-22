import os

# Central configuration directory routing paths
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "matches.duckdb")

# Machine Learning Binary Storage Paths
MODEL_PATH = os.path.join(MODEL_DIR, "over25_model.joblib")
OVER05_MODEL_PATH = os.path.join(MODEL_DIR, "over05_model.joblib")
CORNERS_MODEL_PATH = os.path.join(MODEL_DIR, "corners_model.joblib")
BTTS_MODEL_PATH = os.path.join(MODEL_DIR, "btts_model.joblib")
OUTCOME_MODEL_PATH = os.path.join(MODEL_DIR, "outcome_model.joblib")  # 🌟 FIXED: Added variable definition
