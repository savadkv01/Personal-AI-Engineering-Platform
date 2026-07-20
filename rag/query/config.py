"""Config for the query path. Loads ``config/rag.yaml`` and inherits the
embedding service + Qdrant URL from the M3 ingestion config so the query
embedding model always matches what was indexed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from rag.ingest.config import ServiceConfig, load_config as load_ingest_config


@dataclass
class RetrievalConfig:
    collection: str
    top_k: int
    score_threshold: float


@dataclass
class RerankConfig:
    enabled: bool
    method: str
    candidate_k: int
    lexical_weight: float


@dataclass
class ContextConfig:
    max_context_chars: int
    per_chunk_char_cap: int
    cite: bool


@dataclass
class GenerationConfig:
    provider: str
    base_url: str
    model: str
    temperature: float
    num_ctx: int
    max_tokens: int
    request_timeout: int


@dataclass
class QueryConfig:
    retrieval: RetrievalConfig
    rerank: RerankConfig
    context: ContextConfig
    generation: GenerationConfig
    no_answer_message: str
    embed: ServiceConfig
    qdrant_url: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_query_config(rag_path: str | None = None) -> QueryConfig:
    root = _repo_root()
    path = Path(rag_path or os.environ.get("RAG_CONFIG") or root / "config" / "rag.yaml")
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    ingest = load_ingest_config()  # embed service + qdrant url + catalog

    r = raw.get("retrieval", {})
    rr = raw.get("rerank", {})
    c = raw.get("context", {})
    g = raw.get("generation", {})

    generation = GenerationConfig(
        provider=g.get("provider", "ollama"),
        base_url=os.environ.get("OLLAMA_BASE_URL", g["base_url"]).rstrip("/"),
        model=os.environ.get("CHAT_MODEL", g.get("model", "qwen2.5-coder:7b")),
        temperature=float(g.get("temperature", 0.1)),
        num_ctx=int(g.get("num_ctx", 8192)),
        max_tokens=int(g.get("max_tokens", 512)),
        request_timeout=int(g.get("request_timeout", 600)),
    )

    return QueryConfig(
        retrieval=RetrievalConfig(
            collection=r.get("collection", "kb_docs"),
            top_k=int(r.get("top_k", 4)),
            score_threshold=float(r.get("score_threshold", 0.25)),
        ),
        rerank=RerankConfig(
            enabled=bool(rr.get("enabled", False)),
            method=rr.get("method", "lexical"),
            candidate_k=int(rr.get("candidate_k", 8)),
            lexical_weight=float(rr.get("lexical_weight", 0.15)),
        ),
        context=ContextConfig(
            max_context_chars=int(c.get("max_context_chars", 6000)),
            per_chunk_char_cap=int(c.get("per_chunk_char_cap", 1600)),
            cite=bool(c.get("cite", True)),
        ),
        generation=generation,
        no_answer_message=raw.get("guardrails", {}).get(
            "no_answer_message", "I don't have that in the local knowledge base."),
        embed=ingest.service,
        qdrant_url=ingest.qdrant_url,
    )
