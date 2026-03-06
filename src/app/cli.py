"""CLI: serve (uvicorn), bot start/stop/status."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Project root on path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import typer

app = typer.Typer(help="Polymarket Statistical Bot CLI")
bot_cmd = typer.Typer(help="Bot control")
app.add_typer(bot_cmd, name="bot")


@bot_cmd.command("start")
def bot_start():
    """Start the bot (via API POST /start)."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/start", method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            print(r.read().decode())
    except Exception as e:
        typer.echo(f"Error: {e}. Is the API server running? (uvicorn src.app.main:app)", err=True)
        raise typer.Exit(1)


@bot_cmd.command("stop")
def bot_stop():
    """Stop the bot (via API POST /stop)."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/stop", method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            print(r.read().decode())
    except Exception as e:
        typer.echo(f"Error: {e}. Is the API server running?", err=True)
        raise typer.Exit(1)


@bot_cmd.command("status")
def bot_status():
    """Print bot status (via API GET /status)."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/status", timeout=5) as r:
            print(r.read().decode())
    except Exception as e:
        typer.echo(f"Error: {e}. Is the API server running?", err=True)
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
):
    """Run the FastAPI server (uvicorn)."""
    import uvicorn
    uvicorn.run(
        "src.app.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    app()
