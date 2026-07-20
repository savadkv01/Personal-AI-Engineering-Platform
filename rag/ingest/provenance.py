"""Provenance + idempotency helpers: checksums, stable IDs, payloads."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

# Fixed namespace so point IDs are stable across runs/machines.
_NS = uuid.UUID("6f6b1e2a-8b7a-4d3c-9e21-0a1b2c3d4e5f")


def file_checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def point_id(source: str, chunk_index: int) -> str:
    """Deterministic UUID for a (source, chunk) pair — re-ingest overwrites."""
    return str(uuid.uuid5(_NS, f"{source}::{chunk_index}"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_payload(*, scope: str, source: str, tags: list[str], doc_type: str,
                  chunk_index: int, checksum: str, title: str, text: str,
                  embed_model: str, embed_dim: int, ingested_at: str) -> dict:
    """Payload conventions (M2): scope/source/tags are the indexed filter fields."""
    return {
        "scope": scope,
        "source": source,
        "tags": tags,
        "doc_type": doc_type,
        "chunk_index": chunk_index,
        "checksum": checksum,
        "title": title,
        "text": text,
        "embed_model": embed_model,
        "embed_dim": embed_dim,
        "ingested_at": ingested_at,
    }
