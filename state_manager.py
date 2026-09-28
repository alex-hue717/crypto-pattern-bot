"""Verwaltet den Status (FORMING -> CONFIRMED / FAILED)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("FORMING", "CONFIRMED", "FAILED")


@dataclass
class PatternState:
    symbol: str
    pattern: str
    status: str
    fingerprint: str
    detail: str
    updated_at: str


class StateManager:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pattern_state (
                symbol TEXT NOT NULL,
                pattern TEXT NOT NULL,
                status TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                detail TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (symbol, pattern)
            )
            """
        )
        self._conn.commit()

    def get(self, symbol: str, pattern: str) -> PatternState | None:
        row = self._conn.execute(
            "SELECT * FROM pattern_state WHERE symbol = ? AND pattern = ?",
            (symbol, pattern),
        ).fetchone()
        if row is None:
            return None
        return PatternState(**dict(row))

    def transition(
        self,
        symbol: str,
        pattern: str,
        status: str,
        fingerprint: str,
        detail: str,
    ) -> tuple[PatternState | None, PatternState]:
        if status not in STATUSES:
            raise ValueError(f"Unbekannter Status: {status}")
        previous = self.get(symbol, pattern)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO pattern_state
                (symbol, pattern, status, fingerprint, detail, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, pattern) DO UPDATE SET
                status = excluded.status,
                fingerprint = excluded.fingerprint,
                detail = excluded.detail,
                updated_at = excluded.updated_at
            """,
            (symbol, pattern, status, fingerprint, detail, now),
        )
        self._conn.commit()
        current = self.get(symbol, pattern)
        if current is None:
            raise RuntimeError("Status konnte nicht gespeichert werden")
        return previous, current

    def close(self) -> None:
        self._conn.close()
