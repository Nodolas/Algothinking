"""Order-flow ML strategy: classifier for direction prediction; optional at runtime."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Feature names used for training and inference (must match features.py keys)
ML_FEATURE_KEYS = [
    "bid_ask_spread",
    "spread_pct",
    "orderbook_imbalance",
    "bid_depth_3",
    "ask_depth_3",
    "price_change_1m",
    "price_change_5m",
    "volatility_10m",
    "rolling_mean",
    "rolling_std",
]


def load_ml_model(path: str | Path | None):
    """Load persisted model (joblib). Returns None if path missing or invalid."""
    if not path:
        return None
    try:
        import joblib
        return joblib.load(Path(path))
    except Exception as e:
        logger.warning("Could not load ML model from %s: %s", path, e)
        return None


def ml_predict(
    model: Any,
    features: dict[str, float],
    *,
    feature_keys: list[str] | None = None,
) -> tuple[str, float]:
    """
    Run classifier on feature dict. Returns (direction, confidence): BUY/SELL/HOLD and prob.
    model must have .predict() and optionally .predict_proba().
    """
    if model is None:
        return "HOLD", 0.0
    keys = feature_keys or ML_FEATURE_KEYS
    X = [features.get(k, 0.0) for k in keys]
    try:
        pred = model.predict([X])[0]
        proba = getattr(model, "predict_proba", None)
        if proba is not None:
            probs = proba([X])[0]
            conf = float(max(probs)) if len(probs) else 0.0
        else:
            conf = 0.7
        # pred is often 0/1 or -1/1 or "up"/"down"; map to BUY/SELL/HOLD
        if hasattr(pred, "upper"):
            s = str(pred).upper()
            if "BUY" in s or "UP" in s or s == "1":
                return "BUY", conf
            if "SELL" in s or "DOWN" in s or s == "-1":
                return "SELL", conf
            return "HOLD", 0.0
        if pred == 1 or pred == 1.0:
            return "BUY", conf
        if pred == -1 or pred == 0:
            return "SELL", conf
        return "HOLD", 0.0
    except Exception as e:
        logger.debug("ML predict failed: %s", e)
        return "HOLD", 0.0
