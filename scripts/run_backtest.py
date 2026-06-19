"""scripts/run_backtest.py — run the historical backtest report"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.backtest import evaluate_historical_accuracy

if __name__ == "__main__":
    evaluate_historical_accuracy()
