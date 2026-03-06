"""Last signals per market."""
from fastapi import APIRouter, Query

from src.app.state import get_runner

router = APIRouter()


@router.get("")
async def get_signals(limit: int = Query(20, ge=1, le=100)):
    runner = get_runner()
    if runner is None:
        return {"signals": []}
    return {"signals": runner.get_last_signals(limit=limit)}
