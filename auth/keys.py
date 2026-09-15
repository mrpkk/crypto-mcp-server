"""API key store: `cms_`-prefixed keys, SHA-256 hashed at rest, SQLite-backed.

Keys are shown exactly once at creation; only hashes are stored.
The store also records per-key usage events (in-house metering, no SaaS).
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

KEY_PREFIX = "cms_"
VALID_TIERS = ("free", "pro", "enterprise")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash TEXT PRIMARY KEY,
    prefix TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    label TEXT DEFAULT '',
    created_at REAL NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL,
    tool TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage_events(key_hash, ts);
"""


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class APIKeyStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def create_key(self, tier: str = "free", label: str = "") -> str:
        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Use one of: {', '.join(VALID_TIERS)}")
        raw_key = KEY_PREFIX + secrets.token_urlsafe(24)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO api_keys (key_hash, prefix, tier, label, created_at, revoked) VALUES (?, ?, ?, ?, ?, 0)",
                (hash_key(raw_key), raw_key[:8], tier, label, time.time()),
            )
        return raw_key

    def verify(self, key: str) -> dict[str, Any] | None:
        """Return {'tier', 'prefix'} for a valid non-revoked key, else None."""
        if not key or not key.startswith(KEY_PREFIX):
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT tier, prefix, revoked FROM api_keys WHERE key_hash = ?",
                (hash_key(key),),
            ).fetchone()
        if row is None or row["revoked"]:
            return None
        return {"tier": row["tier"], "prefix": row["prefix"]}

    def revoke(self, key: str) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("UPDATE api_keys SET revoked = 1 WHERE key_hash = ?", (hash_key(key),))
        return cursor.rowcount > 0

    def record_usage(self, key: str, tool: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO usage_events (key_hash, tool, ts) VALUES (?, ?, ?)",
                (hash_key(key), tool, time.time()),
            )

    def usage_count(self, key: str, since: float | None = None) -> int:
        query = "SELECT COUNT(*) AS n FROM usage_events WHERE key_hash = ?"
        params: list[Any] = [hash_key(key)]
        if since is not None:
            query += " AND ts >= ?"
            params.append(since)
        with self._conn() as conn:
            return int(conn.execute(query, params).fetchone()["n"])

    def list_keys(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT prefix, tier, label, created_at, revoked FROM api_keys ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
