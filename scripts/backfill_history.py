"""
Backfill price history from CLOB API into a CSV or DB for training/backtest.
Usage: PYTHONPATH=. python scripts/backfill_history.py --token_id <id> [--interval 1h] [--out history.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


async def main_async(token_id: str, interval: str = "1h", out_path: str | None = None) -> None:
    from src.data.clob_client import ClobDataClient
    client = ClobDataClient()
    history = await client.get_prices_history(token_id, interval=interval)
    if out_path:
        import csv
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "p"])
            for row in history:
                w.writerow([row.get("t"), row.get("p")])
        print(f"Wrote {len(history)} points to {out_path}")
    else:
        print(f"Fetched {len(history)} points (use --out to save)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token_id", required=True, help="CLOB token ID")
    parser.add_argument("--interval", default="1h", help="1m, 1h, 1d, etc.")
    parser.add_argument("--out", default=None, help="Output CSV path")
    args = parser.parse_args()
    import asyncio
    asyncio.run(main_async(args.token_id, args.interval, args.out))


if __name__ == "__main__":
    main()
