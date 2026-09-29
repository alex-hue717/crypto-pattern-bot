# crypto-pattern-bot

Lokaler Bot, der Krypto-Charts auf Double Bottom, eine invertierte
Kopf-Schulter und einen engen Range-Ausbruch prüft. Der Status läuft
`FORMING` → `CONFIRMED` / `FAILED` und wird per Telegram gemeldet.

Marktdaten kommen über [CCXT](https://github.com/ccxt/ccxt) (standardmäßig Binance, nur lesen)
als Pandas-DataFrame. Es werden keine Orders gesendet.

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
└── patterns/
    ├── __init__.py
    ├── base_pattern.py   # Basisklasse für alle Muster
    ├── double_bottom.py  # Erstes Muster
    ├── ihns.py           # Inverse Head and Shoulders
    └── range_breakout.py # Enger Range-Ausbruch
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
```

Ohne Token läuft der Bot trotzdem: Alerts erscheinen dann nur in der Konsole.

## Neues Muster

Neue Datei unter `patterns/`, Klasse von `BasePattern` ableiten, `detect()` implementieren
und in `PATTERNS` in `main.py` einhängen.
