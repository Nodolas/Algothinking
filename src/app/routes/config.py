"""Config (no secrets)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_config():
    try:
        from config.settings import Settings
        s = Settings()
        return {
            "clob_host": s.clob_host,
            "chain_id": s.chain_id,
            "market_ids": s.get_market_ids_list(),
            "polling_interval_seconds": s.polling_interval_seconds,
            "execution_mode": s.execution_mode,
            "confidence_threshold": s.confidence_threshold,
            "kelly_fraction": s.kelly_fraction,
            "max_position_pct": s.max_position_pct,
            "max_daily_loss_pct": s.max_daily_loss_pct,
            "initial_bankroll": s.initial_bankroll,
        }
    except Exception as e:
        return {"error": str(e)}
