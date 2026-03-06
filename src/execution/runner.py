"""Bot runner: asyncio loop that fetches data, runs strategies, and executes (paper or live)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from time import time

from ..data.clob_client import ClobDataClient
from ..data.history_store import HistoryStore
from ..strategies.aggregator import aggregate_signals
from .risk import RiskManager, RiskParams
from .paper import PaperExecutor
from .live import LiveExecutor

logger = logging.getLogger(__name__)


@dataclass
class SignalRecord:
    timestamp: float
    token_id: str
    signal: str
    confidence: float
    strategy_signals: dict
    executed: bool = False


class BotRunner:
    """Main bot loop: poll markets, compute signals, execute via paper or live."""

    def __init__(
        self,
        clob: ClobDataClient,
        history_store: HistoryStore,
        market_ids: list[str],
        *,
        interval_seconds: int = 60,
        execution_mode: str = "paper",
        confidence_threshold: float = 0.65,
        risk_params: RiskParams | None = None,
        strategy_weights: dict | None = None,
        ml_model_path: str | None = None,
        initial_bankroll: float = 10000.0,
        live_executor: LiveExecutor | None = None,
        use_websocket: bool = False,
    ) -> None:
        self.clob = clob
        self.history_store = history_store
        self.market_ids = market_ids
        self.interval_seconds = interval_seconds
        self.execution_mode = execution_mode
        self.confidence_threshold = confidence_threshold
        self.risk_params = risk_params or RiskParams(initial_bankroll=initial_bankroll)
        self.strategy_weights = strategy_weights or {}
        self.ml_model_path = ml_model_path
        self._risk = RiskManager(self.risk_params)
        self._paper = PaperExecutor(initial_balance=initial_bankroll)
        self._live = live_executor
        self._use_websocket = use_websocket
        self._risk.set_bankroll_getter(lambda: self._paper.balance)
        self._last_signals: list[SignalRecord] = []
        self._max_signals = 100
        self._running = False
        self._task: asyncio.Task | None = None
        self._ws_task: asyncio.Task | None = None
        self._start_time: float | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time() - self._start_time

    def get_last_signals(self, limit: int = 20) -> list[dict]:
        out = []
        for s in self._last_signals[-limit:]:
            out.append({
                "timestamp": s.timestamp,
                "token_id": s.token_id,
                "signal": s.signal,
                "confidence": s.confidence,
                "strategy_signals": s.strategy_signals,
                "executed": s.executed,
            })
        return list(reversed(out))

    def get_positions(self) -> list[dict]:
        return self._paper.get_positions()

    def get_balance(self) -> float:
        return self._paper.balance

    async def _tick(self) -> None:
        for token_id in self.market_ids:
            try:
                ob = await self.clob.get_order_book_normalized(token_id)
                if ob is None:
                    continue
                t = time()
                mid = ob.get("mid") or 0.5
                best_bid = ob.get("best_bid") or 0.0
                best_ask = ob.get("best_ask") or 1.0
                self.history_store.append(token_id, t, mid, best_bid, best_ask, 0.0)

                signal, confidence, strategy_signals = aggregate_signals(
                    token_id,
                    ob,
                    self.history_store,
                    weights=self.strategy_weights,
                    ml_model_path=self.ml_model_path,
                    price_window=50,
                    mean_reversion_lookback=100,
                )

                record = SignalRecord(
                    timestamp=t,
                    token_id=token_id,
                    signal=signal,
                    confidence=confidence,
                    strategy_signals=strategy_signals,
                )
                self._last_signals.append(record)
                if len(self._last_signals) > self._max_signals:
                    self._last_signals.pop(0)

                if signal == "HOLD" or confidence < self.confidence_threshold:
                    continue
                if self._risk.daily_loss_limit_breach():
                    logger.warning("Daily loss limit breached; skipping execution")
                    continue

                pos_pct = self._paper.get_position_pct(token_id)
                size = self._risk.allowed_position_size(
                    token_id, confidence, current_position_pct=pos_pct,
                )
                if size <= 0:
                    continue

                # Simple size: spend up to `size` at mid price
                price = mid
                order_size = size / price if price else 0
                if order_size <= 0:
                    continue

                if self.execution_mode == "paper":
                    trade = self._paper.execute(token_id, signal, order_size, price)
                    if trade:
                        record.executed = True
                        self._risk.record_pnl(0.0)  # Could refine with realized PnL
                elif self.execution_mode == "live" and self._live:
                    result = await self._live.execute(token_id, signal, order_size, price)
                    if result:
                        record.executed = True
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Tick error for %s: %s", token_id, e)

    async def run_loop(self) -> None:
        """Run until cancelled."""
        self._running = True
        self._start_time = time()
        if self._use_websocket and self.market_ids:
            try:
                from ..data.ws_client import run_market_ws
                self._ws_task = asyncio.create_task(
                    run_market_ws(self.market_ids, self.history_store)
                )
            except Exception as e:
                logger.warning("WSS client not started: %s", e)
        logger.info("Bot loop started (mode=%s, interval=%ds)", self.execution_mode, self.interval_seconds)
        try:
            while self._running:
                await self._tick()
                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            if self._ws_task and not self._ws_task.done():
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
            self._running = False
            logger.info("Bot loop stopped")

    def start_background(self) -> None:
        """Start the loop as a background task. Idempotent."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self.run_loop())

    def stop(self) -> None:
        """Signal stop and cancel the task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
