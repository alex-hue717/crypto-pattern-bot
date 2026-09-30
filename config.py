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
    "AVAX/USDT",
    "LINK/USDT",
    "NEAR/USDT",
    "FET/USDT",
    "PEPE/USDT",
    "BOME/USDT",
    "ETHFI/USDT",
    "SEI/USDT",
]

TIMEFRAMES = [
    "15m",
    "1h",
]

CANDLE_LIMIT = 850
POLL_INTERVAL_SECONDS = 60

# Double Bottom nur auf 4h und nur für diese Basen, egal ob /USDT oder -USD.
DOUBLE_BOTTOM_TIMEFRAME = "4h"
DOUBLE_BOTTOM_WHITELIST = ("ETH", "SOL", "LINK", "NEAR", "AVAX")
DOUBLE_BOTTOM_MIN_BARS = 15
DOUBLE_BOTTOM_TOLERANCE = 0.01
MIN_BARS_BETWEEN_LOWS = 5
MAX_BARS_BETWEEN_LOWS = 60
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

# Kaufsignale: Trendfolge bleibt am EMA 200, Umkehr nutzt EMA 20 oder RSI.
EMA_PERIOD = 200
EMA_FAST_PERIOD = 20
EMA_TIMEFRAME_MINUTES = 60
RSI_PERIOD = 14
RSI_MIN = 45
MIN_RISK_REWARD = 1.5
TAKE_PROFIT_1_R = 1.0
TAKE_PROFIT_2_R = 2.0
PARTIAL_CLOSE = 0.5
VOLUME_SMA_BARS = 20
VOLUME_BREAKOUT_FACTOR = 1.2

# Alle Muster bleiben je Coin erlaubt. Die Qualität steuert strategy.py.
COIN_PATTERN_RULES = {
    "BTC/USDT": {"disabled_patterns": []},
    "ETH/USDT": {"disabled_patterns": []},
    "SOL/USDT": {"disabled_patterns": []},
    "AVAX/USDT": {"disabled_patterns": []},
    "LINK/USDT": {"disabled_patterns": []},
    "NEAR/USDT": {"disabled_patterns": []},
    "FET/USDT": {"disabled_patterns": []},
    "PEPE/USDT": {"disabled_patterns": []},
    "BOME/USDT": {"disabled_patterns": []},
    "ETHFI/USDT": {"disabled_patterns": []},
    "SEI/USDT": {"disabled_patterns": []},
}


def double_bottom_allowed(symbol: str, timeframe: str) -> bool:
    """True nur für ETH, SOL, LINK, NEAR und AVAX auf dem 4h-Chart."""
    if timeframe.strip().lower() != DOUBLE_BOTTOM_TIMEFRAME:
        return False
    base = symbol.strip().upper().replace("-", "/").split("/", 1)[0]
    return base in DOUBLE_BOTTOM_WHITELIST


def is_pattern_disabled(symbol: str, pattern_name: str) -> bool:
    """True, wenn dieses Muster für den Coin nicht gehandelt werden soll."""
    disabled = COIN_PATTERN_RULES.get(symbol, {}).get("disabled_patterns", [])
    return pattern_name in disabled


def has_pattern_warning(symbol: str, pattern_name: str) -> bool:
    """True, wenn dieses Muster auf dem Coin nur als Hinweis markiert ist."""
    warnings = COIN_PATTERN_RULES.get(symbol, {}).get("warnings", [])
    return pattern_name in warnings


DB_PATH = Path(__file__).resolve().parent / "patterns.db"
