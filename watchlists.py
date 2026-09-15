"""Watchlists & alert rules — SQLite persistence (in-house, no SaaS).

Two stores sharing one database file (same as API keys):
  watchlist: assets / wallets / protocols the user follows
  alert_rules: declarative rules evaluated against live tools on demand
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

WATCHLIST_KINDS = ("asset", "wallet", "protocol")
ALERT_KINDS = ("price_move", "gas_below", "whale_above")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at REAL NOT NULL,
    UNIQUE(kind, value)
);
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    params TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
"""


class WatchlistStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, kind: str, value: str, label: str = "") -> int:
        if kind not in WATCHLIST_KINDS:
            raise ValueError(f"Invalid kind: {kind}. Use one of: {', '.join(WATCHLIST_KINDS)}")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO watchlist (kind, value, label, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(kind, value) DO UPDATE SET label = excluded.label",
                (kind, value, label, time.time()),
            )
            row = conn.execute(
                "SELECT id FROM watchlist WHERE kind = ? AND value = ?", (kind, value)
            ).fetchone()
        return int(row["id"])

    def remove(self, item_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
        return cursor.rowcount > 0

    def list(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT id, kind, value, label, created_at FROM watchlist ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def add_rule(self, kind: str, params: dict[str, Any]) -> int:
        if kind not in ALERT_KINDS:
            raise ValueError(f"Invalid alert kind: {kind}. Use one of: {', '.join(ALERT_KINDS)}")
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO alert_rules (kind, params, enabled, created_at) VALUES (?, ?, 1, ?)",
                (kind, json.dumps(params), time.time()),
            )
        return int(cursor.lastrowid)

    def remove_rule(self, rule_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        return cursor.rowcount > 0

    def list_rules(self, enabled_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT id, kind, params, enabled, created_at FROM alert_rules"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY id"
        with self._conn() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "params": json.loads(row["params"]),
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
