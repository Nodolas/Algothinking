"""Status: running, mode, uptime."""
from fastapi import APIRouter

from src.app.state import get_runner

router = APIRouter()


@router.get("")
async def get_status():
    runner = get_runner()
    if runner is None:
        return {"running": False, "mode": None, "uptime_seconds": 0}
    return {
        "running": runner.running,
        "mode": runner.execution_mode,
        "uptime_seconds": round(runner.uptime_seconds, 1),
    }
