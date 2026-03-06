"""Live executor: place orders via py-clob-client L2 (create_order + post_order)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_l2_client(api_key: str, api_secret: str, api_passphrase: str, host: str, chain_id: int, private_key: str | None, funder: str | None = None) -> Any:
    """Build L2 ClobClient (sync). Requires py_clob_client and ApiCreds."""
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds
    creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)
    if not private_key:
        raise ValueError("PRIVATE_KEY required for live trading")
    return ClobClient(
        host=host,
        chain_id=chain_id,
        key=private_key,
        creds=creds,
        signature_type=2,
        funder=funder or "",
    )


async def live_execute(
    token_id: str,
    side: str,
    size: float,
    price: float,
    *,
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    host: str = "https://clob.polymarket.com",
    chain_id: int = 137,
    private_key: str | None = None,
    funder: str | None = None,
) -> dict | None:
    """
    Create and post a limit order on the CLOB (L2). Runs in thread pool.
    Returns order response dict or None on failure.
    """
    if not private_key:
        logger.error("Live execute: PRIVATE_KEY not set")
        return None
    try:
        from py_clob_client.clob_types import OrderArgs
    except ImportError:
        logger.error("py-clob-client not installed or missing OrderArgs")
        return None

    def _sync_create_and_post() -> dict | None:
        client = _get_l2_client(
            api_key, api_secret, api_passphrase, host, chain_id, private_key, funder
        )
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side.upper(),
        )
        try:
            order = client.create_order(order_args)
            return client.post_order(order)
        except Exception as e:
            logger.exception("Live order failed: %s", e)
            return None

    return await asyncio.to_thread(_sync_create_and_post)


class LiveExecutor:
    """Thin wrapper that holds creds and calls live_execute."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        *,
        host: str = "https://clob.polymarket.com",
        chain_id: int = 137,
        private_key: str | None = None,
        funder: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key
        self.funder = funder

    async def execute(self, token_id: str, side: str, size: float, price: float) -> dict | None:
        return await live_execute(
            token_id,
            side,
            size,
            price,
            api_key=self.api_key,
            api_secret=self.api_secret,
            api_passphrase=self.api_passphrase,
            host=self.host,
            chain_id=self.chain_id,
            private_key=self.private_key,
            funder=self.funder,
        )
