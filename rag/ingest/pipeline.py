"""Ingestion orchestration: load -> chunk -> embed -> idempotent upsert.

Idempotency: each source file's chunks get deterministic point IDs
(``uuid5(source, chunk_index)``) and carry a ``checksum`` payload. On re-run, a
file whose checksum is unchanged is skipped; a changed file has its old points
deleted (by ``source`` filter) before fresh chunks are upserted, so shrinking
files never leave orphans.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client import models as qm

from .chunking import chunk_text
from .config import Config, load_config
from .embedder import embed_texts
from .loaders import iter_files, load_document
from .provenance import build_payload, file_checksum, now_iso, point_id


@dataclass
class Stats:
    files_seen: int = 0
    files_ingested: int = 0
    files_skipped: int = 0
    files_unrouted: int = 0
    chunks_upserted: int = 0
    per_collection: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_ingested": self.files_ingested,
            "files_skipped": self.files_skipped,
            "files_unrouted": self.files_unrouted,
            "chunks_upserted": self.chunks_upserted,
            "per_collection": self.per_collection,
        }


def _source_rel(path: str, source_root: str) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), source_root).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")


def _existing_checksum(client: QdrantClient, collection: str, source: str) -> str | None:
    flt = qm.Filter(must=[qm.FieldCondition(key="source", match=qm.MatchValue(value=source))])
    points, _ = client.scroll(collection_name=collection, scroll_filter=flt,
                              limit=1, with_payload=True, with_vectors=False)
    if points:
        return (points[0].payload or {}).get("checksum")
    return None


def _delete_source(client: QdrantClient, collection: str, source: str) -> None:
    flt = qm.Filter(must=[qm.FieldCondition(key="source", match=qm.MatchValue(value=source))])
    client.delete(collection_name=collection, points_selector=qm.FilterSelector(filter=flt), wait=True)


def run(paths: list[str], *, scope: str = "global", tags: list[str] | None = None,
        collection_override: str | None = None, force: bool = False,
        dry_run: bool = False, source_root: str | None = None,
        config: Config | None = None, log=print) -> Stats:
    cfg = config or load_config()
    tags = tags or []
    source_root = source_root or os.environ.get("INGEST_SOURCE_ROOT") or os.getcwd()

    client = QdrantClient(url=cfg.qdrant_url, timeout=60)

    # Guard the re-embed risk: every target collection must exist with a dim
    # that matches the embedding model (M2 catalog / ADR 0009).
    targets = {collection_override} if collection_override else {
        r.collection for r in cfg.routing}
    for col in targets:
        if col is None:
            continue
        if not client.collection_exists(col):
            raise SystemExit(f"collection '{col}' missing — run scripts/qdrant-init.sh (M2) first")
        info = client.get_collection(col)
        dim = info.config.params.vectors.size
        if dim != cfg.service.dim:
            raise SystemExit(
                f"dim mismatch: collection '{col}' is {dim} but embed dim is "
                f"{cfg.service.dim} (model={cfg.service.model})")

    stats = Stats()
    for path in iter_files(paths, cfg.exclude_dirs, cfg.exclude_names):
        stats.files_seen += 1
        rule = cfg.route(path)
        if rule is None and collection_override is None:
            stats.files_unrouted += 1
            log(f"  ? {path}: no routing rule (skipped)")
            continue

        collection = collection_override or rule.collection
        doc_type = (rule.doc_type if rule else "note")
        source = _source_rel(path, source_root)
        checksum = file_checksum(path)

        if not force:
            prev = _existing_checksum(client, collection, source)
            if prev == checksum:
                stats.files_skipped += 1
                log(f"  = {source}: unchanged (skip)")
                continue

        doc = load_document(path)
        size, overlap = cfg.chunk_params(doc_type)
        chunks = chunk_text(doc.text, size, overlap)
        if not chunks:
            log(f"  ! {source}: no text extracted (skip)")
            continue

        doc_scope = scope
        doc_tags = sorted({*tags, *doc.tags})
        ts = now_iso()

        if dry_run:
            log(f"  ~ {source}: would upsert {len(chunks)} chunk(s) -> {collection}")
            stats.files_ingested += 1
            stats.chunks_upserted += len(chunks)
            stats.per_collection[collection] = stats.per_collection.get(collection, 0) + len(chunks)
            continue

        vectors = embed_texts(chunks, cfg.service)
        points = [
            qm.PointStruct(
                id=point_id(source, idx),
                vector=vec,
                payload=build_payload(
                    scope=doc_scope, source=source, tags=doc_tags, doc_type=doc_type,
                    chunk_index=idx, checksum=checksum, title=doc.title, text=chunk,
                    embed_model=cfg.service.model, embed_dim=cfg.service.dim, ingested_at=ts),
            )
            for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]

        # Replace prior points for this source (handles edits/shrink), then upsert.
        _delete_source(client, collection, source)
        client.upsert(collection_name=collection, points=points, wait=True)

        stats.files_ingested += 1
        stats.chunks_upserted += len(points)
        stats.per_collection[collection] = stats.per_collection.get(collection, 0) + len(points)
        log(f"  + {source}: {len(points)} chunk(s) -> {collection} (type={doc_type})")

    return stats
