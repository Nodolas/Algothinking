"""Risk manager: Kelly position sizing, max position, daily loss limit, stop-loss."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class RiskParams:
    kelly_fraction: float = 0.25
    max_position_pct: float = 0.10
    max_daily_loss_pct: float = 0.20
    stop_loss_pct: float | None = 0.05
    initial_bankroll: float = 10000.0


def kelly_position_size(
    win_prob: float,
    win_loss_ratio: float,
    bankroll: float,
    *,
    kelly_fraction: float = 0.25,
    max_pct: float = 0.10,
) -> float:
    """
    Optimal position size using fractional Kelly. Capped at max_pct of bankroll.
    """
    if win_loss_ratio <= 0:
        return 0.0
    kelly = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
    safe = max(0.0, min(kelly * kelly_fraction, max_pct))
    return bankroll * safe


class RiskManager:
    """Apply position and daily limits; compute allowed size from confidence."""

    def __init__(self, params: RiskParams | None = None) -> None:
        self.params = params or RiskParams()
        self._daily_pnl: float = 0.0
        self._get_bankroll: Callable[[], float] = lambda: self.params.initial_bankroll

    def set_bankroll_getter(self, getter: Callable[[], float]) -> None:
        self._get_bankroll = getter

    def record_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl

    def reset_daily_pnl(self) -> None:
        self._daily_pnl = 0.0

    def daily_loss_limit_breach(self) -> bool:
        bankroll = self._get_bankroll()
        if bankroll <= 0:
            return True
        return (self._daily_pnl / bankroll) <= -self.params.max_daily_loss_pct

    def allowed_position_size(
        self,
        token_id: str,
        signal_confidence: float,
        current_position_pct: float = 0.0,
        *,
        win_prob_estimate: float = 0.55,
        win_loss_ratio: float = 1.0,
    ) -> float:
        """
        Return max allowed notional to add for this market (in bankroll units).
        Returns 0 if daily loss limit breached or already at max position.
        """
        if self.daily_loss_limit_breach():
            return 0.0
        bankroll = self._get_bankroll()
        if bankroll <= 0:
            return 0.0
        if current_position_pct >= self.params.max_position_pct:
            return 0.0
        # Use signal confidence as proxy for win prob
        p = max(0.5, min(win_prob_estimate, 0.95))
        size = kelly_position_size(
            p, win_loss_ratio, bankroll,
            kelly_fraction=self.params.kelly_fraction,
            max_pct=self.params.max_position_pct - current_position_pct,
        )
        return size * signal_confidence
