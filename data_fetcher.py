"""Beschafft OHLCV-Marktdaten über ccxt."""

from __future__ import annotations

import logging

import ccxt
import pandas as pd

import config

log = logging.getLogger(__name__)

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class CryptoDataFetcher:
    """Holt Kerzendaten von einer ccxt-Börse und liefert sie als DataFrame.

    Es werden keine Orders gesendet. Die Börse kommt aus ``config.EXCHANGE``,
    sofern kein anderer ``exchange_id`` übergeben wird.
    """

    def __init__(self, exchange_id: str | None = None) -> None:
        self.exchange_id = (exchange_id or config.EXCHANGE).strip()
        self.exchange = self._create_exchange()

    def _create_exchange(self) -> ccxt.Exchange:
        """Erzeugt den ccxt-Client. Netzwerkfehler entstehen erst beim Abruf."""
        try:
            if not hasattr(ccxt, self.exchange_id):
                raise ValueError(f"Unbekannte Börse: {self.exchange_id}")
            exchange_cls = getattr(ccxt, self.exchange_id)
            return exchange_cls({"enableRateLimit": True})
        except Exception as exc:
            log.exception("Börse %s konnte nicht erstellt werden", self.exchange_id)
            raise RuntimeError(f"Börse {self.exchange_id} ist nicht verfügbar") from exc

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fragt aktuelle Kerzen ab.

        Args:
            symbol: Handelspaar im ccxt-Format, z. B. ``BTC/USDT``.
            timeframe: Kerzenintervall, z. B. ``15m`` oder ``1h``.
            limit: Anzahl Kerzen. Standard 100.

        Returns:
            DataFrame mit den Spalten
            ``timestamp``, ``open``, ``high``, ``low``, ``close``, ``volume``.
            ``timestamp`` ist timezone-aware UTC. Bei einem leeren Antwortsatz
            ist das DataFrame leer, hat aber dieselben Spalten.

        Raises:
            RuntimeError: Die Börse hat den Abruf abgelehnt oder nicht beantwortet.
            ValueError: ``limit`` ist kleiner als 1.
        """
        if limit < 1:
            raise ValueError(f"limit muss mindestens 1 sein, nicht {limit}")

        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except ccxt.BaseError as exc:
            log.error("OHLCV %s %s fehlgeschlagen: %s", symbol, timeframe, exc)
            raise RuntimeError(
                f"Kerzen für {symbol} {timeframe} konnten nicht geladen werden"
            ) from exc
        except Exception as exc:
            log.exception("Unerwarteter Fehler bei %s %s", symbol, timeframe)
            raise RuntimeError(
                f"Unerwarteter Fehler beim Laden von {symbol} {timeframe}"
            ) from exc

        frame = pd.DataFrame(raw, columns=OHLCV_COLUMNS)
        if frame.empty:
            return frame

        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        for column in ("open", "high", "low", "close", "volume"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame.dropna().reset_index(drop=True)
