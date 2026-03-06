"""
Train order-flow direction classifier from historical features.
Usage: from project root, PYTHONPATH=. python scripts/train_orderflow.py [--data path] [--out model.joblib]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Project root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from src.strategies.orderflow_ml import ML_FEATURE_KEYS


def load_or_generate_data(data_path: str | None) -> tuple[np.ndarray, np.ndarray]:
    """
    Load feature matrix X and labels y from file, or generate synthetic for demo.
    File format: CSV with columns = ML_FEATURE_KEYS + ['label'] (0=down, 1=up).
    """
    if data_path and Path(data_path).exists():
        import pandas as pd
        df = pd.read_csv(data_path)
        if "label" not in df.columns:
            df["label"] = (df["mid_price"].shift(-1) > df["mid_price"]).astype(int)
        X = df[[c for c in ML_FEATURE_KEYS if c in df.columns]].fillna(0).values
        y = df["label"].values[: len(X)]
        return X, y
    # Synthetic demo data
    np.random.seed(42)
    n = 500
    X = np.random.randn(n, len(ML_FEATURE_KEYS)).astype(np.float32) * 0.1 + 0.5
    y = (np.random.rand(n) > 0.5).astype(int)
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser(description="Train order-flow classifier")
    parser.add_argument("--data", type=str, default=None, help="CSV with features + label")
    parser.add_argument("--out", type=str, default="models/orderflow_model.joblib", help="Output model path")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    X, y = load_or_generate_data(args.data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=42)

    model = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_split=50, random_state=42)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"Test accuracy: {score:.4f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(f"Model saved to {out_path}")


if __name__ == "__main__":
    main()
