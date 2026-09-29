"""Invertiertes Kopf-Schulter-Muster (Inverse Head and Shoulders)."""

from __future__ import annotations

import config
from patterns.base_pattern import BasePattern, Candle, PatternSignal


class InverseHeadAndShoulders(BasePattern):
    """Erkennt eine inverse Kopf-Schulter-Formation (iH&S).

    Drei lokale Tiefs: linke Schulter, tieferer Kopf, rechte Schulter.
    Die Zwischenhochs dazwischen bilden die Neckline.
    """

    name = "Inverse Head and Shoulders"

    def detect(self, candles: list[list[float]], timeframe: str | None = None) -> PatternSignal | None:
        closed = candles[:-1] if len(candles) > 2 else list(candles)
        lookback = config.SWING_LOOKBACK
        needed = config.IHNS_MAX_BARS * 2 + lookback * 2
        if len(closed) < needed:
            return None

        swings = _swing_lows(closed, lookback)
        structure = _find_structure(swings)
        if structure is None:
            return None

        left_idx, left_low, head_idx, head_low, right_idx, right_low = structure
        peak_left = _highest_high(closed, left_idx, head_idx)
        peak_right = _highest_high(closed, head_idx, right_idx)
        if peak_left is None or peak_right is None:
            return None

        peak1_idx, peak1 = peak_left
        peak2_idx, peak2 = peak_right
        if peak2_idx <= peak1_idx:
            return None
        if peak1 <= head_low or peak2 <= head_low:
            return None
        if peak1 <= left_low or peak2 <= right_low:
            return None

        slope = (peak2 - peak1) / (peak2_idx - peak1_idx)
        last_idx = len(closed) - 1
        neckline = peak2 + slope * (last_idx - peak2_idx)
        if neckline <= head_low:
            return None

        last_close = float(closed[-1][4])
        stop_loss = right_low * (1 - config.FAILED_BREAK_BUFFER)
        if neckline <= stop_loss:
            return None
        target = neckline + (neckline - head_low)
        fingerprint = (
            f"{int(closed[left_idx][0])}:{int(closed[head_idx][0])}:{int(closed[right_idx][0])}"
        )

        if last_close >= neckline * (1 + config.NECKLINE_BREAK_BUFFER):
            status = "CONFIRMED"
            detail = (
                f"Neckline gebrochen bei {last_close:.4f} "
                f"(Neckline {neckline:.4f}). "
                f"Schultern {left_low:.4f} / {right_low:.4f}, Kopf {head_low:.4f}."
            )
        elif last_close <= stop_loss:
            status = "FAILED"
            detail = (
                f"Unter die rechte Schulter gefallen "
                f"({last_close:.4f} <= Stop {stop_loss:.4f}). Setup ungültig."
            )
        else:
            status = "FORMING"
            detail = (
                f"Rechte Schulter bei {right_low:.4f}, Kopf {head_low:.4f}. "
                f"Neckline {neckline:.4f}, Schluss {last_close:.4f}."
            )

        return PatternSignal(
            status=status,
            fingerprint=fingerprint,
            detail=detail,
            neckline_price=float(neckline),
            stop_loss_price=float(stop_loss),
            target_price=float(target),
        )


def _find_structure(
    swings: list[tuple[int, float]],
) -> tuple[int, float, int, float, int, float] | None:
    """Jüngstes gültiges Triple (linke Schulter, Kopf, rechte Schulter)."""
    if len(swings) < 3:
        return None

    min_bars = config.IHNS_MIN_BARS
    max_bars = config.IHNS_MAX_BARS
    tolerance = config.IHNS_SHOULDER_TOLERANCE
    min_depth = config.IHNS_MIN_HEAD_DEPTH

    for right_pos in range(len(swings) - 1, 1, -1):
        right_idx, right_low = swings[right_pos]
        for head_pos in range(right_pos - 1, 0, -1):
            head_idx, head_low = swings[head_pos]
            gap_right = right_idx - head_idx
            if gap_right < min_bars:
                continue
            if gap_right > max_bars:
                break
            if head_low >= right_low:
                continue

            for left_pos in range(head_pos - 1, -1, -1):
                left_idx, left_low = swings[left_pos]
                gap_left = head_idx - left_idx
                if gap_left < min_bars:
                    continue
                if gap_left > max_bars:
                    break
                if head_low >= left_low:
                    continue

                mid = (left_low + right_low) / 2
                if mid <= 0:
                    continue
                if abs(left_low - right_low) / mid > tolerance:
                    continue

                shoulder_floor = min(left_low, right_low)
                if (shoulder_floor - head_low) / shoulder_floor < min_depth:
                    continue

                return left_idx, left_low, head_idx, head_low, right_idx, right_low
    return None


def _highest_high(
    candles: list[Candle],
    start: int,
    end: int,
) -> tuple[int, float] | None:
    """Höchstes High strikt zwischen zwei Tief-Indizes."""
    if end - start < 2:
        return None
    best_idx = start + 1
    best = float(candles[best_idx][2])
    for index in range(start + 1, end):
        high = float(candles[index][2])
        if high >= best:
            best = high
            best_idx = index
    return best_idx, best


def _swing_lows(candles: list[Candle], lookback: int) -> list[tuple[int, float]]:
    swings: list[tuple[int, float]] = []
    for index in range(lookback, len(candles) - lookback):
        low = float(candles[index][3])
        window = [float(candles[j][3]) for j in range(index - lookback, index + lookback + 1)]
        if low == min(window):
            swings.append((index, low))
    return swings
