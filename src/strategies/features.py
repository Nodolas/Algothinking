"""Feature extraction from orderbook + history for all strategies."""
from __future__ import annotations

import math
from typing import Any

from ..data.history_store import HistoryStore


def extract_features(
    token_id: str,
    orderbook: dict[str, Any] | None,
    history_store: HistoryStore,
    *,
    price_window: int = 50,
    volatility_window: int = 20,
) -> dict[str, float]:
    """
    Build one feature dict per token from current orderbook and stored history.
    Missing values are 0.0 or safe defaults.
    """
    features: dict[str, float] = {
        "bid_ask_spread": 0.0,
        "spread_pct": 0.0,
        "orderbook_imbalance": 0.0,
        "bid_depth_3": 0.0,
        "ask_depth_3": 0.0,
        "mid_price": 0.5,
        "best_bid": 0.0,
        "best_ask": 1.0,
        "price_change_1m": 0.0,
        "price_change_5m": 0.0,
        "volatility_10m": 0.0,
        "rolling_mean": 0.5,
        "rolling_std": 0.01,
        "volume_ratio_5m": 1.0,
    }

    if orderbook:
        best_bid = orderbook.get("best_bid") or 0.0
        best_ask = orderbook.get("best_ask") or 1.0
        mid = orderbook.get("mid") or ((best_bid + best_ask) / 2 if (best_bid or best_ask) else 0.5)
        spread = best_ask - best_bid if (best_bid and best_ask) else 0.0
        features["best_bid"] = best_bid
        features["best_ask"] = best_ask
        features["mid_price"] = mid
        features["bid_ask_spread"] = spread
        features["spread_pct"] = spread / mid if mid else 0.0

        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        bid_vol = sum(float(b.get("size", 0)) for b in bids[:3])
        ask_vol = sum(float(a.get("size", 0)) for a in asks[:3])
        total = bid_vol + ask_vol
        features["orderbook_imbalance"] = (bid_vol - ask_vol) / total if total else 0.0
        features["bid_depth_3"] = bid_vol
        features["ask_depth_3"] = ask_vol

    points = history_store.get_points(token_id, window=price_window)
    prices = [p.mid for p in points]
    if prices:
        n = len(prices)
        features["rolling_mean"] = sum(prices) / n
        features["rolling_std"] = (
            math.sqrt(sum((x - features["rolling_mean"]) ** 2 for x in prices) / n)
            if n > 1 else 0.01
        )
        current = prices[-1]
        if n >= 2:
            # Approximate 1m/5m ago by index (e.g. 1 and 5 steps back if we have 1min data)
            idx_1 = max(0, n - 2)
            idx_5 = max(0, n - min(6, n))
            price_1m = prices[idx_1]
            price_5m = prices[idx_5]
            features["price_change_1m"] = (current - price_1m) / price_1m if price_1m else 0.0
            features["price_change_5m"] = (current - price_5m) / price_5m if price_5m else 0.0
        vol_window = history_store.get_prices(token_id, window=volatility_window)
        if len(vol_window) > 1:
            mean_v = sum(vol_window) / len(vol_window)
            features["volatility_10m"] = math.sqrt(
                sum((x - mean_v) ** 2 for x in vol_window) / (len(vol_window) - 1)
            )

    return features
