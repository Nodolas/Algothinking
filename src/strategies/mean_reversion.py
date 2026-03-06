"""Mean reversion strategy: Bollinger-style bands, BUY/SELL/HOLD."""
from __future__ import annotations


def mean_reversion_signal(
    prices: list[float],
    current_price: float,
    *,
    lookback: int = 100,
    entry_threshold: float = 1.5,
) -> tuple[str, float]:
    """
    Returns (signal, confidence): BUY when below lower band, SELL when above upper band, else HOLD.
    """
    if not prices or lookback <= 0:
        return "HOLD", 0.0
    window = prices[-lookback:] if len(prices) >= lookback else prices
    sma = sum(window) / len(window)
    variance = sum((x - sma) ** 2 for x in window) / len(window)
    std = variance ** 0.5 if variance else 0.01
    upper = sma + entry_threshold * std
    lower = sma - entry_threshold * std
    if current_price > upper:
        strength = (current_price - upper) / std if std else 0
        return "SELL", min(strength / 2.0, 1.0)
    if current_price < lower:
        strength = (lower - current_price) / std if std else 0
        return "BUY", min(strength / 2.0, 1.0)
    return "HOLD", 0.0
