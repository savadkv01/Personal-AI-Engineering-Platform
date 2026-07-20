"""Config loading for the ingestion pipeline.

Reads ``config/embeddings.yaml`` (embedding service, chunking, routing) and
``config/index-catalog.yaml`` (collection -> model + dim + distance), applies
env overrides, and exposes small typed accessors used by the pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServiceConfig:
    provider: str
    base_url: str
    endpoint: str
    model: str
    dim: int
    batch_size: int
    request_timeout: int


@dataclass
class RouteRule:
    exts: list[str]
    doc_type: str
    collection: str


@dataclass
class Config:
    service: ServiceConfig
    chunking: dict[str, dict[str, int]]
    routing: list[RouteRule]
    exclude_dirs: set[str]
    exclude_names: set[str]
    qdrant_url: str
    catalog: dict[str, dict]  # collection -> {embed_model, dim, distance, ...}

    def route(self, path: str) -> RouteRule | None:
        ext = Path(path).suffix.lower()
        for rule in self.routing:
            if ext in rule.exts:
                return rule
        return None

    def chunk_params(self, doc_type: str) -> tuple[int, int]:
        c = self.chunking.get(doc_type) or self.chunking.get("note", {})
        return int(c.get("chunk_size", 512)), int(c.get("chunk_overlap", 64))

    def collection_dim(self, collection: str) -> int | None:
        c = self.catalog.get(collection)
        return int(c["dim"]) if c and "dim" in c else None


def _repo_root() -> Path:
    # rag/ingest/config.py -> repo root is two parents up from the package dir.
    return Path(__file__).resolve().parents[2]


def load_config(
    embeddings_path: str | None = None,
    catalog_path: str | None = None,
) -> Config:
    root = _repo_root()
    emb_path = Path(embeddings_path or os.environ.get("EMBEDDINGS_CONFIG")
                    or root / "config" / "embeddings.yaml")
    cat_path = Path(catalog_path or os.environ.get("INDEX_CATALOG")
                    or root / "config" / "index-catalog.yaml")

    with open(emb_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    with open(cat_path, encoding="utf-8") as fh:
        cat = yaml.safe_load(fh)

    svc = raw["service"]
    service = ServiceConfig(
        provider=svc.get("provider", "ollama"),
        base_url=os.environ.get("OLLAMA_BASE_URL", svc["base_url"]).rstrip("/"),
        endpoint=svc.get("endpoint", "/api/embed"),
        model=os.environ.get("EMBED_MODEL", svc["model"]),
        dim=int(svc["dim"]),
        batch_size=int(svc.get("batch_size", 16)),
        request_timeout=int(svc.get("request_timeout", 120)),
    )

    routing = [
        RouteRule(exts=[e.lower() for e in r["exts"]],
                  doc_type=r["doc_type"], collection=r["collection"])
        for r in raw.get("routing", [])
    ]
    excl = raw.get("exclude", {}) or {}

    qdrant_url = os.environ.get(
        "QDRANT_URL", (cat.get("qdrant", {}) or {}).get("url", "http://127.0.0.1:6333")
    ).rstrip("/")

    collections = {name: (spec or {}) for name, spec in (cat.get("collections") or {}).items()}

    return Config(
        service=service,
        chunking=raw.get("chunking", {}),
        routing=routing,
        exclude_dirs=set(excl.get("dirs", [])),
        exclude_names=set(excl.get("names", [])),
        qdrant_url=qdrant_url,
        catalog=collections,
    )
