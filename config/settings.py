"""Configuration via environment and .env. No secrets in defaults."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CLOB
    clob_host: str = Field(default="https://clob.polymarket.com", description="CLOB API host")
    chain_id: int = Field(default=137, description="Polygon chain ID")

    # Auth (for live trading only)
    api_key: str | None = Field(default=None, description="Polymarket API key")
    api_secret: str | None = Field(default=None, description="Polymarket API secret")
    api_passphrase: str | None = Field(default=None, description="Polymarket API passphrase")
    private_key: str | None = Field(default=None, description="Wallet private key (optional, for L1)")

    # Markets: comma-separated condition_ids or token_ids
    market_ids: str = Field(default="", description="Comma-separated market condition_ids or token_ids")

    # Polling
    polling_interval_seconds: int = Field(default=60, ge=10, le=3600)
    use_websocket: bool = Field(default=False, description="Use WSS for real-time orderbook")

    # Execution
    execution_mode: Literal["paper", "live"] = Field(default="paper")

    # Risk
    kelly_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    max_position_pct: float = Field(default=0.10, ge=0.01, le=1.0)
    max_daily_loss_pct: float = Field(default=0.20, ge=0.0, le=1.0)
    stop_loss_pct: float | None = Field(default=0.05, ge=0.0, le=1.0)
    initial_bankroll: float = Field(default=10000.0, gt=0)

    # Strategy
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    weight_mean_reversion: float = Field(default=0.3, ge=0.0, le=1.0)
    weight_mispricing: float = Field(default=0.2, ge=0.0, le=1.0)
    weight_ml: float = Field(default=0.5, ge=0.0, le=1.0)
    weight_arbitrage: float = Field(default=0.0, ge=0.0, le=1.0)

    # ML model
    ml_model_path: str | None = Field(default=None, description="Path to persisted order-flow model (joblib)")

    def get_market_ids_list(self) -> list[str]:
        if not self.market_ids.strip():
            return []
        return [m.strip() for m in self.market_ids.split(",") if m.strip()]
