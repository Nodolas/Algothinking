# Polymarket Statistical Trading Bot

A data-driven trading bot for Polymarket with statistical strategies (mispricing, mean reversion, order-flow ML), paper and live execution, and a FastAPI + CLI interface.

## Setup

1. **Python 3.9+** and a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Configuration**: Copy `config/.env.example` to `.env` in the project root and fill in:

   - `MARKET_IDS`: comma-separated condition IDs or token IDs (from [Polymarket](https://polymarket.com) or Gamma API).
   - For **live trading**: set `EXECUTION_MODE=live` and add `API_KEY`, `API_SECRET`, `API_PASSPHRASE` (and optionally `PRIVATE_KEY` for L1). Get API keys from [Polymarket CLOB Authentication](https://docs.polymarket.com/developers/CLOB/authentication).

3. **Run in paper mode first** (default). Only switch to live after testing and with small position sizes.

## Usage

- **Start API server** (control bot via HTTP):

  ```bash
  uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
  ```

  Then: `POST /start` to start the bot, `POST /stop` to stop, `GET /status`, `GET /signals`, `GET /positions`.

- **CLI** (optional):

  ```bash
  python -m src.app.cli serve    # run FastAPI
  python -m src.app.cli bot start
  python -m src.app.cli bot status
  ```

## Project layout

- `src/data/` – CLOB client, history store, optional WebSocket client.
- `src/strategies/` – Feature extraction, mispricing, mean reversion, ML, arbitrage stub, aggregator.
- `src/execution/` – Risk manager, paper executor, live executor, bot runner.
- `src/app/` – FastAPI routes and CLI.
- `config/` – Settings schema and `.env.example`.
- `scripts/` – Train ML model, backfill history.

## License

MIT.
