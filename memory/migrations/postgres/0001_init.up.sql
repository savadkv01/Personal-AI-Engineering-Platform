-- PAIEP memory schema v1 (M5) — PostgreSQL. Mirrors ../sqlite/0001_init.up.sql.
-- Postgres is the canonical, user-editable source of truth; Qdrant `memory_semantic`
-- holds one vector per ACTIVE item (point id = memory_id). `vector_status` is the
-- outbox flag the async worker uses to keep the two stores consistent.

CREATE TABLE memory_item (
    memory_id          UUID PRIMARY KEY,
    type               TEXT NOT NULL CHECK (type IN
                         ('fact','preference','decision','entity','progress','task_summary','note')),
    scope              TEXT NOT NULL,                 -- 'global' | 'project:<name>' (FR-012)
    content            TEXT NOT NULL,
    content_hash       TEXT NOT NULL,                 -- sha256 of normalized content (exact dedup)
    tags_json          TEXT NOT NULL DEFAULT '[]',
    source             TEXT,                          -- provenance: 'user' | 'session:<id>' | uri
    confidence         REAL NOT NULL DEFAULT 0.7 CHECK (confidence >= 0 AND confidence <= 1),
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN
                         ('active','archived','superseded','merged','expired')),
    superseded_by      UUID REFERENCES memory_item(memory_id) ON DELETE SET NULL,
    vector_status      TEXT NOT NULL DEFAULT 'pending' CHECK (vector_status IN ('pending','synced')),
    reinforce_count    INTEGER NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL,
    updated_at         TIMESTAMPTZ NOT NULL,
    last_reinforced_at TIMESTAMPTZ NOT NULL,
    expires_at         TIMESTAMPTZ
);
CREATE INDEX ix_memory_scope_status ON memory_item (scope, status);
CREATE INDEX ix_memory_hash ON memory_item (content_hash);
CREATE INDEX ix_memory_vector_status ON memory_item (vector_status);
CREATE INDEX ix_memory_expires ON memory_item (expires_at);

CREATE TABLE session (
    session_id        UUID PRIMARY KEY,
    task_id           TEXT,
    scope             TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','expired')),
    summary_memory_id UUID REFERENCES memory_item(memory_id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    expires_at        TIMESTAMPTZ
);
CREATE INDEX ix_session_status ON session (status, expires_at);

CREATE TABLE session_turn (
    turn_id    UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    seq        INTEGER NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant','fact','system')),
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (session_id, seq)
);
