"""Durable LangGraph checkpointers: task state survives restarts so approvals can resume later.

- postgres: isolated ``agents`` schema in the M5 Postgres (rollback: DROP SCHEMA agents CASCADE)
- sqlite:   file in the paiep_memory volume (Profile A)
- memory:   in-process only (tests)
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_SCHEMA = re.compile(r"^[a-z_][a-z0-9_]*$")


def resolve_backend(cfg, memory_backend: str | None) -> str:
    if cfg.checkpoint_backend != "auto":
        return cfg.checkpoint_backend
    return "postgres" if memory_backend == "postgres" else "sqlite"


def open_checkpointer(backend: str, *, dsn: str | None = None, schema: str = "agents",
                      sqlite_path: str = "/data/agents.db"):
    """Return (checkpointer, closer)."""
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver(), lambda: None
    if backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        return saver, conn.close
    if backend == "postgres":
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row

        if not _SCHEMA.match(schema):
            raise ValueError(f"invalid schema name {schema!r}")
        with psycopg.connect(dsn, autocommit=True) as boot:
            boot.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        conn = psycopg.connect(dsn, autocommit=True, prepare_threshold=0, row_factory=dict_row,
                               options=f"-c search_path={schema}")
        saver = PostgresSaver(conn)
        saver.setup()
        return saver, conn.close
    raise ValueError(f"unknown checkpoint backend {backend!r}")
