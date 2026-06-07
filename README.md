# Football Over-2.5 Goals Predictor

A free, open-source Python project for predicting football matches with a final score above 2.5 goals using historical data from 2022 onward.

## What this project includes

- `data/collector.py` — download and assemble historical match data from Football-Data.co.uk
- `features/engineer.py` — create rolling team features, form, H2H, rest days, and match context
- `models/train.py` — train a time-aware classifier and save model assets
- `models/predict.py` — predict over 2.5 goals for a given fixtures file and date
- `scripts/backtest.py` — simulate historical daily predictions and evaluate model performance

## Setup

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Download historical data and build the match database:

```bash
python data/collector.py --build-db
```

3. Train the model:

```bash
python models/train.py
```

4. Predict matches for a future date:

```bash
python models/predict.py --date 2025-05-01 --fixtures data/fixtures.csv
```

5. Run the Streamlit web interface:

```bash
streamlit run app.py
```

6. Backtest against historical match dates:

```bash
python scripts/backtest.py
```

## Notes

- The pipeline uses only free data sources and open-source tools.
- Accuracy will depend on data quality, feature engineering, and the leagues selected.
- Reaching 80% overall accuracy is ambitious with free data alone; this project is designed for strong baseline performance and an extensible architecture.
