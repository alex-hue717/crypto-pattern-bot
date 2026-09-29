"""Gemeinsame Filter für Kaufsignale.

Ein Signal muss im Aufwärtstrend liegen, genug Abstand zwischen Stop und Ziel
haben und mit erhöhtem Volumen kommen. Muster und Coins werden hier nicht gesperrt.
"""

from __future__ import annotations

import re

import config

HOUR_MS = config.EMA_TIMEFRAME_MINUTES * 60_000


def signal_allowed(
    candles: list[list[float]],
    timeframe: str,
    stop: float,
    target: float,
) -> bool:
    """True, wenn Trend, CRV und Volumen zusammenpassen."""
    return rejection_reason(candles, timeframe, stop, target) is None


def rejection_reason(
    candles: list[list[float]],
    timeframe: str,
    stop: float,
    target: float,
) -> str | None:
    """Grund fürs Verwerfen, oder None wenn das Kaufsignal gültig ist."""
    closed = _closed(candles)
    if not closed:
        return "zu wenig Kerzen"
    entry = float(closed[-1][4])
    if not close_above_ema(closed, timeframe):
        return "unter EMA 200"
    if not risk_reward_ok(entry, float(stop), float(target)):
        return "CRV unter 1.5"
    if not volume_confirms(closed, len(closed) - 1)[0]:
        return "Volumen zu schwach"
    return None


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
