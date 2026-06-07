# Football Over-2.5 Goals Predictor

Predicts the probability that a football match will finish with over 2.5 total goals. The project trains a time-aware model on historical fixtures and exposes a Streamlit web UI to score future fixtures.

## Quick summary

- Language: Python 3.9+ (tested in a venv)
- Main UI: `app.py` (Streamlit)
- Training: `models/train.py` → saves `models/over25_model.joblib`
- Prediction API: `models/predict.py` (CLI) and `models/predict` functions used by `app.py`

## Repository layout

- `app.py` — Streamlit web interface (uploads fixtures, selects date, shows predictions)
- `config.py` — central paths and constants (`MODEL_PATH`, `DB_PATH`, `MODEL_DIR`)
- `data/` — data ingestion and fixtures
	- `collector.py` — build the `matches.duckdb` DB from CSV sources
- `features/engineer.py` — feature engineering functions (form, H2H, rolling stats)
- `models/`
	- `train.py` — training entrypoint (fast/full modes)
	- `predict.py` — loading model + prediction helpers used by both CLI and Streamlit
	- `over25_model.joblib` — trained model artifact (may be generated locally)
- `scripts/` — utilities: backtesting, evaluation, deployment helpers
- Other: `requirements.txt`, `README.md`, small tmp scripts for diagnostics

## Quickstart (local)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1    # PowerShell
```

2. Install requirements:

```bash
python -m pip install -r requirements.txt
```

3. Build the match database (this expects the CSV files in `data/` or reachable by the collector):

```bash
python data/collector.py --build-db
```

4. Train a model (fast for quick iteration, full for final model):

```bash
# Fast (shorter training)
python -m models.train --train --fast

# Full training
python -m models.train --train
```

After training the pipeline saves `models/over25_model.joblib` (and optionally a scaler) at the path defined in `config.py`.

5. Run the Streamlit UI locally:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser and upload a fixtures CSV (columns: `date`, `competition`, `home_team`, `away_team`) to view predictions.

### Fixtures folder

You can keep multiple fixture CSVs in a single folder for convenience. Create `data/fixtures/` and paste all your fixtures CSV files there. The CLI and utilities accept a directory path and will concatenate all `*.csv` files in that folder when producing predictions.

Example:

```powershell
mkdir data\fixtures
# copy or move your CSV files into data\fixtures\
```

Then run the CLI using the folder as the fixtures argument:

```bash
python -m models.predict --date 2025-05-01 --fixtures data/fixtures
```

## Model artifacts and Git

- Trained models are stored under `models/` and are referenced by `config.MODEL_PATH`.
- By default the repository may ignore `*.joblib`. If you want to commit a small model artifact to the Git repo, add an allow rule in `.gitignore` or use Git LFS for large artifacts.

Example: enable Git LFS for joblib files (recommended if artifact >100MB):

```bash
git lfs install
git lfs track "models/*.joblib"
git add .gitattributes
git add models/over25_model.joblib
git commit -m "Add model via LFS"
git push origin <branch>
```

If you prefer not to commit trained models, host them externally (S3, GitHub Releases, Hugging Face) and add a download fallback in `models/predict.py` (see Troubleshooting below).

## Deployment to Streamlit Cloud (share.streamlit.io)

- Streamlit apps running on Streamlit Cloud pull from your GitHub repository. If the app requires the model artifact to be present in the repo, either:
	- Commit the artifact (use Git LFS for large files), or
	- Add code to download the model at runtime from a stable URL, or
	- Use a CI workflow to build the model and attach it as a release or artifact the app can fetch.

- Note: Streamlit Cloud may redirect to an auth page when an app requires owner-only access or when the app is private. Public apps should be reachable without login.

## Predicting from the CLI

Example CLI usage:

```bash
python -m models.predict --date 2025-05-01 --fixtures path/to/fixtures.csv --output predictions.csv
```

`models.predict` will:
- Load the trained pipeline from `config.MODEL_PATH` (joblib)
- Load the `matches.duckdb` DB from `config.DB_PATH` for historical features
- Build fixture-level features and score each match

The output CSV contains `home_team`, `away_team`, `over_2_5_probability`, and `prediction` (0/1) among other columns.

## Backtesting / Evaluation

- Use `scripts/backtest.py` to simulate historical predictions and compute performance metrics over time. The backtest script uses the same feature engineering pipeline to ensure reproducibility.

## Troubleshooting

- "Model not found / app asks to run train.py": Ensure `models/over25_model.joblib` exists at `config.MODEL_PATH` and is readable by the runtime. Locally, train then commit or copy the file. On Streamlit Cloud, either commit the model (LFS if large) or implement a download fallback.

- `.gitignore` blocks joblib: If you see `*.joblib` in `.gitignore`, add an exception for `models/`:

```text
*.joblib
!models/*.joblib
```

- File too large for GitHub: If the artifact is >100MB, GitHub will reject the push. Use Git LFS or host the file externally.

- Streamlit redirecting to auth: Streamlit Cloud will redirect to an auth page for private apps or if you are not signed in. Make the app public or ensure proper share settings.

- Team names mismatch causing prediction errors: Uploaded fixtures must use identical naming to the historical database (exact string matches). Use the `tmp_feature_diag.py` helpers to inspect feature mapping and team normalization.

## Development notes

- Feature engineering is in `features/engineer.py`. Changes here must be coordinated with training and backtesting.
- The training pipeline uses an XGBoost classifier inside a `sklearn.pipeline.Pipeline` with `StandardScaler`.
- For fast iteration use `--fast` with `models.train` to reduce `n_estimators` and increase learning rate.

## CI / Automation suggestions

- Add a GitHub Actions workflow that:
	1. Builds the DB and trains the model on push to a trusted branch or on a schedule.
	2. Uploads the model as a release asset or commits it to a model-artifacts branch (use LFS).
	3. Optionally triggers a redeploy of the Streamlit app or updates a storage URL that the app can download from.

## Contributing & contact

Please open issues or PRs. If you want to share improvements to features, model architecture, or deploy automation, submit a PR and include tests or a short reproducible example.

## License

This repository is provided under an open-source-friendly license (check the LICENSE file if present). Use at your own risk; evaluate predictions before using for real betting or financial decisions.

