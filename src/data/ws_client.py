"""Optional WebSocket client for Polymarket Market Channel (real-time orderbook)."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Awaitable

import websockets
from websockets.asyncio.client import ClientConnection

from .history_store import HistoryStore

logger = logging.getLogger(__name__)

WSS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


async def run_market_ws(
    asset_ids: list[str],
    history_store: HistoryStore,
    *,
    on_error: Callable[[Exception], Awaitable[None]] | None = None,
) -> None:
    """
    Connect to Polymarket Market Channel, subscribe to asset_ids, and push
    book/best_bid_ask updates into history_store. Runs until connection closes.
    """
    if not asset_ids:
        return
    payload = {"assets_ids": asset_ids, "type": "market"}  # Polymarket expects assets_ids
    try:
        async with websockets.connect(WSS_URL) as ws:
            await ws.send(json.dumps(payload))
            while True:
                raw = await ws.recv()
                if raw == "PONG":
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event_type = msg.get("event_type")
                if event_type == "book":
                    _handle_book(msg, history_store)
                elif event_type == "best_bid_ask":
                    _handle_best_bid_ask(msg, history_store)
                elif event_type == "price_change":
                    for pc in msg.get("price_changes", []):
                        _handle_price_change(pc, msg.get("timestamp"), history_store)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("WSS market channel error: %s", e)
        if on_error:
            await on_error(e)


def _handle_book(msg: dict, store: HistoryStore) -> None:
    asset_id = msg.get("asset_id")
    if not asset_id:
        return
    bids = msg.get("bids") or msg.get("buys") or []
    asks = msg.get("asks") or msg.get("sells") or []
    t_ms = msg.get("timestamp") or "0"
    t = int(t_ms) / 1000.0 if len(t_ms) > 3 else float(t_ms)
    best_bid = float(bids[0]["price"]) if bids else 0.0
    best_ask = float(asks[0]["price"]) if asks else 1.0
    mid = (best_bid + best_ask) / 2 if (bids and asks) else (best_bid or best_ask)
    store.append(asset_id, t, mid, best_bid, best_ask, 0.0)


def _handle_best_bid_ask(msg: dict, store: HistoryStore) -> None:
    asset_id = msg.get("asset_id")
    if not asset_id:
        return
    best_bid = float(msg.get("best_bid", 0) or 0)
    best_ask = float(msg.get("best_ask", 1) or 1)
    t_ms = msg.get("timestamp") or "0"
    t = int(t_ms) / 1000.0 if len(t_ms) > 3 else float(t_ms)
    mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else (best_bid or best_ask)
    store.append(asset_id, t, mid, best_bid, best_ask, 0.0)


def _handle_price_change(pc: dict, timestamp: str | None, store: HistoryStore) -> None:
    asset_id = pc.get("asset_id")
    if not asset_id:
        return
    best_bid = float(pc.get("best_bid", 0) or 0)
    best_ask = float(pc.get("best_ask", 1) or 1)
    t_ms = timestamp or "0"
    t = int(t_ms) / 1000.0 if t_ms and len(t_ms) > 3 else 0.0
    mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else (best_bid or best_ask)
    store.append(asset_id, t, mid, best_bid, best_ask, 0.0)
