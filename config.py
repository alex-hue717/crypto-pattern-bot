"""Liest die Projekt-Einstellungen.

Tokens und die Börse kommen aus der ``.env``-Datei (python-dotenv).
Handelspaare und Timeframes sind hier als Listen definiert.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _env(name: str, fallback_name: str = "") -> str:
    """Liest eine Umgebungsvariable, optional mit altem Namen als Fallback."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    if fallback_name:
        return os.getenv(fallback_name, "").strip()
    return ""


# Telegram. TELEGRAM_BOT_TOKEN bleibt gültig, falls die lokale .env den alten Namen hat.
TELEGRAM_TOKEN = _env("TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# ccxt-Börsen-ID, z. B. binance, bybit, kraken.
EXCHANGE = os.getenv("EXCHANGE", "binance").strip() or "binance"

SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
]

TIMEFRAMES = [
    "15m",
    "1h",
]

CANDLE_LIMIT = 250
POLL_INTERVAL_SECONDS = 60

# Schwellen für das Double-Bottom-Muster.
DOUBLE_BOTTOM_TOLERANCE = 0.015
MIN_BARS_BETWEEN_LOWS = 5
MAX_BARS_BETWEEN_LOWS = 40
NECKLINE_BREAK_BUFFER = 0.002
FAILED_BREAK_BUFFER = 0.005
SWING_LOOKBACK = 3

# Invertierte Kopf-Schulter (iH&S).
IHNS_SHOULDER_TOLERANCE = 0.02
IHNS_MIN_BARS = 5
IHNS_MAX_BARS = 30
IHNS_MIN_HEAD_DEPTH = 0.015

# Enge Range und Ausbruch.
RANGE_BARS = 30
RANGE_MAX_SPAN_PERCENT = 6.0
RANGE_UPPER_FRACTION = 0.20
RANGE_FAIL_LOOKBACK = 3

# Makro-Zone über die letzten geschlossenen Kerzen.
MACRO_BARS = 200
MACRO_HIGH_PERCENTILE = 95
MACRO_LOW_PERCENTILE = 5
MACRO_PROXIMITY = 0.015
MACRO_BREAKOUT = 0.003
MACRO_STOP_INSIDE = 0.02
MACRO_MIN_TIMEFRAME_MINUTES = 60
MACRO_MIN_SWING_HIGHS = 2
MACRO_MIN_SWING_LOWS = 2

# Ausbruch nur mit überdurchschnittlichem Volumen bestätigen.
VOLUME_SMA_BARS = 20
VOLUME_BREAKOUT_FACTOR = 1.3

# Coin-spezifische Hinweise. "warnings" markiert Muster mit historisch vielen Fehlausbrüchen.
COIN_PATTERN_RULES = {
    "BTC/USDT": {
        "warnings": ["Range Breakout"],  # Oder komplett deaktivieren
    },
    "ETH/USDT": {
        "warnings": ["Range Breakout"],
    },
    "SOL/USDT": {
        "warnings": ["Macro Range"],
    },
}


def has_pattern_warning(symbol: str, pattern_name: str) -> bool:
    """True, wenn dieses Muster auf dem Coin als riskant markiert ist."""
    warnings = COIN_PATTERN_RULES.get(symbol, {}).get("warnings", [])
    return pattern_name in warnings


DB_PATH = Path(__file__).resolve().parent / "patterns.db"
