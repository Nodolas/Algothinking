"""Arbitrage strategy stub: cross-market price comparison; pluggable later."""
from __future__ import annotations


def arbitrage_signal(
    polymarket_yes_price: float,
    external_yes_price: float | None = None,
    *,
    threshold: float = 0.03,
) -> tuple[str, float]:
    """
    If external_yes_price is None, returns HOLD, 0 (no second source).
    Otherwise detects spread between Polymarket and external; returns BUY/SELL/HOLD and confidence.
    """
    if external_yes_price is None:
        return "HOLD", 0.0
    spread = abs(polymarket_yes_price - external_yes_price)
    if spread <= threshold:
        return "HOLD", 0.0
    # Prefer buying the cheaper side; we trade on Polymarket so signal is BUY if poly is cheap
    if polymarket_yes_price < external_yes_price:
        return "BUY", min((spread - threshold) / 0.05, 1.0)
    return "SELL", min((spread - threshold) / 0.05, 1.0)
