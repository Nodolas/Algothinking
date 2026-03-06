"""Positions (paper or live)."""
from fastapi import APIRouter

from src.app.state import get_runner

router = APIRouter()


@router.get("")
async def get_positions():
    runner = get_runner()
    if runner is None:
        return {"positions": [], "balance": 0}
    return {
        "positions": runner.get_positions(),
        "balance": runner.get_balance(),
    }
