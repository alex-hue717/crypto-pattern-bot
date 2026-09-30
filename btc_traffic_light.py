"""BTC-Marktampel. Nur eine Warnung, sie blockiert keine Signale und keine Trades."""

from __future__ import annotations

import logging
import time

from data_fetcher import frame_from_yahoo_history
from strategy import ema

log = logging.getLogger(__name__)

DUMP_PCT = 3.0
CACHE_SECONDS = 15 * 60
_CACHE: tuple[float, dict] | None = None

STATUS_LABEL = {
    "GREEN": "🟢 GRÜN",
    "YELLOW": "🟡 GELB",
    "RED": "🔴 ROT",
    "UNKNOWN": "⚪ UNBEKANNT",
}


def get_btc_traffic_light(force: bool = False) -> dict:
    """Lädt BTC-USD und liefert Status, Preis, EMAs und den Anzeigetext.

    Das Ergebnis wird 15 Minuten gehalten, damit der Scanner Yahoo nicht bei
    jedem Durchlauf neu abfragt. Ein Fehler liefert ``UNKNOWN`` und wirft nicht.
    """
    global _CACHE
    cached_at = 0.0 if _CACHE is None else _CACHE[0]
    if not force and _CACHE is not None and time.monotonic() - cached_at < CACHE_SECONDS:
        return _CACHE[1]
    try:
        info = _load()
    except Exception as exc:
        log.warning("BTC-Ampel nicht verfügbar: %s", exc)
        info = _unknown(str(exc))
    _CACHE = (time.monotonic(), info)
    return info


def format_traffic_light(info: dict) -> str:
    """Zweistellige Kopfzeile für Log und Telegram."""
    price = info.get("price")
    price_text = f" (${price:,.0f})" if isinstance(price, (int, float)) else ""
    label = STATUS_LABEL.get(str(info.get("status")), STATUS_LABEL["UNKNOWN"])
    reason = info.get("reason") or "keine Angabe"
    return f"🚥 MARKT-AMPEL (BTC): {label}{price_text}\n└ {reason}"


def classify(
    price: float,
    ema20: float,
    ema50: float,
    ema200: float,
    change_12h: float | None,
) -> tuple[str, str]:
    """Ampellogik. ROT schlägt GELB und GRÜN."""
    dump = change_12h is not None and change_12h < -DUMP_PCT
    if price < ema200 or dump:
        parts = []
        if price < ema200:
            parts.append("BTC unter Daily EMA 200")
        if dump:
            parts.append(f"12h-Kursverlust {abs(change_12h):.1f} %")
        return "RED", "Warnung: " + " und ".join(parts)
    if price > ema200 and (price < ema20 or price < ema50 or ema20 < ema50):
        if price < ema20:
            detail = "BTC unter Daily EMA 20 (Momentum schwächelt)"
        elif price < ema50:
            detail = "BTC unter Daily EMA 50"
        else:
            detail = "EMA 20 unter EMA 50"
        return "YELLOW", f"Warnung: {detail}"
    if price > ema20 > ema50 > ema200 and not dump:
        return "GREEN", "BTC über EMA 20 > EMA 50 > EMA 200"
    return "YELLOW", "Warnung: kein klares Alignment"


def change_12h(closes: list[float]) -> float | None:
    """Veränderung über die letzten drei 4h-Kerzen, also 12 Stunden."""
    if len(closes) < 4 or closes[-4] <= 0:
        return None
    return (closes[-1] - closes[-4]) / closes[-4] * 100


def _load() -> dict:
    import yfinance as yf

    ticker = yf.Ticker("BTC-USD")
    daily = frame_from_yahoo_history(
        ticker.history(period="2y", interval="1d", auto_adjust=False),
        "",
    )
    hourly = frame_from_yahoo_history(
        ticker.history(period="14d", interval="1h", auto_adjust=False),
        "4h",
    )
    if len(daily) < 250:
        raise RuntimeError(f"nur {len(daily)} Tageskerzen, mindestens 250 nötig")
    closes = [float(value) for value in daily["close"]]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)
    if ema20 is None or ema50 is None or ema200 is None:
        raise RuntimeError("EMA konnte nicht berechnet werden")
    intraday = [float(value) for value in hourly["close"]] if len(hourly) else []
    price = intraday[-1] if intraday else closes[-1]
    move = change_12h(intraday)
    status, reason = classify(price, ema20, ema50, ema200, move)
    info = {
        "status": status,
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "change_12h_pct": move,
        "reason": reason,
    }
    info["text"] = format_traffic_light(info)
    return info


def _unknown(detail: str) -> dict:
    info = {
        "status": "UNKNOWN",
        "price": None,
        "ema20": None,
        "ema50": None,
        "ema200": None,
        "change_12h_pct": None,
        "reason": f"Ampel nicht verfügbar ({detail})",
    }
    info["text"] = format_traffic_light(info)
    return info
