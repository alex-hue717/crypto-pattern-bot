"""Der Haupt-Loop (Steuerung)."""

from __future__ import annotations

import argparse
import logging
import time

import pandas as pd

import config
from data_fetcher import CryptoDataFetcher
from patterns.double_bottom import DoubleBottom
from patterns.ihns import InverseHeadAndShoulders
from patterns.range_breakout import RangeBreakout
from patterns.macro_range import MacroRange
from state_manager import StateManager
from telegram_bot import format_alert, send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("crypto-pattern-bot")

PATTERNS = [DoubleBottom(), InverseHeadAndShoulders(), RangeBreakout(), MacroRange()]


def candles_from_frame(frame: pd.DataFrame) -> list[list[float]]:
    """Wandelt das OHLCV-DataFrame in die Listenform der Mustererkennung."""
    if frame.empty:
        return []
    stamps = frame["timestamp"].astype("int64").to_numpy() // 1_000_000
    candles: list[list[float]] = []
    for index, row in enumerate(frame.itertuples(index=False)):
        candles.append(
            [
                int(stamps[index]),
                float(row.open),
                float(row.high),
                float(row.low),
                float(row.close),
                float(row.volume),
            ]
        )
    return candles


def _matching_active(
    state: StateManager,
    symbol: str,
    timeframe: str,
    pattern_name: str,
) -> list[dict]:
    return [
        row
        for row in state.get_active_patterns()
        if row["symbol"] == symbol
        and row["timeframe"] == timeframe
        and row["pattern_name"] == pattern_name
    ]


def _notify(symbol: str, pattern_name: str, status: str, detail: str, timeframe: str) -> None:
    text = format_alert(symbol, pattern_name, status, detail, timeframe)
    log.info("Alert:\n%s", text)
    send_message(text)


def run_once(fetcher: CryptoDataFetcher, state: StateManager) -> None:
    removed = state.cleanup_old_records()
    if removed:
        log.info("%s alte Muster entfernt", removed)

    for symbol in config.SYMBOLS:
        for timeframe in config.TIMEFRAMES:
            try:
                frame = fetcher.get_ohlcv(symbol, timeframe, limit=config.CANDLE_LIMIT)
            except Exception:
                log.exception("Marktdaten für %s %s fehlgeschlagen", symbol, timeframe)
                continue

            candles = candles_from_frame(frame)
            for pattern in PATTERNS:
                signal = pattern.detect(candles)
                if signal is None:
                    log.info("%s %s %s: kein Setup", symbol, timeframe, pattern.name)
                    continue
                if (
                    signal.neckline_price is None
                    or signal.stop_loss_price is None
                    or signal.target_price is None
                ):
                    log.info("%s %s ohne Preisniveaus, übersprungen", symbol, pattern.name)
                    continue

                active = _matching_active(state, symbol, timeframe, pattern.name)
                if signal.status == "FORMING":
                    if active or state.has_active_forming_pattern(
                        symbol, timeframe, pattern.name
                    ):
                        log.info("%s %s %s bleibt FORMING", symbol, timeframe, pattern.name)
                        continue
                    pattern_id = state.add_pattern(
                        symbol,
                        timeframe,
                        pattern.name,
                        signal.neckline_price,
                        signal.stop_loss_price,
                        signal.target_price,
                    )
                    log.info("FORMING gespeichert: id=%s", pattern_id)
                    _notify(symbol, pattern.name, signal.status, signal.detail, timeframe)
                    continue

                if not active:
                    log.info(
                        "%s %s %s ist %s, kein offenes FORMING",
                        symbol,
                        timeframe,
                        pattern.name,
                        signal.status,
                    )
                    continue

                for row in active:
                    if state.update_status(row["id"], signal.status):
                        log.info("Muster %s -> %s", row["id"], signal.status)
                        _notify(symbol, pattern.name, signal.status, signal.detail, timeframe)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto Pattern Bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Nur einen Durchlauf, dann beenden",
    )
    args = parser.parse_args()

    log.info(
        "Starte Bot | Börse=%s | TF=%s | Coins=%s",
        config.EXCHANGE,
        ", ".join(config.TIMEFRAMES),
        ", ".join(config.SYMBOLS),
    )
    fetcher = CryptoDataFetcher()
    state = StateManager(config.DB_PATH)
    try:
        if args.once:
            run_once(fetcher, state)
            return
        while True:
            run_once(fetcher, state)
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Bot gestoppt.")


if __name__ == "__main__":
    main()
