"""Offline unit tests for the M4 query path (no Ollama / Qdrant needed)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag.query import engine, retriever
from rag.query.assembler import assemble
from rag.query.config import load_query_config
from rag.query.generator import build_system_prompt
from rag.query.rerank import rerank
from rag.query.retriever import RetrievedChunk, _build_filter


@pytest.fixture
def cfg():
    return load_query_config()


def chunk(n: int, score: float = 0.5, text: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(id=str(n), score=score, text=text or f"passage number {n}",
                          source=f"knowledge/notes/{n}.md", title=f"T{n}", scope="global",
                          tags=[], chunk_index=0)


# --- retrieval filter ------------------------------------------------------

def test_build_filter_none_when_unfiltered():
    assert _build_filter(None, None) is None
    assert _build_filter(None, []) is None


def test_build_filter_scope_and_tags():
    flt = _build_filter("project:paiep", ["rag", "docs"])
    keys = {c.key for c in flt.must}
    assert keys == {"scope", "tags"}
    scope = next(c for c in flt.must if c.key == "scope")
    tags = next(c for c in flt.must if c.key == "tags")
    assert scope.match.value == "project:paiep"
    assert tags.match.any == ["rag", "docs"]


def test_retrieve_uses_query_points_and_maps_payload(cfg, monkeypatch):
    calls = {}

    class FakeClient:
        def __init__(self, url, timeout):
            calls["url"] = url

        def query_points(self, **kw):
            calls.update(kw)
            hit = SimpleNamespace(id=7, score=0.81, payload={
                "text": "hello", "source": "knowledge/a.md", "title": "A",
                "scope": "global", "tags": ["x"], "chunk_index": 3})
            return SimpleNamespace(points=[hit])

    monkeypatch.setattr(retriever, "QdrantClient", FakeClient)
    monkeypatch.setattr(retriever, "embed_texts", lambda texts, svc: [[0.0] * svc.dim])

    out = retriever.retrieve("q?", cfg, scope="global", limit=3)

    assert calls["limit"] == 3
    assert calls["collection_name"] == cfg.retrieval.collection
    assert calls["score_threshold"] == cfg.retrieval.score_threshold
    assert calls["query_filter"].must[0].match.value == "global"
    assert len(out) == 1
    c = out[0]
    assert (c.id, c.score, c.source, c.chunk_index, c.tags) == ("7", 0.81, "knowledge/a.md", 3, ["x"])


# --- context assembly ------------------------------------------------------

def test_assemble_numbers_sources_and_respects_budget(cfg):
    cfg.context.max_context_chars = 100
    cfg.context.per_chunk_char_cap = 80
    chunks = [chunk(i, text="word " * 10) for i in range(1, 4)]  # 49 chars each

    ctx = assemble(chunks, cfg)

    assert [c.n for c in ctx.citations] == [1, 2]
    assert ctx.text.startswith("[1] (source: knowledge/notes/1.md)")
    assert "[3]" not in ctx.text


def test_assemble_caps_long_chunk(cfg):
    cfg.context.per_chunk_char_cap = 40
    ctx = assemble([chunk(1, text="abc def " * 50)], cfg)
    body = ctx.text.split("\n", 1)[1]
    assert body.endswith("…")
    assert len(body) <= 42


def test_assemble_always_keeps_first_chunk(cfg):
    cfg.context.max_context_chars = 10
    ctx = assemble([chunk(1, text="x" * 50)], cfg)
    assert len(ctx.used) == 1


# --- re-rank ---------------------------------------------------------------

def test_rerank_disabled_truncates_to_top_k(cfg):
    cfg.rerank.enabled = False
    cfg.retrieval.top_k = 2
    out = rerank("q", [chunk(i) for i in range(5)], cfg)
    assert [c.id for c in out] == ["0", "1"]


def test_rerank_lexical_promotes_term_overlap(cfg):
    cfg.rerank.enabled = True
    cfg.rerank.method = "lexical"
    cfg.rerank.lexical_weight = 0.5
    cfg.retrieval.top_k = 2
    a = chunk(1, score=0.50, text="something unrelated entirely")
    b = chunk(2, score=0.45, text="qdrant vector store details")
    out = rerank("qdrant vector store", [a, b], cfg)
    assert [c.id for c in out] == ["2", "1"]
    assert out[0].rerank_score == pytest.approx(0.725)


# --- grounding guardrails --------------------------------------------------

def test_system_prompt_uses_configured_no_answer_message():
    assert '"Nope, not in the KB."' in build_system_prompt("Nope, not in the KB.")


@pytest.mark.parametrize("text,expected", [
    ("I don't have information about that in the local knowledge base.", True),
    ("i don't have information about that in the local knowledge base", True),
    ("I don't have information about that in the local knowledge base. But [1] says X.", False),
    ("PAIEP runs offline [1].", False),
])
def test_is_refusal(text, expected):
    msg = "I don't have information about that in the local knowledge base."
    assert engine.is_refusal(text, msg) is expected


def test_cited_only_narrows_and_falls_back(cfg):
    cits = assemble([chunk(1), chunk(2), chunk(3)], cfg).citations
    assert [c.n for c in engine.cited_only("A [2] and [3].", cits)] == [2, 3]
    assert [c.n for c in engine.cited_only("No markers here.", cits)] == [1, 2, 3]
    assert [c.n for c in engine.cited_only("Bogus [9].", cits)] == [1, 2, 3]


def _no_model(*a, **k):
    raise AssertionError("model must not be called")


def test_answer_empty_retrieval_skips_model(cfg, monkeypatch):
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(engine, "generate", _no_model)
    res = engine.answer("q", cfg=cfg)
    assert res.grounded is False and res.citations == [] and res.retrieved == 0
    assert res.answer == cfg.no_answer_message


def test_answer_model_refusal_is_ungrounded(cfg, monkeypatch):
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [chunk(1), chunk(2)])
    monkeypatch.setattr(engine, "generate", lambda *a, **k: cfg.no_answer_message)
    res = engine.answer("q", cfg=cfg)
    assert res.grounded is False
    assert res.citations == []
    assert res.retrieved == 2


def test_answer_grounded_returns_only_cited_sources(cfg, monkeypatch):
    seen = {}

    def fake_generate(question, context, gen, no_answer_message, history=None):
        seen["no_answer"] = no_answer_message
        return "PAIEP works offline [2]."

    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [chunk(1), chunk(2), chunk(3)])
    monkeypatch.setattr(engine, "generate", fake_generate)
    res = engine.answer("q", cfg=cfg)
    assert res.grounded is True
    assert [c.n for c in res.citations] == [2]
    assert seen["no_answer"] == cfg.no_answer_message
    assert res.as_dict()["citations"][0]["source"] == "knowledge/notes/2.md"


# --- M5 memory in context ------------------------------------------------------

class FakeMemory:
    def __init__(self, hits=None, fail=False, history=None):
        self.hits = hits or []
        self.fail = fail
        self._history = history or []
        self.recall_calls = []
        self.turns = []
        self.reinforced = []

    def recall(self, question, *, scope=None, top_k=None, threshold=None):
        self.recall_calls.append((question, scope, top_k, threshold))
        if self.fail:
            raise ConnectionError("postgres down")
        return self.hits[:top_k]

    def history(self, session_id):
        return self._history

    def add_turn(self, session_id, role, content):
        self.turns.append((session_id, role, content))

    def reinforce(self, ids):
        self.reinforced.extend(ids)


def mem_hit(mid: str, content: str, score: float = 0.8, type: str = "preference"):
    item = SimpleNamespace(memory_id=mid, content=content, type=type, scope="global", tags=[])
    return SimpleNamespace(item=item, score=score)


@pytest.fixture
def mem_cfg(cfg):
    cfg.memory.enabled = True
    cfg.memory.top_k = 3
    cfg.memory.max_context_chars = 1200
    cfg.memory.reinforce_on_use = True
    return cfg


def test_memory_is_prepended_cited_and_reinforced(mem_cfg, monkeypatch):
    mem = FakeMemory([mem_hit("aaaaaaaa-1111", "User prefers pytest"), mem_hit("bbbbbbbb-2222", "Uses ruff")])
    seen = {}

    def fake_generate(question, context, gen, no_answer_message, history=None):
        seen["context"] = context
        return "Use pytest [1] as documented [3]."

    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [chunk(1)])
    monkeypatch.setattr(engine, "generate", fake_generate)
    res = engine.answer("which test framework?", cfg=mem_cfg, memory=mem, scope="project:paiep")

    assert seen["context"].startswith("[1] (source: memory:preference/aaaaaaaa)")
    assert "[3] (source: knowledge/notes/1.md)" in seen["context"]
    assert [c.source for c in res.citations] == ["memory:preference/aaaaaaaa", "knowledge/notes/1.md"]
    assert res.memories == 2 and res.retrieved == 1
    assert mem.reinforced == ["aaaaaaaa-1111"]  # only the cited memory
    assert mem.recall_calls[0][1] == "project:paiep"


def test_memory_alone_can_ground_an_answer(mem_cfg, monkeypatch):
    mem = FakeMemory([mem_hit("cccccccc-3333", "The staging host is db-staging-01", type="fact")])
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(engine, "generate", lambda *a, **k: "It is db-staging-01 [1].")
    res = engine.answer("staging host?", cfg=mem_cfg, memory=mem)
    assert res.grounded and res.memories == 1 and res.retrieved == 0


def test_memory_budget_is_capped(mem_cfg, monkeypatch):
    mem_cfg.memory.max_context_chars = 30
    mem = FakeMemory([mem_hit("m1-xxxxxxxx", "x" * 25), mem_hit("m2-xxxxxxxx", "y" * 25)])
    assert len(engine.recall_memories("q", None, mem_cfg, mem)) == 1


def test_memory_failure_is_fail_soft(mem_cfg, monkeypatch):
    mem = FakeMemory(fail=True)
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [chunk(1)])
    monkeypatch.setattr(engine, "generate", lambda *a, **k: "Answer [1].")
    res = engine.answer("q", cfg=mem_cfg, memory=mem)
    assert res.grounded and res.memories == 0


def test_memory_disabled_skips_recall(cfg, monkeypatch):
    cfg.memory.enabled = False
    mem = FakeMemory([mem_hit("dddddddd-4444", "ignored")])
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(engine, "generate", _no_model)
    res = engine.answer("q", cfg=cfg, memory=mem)
    assert mem.recall_calls == [] and not res.grounded


def test_session_history_is_sent_and_turns_logged(mem_cfg, monkeypatch):
    hist = [SimpleNamespace(role="user", content="Earlier question"),
            SimpleNamespace(role="assistant", content="Earlier answer")]
    mem = FakeMemory(history=hist)
    seen = {}

    def fake_generate(question, context, gen, no_answer_message, history=None):
        seen["history"] = history
        return "Follow-up answer [1]."

    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [chunk(1)])
    monkeypatch.setattr(engine, "generate", fake_generate)
    res = engine.answer("And now?", cfg=mem_cfg, memory=mem, session_id="s-1")
    assert seen["history"] == [{"role": "user", "content": "Earlier question"},
                               {"role": "assistant", "content": "Earlier answer"}]
    assert mem.turns == [("s-1", "user", "And now?"), ("s-1", "assistant", "Follow-up answer [1].")]
    assert res.as_dict()["session_id"] == "s-1"


def test_no_answer_is_still_logged_to_session(mem_cfg, monkeypatch):
    mem = FakeMemory()
    monkeypatch.setattr(engine, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(engine, "generate", _no_model)
    engine.answer("unknown?", cfg=mem_cfg, memory=mem, session_id="s-2")
    assert mem.turns[-1] == ("s-2", "assistant", mem_cfg.no_answer_message)
