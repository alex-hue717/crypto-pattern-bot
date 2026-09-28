"""Dein erstes Muster: Double Bottom."""

from __future__ import annotations

import config
from patterns.base_pattern import BasePattern, Candle, PatternSignal


class DoubleBottom(BasePattern):
    name = "Double Bottom"

    def detect(self, candles: list[Candle]) -> PatternSignal | None:
        closed = candles[:-1] if len(candles) > 2 else list(candles)
        needed = config.MAX_BARS_BETWEEN_LOWS + config.SWING_LOOKBACK * 2
        if len(closed) < needed:
            return None

        swings = _swing_lows(closed, config.SWING_LOOKBACK)
        if len(swings) < 2:
            return None

        second_idx, second_low = swings[-1]
        first: tuple[int, float] | None = None
        for idx, low in reversed(swings[:-1]):
            gap = second_idx - idx
            if gap < config.MIN_BARS_BETWEEN_LOWS:
                continue
            if gap > config.MAX_BARS_BETWEEN_LOWS:
                break
            mid = (low + second_low) / 2
            if mid <= 0:
                continue
            if abs(low - second_low) / mid <= config.DOUBLE_BOTTOM_TOLERANCE:
                first = (idx, low)
                break
        if first is None:
            return None

        first_idx, first_low = first
        between = closed[first_idx + 1 : second_idx]
        if not between:
            return None

        neckline = max(candle[2] for candle in between)
        last_close = float(closed[-1][4])
        deeper = min(first_low, second_low)
        fingerprint = f"{int(closed[first_idx][0])}:{int(closed[second_idx][0])}"

        if last_close >= neckline * (1 + config.NECKLINE_BREAK_BUFFER):
            status = "CONFIRMED"
            detail = (
                f"Neckline gebrochen bei {last_close:.4f} "
                f"(Neckline {neckline:.4f}). "
                f"Tiefs {first_low:.4f} / {second_low:.4f}."
            )
        elif last_close <= deeper * (1 - config.FAILED_BREAK_BUFFER):
            status = "FAILED"
            detail = (
                f"Unter das Doppel-Tief gefallen "
                f"({last_close:.4f} < {deeper:.4f}). Setup ungültig."
            )
        else:
            status = "FORMING"
            detail = (
                f"Zweites Tief bei {second_low:.4f} (erstes {first_low:.4f}). "
                f"Neckline {neckline:.4f}, Schluss {last_close:.4f}."
            )

        return PatternSignal(status=status, fingerprint=fingerprint, detail=detail)


def _swing_lows(candles: list[Candle], lookback: int) -> list[tuple[int, float]]:
    swings: list[tuple[int, float]] = []
    for i in range(lookback, len(candles) - lookback):
        low = float(candles[i][3])
        window = [float(candles[j][3]) for j in range(i - lookback, i + lookback + 1)]
        if low == min(window):
            swings.append((i, low))
    return swings
