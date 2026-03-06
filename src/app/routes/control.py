"""Control: start, stop bot."""
from fastapi import APIRouter, HTTPException

from src.app.state import get_runner

router = APIRouter()


@router.post("/start")
async def start_bot():
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Runner not initialized; set MARKET_IDS and run from project root")
    if runner.running:
        return {"status": "already_running"}
    runner.start_background()
    return {"status": "started"}


@router.post("/stop")
async def stop_bot():
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Runner not initialized")
    runner.stop()
    return {"status": "stopped"}
