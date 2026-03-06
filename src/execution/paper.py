"""Paper executor: virtual balance and positions, no CLOB calls."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import time

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    token_id: str
    side: str  # BUY -> long
    size: float
    entry_price: float
    entry_time: float = field(default_factory=time)


class PaperExecutor:
    """Maintain virtual balance and positions; execute orders in-memory."""

    def __init__(self, initial_balance: float = 10000.0) -> None:
        self._balance = initial_balance
        self._positions: list[PaperPosition] = []
        self._trades: list[dict] = []

    @property
    def balance(self) -> float:
        return self._balance

    def get_positions(self) -> list[dict]:
        return [
            {
                "token_id": p.token_id,
                "side": p.side,
                "size": p.size,
                "entry_price": p.entry_price,
                "entry_time": p.entry_time,
            }
            for p in self._positions
        ]

    def get_position_pct(self, token_id: str) -> float:
        """Current exposure to this token as fraction of initial balance (simplified)."""
        total = 0.0
        for p in self._positions:
            if p.token_id == token_id:
                total += p.size * p.entry_price
        return total / self._balance if self._balance else 0.0

    def execute(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict | None:
        """
        Execute a paper order. Deducts cost from balance (BUY) or adds proceeds (SELL).
        Returns trade record or None if insufficient balance for BUY.
        """
        cost = size * price
        if side.upper() == "BUY":
            if cost > self._balance:
                logger.warning("Paper BUY skipped: cost %.2f > balance %.2f", cost, self._balance)
                return None
            self._balance -= cost
            self._positions.append(
                PaperPosition(token_id=token_id, side="BUY", size=size, entry_price=price)
            )
            trade = {
                "token_id": token_id,
                "side": "BUY",
                "size": size,
                "price": price,
                "time": time(),
                "balance_after": self._balance,
            }
        else:
            self._balance += cost
            # Close or reduce matching position if any
            remaining = size
            for p in list(self._positions):
                if p.token_id == token_id and p.side == "BUY" and remaining > 0:
                    close_size = min(p.size, remaining)
                    pnl = close_size * (price - p.entry_price)
                    remaining -= close_size
                    if close_size >= p.size:
                        self._positions.remove(p)
                    else:
                        p.size -= close_size
                    break
            trade = {
                "token_id": token_id,
                "side": "SELL",
                "size": size,
                "price": price,
                "time": time(),
                "balance_after": self._balance,
            }
        self._trades.append(trade)
        logger.info("Paper %s %s %.4f @ %.4f | balance %.2f", side, token_id, size, price, self._balance)
        return trade

    def pnl(self, initial_balance: float | None = None) -> float:
        """Realized + unrealized PnL vs initial balance."""
        init = initial_balance or (self._balance + sum(p.size * p.entry_price for p in self._positions))
        return self._balance + sum(p.size * p.entry_price for p in self._positions) - init
