"""Einstellungen (Coins, Timeframes, Schwellenwerte)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# ccxt-Börsen-ID, z.B. binance, bybit, kraken
EXCHANGE = os.getenv("EXCHANGE", "binance")

SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
]

TIMEFRAME = "1h"
CANDLE_LIMIT = 200
POLL_INTERVAL_SECONDS = 60

# Double Bottom
DOUBLE_BOTTOM_TOLERANCE = 0.015  # max. relativer Abstand der beiden Tiefs
MIN_BARS_BETWEEN_LOWS = 5
MAX_BARS_BETWEEN_LOWS = 40
NECKLINE_BREAK_BUFFER = 0.002  # Schluss so weit über der Neckline = CONFIRMED
FAILED_BREAK_BUFFER = 0.005  # Schluss so weit unter dem tieferen Tief = FAILED
SWING_LOOKBACK = 3

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DB_PATH = Path(__file__).resolve().parent / "data" / "state.db"
