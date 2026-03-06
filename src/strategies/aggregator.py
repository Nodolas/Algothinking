"""Aggregate signals from all strategies into one BUY/SELL/HOLD and confidence."""
from __future__ import annotations

from typing import Any

from .mispricing import mispricing_signal
from .mean_reversion import mean_reversion_signal
from .orderflow_ml import load_ml_model, ml_predict, ML_FEATURE_KEYS
from .arbitrage import arbitrage_signal
from .features import extract_features
from ..data.history_store import HistoryStore


def aggregate_signals(
    token_id: str,
    orderbook: dict[str, Any] | None,
    history_store: HistoryStore,
    *,
    weights: dict[str, float] | None = None,
    ml_model_path: str | None = None,
    ml_model: Any = None,
    price_window: int = 50,
    mean_reversion_lookback: int = 100,
    z_threshold: float = 2.0,
    entry_threshold: float = 1.5,
) -> tuple[str, float, dict[str, tuple[str, float]]]:
    """
    Run all strategies and return (final_signal, confidence, strategy_signals).
    final_signal is BUY, SELL, or HOLD. strategy_signals maps strategy name -> (signal, conf).
    """
    w = weights or {
        "mean_reversion": 0.3,
        "mispricing": 0.2,
        "ml": 0.5,
        "arbitrage": 0.0,
    }
    features = extract_features(token_id, orderbook, history_store, price_window=price_window)
    strategy_signals: dict[str, tuple[str, float]] = {}

    # Mispricing: map OVERPRICED->SELL, UNDERPRICED->BUY
    mr_sig, mr_conf = mispricing_signal(
        features["rolling_mean"],
        features["rolling_std"],
        features["mid_price"],
        z_threshold=z_threshold,
    )
    if mr_sig == "OVERPRICED":
        strategy_signals["mispricing"] = ("SELL", mr_conf)
    elif mr_sig == "UNDERPRICED":
        strategy_signals["mispricing"] = ("BUY", mr_conf)
    else:
        strategy_signals["mispricing"] = ("HOLD", 0.0)

    # Mean reversion
    prices = history_store.get_prices(token_id, window=mean_reversion_lookback)
    mrev_sig, mrev_conf = mean_reversion_signal(
        prices, features["mid_price"], lookback=mean_reversion_lookback, entry_threshold=entry_threshold
    )
    strategy_signals["mean_reversion"] = (mrev_sig, mrev_conf)

    # ML
    model = ml_model or (load_ml_model(ml_model_path) if ml_model_path else None)
    ml_sig, ml_conf = ml_predict(model, features, feature_keys=ML_FEATURE_KEYS)
    strategy_signals["ml"] = (ml_sig, ml_conf)

    # Arbitrage (no external source by default)
    arb_sig, arb_conf = arbitrage_signal(features["mid_price"], None, threshold=0.03)
    strategy_signals["arbitrage"] = (arb_sig, arb_conf)

    # Weighted vote: sum(BUY) - sum(SELL) by weighted confidence
    buy_score = 0.0
    sell_score = 0.0
    for name, (sig, conf) in strategy_signals.items():
        weight = w.get(name, 0.0)
        if sig == "BUY":
            buy_score += weight * conf
        elif sig == "SELL":
            sell_score += weight * conf
    total_w = sum(w.get(n, 0) for n in strategy_signals)
    if total_w <= 0:
        return "HOLD", 0.0, strategy_signals
    if buy_score > sell_score:
        confidence = min((buy_score - sell_score) / total_w, 1.0)
        return "BUY", confidence, strategy_signals
    if sell_score > buy_score:
        confidence = min((sell_score - buy_score) / total_w, 1.0)
        return "SELL", confidence, strategy_signals
    return "HOLD", 0.0, strategy_signals
