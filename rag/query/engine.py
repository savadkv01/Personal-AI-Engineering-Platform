"""Orchestrator: recall memory + retrieve -> (re-rank) -> assemble -> ground -> answer.

Guardrails:
- Empty retrieval (no document chunk AND no memory clears its threshold) -> return the
  no-answer message WITHOUT calling the model, so no citation is ever hallucinated.
- Model refusal (it replied with the no-answer phrase) -> ungrounded, no citations.
- Citations are narrowed to the [n] markers the answer actually uses.
- Context is budget-bounded by the assembler (no window overflow); memories get their
  own sub-budget (``memory.max_context_chars``).

Memory (M5) is optional and fail-soft: ``memory`` is any object with ``recall``,
``history``, ``add_turn`` and ``reinforce`` (``memory.service.MemoryService``); errors
from it are logged and the answer proceeds from documents only.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from .assembler import Citation, assemble
from .config import QueryConfig, load_query_config
from .generator import generate
from .rerank import rerank
from .retriever import RetrievedChunk, retrieve

log = logging.getLogger("paiep.rag")

MEMORY_SOURCE_PREFIX = "memory:"
_CITE_MARKER = re.compile(r"\[(\d+)\]")
_NON_WORD = re.compile(r"\W+")


def _normalize(text: str) -> str:
    return _NON_WORD.sub(" ", text).strip().lower()


def is_refusal(text: str, no_answer_message: str) -> bool:
    """True when the model declined (no-answer phrase, no citation markers)."""
    return (_normalize(text).startswith(_normalize(no_answer_message))
            and not _CITE_MARKER.search(text))


def cited_only(text: str, citations: list[Citation]) -> list[Citation]:
    """Keep citations referenced as [n] in the answer; all of them if none are marked."""
    used = {int(n) for n in _CITE_MARKER.findall(text)}
    narrowed = [c for c in citations if c.n in used]
    return narrowed or citations


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    grounded: bool = False
    collection: str = ""
    scope: str | None = None
    retrieved: int = 0
    memories: int = 0
    session_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "grounded": self.grounded,
            "collection": self.collection,
            "scope": self.scope,
            "retrieved": self.retrieved,
            "memories": self.memories,
            "session_id": self.session_id,
            "citations": [
                {"n": c.n, "source": c.source, "title": c.title,
                 "score": c.score, "chunk_index": c.chunk_index}
                for c in self.citations
            ],
        }


def recall_memories(question: str, scope: str | None, cfg: QueryConfig,
                    memory) -> list[RetrievedChunk]:
    """Recall long-term memories as context chunks (fail-soft, budget-capped)."""
    if memory is None or not cfg.memory.enabled:
        return []
    try:
        hits = memory.recall(question, scope=scope, top_k=cfg.memory.top_k,
                             threshold=cfg.memory.score_threshold)
    except Exception as exc:  # noqa: BLE001 - memory must never break answering
        log.warning("memory recall failed, continuing without memory: %s", exc)
        return []
    out: list[RetrievedChunk] = []
    used = 0
    for h in hits:
        it = h.item
        if used + len(it.content) > cfg.memory.max_context_chars and out:
            break
        used += len(it.content)
        out.append(RetrievedChunk(
            id=it.memory_id, score=float(h.score), text=it.content,
            source=f"{MEMORY_SOURCE_PREFIX}{it.type}/{it.memory_id[:8]}",
            title=f"memory ({it.type}, {it.scope})", scope=it.scope, tags=list(it.tags),
            chunk_index=0))
    return out


def _session_history(memory, session_id: str | None) -> list[dict]:
    if memory is None or not session_id:
        return []
    try:
        return [{"role": t.role, "content": t.content} for t in memory.history(session_id)]
    except Exception as exc:  # noqa: BLE001
        log.warning("session history unavailable (%s): %s", session_id, exc)
        return []


def _log_turns(memory, session_id: str | None, question: str, answer_text: str) -> None:
    if memory is None or not session_id:
        return
    try:
        memory.add_turn(session_id, "user", question)
        memory.add_turn(session_id, "assistant", answer_text)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not record session turns (%s): %s", session_id, exc)


def answer(question: str, *, scope: str | None = None, tags: list[str] | None = None,
           collection: str | None = None, cfg: QueryConfig | None = None,
           memory=None, session_id: str | None = None) -> Answer:
    cfg = cfg or load_query_config()
    col = collection or cfg.retrieval.collection

    memories = recall_memories(question, scope, cfg, memory)
    candidates = retrieve(question, cfg, collection=col, scope=scope, tags=tags)
    chunks = rerank(question, candidates, cfg)
    base = dict(question=question, collection=col, scope=scope, session_id=session_id)

    # Guardrail: nothing relevant -> no-answer, no model call, no citations.
    if not chunks and not memories:
        _log_turns(memory, session_id, question, cfg.no_answer_message)
        return Answer(answer=cfg.no_answer_message, grounded=False, retrieved=0, **base)

    history = _session_history(memory, session_id)
    ctx = assemble(memories + chunks, cfg)
    n_mem = sum(1 for c in ctx.used if c.source.startswith(MEMORY_SOURCE_PREFIX))
    n_doc = len(ctx.used) - n_mem
    text = generate(question, ctx.text, cfg.generation, cfg.no_answer_message, history=history)

    if is_refusal(text, cfg.no_answer_message):
        _log_turns(memory, session_id, question, cfg.no_answer_message)
        return Answer(answer=cfg.no_answer_message, grounded=False, retrieved=n_doc,
                      memories=n_mem, **base)

    citations = cited_only(text, ctx.citations)
    _log_turns(memory, session_id, question, text)
    if memory is not None and cfg.memory.reinforce_on_use:
        cited_mem = [c.source for c in citations if c.source.startswith(MEMORY_SOURCE_PREFIX)]
        ids = [u.id for u in ctx.used if u.source in cited_mem]
        if ids:
            try:
                memory.reinforce(ids)
            except Exception as exc:  # noqa: BLE001
                log.warning("memory reinforce failed: %s", exc)
    return Answer(answer=text, citations=citations, grounded=True, retrieved=n_doc,
                  memories=n_mem, **base)
