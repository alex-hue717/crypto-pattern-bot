"""Der Haupt-Loop (Steuerung)."""

from __future__ import annotations

import argparse
import logging
import time

import config
from data_fetcher import create_exchange, fetch_ohlcv
from patterns.double_bottom import DoubleBottom
from state_manager import StateManager
from telegram_bot import format_alert, send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("crypto-pattern-bot")

PATTERNS = [DoubleBottom()]


def should_notify(
    previous_status: str | None,
    previous_fingerprint: str | None,
    status: str,
    fingerprint: str,
) -> bool:
    if previous_status is None or previous_status != status:
        return True
    return previous_fingerprint != fingerprint and status == "FORMING"


def run_once(exchange, state: StateManager) -> None:
    for symbol in config.SYMBOLS:
        try:
            candles = fetch_ohlcv(exchange, symbol)
        except Exception:
            log.exception("Marktdaten für %s fehlgeschlagen", symbol)
            continue

        for pattern in PATTERNS:
            signal = pattern.detect(candles)
            if signal is None:
                log.info("%s %s: kein Setup", symbol, pattern.name)
                continue

            previous, _current = state.transition(
                symbol=symbol,
                pattern=pattern.name,
                status=signal.status,
                fingerprint=signal.fingerprint,
                detail=signal.detail,
            )
            prev_status = previous.status if previous else None
            prev_fp = previous.fingerprint if previous else None
            if not should_notify(prev_status, prev_fp, signal.status, signal.fingerprint):
                log.info("%s %s bleibt %s", symbol, pattern.name, signal.status)
                continue

            text = format_alert(
                symbol,
                pattern.name,
                signal.status,
                signal.detail,
                config.TIMEFRAME,
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
        config.TIMEFRAME,
        ", ".join(config.SYMBOLS),
    )
    exchange = create_exchange()
    state = StateManager(config.DB_PATH)
    try:
        if args.once:
            run_once(exchange, state)
            return
        while True:
            run_once(exchange, state)
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Bot gestoppt.")
    finally:
        state.close()


if __name__ == "__main__":
    main()
