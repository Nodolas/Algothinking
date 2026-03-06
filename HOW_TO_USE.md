# How to Use the Polymarket Statistical Bot

This guide explains what you need to do before running the bot and how to use it.

---

## What You Need Before Starting

1. **Python 3.9+** on your machine.
2. **Polymarket account** (for live trading; optional for paper trading).
3. **Market IDs** (condition IDs or token IDs) of the markets you want the bot to watch and trade. You can get these from [Polymarket](https://polymarket.com) or the Gamma API.
4. **API keys** (only for **live** trading): API key, secret, passphrase, and your wallet private key. See [Polymarket CLOB Authentication](https://docs.polymarket.com/developers/CLOB/authentication).

---

## Step 1: Install Dependencies

From the project root (`Algothinking`):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

1. Copy the example env file:

   ```bash
   copy config\.env.example .env    # Windows
   # cp config/.env.example .env   # macOS/Linux
   ```

2. Edit `.env` in the project root. **Minimum to run the bot:**

   | Variable | What to do |
   |----------|------------|
   | `MARKET_IDS` | **Required.** Comma-separated list of market condition IDs or token IDs, e.g. `0xabc...,0xdef...`. Get these from a Polymarket market URL or API. |
   | `EXECUTION_MODE` | Leave as `paper` for testing. Set to `live` only when you are ready to trade with real funds. |
   | `POLLING_INTERVAL_SECONDS` | Optional. Default `60`. How often the bot fetches data and evaluates signals. |

3. **For live trading only**, also set:

   | Variable | What to do |
   |----------|------------|
   | `API_KEY` | From Polymarket (derive or create via their docs). |
   | `API_SECRET` | From Polymarket. |
   | `API_PASSPHRASE` | From Polymarket. |
   | `PRIVATE_KEY` | Your wallet private key (e.g. from MetaMask export or Magic link export). |
   | `EXECUTION_MODE` | Set to `live`. |

Never commit `.env` or share these values.

---

## Step 3: Run the API Server

From the project root:

```bash
uvicorn src.app.main:app --host 0.0.0.0 --port 8000
```

Or with the CLI:

```bash
python -m src.app.cli serve
```

You should see the server start. Open **http://127.0.0.1:8000/docs** for the interactive API docs.

---

## Step 4: Start and Stop the Bot

- **Start the bot** (begins the polling loop and strategy evaluation):

  ```bash
  curl -X POST http://127.0.0.1:8000/start
  ```

  Or use the CLI (with the server already running):

  ```bash
  python -m src.app.cli bot start
  ```

- **Stop the bot**:

  ```bash
  curl -X POST http://127.0.0.1:8000/stop
  # or
  python -m src.app.cli bot stop
  ```

- **Check status** (running/stopped, mode, uptime):

  ```bash
  curl http://127.0.0.1:8000/status
  # or
  python -m src.app.cli bot status
  ```

---

## Step 5: Monitor Signals and Positions

- **Recent signals** (per market: signal, confidence, strategy breakdown):

  ```bash
  curl "http://127.0.0.1:8000/signals?limit=20"
  ```

- **Positions and balance** (paper positions and virtual balance, or live if you use live mode):

  ```bash
  curl http://127.0.0.1:8000/positions
  ```

- **Current config** (no secrets):

  ```bash
  curl http://127.0.0.1:8000/config
  ```

---

## What Needs to Be Done (Checklist)

| # | Task | Required? |
|---|------|-----------|
| 1 | Install Python 3.9+ and create a venv | Yes |
| 2 | Run `pip install -r requirements.txt` | Yes |
| 3 | Copy `config/.env.example` to `.env` | Yes |
| 4 | Set `MARKET_IDS` in `.env` (comma-separated market/token IDs) | Yes |
| 5 | Leave `EXECUTION_MODE=paper` until you have tested | Recommended |
| 6 | For **live** trading: get Polymarket API key, secret, passphrase, and set `PRIVATE_KEY` in `.env` | Only for live |
| 7 | Start the API server (`uvicorn` or `python -m src.app.cli serve`) | Yes |
| 8 | Call `POST /start` (or `bot start`) to run the bot | Yes |
| 9 | Optionally train an ML model and set `ML_MODEL_PATH` in `.env` | Optional |
| 10 | Optionally set `USE_WEBSOCKET=true` for real-time orderbook updates | Optional |

---

## Optional: Train the ML Model

The bot can use an order-flow classifier for extra signals. To train it:

1. (Optional) Backfill price history for a token:

   ```bash
   set PYTHONPATH=.   # Windows
   python scripts/backfill_history.py --token_id <CLOB_TOKEN_ID> --interval 1h --out data/history.csv
   ```

2. Train the model (uses your CSV if provided, otherwise synthetic data):

   ```bash
   python scripts/train_orderflow.py --data data/history.csv --out models/orderflow_model.joblib
   ```

3. In `.env`, set:

   ```
   ML_MODEL_PATH=models/orderflow_model.joblib
   ```

Restart the server so it picks up the new model.

---

## Optional: Real-Time Data (WebSocket)

To use the Polymarket WebSocket for live orderbook updates:

1. In `.env`, set:

   ```
   USE_WEBSOCKET=true
   ```

2. Restart the server. The bot will subscribe to the market channel for your `MARKET_IDS` in addition to polling.

---

## Paper vs Live Mode

- **Paper** (`EXECUTION_MODE=paper`): The bot evaluates signals and “executes” trades in memory. No real orders are sent. Use this to test strategies and the UI.
- **Live** (`EXECUTION_MODE=live`): The bot sends real limit orders to Polymarket using your API key and private key. Only switch to live after testing in paper and with small position sizes. Risk limits (max position %, daily loss %, etc.) are in `.env`.

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `Runner not initialized` on `/start` | Set `MARKET_IDS` in `.env` and restart the server. The runner is only created when at least one market ID is set. |
| `ModuleNotFoundError: py_clob_client` | Run `pip install -r requirements.txt` from the project root. |
| No signals or low confidence | The bot needs some price history. Let it run for a few polling intervals (or use WSS) so the history store fills; strategies use rolling windows (e.g. 50–100 points). |
| Live orders fail | Check API key, secret, passphrase, and `PRIVATE_KEY` in `.env`. Ensure your Polymarket account and API keys are valid and not restricted. |

---

## Quick Reference: API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/status` | Bot running/stopped, mode, uptime |
| POST | `/start` | Start the bot loop |
| POST | `/stop` | Stop the bot loop |
| GET | `/signals?limit=20` | Last N signals per market |
| GET | `/positions` | Positions and balance |
| GET | `/config` | Current config (no secrets) |
| GET | `/docs` | Swagger UI |

All of this assumes you run commands from the **project root** and that `.env` is in the project root.
