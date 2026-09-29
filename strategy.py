"""Gemeinsame Filter für Kaufsignale.

Trendfolge braucht einen Schluss über dem EMA 200. Umkehrmuster brauchen
Stattdessen Schwung über dem EMA 20 oder einen RSI über 45. CRV und Volumen
gelten für jedes Muster.
"""

from __future__ import annotations

import re

import config

HOUR_MS = config.EMA_TIMEFRAME_MINUTES * 60_000
TREND_PATTERNS = {"Macro Range", "Range Breakout"}
REVERSAL_PATTERNS = {"Double Bottom", "Inverse Head and Shoulders"}


def signal_allowed(
    candles: list[list[float]],
    timeframe: str,
    stop: float,
    target: float,
    pattern_name: str,
) -> bool:
    """True, wenn der passende Trendfilter, CRV und Volumen zusammenpassen."""
    return rejection_reason(candles, timeframe, stop, target, pattern_name) is None


def rejection_reason(
    candles: list[list[float]],
    timeframe: str,
    stop: float,
    target: float,
    pattern_name: str,
) -> str | None:
    """Grund fürs Verwerfen, oder None wenn das Kaufsignal gültig ist."""
    closed = _closed(candles)
    if not closed:
        return "zu wenig Kerzen"
    entry = float(closed[-1][4])
    if pattern_name in REVERSAL_PATTERNS:
        if not momentum_confirms(closed):
            return "kein Schwung (EMA 20 und RSI)"
    elif pattern_name in TREND_PATTERNS or pattern_name not in REVERSAL_PATTERNS:
        if not close_above_ema(closed, timeframe):
            return "unter EMA 200"
    if not risk_reward_ok(entry, float(stop), float(target)):
        return "CRV unter 1.5"
    if not volume_confirms(closed, len(closed) - 1)[0]:
        return "Volumen zu schwach"
    return None


def momentum_confirms(candles: list[list[float]]) -> bool:
    """Umkehr ist gültig über dem EMA 20 oder bei RSI(14) über 45."""
    if not candles:
        return False
    closes = [float(candle[4]) for candle in candles]
    price = closes[-1]
    fast = ema(closes, config.EMA_FAST_PERIOD)
    if fast is not None and price > fast:
        return True
    value = rsi(closes, config.RSI_PERIOD)
    return value is not None and value > config.RSI_MIN


def rsi(values: list[float], period: int) -> float | None:
    """RSI nach Wilder. None, solange weniger als ``period`` Änderungen vorliegen."""
    if period <= 0 or len(values) < period + 1:
        return None
    gains = [max(values[index] - values[index - 1], 0.0) for index in range(1, len(values))]
    losses = [max(values[index - 1] - values[index], 0.0) for index in range(1, len(values))]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for index in range(period, len(gains)):
        average_gain = (average_gain * (period - 1) + gains[index]) / period
        average_loss = (average_loss * (period - 1) + losses[index]) / period
    if average_loss == 0:
        return 100.0
    relative = average_gain / average_loss
    return 100 - (100 / (1 + relative))


def close_above_ema(candles: list[list[float]], timeframe: str) -> bool:
    """Schlusskurs über dem EMA 200. Unter 1h wird auf Stundenkerzen aggregiert."""
    if not candles:
        return False
    price = float(candles[-1][4])
    average = ema(trend_closes(candles, timeframe), config.EMA_PERIOD)
    if average is None:
        return False
    return price > average


def risk_reward_ok(entry: float, stop: float, target: float) -> bool:
    """True, wenn (Ziel - Einstieg) / (Einstieg - Stop) mindestens 1.5 ist."""
    risk = entry - stop
    reward = target - entry
    if risk <= 0 or reward <= 0:
        return False
    return reward / risk >= config.MIN_RISK_REWARD


def volume_confirms(candles: list[list[float]], signal_index: int) -> tuple[bool, float, float]:
    """True, wenn die Signalkerze strikt über dem 1,2-fachen des 20er-Volumenschnitts liegt."""
    bars = config.VOLUME_SMA_BARS
    if signal_index < bars:
        return False, 0.0, 0.0
    current = float(candles[signal_index][5])
    sample = [float(candles[index][5]) for index in range(signal_index - bars, signal_index)]
    average = sum(sample) / bars
    if average <= 0:
        return False, current, average
    return current > average * config.VOLUME_BREAKOUT_FACTOR, current, average


def ema(values: list[float], period: int) -> float | None:
    """EMA. Die ersten ``period`` Werte bilden den Start als einfachen Durchschnitt."""
    if period <= 0 or len(values) < period:
        return None
    alpha = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = (price - value) * alpha + value
    return value


def trend_closes(candles: list[list[float]], timeframe: str) -> list[float]:
    """Schlusskurse für den Trend: ab 1h direkt, darunter zu Stundenkerzen zusammengefasst."""
    minutes = _timeframe_minutes(timeframe)
    if minutes is None or minutes >= config.EMA_TIMEFRAME_MINUTES:
        return [float(candle[4]) for candle in candles]
    buckets: dict[int, float] = {}
    order: list[int] = []
    for candle in candles:
        hour = int(candle[0]) // HOUR_MS
        if hour not in buckets:
            order.append(hour)
        buckets[hour] = float(candle[4])
    return [buckets[hour] for hour in order]


def _closed(candles: list[list[float]]) -> list[list[float]]:
    return candles[:-1] if len(candles) > 2 else list(candles)


def _timeframe_minutes(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)([mhdw])", value.strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    factor = {"m": 1, "h": 60, "d": 1440, "w": 10080}[match.group(2)]
    return amount * factor
