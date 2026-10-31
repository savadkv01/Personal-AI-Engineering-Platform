"""Config for the memory service.

``config/memory.yaml`` holds the defaults; ``MEMORY_CONFIG`` may point at an
overlay (e.g. ``memory.profile-a.yaml``) that is deep-merged on top. The
embedding service is inherited from the M3 config so memory vectors always use
the model recorded for ``memory_semantic`` in the index catalog.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from rag.ingest.config import ServiceConfig
from rag.ingest.config import load_config as load_ingest_config

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = REPO_ROOT / "config" / "memory.yaml"


@dataclass
class RecallConfig:
    top_k: int = 5
    score_threshold: float = 0.5
    include_global: bool = True


@dataclass
class ConsolidationConfig:
    promote_roles: list[str] = field(default_factory=lambda: ["fact"])
    capture_prefixes: list[str] = field(default_factory=lambda: ["remember:", "note:"])
    fact_confidence: float = 0.8
    summarize_with_llm: bool = False
    summary_max_tokens: int = 200
    chat_model: str = "qwen2.5-coder:7b"
    chat_base_url: str = "http://ollama:11434"


@dataclass
class RetentionConfig:
    default_confidence: float = 0.7
    reinforce_step: float = 0.05
    half_life_days: float = 90.0
    archive_below: float = 0.2
    exempt_types: list[str] = field(default_factory=lambda: ["preference", "decision"])
    default_ttl_days: dict[str, float] = field(default_factory=dict)
    max_active_items: int = 5000


@dataclass
class SessionConfig:
    ttl_hours: float = 24.0
    max_turns: int = 200
    history_turns: int = 6
    evict_on_close: bool = True


@dataclass
class MemoryConfig:
    backend: str = "postgres"            # postgres | sqlite
    dsn: str = ""                         # postgres DSN (built from parts + env)
    sqlite_path: str = "/data/memory.db"
    auto_migrate: bool = True
    vector_backend: str = "qdrant"       # qdrant | local
    collection: str = "memory_semantic"
    qdrant_url: str = "http://qdrant:6333"
    async_writes: bool = True
    dedup_threshold: float = 0.92
    recall: RecallConfig = field(default_factory=RecallConfig)
    consolidation: ConsolidationConfig = field(default_factory=ConsolidationConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    embed: ServiceConfig | None = None

    def validate(self) -> None:
        if self.backend not in ("postgres", "sqlite"):
            raise ValueError(f"memory backend must be postgres|sqlite, got {self.backend!r}")
        if self.vector_backend not in ("qdrant", "local"):
            raise ValueError(f"vectors.backend must be qdrant|local, got {self.vector_backend!r}")
        if self.vector_backend == "local" and self.backend != "sqlite":
            raise ValueError("vectors.backend: local requires backend: sqlite")


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _postgres_dsn(pg: dict) -> str:
    if os.environ.get("MEMORY_DSN"):
        return os.environ["MEMORY_DSN"]
    parts = {
        "host": pg.get("host", "postgres"),
        "port": pg.get("port", 5432),
        "dbname": pg.get("dbname", "paiep"),
        "user": pg.get("user", "paiep"),
    }
    password = os.environ.get("POSTGRES_PASSWORD")
    if password:
        parts["password"] = password
    # libpq key=value form; values here never contain spaces/quotes.
    return " ".join(f"{k}={v}" for k, v in parts.items())


def load_memory_config(path: str | None = None, *, with_embed: bool = True) -> MemoryConfig:
    raw = _read_yaml(DEFAULT_PATH) if DEFAULT_PATH.exists() else {}
    overlay = path or os.environ.get("MEMORY_CONFIG")
    if overlay and Path(overlay).resolve() != DEFAULT_PATH.resolve():
        raw = _deep_merge(raw, _read_yaml(Path(overlay)))

    rc, cons = raw.get("recall") or {}, raw.get("consolidation") or {}
    ret, ses = raw.get("retention") or {}, raw.get("session") or {}
    decay = ret.get("decay") or {}
    vec = raw.get("vectors") or {}

    embed = None
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333").rstrip("/")
    if with_embed:
        ingest = load_ingest_config()
        embed, qdrant_url = ingest.service, ingest.qdrant_url

    cfg = MemoryConfig(
        backend=raw.get("backend", "postgres"),
        dsn=_postgres_dsn(raw.get("postgres") or {}),
        sqlite_path=os.environ.get("MEMORY_SQLITE_PATH",
                                   (raw.get("sqlite") or {}).get("path", "/data/memory.db")),
        auto_migrate=bool(raw.get("auto_migrate", True)),
        vector_backend=vec.get("backend", "qdrant"),
        collection=vec.get("collection", "memory_semantic"),
        qdrant_url=qdrant_url,
        async_writes=bool((raw.get("writes") or {}).get("async", True)),
        dedup_threshold=float((raw.get("dedup") or {}).get("semantic_threshold", 0.92)),
        recall=RecallConfig(
            top_k=int(rc.get("top_k", 5)),
            score_threshold=float(rc.get("score_threshold", 0.5)),
            include_global=bool(rc.get("include_global", True)),
        ),
        consolidation=ConsolidationConfig(
            promote_roles=list(cons.get("promote_roles", ["fact"])),
            capture_prefixes=[p.lower() for p in cons.get("capture_prefixes", ["remember:", "note:"])],
            fact_confidence=float(cons.get("fact_confidence", 0.8)),
            summarize_with_llm=bool(cons.get("summarize_with_llm", False)),
            summary_max_tokens=int(cons.get("summary_max_tokens", 200)),
            chat_model=os.environ.get("CHAT_MODEL", cons.get("chat_model", "qwen2.5-coder:7b")),
            chat_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/"),
        ),
        retention=RetentionConfig(
            default_confidence=float(ret.get("default_confidence", 0.7)),
            reinforce_step=float(ret.get("reinforce_step", 0.05)),
            half_life_days=float(decay.get("half_life_days", 90)),
            archive_below=float(decay.get("archive_below", 0.2)),
            exempt_types=list(decay.get("exempt_types", ["preference", "decision"])),
            default_ttl_days={k: float(v) for k, v in (ret.get("default_ttl_days") or {}).items()
                              if v is not None},
            max_active_items=int(ret.get("max_active_items", 5000)),
        ),
        session=SessionConfig(
            ttl_hours=float(ses.get("ttl_hours", 24)),
            max_turns=int(ses.get("max_turns", 200)),
            history_turns=int(ses.get("history_turns", 6)),
            evict_on_close=bool(ses.get("evict_on_close", True)),
        ),
        embed=embed,
    )
    cfg.validate()
    return cfg
