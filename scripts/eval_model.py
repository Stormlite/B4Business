import joblib
from config import MODEL_PATH, DB_PATH
from features.engineer import build_features, select_feature_matrix
import duckdb

model = joblib.load(MODEL_PATH)
con = duckdb.connect(DB_PATH)
df = con.execute("SELECT * FROM matches ORDER BY date").df()
con.close()
features = build_features(df)
X, y = select_feature_matrix(features)

try:
    probs = model.predict_proba(X)[:, 1]
except Exception:
    probs = model.predict(X)

preds = (probs >= 0.5).astype(int)

from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score

print('Full-dataset evaluation:')
print('Matches', len(y))
print('Accuracy', accuracy_score(y, preds))
print('Brier', brier_score_loss(y, probs))
print('Precision', precision_score(y, preds, zero_division=0))
print('Recall', recall_score(y, preds, zero_division=0))
