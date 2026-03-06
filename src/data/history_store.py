"""In-memory price/history store per token, updated from REST (and optionally WSS)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import time


@dataclass
class PricePoint:
    """Single point: timestamp, mid, bid, ask, optional volume."""
    t: float
    mid: float
    bid: float
    ask: float
    volume: float = 0.0


class HistoryStore:
    """Per-token_id deque of PricePoints with max length. Thread-safe."""

    def __init__(self, max_points_per_token: int = 500) -> None:
        self._max_points = max_points_per_token
        self._data: dict[str, deque[PricePoint]] = {}
        self._lock = Lock()

    def append(
        self,
        token_id: str,
        t: float,
        mid: float,
        bid: float,
        ask: float,
        volume: float = 0.0,
    ) -> None:
        with self._lock:
            if token_id not in self._data:
                self._data[token_id] = deque(maxlen=self._max_points)
            self._data[token_id].append(
                PricePoint(t=t, mid=mid, bid=bid, ask=ask, volume=volume)
            )

    def get_prices(self, token_id: str, window: int | None = None) -> list[float]:
        """Return list of mid prices, most recent last. If window set, last N points."""
        with self._lock:
            points = self._data.get(token_id)
            if not points:
                return []
            mids = [p.mid for p in points]
            if window is not None and len(mids) > window:
                return mids[-window:]
            return list(mids)

    def get_points(self, token_id: str, window: int | None = None) -> list[PricePoint]:
        """Return list of PricePoints, most recent last."""
        with self._lock:
            points = self._data.get(token_id)
            if not points:
                return []
            out = list(points)
            if window is not None and len(out) > window:
                out = out[-window:]
            return out

    def get_last_mid(self, token_id: str) -> float | None:
        with self._lock:
            points = self._data.get(token_id)
            if not points:
                return None
            return points[-1].mid

    def token_ids(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())
