-- PAIEP memory schema v1 (M5) — SQLite (Profile A substitute). Mirrors ../postgres/0001_init.up.sql.
-- UUIDs and timestamps are TEXT (ISO-8601 UTC, fixed microsecond precision so they sort correctly).
-- `memory_vector` backs the dependency-free local vector index (vectors.backend: local).

CREATE TABLE memory_item (
    memory_id          TEXT PRIMARY KEY,
    type               TEXT NOT NULL CHECK (type IN
                         ('fact','preference','decision','entity','progress','task_summary','note')),
    scope              TEXT NOT NULL,
    content            TEXT NOT NULL,
    content_hash       TEXT NOT NULL,
    tags_json          TEXT NOT NULL DEFAULT '[]',
    source             TEXT,
    confidence         REAL NOT NULL DEFAULT 0.7 CHECK (confidence >= 0 AND confidence <= 1),
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN
                         ('active','archived','superseded','merged','expired')),
    superseded_by      TEXT REFERENCES memory_item(memory_id) ON DELETE SET NULL,
    vector_status      TEXT NOT NULL DEFAULT 'pending' CHECK (vector_status IN ('pending','synced')),
    reinforce_count    INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    last_reinforced_at TEXT NOT NULL,
    expires_at         TEXT
);
CREATE INDEX ix_memory_scope_status ON memory_item (scope, status);
CREATE INDEX ix_memory_hash ON memory_item (content_hash);
CREATE INDEX ix_memory_vector_status ON memory_item (vector_status);
CREATE INDEX ix_memory_expires ON memory_item (expires_at);

CREATE TABLE session (
    session_id        TEXT PRIMARY KEY,
    task_id           TEXT,
    scope             TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','expired')),
    summary_memory_id TEXT REFERENCES memory_item(memory_id) ON DELETE SET NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    expires_at        TEXT
);
CREATE INDEX ix_session_status ON session (status, expires_at);

CREATE TABLE session_turn (
    turn_id    TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    seq        INTEGER NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant','fact','system')),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (session_id, seq)
);

-- Local vector index (no Qdrant on Profile A). Brute-force cosine; fine for <~20k memories.
CREATE TABLE memory_vector (
    memory_id   TEXT PRIMARY KEY,
    scope       TEXT NOT NULL,
    vector_json TEXT NOT NULL
);
CREATE INDEX ix_memory_vector_scope ON memory_vector (scope);
