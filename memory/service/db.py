"""Thin DB adapter over sqlite3 (stdlib) and psycopg 3 (Postgres).

Queries are written once with ``?`` placeholders and translated for psycopg.
Timestamps are timezone-aware UTC ``datetime`` objects in Python; SQLite stores
them as fixed-precision ISO-8601 text (sortable), Postgres as TIMESTAMPTZ.
"""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_TS_COLUMNS = {"created_at", "updated_at", "last_reinforced_at", "expires_at", "applied_at"}


def ts_to_text(d: datetime) -> str:
    return d.isoformat(timespec="microseconds")


sqlite3.register_adapter(datetime, ts_to_text)


class Database:
    """One connection; not shared across threads (the async worker opens its own)."""

    def __init__(self, backend: str, target: str):
        self.backend = backend
        self.target = target
        self._lock = threading.RLock()
        if backend == "sqlite":
            if target != ":memory:":
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(target, isolation_level=None, check_same_thread=False,
                                         timeout=30)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 30000")
            if target != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL")
        elif backend == "postgres":
            import psycopg  # lazy: SQLite-only installs don't need it
            from psycopg.rows import dict_row

            self._conn = psycopg.connect(target, autocommit=True, row_factory=dict_row,
                                         connect_timeout=10)
        else:
            raise ValueError(f"unknown backend {backend!r}")

    # --- helpers -----------------------------------------------------------
    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.backend == "postgres" else sql

    @staticmethod
    def _norm(row) -> dict:
        out = dict(row)
        for k, v in out.items():
            if v is None:
                continue
            if k in _TS_COLUMNS and isinstance(v, str):
                out[k] = datetime.fromisoformat(v)
            elif k.endswith("_id") and not isinstance(v, (str, int)):
                out[k] = str(v)  # psycopg returns uuid.UUID
        return out

    # --- API ---------------------------------------------------------------
    def execute(self, sql: str, params: tuple | list = ()) -> int:
        with self._lock:
            cur = self._conn.execute(self._sql(sql), tuple(params))
            return cur.rowcount

    def query(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(self._sql(sql), tuple(params))
            return [self._norm(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: tuple | list = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    @contextmanager
    def transaction(self) -> Iterator[Database]:
        with self._lock:
            if self.backend == "sqlite":
                self._conn.execute("BEGIN IMMEDIATE")
                try:
                    yield self
                except BaseException:
                    self._conn.execute("ROLLBACK")
                    raise
                self._conn.execute("COMMIT")
            else:
                with self._conn.transaction():
                    yield self

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# --- Migrations -------------------------------------------------------------

def _migration_files(backend: str) -> list[tuple[str, Path, Path]]:
    d = MIGRATIONS_DIR / backend
    out = []
    for up in sorted(d.glob("*.up.sql")):
        version = up.name.removesuffix(".up.sql")
        out.append((version, up, d / f"{version}.down.sql"))
    return out


def _ensure_ledger(db: Database) -> None:
    ts_type = "TIMESTAMPTZ" if db.backend == "postgres" else "TEXT"
    db.execute(f"CREATE TABLE IF NOT EXISTS schema_migrations "
               f"(version TEXT PRIMARY KEY, applied_at {ts_type} NOT NULL)")


def applied_versions(db: Database) -> list[str]:
    _ensure_ledger(db)
    return [r["version"] for r in db.query("SELECT version FROM schema_migrations ORDER BY version")]


def migrate_up(db: Database, now: datetime) -> list[str]:
    done = set(applied_versions(db))
    applied = []
    for version, up, _ in _migration_files(db.backend):
        if version in done:
            continue
        with db.transaction():
            for stmt in _split_sql(up.read_text(encoding="utf-8")):
                db.execute(stmt)
            db.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                       (version, now))
        applied.append(version)
    return applied


def migrate_down(db: Database, steps: int = 1) -> list[str]:
    files = {v: down for v, _, down in _migration_files(db.backend)}
    reverted = []
    for version in reversed(applied_versions(db)):
        if len(reverted) >= steps:
            break
        script = files[version].read_text(encoding="utf-8")
        with db.transaction():
            for stmt in _split_sql(script):
                db.execute(stmt)
            db.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
        reverted.append(version)
    return reverted


def _split_sql(script: str) -> list[str]:
    """Split into statements (no procedural blocks in migrations); one txn per file, both backends.

    ``executescript`` is avoided because SQLite's version commits implicitly.
    """
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
