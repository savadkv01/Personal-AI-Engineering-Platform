"""Orchestrator: retrieve -> (re-rank) -> assemble -> ground -> answer.

Guardrails:
- Empty retrieval (nothing clears the score threshold) -> return the no-answer
  message WITHOUT calling the model, so no citation is ever hallucinated.
- Context is budget-bounded by the assembler (no window overflow).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .assembler import Citation, assemble
from .config import QueryConfig, load_query_config
from .generator import generate
from .rerank import rerank
from .retriever import RetrievedChunk, retrieve


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    grounded: bool = False
    collection: str = ""
    scope: str | None = None
    retrieved: int = 0

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "grounded": self.grounded,
            "collection": self.collection,
            "scope": self.scope,
            "retrieved": self.retrieved,
            "citations": [
                {"n": c.n, "source": c.source, "title": c.title,
                 "score": c.score, "chunk_index": c.chunk_index}
                for c in self.citations
            ],
        }


def answer(question: str, *, scope: str | None = None, tags: list[str] | None = None,
           collection: str | None = None, cfg: QueryConfig | None = None) -> Answer:
    cfg = cfg or load_query_config()
    col = collection or cfg.retrieval.collection

    candidates = retrieve(question, cfg, collection=col, scope=scope, tags=tags)
    chunks = rerank(question, candidates, cfg)

    # Guardrail: nothing relevant -> no-answer, no model call, no citations.
    if not chunks:
        return Answer(question=question, answer=cfg.no_answer_message, grounded=False,
                      collection=col, scope=scope, retrieved=0)

    ctx = assemble(chunks, cfg)
    text = generate(question, ctx.text, cfg.generation)
    return Answer(question=question, answer=text, citations=ctx.citations, grounded=True,
                  collection=col, scope=scope, retrieved=len(ctx.used))
