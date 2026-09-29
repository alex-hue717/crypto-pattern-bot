"""Übergeordnete Preiszone (Macro Range) über die letzten 200 Kerzen."""

from __future__ import annotations

import config
from patterns.base_pattern import BasePattern, PatternSignal


class MacroRange(BasePattern):
    """Erkennt Tests, Ausbrüche und Abpraller an einer Makro-Zone.

    Das obere Band ist das 95. Perzentil der Hochs, das untere das 5. Perzentil
    der Tiefs. Die laufende Kerze zählt nicht mit.
    """

    name = "Macro Range"

    def detect(self, candles: list[list[float]]) -> PatternSignal | None:
        closed = candles[:-1] if len(candles) > 2 else list(candles)
        bars = config.MACRO_BARS
        if len(closed) < bars:
            return None

        window = closed[-bars:]
        highs = [float(candle[2]) for candle in window]
        lows = [float(candle[3]) for candle in window]
        zone_high = _percentile(highs, config.MACRO_HIGH_PERCENTILE)
        zone_low = _percentile(lows, config.MACRO_LOW_PERCENTILE)
        if zone_low <= 0 or zone_high <= zone_low:
            return None

        last = window[-1]
        last_high = float(last[2])
        last_low = float(last[3])
        last_close = float(last[4])
        upper_break = zone_high * (1 + config.MACRO_BREAKOUT)
        lower_break = zone_low * (1 - config.MACRO_BREAKOUT)
        near_high = abs(last_close - zone_high) / zone_high <= config.MACRO_PROXIMITY
        near_low = abs(last_close - zone_low) / zone_low <= config.MACRO_PROXIMITY
        clear_of_high = last_close < zone_high * (1 - config.MACRO_PROXIMITY)
        clear_of_low = last_close > zone_low * (1 + config.MACRO_PROXIMITY)

        if last_close >= upper_break:
            side = "high"
            status = "CONFIRMED"
            detail = (
                f"Ausbruch über die Makro-Zone bei {last_close:.4f} "
                f"(oberes Band {zone_high:.4f})."
            )
        elif last_close <= lower_break:
            side = "low"
            status = "CONFIRMED"
            detail = (
                f"Ausbruch unter die Makro-Zone bei {last_close:.4f} "
                f"(unteres Band {zone_low:.4f})."
            )
        elif near_high or near_low:
            side = _nearer_side(last_close, zone_low, zone_high, near_high, near_low)
            status = "FORMING"
            if side == "high":
                detail = (
                    f"Testet den oberen Rand (Widerstand) bei {zone_high:.4f}. "
                    f"Schluss {last_close:.4f}, unteres Band {zone_low:.4f}."
                )
            else:
                detail = (
                    f"Testet den unteren Rand (Unterstützung) bei {zone_low:.4f}. "
                    f"Schluss {last_close:.4f}, oberes Band {zone_high:.4f}."
                )
        elif last_high >= upper_break and clear_of_high and last_close > zone_low:
            side = "high"
            status = "FAILED"
            detail = (
                f"Abpraller am oberen Rand. Hoch {last_high:.4f}, "
                f"Schluss wieder innerhalb bei {last_close:.4f} "
                f"(Band {zone_low:.4f}–{zone_high:.4f})."
            )
        elif last_low <= lower_break and clear_of_low and last_close < zone_high:
            side = "low"
            status = "FAILED"
            detail = (
                f"Abpraller am unteren Rand. Tief {last_low:.4f}, "
                f"Schluss wieder innerhalb bei {last_close:.4f} "
                f"(Band {zone_low:.4f}–{zone_high:.4f})."
            )
        else:
            return None

        neckline, stop_loss, target = _levels(side, zone_low, zone_high)
        if target <= 0 or stop_loss <= 0:
            return None

        fingerprint = f"{int(window[0][0])}:{int(window[-1][0])}:{side}"
        return PatternSignal(
            status=status,
            fingerprint=fingerprint,
            detail=detail,
            neckline_price=float(neckline),
            stop_loss_price=float(stop_loss),
            target_price=float(target),
        )


def _levels(side: str, zone_low: float, zone_high: float) -> tuple[float, float, float]:
    """Neckline an der getesteten Kante, Stop 2 % innerhalb der Zone, Ziel = Zonenhöhe."""
    height = zone_high - zone_low
    midpoint = zone_low + height / 2
    if side == "high":
        neckline = zone_high
        stop = zone_high * (1 - config.MACRO_STOP_INSIDE)
        if stop <= zone_low:
            stop = midpoint
        target = zone_high + height
        return neckline, stop, target

    neckline = zone_low
    stop = zone_low * (1 + config.MACRO_STOP_INSIDE)
    if stop >= zone_high:
        stop = midpoint
    target = zone_low - height
    return neckline, stop, target


def _nearer_side(
    close: float,
    zone_low: float,
    zone_high: float,
    near_high: bool,
    near_low: bool,
) -> str:
    if near_high and not near_low:
        return "high"
    if near_low and not near_high:
        return "low"
    high_distance = abs(close - zone_high) / zone_high
    low_distance = abs(close - zone_low) / zone_low
    return "high" if high_distance <= low_distance else "low"


def _percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percent / 100)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight
