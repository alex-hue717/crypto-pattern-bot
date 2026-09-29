# crypto-pattern-bot

Lokaler Bot, der Krypto-Charts auf Double Bottom, eine invertierte
Kopf-Schulter, einen engen Range-Ausbruch und eine Makro-Zone prüft. Der Status läuft
`FORMING` → `CONFIRMED` / `FAILED` und wird per Telegram gemeldet.

Marktdaten kommen über [CCXT](https://github.com/ccxt/ccxt) (standardmäßig Binance, nur lesen)
als Pandas-DataFrame. Es werden keine Orders gesendet. Range- und Makro-Ausbrüche
zählen erst als bestätigt, wenn das Volumen mindestens das 1,3-fache des
20-Kerzen-Schnitts erreicht. Schwache Makro-Tests unter 1h werden ignoriert.

## Ordnerstruktur

```text
crypto-pattern-bot/
├── .env                 # Tokens & Keys — NIEMALS committen (liegt nicht im Repo)
├── .env.example         # Vorlage für .env
├── .gitignore
├── requirements.txt
├── config.py            # Tokens aus .env, Coins, Timeframes
├── data_fetcher.py      # CryptoDataFetcher.get_ohlcv -> DataFrame
├── state_manager.py     # FORMING -> CONFIRMED / FAILED (SQLite, patterns.db)
├── telegram_bot.py      # Formatierte Telegram-Nachrichten
├── main.py               # Haupt-Loop
├── backtest.py           # Walk-Forward-Backtest, keine echten Orders
└── patterns/
    ├── __init__.py
    ├── base_pattern.py   # Basisklasse für alle Muster
    ├── double_bottom.py  # Erstes Muster
    ├── ihns.py           # Inverse Head and Shoulders
    ├── range_breakout.py # Enger Range-Ausbruch
    └── macro_range.py    # Makro-Zone über 200 Kerzen
```

`patterns.db` entsteht beim ersten Lauf und ist per `.gitignore` ausgeschlossen.

## Start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

In `.env` eintragen:

- `TELEGRAM_TOKEN` — von [@BotFather](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` — deine Chat-ID (z.B. über [@userinfobot](https://t.me/userinfobot))
- `EXCHANGE` — optional, Standard `binance`

Coins und Timeframes stehen in `config.py` (`SYMBOLS`, `TIMEFRAMES`).

```bash
python state_manager.py   # legt ein Test-Muster an und setzt es auf CONFIRMED
python main.py --once     # ein Durchlauf
python main.py            # Loop, Strg+C beendet
python backtest.py --symbol BTC/USDT --timeframe 1h --limit 1000
python backtest.py --ignore-warned
```

Der Backtest zieht je Trade 0,15 % Gebühr ab und zeigt danach die Ergebnisse je Muster.
`--ignore-warned` lässt zusätzlich als Hinweis markierte Kombinationen weg.
Muster aus `disabled_patterns` werden im Live-Bot und im Backtest immer übersprungen.

Im Dauerbetrieb schreibt der Bot nach `bot.log` und in die Konsole. Ein Fehler beendet ihn nicht: er wartet 60 Sekunden und scannt weiter.

Ohne Token läuft der Bot trotzdem: Alerts erscheinen dann nur in der Konsole.

## Geplanter Scan

`.github/workflows/scheduled_scan.yml` startet alle 4 Stunden (UTC) einen Durchlauf mit `python main.py --once`.
Dafür im Repository unter Settings → Secrets die Werte `TELEGRAM_TOKEN` und `TELEGRAM_CHAT_ID` anlegen.
Der Lauf hat keine gespeicherte `patterns.db`, deshalb kann ein FORMING-Hinweis beim nächsten Cron erneut kommen.

## Neues Muster

Neue Datei unter `patterns/`, Klasse von `BasePattern` ableiten, `detect()` implementieren
und in `PATTERNS` in `main.py` einhängen.
