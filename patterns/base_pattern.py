"""Basisklasse für alle Muster."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

Candle = list[Any]


@dataclass(frozen=True)
class PatternSignal:
    status: str
    fingerprint: str
    detail: str
    neckline_price: float | None = None
    stop_loss_price: float | None = None
    target_price: float | None = None


class BasePattern(ABC):
    name: str

    @abstractmethod
    def detect(self, candles: list[Candle]) -> PatternSignal | None:
        """None, wenn gerade kein aktives Muster vorliegt."""
