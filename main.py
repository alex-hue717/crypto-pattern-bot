"""Der Haupt-Loop (Steuerung)."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd

import config
import strategy
from btc_traffic_light import get_btc_traffic_light
from data_fetcher import CryptoDataFetcher
from patterns.double_bottom import DoubleBottom
from patterns.ihns import InverseHeadAndShoulders
from patterns.range_breakout import RangeBreakout
from patterns.macro_range import MacroRange
from state_manager import StateManager
from telegram_bot import format_alert, send_message

log = logging.getLogger("crypto-pattern-bot")


def setup_logging() -> None:
    """Schreibt jedes Log in die Konsole und nach bot.log."""
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    log_path = str(Path(__file__).resolve().parent / "bot.log")
    has_console = any(type(handler) is logging.StreamHandler for handler in root.handlers)
    has_file = any(getattr(handler, "baseFilename", "") == log_path for handler in root.handlers)
    if not has_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    if not has_file:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


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


def _notify(
    symbol: str,
    pattern_name: str,
    status: str,
    detail: str,
    timeframe: str,
    market_header: str = "",
) -> None:
    text = format_alert(symbol, pattern_name, status, detail, timeframe, market_header or None)
    delivered = send_message(text)
    if delivered:
        log.info("Telegram gesendet: %s %s %s %s", symbol, timeframe, pattern_name, status)
    else:
        log.info("Telegram nicht zugestellt: %s %s %s %s", symbol, timeframe, pattern_name, status)


def _scan_patterns(
    state: StateManager,
    symbol: str,
    timeframe: str,
    candles: list[list[float]],
    patterns: list,
    market_header: str = "",
) -> None:
    for pattern in patterns:
        if pattern.name == "Double Bottom" and not config.double_bottom_allowed(symbol, timeframe):
            continue
        if config.is_pattern_disabled(symbol, pattern.name):
            continue
        signal = pattern.detect(candles, timeframe)
        if signal is None:
            log.info("%s %s %s: kein Setup", symbol, timeframe, pattern.name)
            continue
        log.info("Signal %s: %s %s %s\n%s", signal.status, symbol, timeframe, pattern.name, market_header)
        if (
            signal.neckline_price is None
            or signal.stop_loss_price is None
            or signal.target_price is None
        ):
            log.info("%s %s ohne Preisniveaus, übersprungen", symbol, pattern.name)
            continue
        reason = strategy.rejection_reason(
            candles,
            timeframe,
            signal.stop_loss_price,
            signal.target_price,
            pattern.name,
        )
        if reason is not None:
            log.info(
                "%s %s %s verworfen: %s",
                symbol,
                timeframe,
                pattern.name,
                reason,
            )
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
            _notify(symbol, pattern.name, signal.status, signal.detail, timeframe, market_header)
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
                _notify(symbol, pattern.name, signal.status, signal.detail, timeframe, market_header)


def run_once(fetcher: CryptoDataFetcher, state: StateManager) -> None:
    log.info("Scan gestartet")
    removed = state.cleanup_old_records()
    if removed:
        log.info("%s alte Muster entfernt", removed)

    light = get_btc_traffic_light()
    market_header = str(light["text"])
    log.info("%s", market_header)

    regular = [pattern for pattern in PATTERNS if pattern.name != "Double Bottom"]
    double_bottom = [pattern for pattern in PATTERNS if pattern.name == "Double Bottom"]
    higher_timeframe = config.DOUBLE_BOTTOM_TIMEFRAME

    for symbol in config.SYMBOLS:
        for timeframe in config.TIMEFRAMES:
            try:
                frame = fetcher.get_ohlcv(symbol, timeframe, limit=config.CANDLE_LIMIT)
            except Exception:
                log.exception("Marktdaten für %s %s fehlgeschlagen", symbol, timeframe)
                continue
            _scan_patterns(state, symbol, timeframe, candles_from_frame(frame), regular, market_header)

        if not config.double_bottom_allowed(symbol, higher_timeframe):
            continue
        try:
            frame = fetcher.get_double_bottom_ohlcv(
                symbol,
                higher_timeframe,
                limit=config.CANDLE_LIMIT,
            )
        except Exception:
            log.exception("Double-Bottom-Daten für %s %s fehlgeschlagen", symbol, higher_timeframe)
            continue
        _scan_patterns(
            state,
            symbol,
            higher_timeframe,
            candles_from_frame(frame),
            double_bottom,
            market_header,
        )


def run_forever(fetcher: CryptoDataFetcher, state: StateManager, sleep=time.sleep) -> None:
    """Scannt dauerhaft. Ein Fehler beendet den Bot nicht."""
    while True:
        try:
            run_once(fetcher, state)
        except Exception as exc:
            log.error("Scan fehlgeschlagen: %s", exc)
            sleep(60)
            continue
        sleep(config.POLL_INTERVAL_SECONDS)


def main() -> None:
    setup_logging()
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
        run_forever(fetcher, state)
    except KeyboardInterrupt:
        log.info("Bot gestoppt.")


if __name__ == "__main__":
    main()
