# Football Over-2.5 Goals Predictor

A Python-based prediction system for football matches, focused on over/under goals and multi-market match scoring. The repository combines:
- historical data ingestion into DuckDB,
- feature engineering from team rolling statistics,
- machine learning model training for Over 2.5 goals, BTTS, and 1X2 outcomes,
- a Streamlit dashboard for live prediction display.

## What this repository contains

### Core files
- `app.py`
  - Streamlit web application.
  - Loads live prediction scores via `models.predict.score_todays_fixtures()`.
  - Displays probabilities for Over 2.5, BTTS, 1X2 outcomes, plus live odds and match kickoff information.

- `config.py`
  - Central path definitions for model artifacts and the DuckDB file.
  - Exposes `MODEL_PATH`, `BTTS_MODEL_PATH`, `OUTCOME_MODEL_PATH`, and `DB_PATH`.

### Data ingestion
- `data/collector.py`
  - Fetches today's fixtures from API-Football v3 using `API_FOOTBALL_KEY`.
  - Fetches matcher odds from The Odds API v4 using `THE_ODDS_API_KEY`.
  - Writes or updates `historical_matches` in the DuckDB file at `config.DB_PATH`.
  - Provides:
    - `fetch_live_market_odds()`
    - `fetch_todays_fixtures_from_api()`
    - `update_database()`
  - Also includes a CLI entrypoint for `--build-db` and `--fetch-today`.

### Feature engineering
- `features/engineer.py`
  - Loads raw historical match results from DuckDB.
  - Calculates team rolling statistics for home/away scoring and conceded goals.
  - Builds these features for both
    - historical training rows, and
    - today’s live prediction rows.
  - Features used by the models:
    - `home_rolling_scored`
    - `home_rolling_conceded`
    - `away_rolling_scored`
    - `away_rolling_conceded`
    - `combined_rolling_scoring_power`
    - `combined_rolling_defensive_leakage`
    - `combined_btts_trend`

### Modeling
- `models/train.py`
  - Training pipeline for three classifiers:
    - Over 2.5 goals (`models/over25_model.joblib`)
    - Both Teams To Score (`models/btts_model.joblib`)
    - 3-way match outcome (`models/outcome_model.joblib`)
  - Reads engineered features from `features/engineer.generate_feature_pipeline()`.
  - Trains `RandomForestClassifier` models with balanced class weights.

- `models/predict.py`
  - Loads the saved model artifacts.
  - Generates live features for today’s fixtures.
  - Produces a prediction DataFrame containing:
    - `over_2_5_probability`
    - `btts_probability`
    - `prob_home_win`
    - `prob_draw`
    - `prob_away_win`
  - Merges match metadata such as kickoff time and odds from DuckDB.

### Scripts and utilities
- `scripts/backtest.py`
  - Simple historical analytics on finished matches in DuckDB.
  - Calculates actual over-2.5 frequency for past games.

- `scripts/eval_model.py`
  - Diagnostic evaluation script using `data/matches` and model predictions.
  - Computes accuracy, Brier score, precision, and recall for the loaded model.

- `scripts/inspect_fixtures.py`
  - Helps inspect fixture files under `data/fixtures`.
  - Prints sample rows, columns, and competitions.

- `scripts/run_fast_train.py`
  - Convenience wrapper intended to call a fast training routine.
  - Current repo code may require small wiring fixes before this wrapper works cleanly.

- `scripts/run_local_prediction.py`
  - Convenience wrapper intended for local prediction workflows.
  - The current version expects helper functions in `models.predict` that may not yet be defined.

## Data and integration flow

1. `data/collector.py` pulls live schedule and odds into `duckdb`.
2. `features/engineer.py` computes team and match-level features from historical results.
3. `models/train.py` trains three model artifacts and saves them to `models/`.
4. `models/predict.py` loads those artifacts and scores today’s fixture rows.
5. `app.py` renders the Streamlit dashboard using the scored output.

This means your prediction stack currently integrates:
- API-Football v3 for scheduled fixtures,
- The Odds API v4 for market pricing,
- DuckDB for lightweight analytical storage,
- scikit-learn for machine learning,
- Streamlit for live delivery.

## Setup and run locally

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Initialize the DuckDB schema:

```powershell
python data/collector.py --build-db
```

4. Fetch today’s fixtures and odds:

```powershell
python data/collector.py --fetch-today
```

5. Train the models:

```powershell
python models/train.py
```

6. Run the Streamlit app:

```powershell
streamlit run app.py
```

7. Open the browser at `http://localhost:8501`.

## Important paths and files

- `config.py` — dataset and artifact path configuration.
- `data/matches.duckdb` — main DuckDB file used by feature engineering and predictions.
- `models/over25_model.joblib` — Over 2.5 goals model.
- `models/btts_model.joblib` — BTTS model.
- `models/outcome_model.joblib` — 3-way outcome model.

## How to use the Streamlit app

The app uses `models.predict.score_todays_fixtures()` to:
- load all three saved models,
- create live prediction rows from today’s data,
- compute probabilities,
- merge in match time and betting odds,
- display a sortable, exportable table.

### Required data shape

Fixtures should use consistent team naming between today’s feed and the historical DuckDB records. If names do not match, predictions may not align correctly.

## Notes on current repo consistency

- The core prediction flow is implemented via `app.py`, `models/predict.py`, and `features/engineer.py`.
- Some script wrappers in `scripts/` refer to helper functions or training entrypoints that may require repository alignment.
- If a utility fails, use the main modules directly:
  - `python data/collector.py --build-db`
  - `python data/collector.py --fetch-today`
  - `python models/train.py`
  - `streamlit run app.py`

## Troubleshooting

- `app.py` returns no data:
  - Confirm `models/*.joblib` exists.
  - Confirm `data/matches.duckdb` exists and contains `historical_matches`.

- API keys:
  - `API_FOOTBALL_KEY` for fixtures.
  - `THE_ODDS_API_KEY` for odds.

- Model artifact handling:
  - If you choose not to commit large `.joblib` files, store them externally or use a download fallback in the prediction code.

- Data consistency:
  - Team names must match between live fixture input and archived historical records.

## Recommended next improvements

- Add a `models.predict.load_model()` / `predict_for_date()` wrapper so `scripts/run_local_prediction.py` works consistently.
- Add a GitHub Actions workflow to build the DB, train models, and optionally publish artifacts.
- Add a `scripts/retrain.sh` or `Makefile` for reproducible local automation.
- Add a small notebook or script to validate fixture name normalization.

## License

This repository contains predictive analytics code for football match markets. Evaluate with domain expertise and do not treat outputs as guaranteed betting advice.

