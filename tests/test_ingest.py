"""Offline unit tests for the M3 ingestion path (no Ollama / Qdrant needed)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag.ingest import pipeline
from rag.ingest.chunking import _char_window, chunk_text
from rag.ingest.config import load_config
from rag.ingest.loaders import _parse_front_matter, iter_files, load_document
from rag.ingest.provenance import point_id


@pytest.fixture
def cfg():
    return load_config()


# --- loaders ---------------------------------------------------------------

def test_front_matter_parsed_and_stripped():
    meta, body = _parse_front_matter("---\ntitle: T\nscope: project:x\n---\n# H\nbody")
    assert meta == {"title": "T", "scope": "project:x"}
    assert body == "# H\nbody"


def test_front_matter_absent_or_invalid_is_ignored():
    assert _parse_front_matter("# Just text") == ({}, "# Just text")
    assert _parse_front_matter("---\n: [bad\n---\nx")[0] == {}


def test_load_markdown_title_tags_scope(tmp_path):
    p = tmp_path / "note.md"
    p.write_text("---\ntags: a, b\nscope: project:x\n---\n# Heading\ntext", encoding="utf-8")
    doc = load_document(str(p))
    assert doc.title == "Heading"
    assert doc.tags == ["a", "b"]
    assert doc.scope == "project:x"


def test_load_code_uses_filename_title(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("print('hi')\n", encoding="utf-8")
    doc = load_document(str(p))
    assert doc.title == "mod.py" and doc.extra["lang"] == "py"


def test_iter_files_honors_excludes(tmp_path):
    (tmp_path / "keep.md").write_text("x")
    (tmp_path / ".hidden.md").write_text("x")
    (tmp_path / ".gitkeep").write_text("")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.md").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.md").write_text("x")
    got = sorted(p.replace("\\", "/").split("/")[-1]
                 for p in iter_files([str(tmp_path)], {"node_modules"}, {".gitkeep"}))
    assert got == ["deep.md", "keep.md"]


# --- chunking / provenance / config ---------------------------------------

def test_chunk_text_empty_and_nonempty():
    assert chunk_text("   ", 512, 64) == []
    assert chunk_text("One sentence. Another sentence.", 512, 64)


def test_char_window_overlaps():
    assert _char_window("abcdefghij", 4, 2) == ["abcd", "cdef", "efgh", "ghij", "ij"]


def test_point_id_is_deterministic():
    assert point_id("a.md", 0) == point_id("a.md", 0)
    assert point_id("a.md", 0) != point_id("a.md", 1)
    assert point_id("a.md", 0) != point_id("b.md", 0)


def test_config_routing_and_chunk_params(cfg):
    assert cfg.route("x/note.MD").collection == "kb_docs"
    assert cfg.route("x/app.py").doc_type == "code"
    assert cfg.route("x/image.png") is None
    assert cfg.chunk_params("code") == (768, 96)
    assert cfg.chunk_params("unknown") == cfg.chunk_params("note")


# --- prune -----------------------------------------------------------------

def test_stale_sources_restricted_to_roots():
    indexed = {"knowledge/a.md", "knowledge/gone.md", "knowledge-old/x.md", "other/keep.md"}
    seen = {"knowledge/a.md"}
    assert pipeline.stale_sources(indexed, seen, ["knowledge"]) == {"knowledge/gone.md"}
    assert pipeline.stale_sources(indexed, seen, ["knowledge/"]) == {"knowledge/gone.md"}
    assert pipeline.stale_sources(indexed, seen, ["."]) == indexed - seen


# --- run(): scope precedence + prune with a fake Qdrant --------------------

class FakeQdrant:
    def __init__(self, dim: int, indexed: dict[str, list[str]]):
        self.dim = dim
        self.indexed = indexed
        self.deleted: list[tuple[str, str]] = []
        self.upserted: list = []

    def collection_exists(self, name):
        return True

    def get_collection(self, name):
        vectors = SimpleNamespace(size=self.dim)
        return SimpleNamespace(config=SimpleNamespace(params=SimpleNamespace(vectors=vectors)))

    def scroll(self, collection_name, scroll_filter=None, limit=10, offset=None, **kw):
        if scroll_filter is not None:  # checksum lookup -> nothing indexed yet
            return [], None
        pts = [SimpleNamespace(payload={"source": s}) for s in self.indexed.get(collection_name, [])]
        return pts, None

    def delete(self, collection_name, points_selector, wait=True):
        src = points_selector.filter.must[0].match.value
        self.deleted.append((collection_name, src))

    def upsert(self, collection_name, points, wait=True):
        self.upserted.extend(points)


@pytest.fixture
def corpus(tmp_path):
    notes = tmp_path / "knowledge"
    notes.mkdir()
    (notes / "scoped.md").write_text("---\nscope: project:x\n---\n# S\nScoped text.", encoding="utf-8")
    (notes / "plain.md").write_text("# P\nPlain text.", encoding="utf-8")
    return tmp_path


def _run(monkeypatch, cfg, corpus, fake, **kw):
    monkeypatch.setattr(pipeline, "QdrantClient", lambda url, timeout: fake)
    monkeypatch.setattr(pipeline, "embed_texts",
                        lambda texts, svc: [[0.0] * svc.dim for _ in texts])
    return pipeline.run([str(corpus / "knowledge")], scope="global", source_root=str(corpus),
                        config=cfg, log=lambda *_: None, **kw)


def test_front_matter_scope_overrides_run_scope(monkeypatch, cfg, corpus):
    fake = FakeQdrant(cfg.service.dim, {})
    _run(monkeypatch, cfg, corpus, fake)
    scopes = {p.payload["source"]: p.payload["scope"] for p in fake.upserted}
    assert scopes == {"knowledge/scoped.md": "project:x", "knowledge/plain.md": "global"}


def test_prune_deletes_only_missing_sources_under_paths(monkeypatch, cfg, corpus):
    indexed = {"kb_docs": ["knowledge/plain.md", "knowledge/gone.md", "elsewhere/keep.md"]}
    fake = FakeQdrant(cfg.service.dim, indexed)
    stats = _run(monkeypatch, cfg, corpus, fake, prune=True)
    assert stats.sources_pruned == 1
    assert ("kb_docs", "knowledge/gone.md") in fake.deleted
    assert all(src != "elsewhere/keep.md" for _, src in fake.deleted)


def test_prune_dry_run_deletes_nothing(monkeypatch, cfg, corpus):
    fake = FakeQdrant(cfg.service.dim, {"kb_docs": ["knowledge/gone.md"]})
    stats = _run(monkeypatch, cfg, corpus, fake, prune=True, dry_run=True)
    assert stats.sources_pruned == 1
    assert fake.deleted == [] and fake.upserted == []


def test_no_prune_by_default(monkeypatch, cfg, corpus):
    fake = FakeQdrant(cfg.service.dim, {"kb_docs": ["knowledge/gone.md"]})
    stats = _run(monkeypatch, cfg, corpus, fake)
    assert stats.sources_pruned == 0
    assert ("kb_docs", "knowledge/gone.md") not in fake.deleted
