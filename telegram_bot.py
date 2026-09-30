"""Versendet formatierte Telegram-Nachrichten."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

import config

log = logging.getLogger(__name__)

STATUS_MARK = {
    "FORMING": "FORMING",
    "CONFIRMED": "CONFIRMED",
    "FAILED": "FAILED",
}


def format_alert(
    symbol: str,
    pattern: str,
    status: str,
    detail: str,
    timeframe: str,
    market_header: str | None = None,
) -> str:
    label = STATUS_MARK.get(status, status)
    lines = [
        f"<b>{pattern}</b> · {label}",
        f"<b>{symbol}</b> · {timeframe}",
        detail,
    ]
    if config.has_pattern_warning(symbol, pattern):
        lines.insert(
            0,
            "<b>⚠️ HINWEIS: Historisch erhöhtes Fehlausbruchs-Risiko "
            f"bei {pattern} auf {symbol}!</b>",
        )
    if market_header:
        lines.insert(0, market_header)
    return "\n".join(lines)


def send_message(text: str) -> bool:
    token = config.TELEGRAM_TOKEN.strip()
    chat_id = config.TELEGRAM_CHAT_ID.strip()
    if not token or not chat_id:
        log.warning("Telegram nicht konfiguriert. Nachricht nur lokal:\n%s", text)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        log.error("Telegram-Versand fehlgeschlagen: %s", exc)
        return False

    if not body.get("ok"):
        log.error("Telegram-Antwort: %s", body)
        return False
    return True
