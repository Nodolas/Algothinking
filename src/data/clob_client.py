"""Async wrapper around py-clob-client for read-only CLOB data."""
from __future__ import annotations

import asyncio
from typing import Any

try:
    from py_clob_client.client import ClobClient
except ImportError:
    ClobClient = None  # type: ignore[misc, assignment]

import aiohttp


class ClobDataClient:
    """Async data client: wraps sync CLOB client in thread pool and adds price history via REST."""

    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137) -> None:
        if ClobClient is None:
            raise ImportError("Install py-clob-client: pip install py-clob-client")
        self._host = host.rstrip("/")
        self._chain_id = chain_id
        self._client = ClobClient(host=host, chain_id=chain_id)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _sync_get_order_book(self, token_id: str) -> Any:
        return self._client.get_order_book(token_id)

    def _sync_get_market(self, condition_id: str) -> Any:
        return self._client.get_market(condition_id)

    def _sync_get_market_trades_events(self, condition_id: str) -> Any:
        return self._client.get_market_trades_events(condition_id)

    async def get_order_book(self, token_id: str) -> Any:
        return await asyncio.to_thread(self._sync_get_order_book, token_id)

    async def get_order_book_normalized(self, token_id: str) -> dict | None:
        """Return orderbook as dict with bids, asks (list of {price, size}), mid, best_bid, best_ask."""
        ob = await self.get_order_book(token_id)
        if ob is None:
            return None
        bids = getattr(ob, "bids", None) or getattr(ob, "buys", None) or []
        asks = getattr(ob, "asks", None) or getattr(ob, "sells", None) or []
        def level(l: Any) -> dict:
            if hasattr(l, "price") and hasattr(l, "size"):
                return {"price": float(l.price), "size": float(l.size)}
            if isinstance(l, (list, tuple)) and len(l) >= 2:
                return {"price": float(l[0]), "size": float(l[1])}
            return {"price": float(l.get("price", 0)), "size": float(l.get("size", 0))}
        bids = [level(b) for b in (bids or [])[:10]]
        asks = [level(a) for a in (asks or [])[:10]]
        best_bid = bids[0]["price"] if bids else 0.0
        best_ask = asks[0]["price"] if asks else 1.0
        mid = (best_bid + best_ask) / 2 if (bids and asks) else (best_bid or best_ask)
        return {
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "asset_id": token_id,
        }

    async def get_market(self, condition_id: str) -> Any:
        return await asyncio.to_thread(self._sync_get_market, condition_id)

    async def get_market_trades_events(self, condition_id: str) -> Any:
        return await asyncio.to_thread(self._sync_get_market_trades_events, condition_id)

    async def get_prices_history(
        self,
        token_id: str,
        *,
        interval: str = "1h",
        start_ts: int | None = None,
        end_ts: int | None = None,
        fidelity: int | None = None,
    ) -> list[dict[str, float]]:
        """Fetch price history for a token. Returns list of {t: timestamp, p: price}."""
        params: dict[str, str | int] = {"market": token_id, "interval": interval}
        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts
        if fidelity is not None:
            params["fidelity"] = fidelity
        session = await self._get_session()
        url = f"{self._host}/prices-history"
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data.get("history", [])
