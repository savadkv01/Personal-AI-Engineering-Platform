"""Retrieval: embed the query and search Qdrant with optional scope/tags filters."""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client import models as qm

from rag.ingest.embedder import embed_texts
from .config import QueryConfig


@dataclass
class RetrievedChunk:
    id: str
    score: float               # vector similarity (cosine)
    text: str
    source: str
    title: str
    scope: str
    tags: list[str]
    chunk_index: int
    rerank_score: float | None = None


def _build_filter(scope: str | None, tags: list[str] | None) -> qm.Filter | None:
    must: list = []
    if scope:
        must.append(qm.FieldCondition(key="scope", match=qm.MatchValue(value=scope)))
    if tags:
        must.append(qm.FieldCondition(key="tags", match=qm.MatchAny(any=tags)))
    return qm.Filter(must=must) if must else None


def retrieve(question: str, cfg: QueryConfig, *, collection: str | None = None,
             scope: str | None = None, tags: list[str] | None = None,
             limit: int | None = None) -> list[RetrievedChunk]:
    col = collection or cfg.retrieval.collection
    k = limit or (cfg.rerank.candidate_k if cfg.rerank.enabled else cfg.retrieval.top_k)

    vector = embed_texts([question], cfg.embed)[0]
    client = QdrantClient(url=cfg.qdrant_url, timeout=60)
    hits = client.search(
        collection_name=col,
        query_vector=vector,
        query_filter=_build_filter(scope, tags),
        limit=k,
        score_threshold=cfg.retrieval.score_threshold,
        with_payload=True,
    )
    out: list[RetrievedChunk] = []
    for h in hits:
        p = h.payload or {}
        out.append(RetrievedChunk(
            id=str(h.id), score=float(h.score), text=p.get("text", ""),
            source=p.get("source", "?"), title=p.get("title", p.get("source", "?")),
            scope=p.get("scope", ""), tags=p.get("tags", []) or [],
            chunk_index=int(p.get("chunk_index", 0)),
        ))
    return out
