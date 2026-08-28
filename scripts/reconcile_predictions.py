"""scripts/reconcile_predictions.py — compares every saved prediction
against its real outcome, once the match has finished. Foundation for the
track-record feature.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import reconcile_predictions

if __name__ == "__main__":
    reconcile_predictions()
