"""Der Haupt-Loop (Steuerung)."""

from __future__ import annotations

import argparse
import logging
import time

import pandas as pd

import config
from data_fetcher import CryptoDataFetcher
from patterns.double_bottom import DoubleBottom
from state_manager import StateManager
from telegram_bot import format_alert, send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("crypto-pattern-bot")

PATTERNS = [DoubleBottom()]


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


def should_notify(
    previous_status: str | None,
    previous_fingerprint: str | None,
    status: str,
    fingerprint: str,
) -> bool:
    if previous_status is None or previous_status != status:
        return True
    return previous_fingerprint != fingerprint and status == "FORMING"


def run_once(fetcher: CryptoDataFetcher, state: StateManager) -> None:
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
                pattern_key = f"{pattern.name} {timeframe}"
                if signal is None:
                    log.info("%s %s: kein Setup", symbol, pattern_key)
                    continue

                previous, _current = state.transition(
                    symbol=symbol,
                    pattern=pattern_key,
                    status=signal.status,
                    fingerprint=signal.fingerprint,
                    detail=signal.detail,
                )
                prev_status = previous.status if previous else None
                prev_fp = previous.fingerprint if previous else None
                if not should_notify(prev_status, prev_fp, signal.status, signal.fingerprint):
                    log.info("%s %s bleibt %s", symbol, pattern_key, signal.status)
                    continue

                text = format_alert(
                    symbol,
                    pattern.name,
                    signal.status,
                    signal.detail,
                    timeframe,
                )
                log.info("Alert:\n%s", text)
                send_message(text)


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
    finally:
        state.close()


if __name__ == "__main__":
    main()
