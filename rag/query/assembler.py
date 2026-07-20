"""Context assembly: pack retrieved chunks into a budgeted, numbered context
block and emit matching citations. Numbering ([1], [2], ...) is what the model
is told to cite, so citations map 1:1 to the assembled sources.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import QueryConfig
from .retriever import RetrievedChunk


@dataclass
class Citation:
    n: int
    source: str
    title: str
    score: float
    chunk_index: int


@dataclass
class AssembledContext:
    text: str
    citations: list[Citation]
    used: list[RetrievedChunk]


def assemble(chunks: list[RetrievedChunk], cfg: QueryConfig) -> AssembledContext:
    budget = cfg.context.max_context_chars
    cap = cfg.context.per_chunk_char_cap
    blocks: list[str] = []
    citations: list[Citation] = []
    used: list[RetrievedChunk] = []

    n = 0
    for c in chunks:
        snippet = c.text.strip()
        if len(snippet) > cap:
            snippet = snippet[:cap].rsplit(" ", 1)[0] + " …"
        # Stop before exceeding the total context budget (no truncation errors).
        if budget - len(snippet) < 0 and used:
            break
        n += 1
        budget -= len(snippet)
        blocks.append(f"[{n}] (source: {c.source})\n{snippet}")
        citations.append(Citation(n=n, source=c.source, title=c.title,
                                   score=round(c.rerank_score if c.rerank_score is not None else c.score, 4),
                                   chunk_index=c.chunk_index))
        used.append(c)

    return AssembledContext(text="\n\n".join(blocks), citations=citations, used=used)
