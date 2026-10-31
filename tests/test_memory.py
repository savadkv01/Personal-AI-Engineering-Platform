"""Offline tests for the M5 memory service (SQLite + local vectors, fake embedder/clock)."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone

import pytest

from memory.service import cli as memory_cli
from memory.service.config import MemoryConfig, RetentionConfig, SessionConfig, load_memory_config
from memory.service.db import Database, applied_versions, migrate_down, migrate_up
from memory.service.service import MemoryService

DIM = 64
_TOKEN = re.compile(r"[a-z0-9]+")


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic bag-of-words vectors: shared words => high cosine."""
    out = []
    for t in texts:
        v = [0.0] * DIM
        for tok in _TOKEN.findall(t.lower()):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)  # noqa: UP017

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw) -> None:
        self.now += timedelta(**kw)


def make_cfg(tmp_path, **kw) -> MemoryConfig:
    base = dict(backend="sqlite", sqlite_path=str(tmp_path / "memory.db"), vector_backend="local",
                async_writes=False, dedup_threshold=0.92)
    base.update(kw)
    cfg = MemoryConfig(**base)
    cfg.recall.score_threshold = 0.3
    return cfg


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def svc(tmp_path, clock):
    s = MemoryService(make_cfg(tmp_path), embed=fake_embed, clock=clock,
                      chat=lambda prompt: "- Session decided to use Qdrant for vectors.")
    yield s
    s.close()


# --- schema / migrations ----------------------------------------------------

def test_migrations_up_down_are_reversible(tmp_path, clock):
    db = Database("sqlite", str(tmp_path / "m.db"))
    assert migrate_up(db, clock()) == ["0001_init"]
    assert migrate_up(db, clock()) == []
    assert applied_versions(db) == ["0001_init"]
    tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"memory_item", "session", "session_turn", "memory_vector"} <= tables
    assert migrate_down(db) == ["0001_init"]
    tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "memory_item" not in tables
    db.close()


def test_postgres_and_sqlite_migrations_define_same_tables():
    from memory.service.db import MIGRATIONS_DIR

    def tables(dialect):
        sql = (MIGRATIONS_DIR / dialect / "0001_init.up.sql").read_text(encoding="utf-8")
        return set(re.findall(r"CREATE TABLE (\w+)", sql))

    assert tables("postgres") | {"memory_vector"} == tables("sqlite")


# --- CRUD (FR-013) ------------------------------------------------------------

def test_remember_get_list_and_validation(svc):
    a = svc.remember("PAIEP uses Qdrant for vectors", type="decision", scope="project:paiep",
                     tags=["rag", "rag", "db"])
    assert a.status == "active" and a.vector_status == "synced"
    assert a.tags == ["db", "rag"]
    assert svc.get(a.memory_id).content == "PAIEP uses Qdrant for vectors"
    assert [i.memory_id for i in svc.list_items(scope="project:paiep")] == [a.memory_id]
    with pytest.raises(ValueError):
        svc.remember("x", scope="team")
    with pytest.raises(ValueError):
        svc.remember("x", type="gossip")
    with pytest.raises(ValueError):
        svc.remember("   ")


def test_exact_duplicate_reinforces_instead_of_inserting(svc):
    a = svc.remember("Prefer pytest over unittest", type="preference")
    b = svc.remember("  prefer   PYTEST over unittest ", type="preference")
    assert b.memory_id == a.memory_id
    assert b.reinforce_count == 1 and b.confidence == pytest.approx(0.75)
    assert len(svc.list_items()) == 1


def test_semantic_near_duplicate_is_merged(svc):
    a = svc.remember("The gateway listens on port 8081.")
    b = svc.remember("the gateway listens on port 8081")  # punctuation differs: not an exact hash dup
    assert b.memory_id != a.memory_id
    merged = svc.get(b.memory_id)
    assert merged.status == "merged" and merged.superseded_by == a.memory_id
    assert svc.get(a.memory_id).reinforce_count == 1
    assert svc.check()["consistent"]


def test_edit_reembeds_and_status_controls_recall(svc):
    a = svc.remember("Ollama runs the chat model")
    svc.edit(a.memory_id, content="Qdrant stores semantic memory vectors")
    assert [r.item.memory_id for r in svc.recall("semantic memory vectors")] == [a.memory_id]
    assert svc.recall("Ollama chat model", threshold=0.5) == []
    svc.edit(a.memory_id, status="archived")
    assert svc.recall("semantic memory vectors") == []
    svc.edit(a.memory_id, status="active")
    assert len(svc.recall("semantic memory vectors")) == 1
    with pytest.raises(KeyError):
        svc.edit("nope", content="x")


def test_delete_cascades_to_vector(svc):
    a = svc.remember("Temporary fact to delete")
    assert svc.delete(a.memory_id) is True
    assert svc.get(a.memory_id) is None
    assert a.memory_id not in svc.index.all_ids()
    assert svc.delete(a.memory_id) is False
    assert svc.check()["consistent"]


def test_supersede_keeps_history_and_hides_old(svc):
    old = svc.remember("Default chat model is llama3 8b", type="decision")
    new = svc.supersede(old.memory_id, "Default chat model is qwen2.5-coder 7b")
    o = svc.get(old.memory_id)
    assert o.status == "superseded" and o.superseded_by == new.memory_id
    ids = [r.item.memory_id for r in svc.recall("default chat model")]
    assert ids == [new.memory_id]
    with pytest.raises(ValueError):
        svc.supersede(new.memory_id, "Default chat model is qwen2.5-coder 7b")


# --- recall + scope (FR-012) ------------------------------------------------

def test_recall_is_scope_filtered(svc):
    g = svc.remember("Use conventional commits for git messages", scope="global")
    p = svc.remember("Project paiep commits use the copilot trailer", scope="project:paiep")
    o = svc.remember("Project other commits are squashed", scope="project:other")
    q = "commits git messages"

    def ids(**kw):
        return {r.item.memory_id for r in svc.recall(q, threshold=0.1, **kw)}

    assert ids() == {g.memory_id, p.memory_id, o.memory_id}
    assert ids(scope="global") == {g.memory_id}
    assert ids(scope="project:paiep") == {p.memory_id, g.memory_id}
    assert ids(scope="project:paiep", include_global=False) == {p.memory_id}
    assert o.memory_id not in ids(scope="project:paiep")


def test_recall_ranks_relevant_first_and_respects_types(svc):
    svc.remember("The vector database is Qdrant", type="decision")
    svc.remember("I like hiking on weekends", type="preference")
    hits = svc.recall("which vector database")
    assert hits[0].item.content == "The vector database is Qdrant"
    assert svc.recall("which vector database", types=["preference"]) == []


def test_reinforce_bumps_confidence(svc):
    a = svc.remember("Reinforced fact about embeddings", confidence=0.98)
    svc.recall("embeddings fact", reinforce=True)
    item = svc.get(a.memory_id)
    assert item.confidence == 1.0 and item.reinforce_count == 1


def test_archive_scope(svc):
    svc.remember("Old project detail one", scope="project:old")
    svc.remember("Old project detail two", scope="project:old")
    keep = svc.remember("Global detail", scope="global")
    assert svc.archive_scope("project:old") == 2
    assert {i.memory_id for i in svc.list_items()} == {keep.memory_id}
    assert svc.check()["consistent"]


# --- forgetting policy --------------------------------------------------------

def test_ttl_expires_items(svc, clock):
    a = svc.remember("Ephemeral build status is green", type="progress", ttl_days=1)
    b = svc.remember("Durable fact about the stack")
    clock.advance(days=2)
    assert svc.recall("ephemeral build status") == []  # filtered even before maintain
    rep = svc.maintain()
    assert rep["expired"] == 1
    assert svc.get(a.memory_id).status == "expired"
    assert svc.get(b.memory_id).status == "active"
    assert a.memory_id not in svc.index.all_ids()


def test_default_ttl_by_type(tmp_path, clock):
    cfg = make_cfg(tmp_path, retention=RetentionConfig(default_ttl_days={"progress": 7}))
    with MemoryService(cfg, embed=fake_embed, clock=clock) as s:
        item = s.remember("Sprint progress at 50 percent", type="progress")
        assert item.expires_at == clock.now + timedelta(days=7)
        assert s.remember("A plain fact").expires_at is None


def test_decay_archives_unused_low_confidence_but_exempts_preferences(svc, clock):
    stale = svc.remember("Rarely used fact", confidence=0.5)
    pref = svc.remember("Prefer tabs over spaces", type="preference", confidence=0.5)
    fresh = svc.remember("Recently used fact", confidence=0.5)
    clock.advance(days=200)  # 0.5 * 0.5^(200/90) ~= 0.107 < 0.2
    svc.recall("Recently used fact", top_k=1, reinforce=True)
    preview = svc.maintain(dry_run=True)
    assert preview["decayed"] == 1 and svc.get(stale.memory_id).status == "active"
    svc.maintain()
    assert svc.get(stale.memory_id).status == "archived"
    assert svc.get(pref.memory_id).status == "active"
    assert svc.get(fresh.memory_id).status == "active"


def test_size_cap_archives_lowest_confidence(tmp_path, clock):
    cfg = make_cfg(tmp_path, retention=RetentionConfig(max_active_items=2))
    with MemoryService(cfg, embed=fake_embed, clock=clock) as s:
        low = s.remember("alpha low value item", confidence=0.3)
        s.remember("beta medium value item", confidence=0.6)
        s.remember("gamma high value item", confidence=0.9)
        assert s.maintain()["capped"] == 1
        assert s.get(low.memory_id).status == "archived"
        assert len(s.list_items()) == 2


# --- session memory -----------------------------------------------------------

def test_session_turns_history_and_cap(tmp_path, clock):
    cfg = make_cfg(tmp_path, session=SessionConfig(max_turns=4, history_turns=2))
    with MemoryService(cfg, embed=fake_embed, clock=clock) as s:
        sess = s.start_session(scope="project:paiep", task_id="T-1")
        s.add_turn(sess.session_id, "fact", "Kept fact turn")
        for i in range(6):
            s.add_turn(sess.session_id, "user" if i % 2 == 0 else "assistant", f"turn {i}")
        turns = s.get_turns(sess.session_id)
        assert [t.content for t in turns] == ["Kept fact turn", "turn 2", "turn 3", "turn 4", "turn 5"]
        assert [t.content for t in s.history(sess.session_id)] == ["turn 4", "turn 5"]
        with pytest.raises(ValueError):
            s.add_turn(sess.session_id, "robot", "x")


def test_close_session_promotes_salient_and_evicts(svc):
    sess = svc.start_session(scope="project:paiep")
    sid = sess.session_id
    svc.add_turn(sid, "user", "What vector DB do we use?")
    svc.add_turn(sid, "assistant", "Qdrant.")
    svc.add_turn(sid, "fact", "The memory collection is memory_semantic")
    svc.add_turn(sid, "user", "Remember: deploy only on Fridays")
    rep = svc.close_session(sid, summarize=True)

    promoted = {svc.get(m).content for m in rep["promoted"]}
    assert promoted == {"The memory collection is memory_semantic", "deploy only on Fridays"}
    assert all(svc.get(m).scope == "project:paiep" for m in rep["promoted"])
    assert all(svc.get(m).source == f"session:{sid}" for m in rep["promoted"])
    summary = svc.get(rep["summary"])
    assert summary.type == "task_summary" and "Qdrant" in summary.content
    assert rep["evicted_turns"] == 4 and svc.get_turns(sid) == []
    assert svc.get_session(sid).status == "closed"
    with pytest.raises(ValueError):
        svc.add_turn(sid, "user", "too late")


def test_cross_session_recall(svc):
    s1 = svc.start_session(scope="project:paiep")
    svc.add_turn(s1.session_id, "fact", "The staging database host is db-staging-01")
    svc.close_session(s1.session_id)
    s2 = svc.start_session(scope="project:paiep")
    hits = svc.recall("staging database host", scope="project:paiep")
    assert hits and "db-staging-01" in hits[0].item.content
    assert svc.get_session(s2.session_id).status == "open"


def test_abandoned_session_expires_via_maintain(svc, clock):
    sess = svc.start_session()
    svc.add_turn(sess.session_id, "fact", "Abandoned session fact")
    clock.advance(hours=25)
    assert svc.maintain()["sessions_expired"] == 1
    assert svc.get_session(sess.session_id).status == "expired"
    assert svc.recall("abandoned session fact")


# --- async writes, persistence, consistency ------------------------------------

def test_async_writes_are_non_blocking_and_flush(tmp_path, clock):
    import threading

    gate = threading.Event()

    def slow_embed(texts):
        gate.wait(5)
        return fake_embed(texts)

    cfg = make_cfg(tmp_path, async_writes=True)
    s = MemoryService(cfg, embed=slow_embed, clock=clock)
    item = s.remember("Async written fact")
    assert item.vector_status == "pending"  # returned before embedding finished
    gate.set()
    assert s.flush(timeout=10)
    assert s.get(item.memory_id).vector_status == "synced"
    s.close()


def test_memory_persists_across_restart(tmp_path, clock):
    cfg = make_cfg(tmp_path)
    with MemoryService(cfg, embed=fake_embed, clock=clock) as s:
        mid = s.remember("Persistent fact across restarts").memory_id
    with MemoryService(cfg, embed=fake_embed, clock=clock) as s2:
        assert s2.get(mid) is not None
        assert s2.recall("persistent fact restarts")[0].item.memory_id == mid


def test_check_detects_and_repairs_drift(svc):
    a = svc.remember("Fact whose vector goes missing")
    svc.index.delete([a.memory_id])
    svc.index.upsert("00000000-0000-0000-0000-000000000000", fake_embed(["ghost"])[0],
                     {"scope": "global"})
    rep = svc.check()
    assert not rep["consistent"]
    assert rep["missing_vectors"] == [a.memory_id]
    assert rep["dangling_vectors"] == ["00000000-0000-0000-0000-000000000000"]
    assert svc.check(repair=True)["repaired"]
    assert svc.check()["consistent"]


def test_sync_pending_recovers_outbox(svc):
    a = svc.remember("Fact left pending by a crash")
    svc.db.execute("UPDATE memory_item SET vector_status = 'pending' WHERE memory_id = ?",
                   (a.memory_id,))
    svc.index.delete([a.memory_id])
    assert svc.sync_pending() == 1
    assert svc.check()["consistent"]


def test_stats(svc):
    svc.remember("one")
    svc.start_session()
    st = svc.stats()
    assert st["items_by_status"] == {"active": 1}
    assert st["sessions_by_status"] == {"open": 1}
    assert st["pending_vectors"] == 0


# --- config + CLI -------------------------------------------------------------

def test_profile_a_overlay_merges_with_defaults(monkeypatch):
    monkeypatch.delenv("MEMORY_CONFIG", raising=False)
    monkeypatch.delenv("MEMORY_SQLITE_PATH", raising=False)
    base = load_memory_config(with_embed=False)
    assert base.backend == "postgres" and base.vector_backend == "qdrant"
    a = load_memory_config("config/memory.profile-a.yaml", with_embed=False)
    assert (a.backend, a.vector_backend, a.recall.top_k) == ("sqlite", "local", 3)
    assert a.dedup_threshold == base.dedup_threshold  # inherited from memory.yaml
    assert a.retention.max_active_items == 2000


def test_dsn_from_env(monkeypatch):
    monkeypatch.delenv("MEMORY_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret")
    assert load_memory_config(with_embed=False).dsn == \
        "host=postgres port=5432 dbname=paiep user=paiep password=s3cret"
    monkeypatch.setenv("MEMORY_DSN", "postgresql://u:p@h/db")
    assert load_memory_config(with_embed=False).dsn == "postgresql://u:p@h/db"


def test_invalid_backend_combination_rejected():
    with pytest.raises(ValueError):
        MemoryConfig(backend="postgres", vector_backend="local").validate()


def test_cli_add_recall_list_json(tmp_path, clock, monkeypatch, capsys):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(memory_cli, "load_memory_config", lambda *a, **k: cfg)
    monkeypatch.setattr(memory_cli, "MemoryService",
                        lambda c: MemoryService(c, embed=fake_embed, clock=clock))

    assert memory_cli.main(["--json", "add", "CLI stored preference for black formatter",
                            "--type", "preference", "--scope", "project:paiep"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["type"] == "preference" and "write_ms" in added

    assert memory_cli.main(["--json", "recall", "black formatter", "--scope", "project:paiep"]) == 0
    rec = json.loads(capsys.readouterr().out)
    assert rec["results"][0]["memory_id"] == added["memory_id"]

    assert memory_cli.main(["--json", "list", "--status", "all"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1
    assert memory_cli.main(["get", "does-not-exist"]) == 2
