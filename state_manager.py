"""Lokales Gedächtnis des Bots.

Verwaltet den Lebenszyklus von Chart-Mustern: FORMING -> CONFIRMED oder FAILED.
Die Daten liegen in einer SQLite-Datei ``patterns.db``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar

FORMING = "FORMING"
CONFIRMED = "CONFIRMED"
FAILED = "FAILED"
TERMINAL_STATUSES = (CONFIRMED, FAILED)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    status TEXT NOT NULL,
    neckline_price REAL NOT NULL,
    stop_loss_price REAL NOT NULL,
    target_price REAL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

T = TypeVar("T")


def _utc_stamp(moment: datetime | None = None) -> str:
    """UTC-Zeitstempel, lexikografisch sortierbar."""
    current = moment or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class StateManager:
    """Speichert Muster in SQLite. Jede Methode öffnet eine eigene Verbindung."""

    def __init__(self, db_path: str | Path = "patterns.db") -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent not in (Path("."), Path("")):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _run(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        """Transaktion per Context Manager, Verbindung wird danach geschlossen."""
        connection: sqlite3.Connection | None = None
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.row_factory = sqlite3.Row
                return operation(connection)
        finally:
            if connection is not None:
                connection.close()

    def _init_db(self) -> None:
        self._run(lambda connection: connection.execute(_CREATE_TABLE))

    def has_active_forming_pattern(
        self,
        symbol: str,
        timeframe: str,
        pattern_name: str,
        cooldown_hours: int = 2,
    ) -> bool:
        """True, wenn ein FORMING-Muster jünger als ``cooldown_hours`` existiert."""
        cutoff = _utc_stamp(datetime.now(timezone.utc) - timedelta(hours=cooldown_hours))

        def query(connection: sqlite3.Connection) -> sqlite3.Row | None:
            return connection.execute(
                """
                SELECT 1
                FROM patterns
                WHERE symbol = ?
                  AND timeframe = ?
                  AND pattern_name = ?
                  AND status = ?
                  AND created_at >= ?
                LIMIT 1
                """,
                (symbol, timeframe, pattern_name, FORMING, cutoff),
            ).fetchone()

        return self._run(query) is not None

    def add_pattern(
        self,
        symbol: str,
        timeframe: str,
        pattern_name: str,
        neckline_price: float,
        stop_loss_price: float,
        target_price: float,
    ) -> int:
        """Legt ein Muster mit Status FORMING an und gibt die neue ID zurück."""
        now = _utc_stamp()

        def insert(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(
                """
                INSERT INTO patterns (
                    symbol, timeframe, pattern_name, status,
                    neckline_price, stop_loss_price, target_price,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    timeframe,
                    pattern_name,
                    FORMING,
                    float(neckline_price),
                    float(stop_loss_price),
                    float(target_price),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

        return self._run(insert)

    def get_active_patterns(self) -> list[dict]:
        """Alle Muster mit Status FORMING, als Dictionaries."""

        def query(connection: sqlite3.Connection) -> list[dict]:
            rows = connection.execute(
                """
                SELECT *
                FROM patterns
                WHERE status = ?
                ORDER BY created_at ASC, id ASC
                """,
                (FORMING,),
            ).fetchall()
            return [dict(row) for row in rows]

        return self._run(query)

    def update_status(self, pattern_id: int, new_status: str) -> bool:
        """Setzt den Status auf CONFIRMED oder FAILED und aktualisiert ``updated_at``."""
        if new_status not in TERMINAL_STATUSES:
            raise ValueError("new_status muss CONFIRMED oder FAILED sein")
        now = _utc_stamp()

        def update(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(
                """
                UPDATE patterns
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_status, now, pattern_id),
            )
            return cursor.rowcount > 0

        return self._run(update)

    def cleanup_old_records(self, days: int = 7) -> int:
        """Löscht CONFIRMED- und FAILED-Muster, deren ``updated_at`` älter als ``days`` ist."""
        cutoff = _utc_stamp(datetime.now(timezone.utc) - timedelta(days=days))

        def delete(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(
                """
                DELETE FROM patterns
                WHERE status IN (?, ?)
                  AND updated_at < ?
                """,
                (CONFIRMED, FAILED, cutoff),
            )
            return int(cursor.rowcount)

        return self._run(delete)


if __name__ == "__main__":
    import tempfile

    demo_dir = Path(tempfile.mkdtemp(prefix="pattern-state-"))
    manager = StateManager(demo_dir / "patterns.db")

    pattern_id = manager.add_pattern(
        symbol="BTC/USDT",
        timeframe="15m",
        pattern_name="Double Bottom",
        neckline_price=65000.0,
        stop_loss_price=62000.0,
        target_price=68000.0,
    )
    print(f"angelegt: id={pattern_id}")
    print("aktiv davor:", manager.get_active_patterns())
    print(
        "Spam-Schutz:",
        manager.has_active_forming_pattern("BTC/USDT", "15m", "Double Bottom"),
    )

    updated = manager.update_status(pattern_id, CONFIRMED)
    print(f"Status auf CONFIRMED gesetzt: {updated}")
    print("aktiv danach:", manager.get_active_patterns())

    with sqlite3.connect(manager.db_path) as check:
        check.row_factory = sqlite3.Row
        stored = dict(
            check.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,)).fetchone()
        )
    check.close()
    print("gespeichert:", stored)
