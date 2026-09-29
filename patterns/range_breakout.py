"""Ausbruch aus einer engen Seitwärtsphase."""

from __future__ import annotations

import config
from patterns.base_pattern import BasePattern, Candle, PatternSignal


class RangeBreakout(BasePattern):
    """Erkennt eine enge Konsolidierung und den Ausbruch nach oben.

    Die Range wird aus den 30 geschlossenen Kerzen vor den letzten
    Prüfkerzen gebildet. Die aktuell laufende Kerze zählt nicht mit,
    sonst könnte der Schluss nie über dem Hoch derselben Kerze liegen.
    """

    name = "Range Breakout"

    def detect(self, candles: list[list[float]], timeframe: str | None = None) -> PatternSignal | None:
        closed = candles[:-1] if len(candles) > 2 else list(candles)
        range_bars = config.RANGE_BARS
        lookback = config.RANGE_FAIL_LOOKBACK
        if len(closed) < range_bars + lookback:
            return None

        recent = closed[-lookback:]
        window = closed[-(range_bars + lookback) : -lookback]
        if len(window) != range_bars:
            return None

        range_low = min(float(candle[3]) for candle in window)
        range_high = max(float(candle[2]) for candle in window)
        if range_low <= 0 or range_high <= range_low:
            return None

        span_percent = ((range_high - range_low) / range_low) * 100
        if span_percent >= config.RANGE_MAX_SPAN_PERCENT:
            return None

        height = range_high - range_low
        midpoint = range_low + height / 2
        neckline = range_high
        stop_loss = midpoint
        target = range_high + height
        breakout = neckline * (1 + config.NECKLINE_BREAK_BUFFER)
        upper_edge = range_low + height * (1 - config.RANGE_UPPER_FRACTION)

        last_close = float(recent[-1][4])
        volume_ok, current_volume, average_volume = _volume_confirms(closed, len(closed) - 1)
        broke_out = any(float(candle[4]) >= breakout for candle in recent) or any(
            float(candle[2]) > neckline for candle in recent
        )
        fingerprint = (
            f"{int(window[0][0])}:{int(window[-1][0])}:"
            f"{range_low:.6f}:{range_high:.6f}"
        )

        if last_close >= breakout and volume_ok:
            status = "CONFIRMED"
            detail = (
                f"Range-Ausbruch bei {last_close:.4f} über {neckline:.4f}. "
                f"Volumen {current_volume:.0f} gegen Schnitt {average_volume:.0f}. "
                f"Spanne {span_percent:.2f} % ({range_low:.4f}–{range_high:.4f})."
            )
        elif last_close >= breakout:
            status = "FORMING"
            detail = (
                f"Kurs über der Range bei {last_close:.4f}, Volumen zu schwach "
                f"({current_volume:.0f} < {average_volume * config.VOLUME_BREAKOUT_FACTOR:.0f}). "
                f"Neckline {neckline:.4f}."
            )
        elif broke_out and last_close <= stop_loss:
            status = "FAILED"
            detail = (
                f"Ausbruch zurück unter die Range-Mitte "
                f"({last_close:.4f} <= {stop_loss:.4f}). Setup ungültig."
            )
        elif upper_edge <= last_close < breakout:
            status = "FORMING"
            detail = (
                f"Konsolidierung {span_percent:.2f} %, Kurs am oberen Rand. "
                f"Range {range_low:.4f}–{range_high:.4f}, Schluss {last_close:.4f}."
            )
        else:
            return None

        return PatternSignal(
            status=status,
            fingerprint=fingerprint,
            detail=detail,
            neckline_price=float(neckline),
            stop_loss_price=float(stop_loss),
            target_price=float(target),
        )


def _volume_confirms(candles: list[Candle], signal_index: int) -> tuple[bool, float, float]:
    """True, wenn die Ausbruchskerze mindestens das 1,3-fache des 20er-Volumenschnitts hat."""
    bars = config.VOLUME_SMA_BARS
    if signal_index < bars:
        return False, 0.0, 0.0
    current = float(candles[signal_index][5])
    sample = [float(candles[index][5]) for index in range(signal_index - bars, signal_index)]
    average = sum(sample) / bars
    if average <= 0:
        return False, current, average
    return current >= average * config.VOLUME_BREAKOUT_FACTOR, current, average
