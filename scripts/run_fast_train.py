"""scripts/run_fast_train.py — convenience wrapper to retrain all models"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.train import run_training_pipeline

if __name__ == "__main__":
    run_training_pipeline(verbose=True)
