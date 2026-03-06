"""FastAPI app for bot control and monitoring."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on path when running uvicorn src.app.main
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routes import status, control, signals, positions, config as config_routes
from src.app.state import set_runner, set_clob, set_history_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load config and create runner on startup if env is set
    try:
        from config.settings import Settings
        s = Settings()
        ids = s.get_market_ids_list()
        if ids:
            from src.data.clob_client import ClobDataClient
            from src.data.history_store import HistoryStore
            from src.execution.runner import BotRunner
            from src.execution.risk import RiskParams
            from src.execution.live import LiveExecutor
            clob = ClobDataClient(host=s.clob_host, chain_id=s.chain_id)
            store = HistoryStore()
            params = RiskParams(
                kelly_fraction=s.kelly_fraction,
                max_position_pct=s.max_position_pct,
                max_daily_loss_pct=s.max_daily_loss_pct,
                stop_loss_pct=s.stop_loss_pct,
                initial_bankroll=s.initial_bankroll,
            )
            live_exec = None
            if s.execution_mode == "live" and s.api_key and s.api_secret and s.api_passphrase and s.private_key:
                live_exec = LiveExecutor(
                    api_key=s.api_key,
                    api_secret=s.api_secret,
                    api_passphrase=s.api_passphrase,
                    host=s.clob_host,
                    chain_id=s.chain_id,
                    private_key=s.private_key,
                )
            runner = BotRunner(
                clob=clob,
                history_store=store,
                market_ids=ids,
                interval_seconds=s.polling_interval_seconds,
                execution_mode=s.execution_mode,
                confidence_threshold=s.confidence_threshold,
                risk_params=params,
                strategy_weights={
                    "mean_reversion": s.weight_mean_reversion,
                    "mispricing": s.weight_mispricing,
                    "ml": s.weight_ml,
                    "arbitrage": s.weight_arbitrage,
                },
                ml_model_path=s.ml_model_path,
                initial_bankroll=s.initial_bankroll,
                live_executor=live_exec,
                use_websocket=s.use_websocket,
            )
            set_clob(clob)
            set_history_store(store)
            set_runner(runner)
        else:
            set_runner(None)
            set_clob(None)
            set_history_store(None)
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("Could not init runner from config: %s", e)
    yield
    from src.app.state import get_clob
    clob = get_clob()
    if clob:
        await clob.close()


app = FastAPI(title="Polymarket Bot API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(control.router, tags=["control"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(positions.router, prefix="/positions", tags=["positions"])
app.include_router(config_routes.router, prefix="/config", tags=["config"])


@app.get("/")
async def root():
    return {"service": "Polymarket Statistical Bot", "docs": "/docs"}
