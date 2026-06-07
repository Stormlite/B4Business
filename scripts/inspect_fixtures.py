import sys
from pathlib import Path

# Ensure project root on sys.path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from models.predict import load_fixtures

p = Path('data/fixtures')
df = load_fixtures(p)
print('Columns:', df.columns.tolist())
print('\nSample rows:\n', df.head().to_string(index=False))
print('\nUnique competitions:', df['competition'].unique()[:20])
