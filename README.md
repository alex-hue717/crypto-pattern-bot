# crypto-pattern-bot

Lokaler Bot, der Krypto-Charts auf ein Double Bottom prüft und den Status
`FORMING` → `CONFIRMED` / `FAILED` per Telegram meldet.

Marktdaten kommen über [CCXT](https://github.com/ccxt/ccxt) (standardmäßig Binance, nur lesen).
Es werden keine Orders gesendet.

## Ordnerstruktur

```text
crypto-pattern-bot/
├── .env                 # Tokens & Keys — NIEMALS committen (liegt nicht im Repo)
├── .env.example         # Vorlage für .env
├── .gitignore
├── requirements.txt
├── config.py            # Coins, Timeframe, Schwellenwerte
├── data_fetcher.py      # Marktdaten via CCXT
├── state_manager.py     # FORMING -> CONFIRMED / FAILED (SQLite, lokal)
├── telegram_bot.py      # Formatierte Telegram-Nachrichten
├── main.py               # Haupt-Loop
└── patterns/
    ├── __init__.py
    ├── base_pattern.py   # Basisklasse für alle Muster
    └── double_bottom.py  # Erstes Muster
```

`data/state.db` entsteht beim ersten Lauf und ist per `.gitignore` ausgeschlossen.

## Start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

In `.env` eintragen:

- `TELEGRAM_BOT_TOKEN` — von [@BotFather](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` — deine Chat-ID (z.B. über [@userinfobot](https://t.me/userinfobot))
- `EXCHANGE` — optional, Standard `binance`

Coins, Timeframe und Schwellen stehen in `config.py`.

```bash
python main.py --once   # ein Durchlauf
python main.py          # Loop, Strg+C beendet
```

Ohne Token läuft der Bot trotzdem: Alerts erscheinen dann nur in der Konsole.

## Neues Muster

Neue Datei unter `patterns/`, Klasse von `BasePattern` ableiten, `detect()` implementieren
und in `PATTERNS` in `main.py` einhängen.
