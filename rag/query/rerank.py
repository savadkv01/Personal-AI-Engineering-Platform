"""Optional re-ranking. Default is a zero-model lexical overlap re-rank that
blends the vector score with query-term coverage — cheap enough for Profile A.
A cross-encoder re-ranker is a future (Profile B-D) upgrade.
"""
from __future__ import annotations

import re

from .config import QueryConfig
from .retriever import RetrievedChunk

_WORD = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.lower()) if len(t) > 2}


def _lexical_overlap(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0
    doc_terms = _terms(text)
    if not doc_terms:
        return 0.0
    return len(query_terms & doc_terms) / len(query_terms)


def rerank(question: str, chunks: list[RetrievedChunk], cfg: QueryConfig) -> list[RetrievedChunk]:
    if not cfg.rerank.enabled or not chunks:
        return chunks[: cfg.retrieval.top_k]
    if cfg.rerank.method != "lexical":
        # Unknown method -> no-op, keep vector order.
        return chunks[: cfg.retrieval.top_k]

    qt = _terms(question)
    w = cfg.rerank.lexical_weight
    for c in chunks:
        c.rerank_score = (1 - w) * c.score + w * _lexical_overlap(qt, c.text)
    ranked = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
    return ranked[: cfg.retrieval.top_k]
