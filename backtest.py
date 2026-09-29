"""Walk-Forward-Backtest der registrierten Chartmuster.

Es werden keine echten Orders gesendet. Jeder bestätigte Ausbruch öffnet
einen virtuellen Long-Trade zum Schlusskurs, mit Ziel und Stop aus dem Signal.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

import config
from data_fetcher import CryptoDataFetcher
from main import PATTERNS, candles_from_frame
from patterns.base_pattern import BasePattern

START_INDEX = 100
START_EQUITY = 10_000.0
FEE_PCT = 0.0015


@dataclass
class Trade:
    symbol: str
    timeframe: str
    pattern: str
    entry: float
    exit: float
    pnl_pct: float
    reason: str


@dataclass
class PatternStats:
    name: str
    trades: int
    win_rate: float
    net_pct: float


@dataclass
class BacktestReport:
    symbol: str
    timeframe: str
    candles: int
    trades: list[Trade]

    @property
    def count(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for trade in self.trades if trade.pnl_pct > 0)

    @property
    def losses(self) -> int:
        return self.count - self.wins

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return 100.0 * self.wins / self.count

    def equity_curve(self) -> list[float]:
        equity = START_EQUITY
        curve = [equity]
        for trade in self.trades:
            equity *= 1 + trade.pnl_pct
            curve.append(equity)
        return curve

    @property
    def total_return_pct(self) -> float:
        end = self.equity_curve()[-1]
        return (end / START_EQUITY - 1) * 100

    @property
    def max_drawdown_pct(self) -> float:
        peak = START_EQUITY
        worst = 0.0
        for equity in self.equity_curve():
            peak = max(peak, equity)
            if peak > 0:
                worst = max(worst, (peak - equity) / peak)
        return worst * 100

    @property
    def profit_factor(self) -> float | None:
        gross_win = 0.0
        gross_loss = 0.0
        equity = START_EQUITY
        for trade in self.trades:
            pnl = equity * trade.pnl_pct
            if pnl > 0:
                gross_win += pnl
            elif pnl < 0:
                gross_loss += -pnl
            equity += pnl
        if gross_loss == 0:
            return None if gross_win == 0 else float("inf")
        return gross_win / gross_loss

    def pattern_breakdown(self) -> list[PatternStats]:
        """Trades, Win-Rate und Netto-Prozent je Mustername."""
        names = [pattern.name for pattern in PATTERNS]
        for trade in self.trades:
            if trade.pattern not in names:
                names.append(trade.pattern)
        rows: list[PatternStats] = []
        for name in names:
            group = [trade for trade in self.trades if trade.pattern == name]
            count = len(group)
            wins = sum(1 for trade in group if trade.pnl_pct > 0)
            win_rate = 100.0 * wins / count if count else 0.0
            net_pct = sum(trade.pnl_pct for trade in group) * 100
            rows.append(PatternStats(name=name, trades=count, win_rate=win_rate, net_pct=net_pct))
        return rows


def _as_closed(candles: list[list[float]], index: int) -> list[list[float]]:
    """Kerze ``index`` ist geschlossen. Die letzte Liste ist nur der Platzhalter."""
    history = [row[:] for row in candles[: index + 1]]
    history.append(history[-1][:])
    return history


def _manage_trade(
    candles: list[list[float]],
    entry_index: int,
    stop: float,
    target: float,
) -> tuple[float, str, int]:
    """Folgt dem Trade, bis Take-Profit oder Stop-Loss fällt.

    Liegen beide in derselben Kerze, zählt der Stop. Ein Trade ohne Treffer
    wird zum letzten verfügbaren Schluss geschlossen.
    """
    for index in range(entry_index + 1, len(candles)):
        high = float(candles[index][2])
        low = float(candles[index][3])
        hit_stop = low <= stop
        hit_target = high >= target
        if hit_stop and hit_target:
            return stop, "SL", index
        if hit_stop:
            return stop, "SL", index
        if hit_target:
            return target, "TP", index
    last = len(candles) - 1
    return float(candles[last][4]), "Schluss", last


def run_backtest(
    candles: list[list[float]],
    patterns: list[BasePattern],
    symbol: str,
    timeframe: str,
    ignore_warned: bool = False,
) -> BacktestReport:
    """Geht von Kerze 100 bis zum Ende und handelt bestätigte Signale nacheinander."""
    trades: list[Trade] = []
    index = START_INDEX
    last_entry = len(candles) - 1
    while index < last_entry:
        view = _as_closed(candles, index)
        opened = False
        for pattern in patterns:
            if config.is_pattern_disabled(symbol, pattern.name):
                continue
            signal = pattern.detect(view, timeframe)
            if signal is None or signal.status != "CONFIRMED":
                continue
            if ignore_warned and config.has_pattern_warning(symbol, pattern.name):
                continue
            if signal.stop_loss_price is None or signal.target_price is None:
                continue
            entry = float(candles[index][4])
            stop = float(signal.stop_loss_price)
            target = float(signal.target_price)
            if not (stop < entry < target):
                continue
            exit_price, reason, exit_index = _manage_trade(
                candles, index, stop, target
            )
            trades.append(
                Trade(
                    symbol=symbol,
                    timeframe=timeframe,
                    pattern=pattern.name,
                    entry=entry,
                    exit=exit_price,
                    pnl_pct=((exit_price - entry) / entry) - FEE_PCT,
                    reason=reason,
                )
            )
            index = exit_index
            opened = True
            break
        if not opened:
            index += 1
    return BacktestReport(
        symbol=symbol,
        timeframe=timeframe,
        candles=len(candles),
        trades=trades,
    )


def _format_profit_factor(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == float("inf"):
        return "unendlich (keine Verluste)"
    return f"{value:.2f}"


def print_report(report: BacktestReport) -> None:
    open_until_end = sum(1 for trade in report.trades if trade.reason == "Schluss")
    names = ", ".join(pattern.name for pattern in PATTERNS)
    print()
    print(f"{report.symbol} {report.timeframe} | Kerzen {report.candles}")
    print(f"Muster: {names}")
    print(f"Anzahl Gesamt-Trades: {report.count}")
    print(f"Win-Rate: {report.win_rate:.2f} %")
    print(f"Profit-Factor: {_format_profit_factor(report.profit_factor)}")
    print(f"Gesamt-Rendite: {report.total_return_pct:.2f} %")
    print(f"Max Drawdown: {report.max_drawdown_pct:.2f} %")
    if open_until_end:
        print(f"Davon zum letzten Kurs geschlossen: {open_until_end}")
    if report.count == 0:
        print("Kein bestätigtes Signal im Zeitraum.")
    print()
    print(f"{'Muster':<30} {'Trades':>6} {'Win-Rate':>10} {'Gewinn/Verlust':>16}")
    for row in report.pattern_breakdown():
        print(
            f"{row.name:<30} {row.trades:>6} {row.win_rate:>9.2f} % {row.net_pct:>+14.2f} %"
        )


def load_candles(fetcher: CryptoDataFetcher, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
    frame = fetcher.get_ohlcv_history(symbol, timeframe, limit=limit)
    if not isinstance(frame, pd.DataFrame):
        raise RuntimeError(f"Unerwartete Daten für {symbol} {timeframe}")
    return candles_from_frame(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-Forward-Backtest")
    parser.add_argument("--symbol", action="append", help="z. B. BTC/USDT, mehrfach möglich")
    parser.add_argument("--timeframe", action="append", help="z. B. 1h, mehrfach möglich")
    parser.add_argument("--limit", type=int, default=1000, help="Anzahl historischer Kerzen")
    parser.add_argument(
        "--ignore-warned",
        action="store_true",
        help="Überspringt Coin/Muster-Kombinationen aus COIN_PATTERN_RULES",
    )
    args = parser.parse_args()

    symbols = args.symbol or list(config.SYMBOLS)
    timeframes = args.timeframe or list(config.TIMEFRAMES)
    if args.limit < START_INDEX + 2:
        raise SystemExit(f"--limit muss mindestens {START_INDEX + 2} sein")

    fetcher = CryptoDataFetcher()
    warned = "Warn-Muster aus" if args.ignore_warned else "Warn-Muster an"
    print(
        "Backtest | Börse "
        f"{config.EXCHANGE} | Limit {args.limit} | {warned} | "
        "eine Position, volles Kapital, ohne Hebel, Gebühr 0,15 % je Trade"
    )
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                candles = load_candles(fetcher, symbol, timeframe, args.limit)
            except Exception as exc:
                print()
                print(f"{symbol} {timeframe}: Daten fehlgeschlagen ({exc})")
                continue
            if len(candles) <= START_INDEX:
                print()
                print(f"{symbol} {timeframe}: nur {len(candles)} Kerzen, zu wenig für den Start bei {START_INDEX}")
                continue
            report = run_backtest(
                candles, PATTERNS, symbol, timeframe, ignore_warned=args.ignore_warned
            )
            print_report(report)


if __name__ == "__main__":
    main()
