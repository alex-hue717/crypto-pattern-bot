"""Holt Marktdaten via CCXT."""

from __future__ import annotations

from typing import Any

import ccxt

import config

Candle = list[Any]


def create_exchange() -> ccxt.Exchange:
    if not hasattr(ccxt, config.EXCHANGE):
        raise ValueError(f"Unbekannte Börse: {config.EXCHANGE}")
    exchange_cls = getattr(ccxt, config.EXCHANGE)
    return exchange_cls({"enableRateLimit": True})


def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str) -> list[Candle]:
    """Kerzen als [timestamp, open, high, low, close, volume]."""
    return exchange.fetch_ohlcv(
        symbol,
        timeframe=config.TIMEFRAME,
        limit=config.CANDLE_LIMIT,
    )
