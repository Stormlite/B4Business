from pathlib import Path
import pandas as pd

import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from models.predict import load_model, load_match_history, load_fixtures, predict_for_date


def main():
    print('Loading model...')
    model = load_model()
    print('Loading history...')
    history = load_match_history()
    fixtures_dir = Path('data/fixtures')
    print(f'Loading fixtures from {fixtures_dir}...')
    fixtures = load_fixtures(fixtures_dir)
    fixtures['date'] = pd.to_datetime(fixtures['date'])
    dates = sorted(fixtures['date'].unique())
    if not dates:
        raise SystemExit('No fixture dates found')
    date = dates[0]
    print(f'Running predictions for {date.date()} on {len(fixtures)} fixtures...')
    preds = predict_for_date(model, history, fixtures, date)
    print(preds.head().to_string(index=False))
    out = Path('predictions_sample.csv')
    preds.to_csv(out, index=False)
    print(f'Wrote sample predictions to {out}')


if __name__ == '__main__':
    main()
