"""Vector indexes for semantic recall.

- ``QdrantIndex``: the A+ default — ``memory_semantic`` collection (M2), point id = memory_id.
- ``LocalIndex``: Profile A — vectors in the SQLite ``memory_vector`` table, brute-force cosine.

Both expose the same small interface so the service is storage-agnostic (NFR-023).
"""
from __future__ import annotations

import json
import math
from typing import Protocol

from .db import Database


class VectorIndex(Protocol):
    def ensure(self, dim: int) -> None: ...
    def upsert(self, memory_id: str, vector: list[float], payload: dict) -> None: ...
    def delete(self, memory_ids: list[str]) -> None: ...
    def search(self, vector: list[float], scopes: list[str] | None, limit: int,
               threshold: float) -> list[tuple[str, float]]: ...
    def all_ids(self) -> set[str]: ...


class QdrantIndex:
    def __init__(self, url: str, collection: str):
        from qdrant_client import QdrantClient

        self.collection = collection
        self.client = QdrantClient(url=url, timeout=30)

    def ensure(self, dim: int) -> None:
        if not self.client.collection_exists(self.collection):
            raise RuntimeError(f"collection '{self.collection}' missing — run scripts/qdrant-init.sh (M2)")
        size = self.client.get_collection(self.collection).config.params.vectors.size
        if size != dim:
            raise RuntimeError(f"dim mismatch: '{self.collection}' is {size}, embed dim is {dim}")

    def upsert(self, memory_id: str, vector: list[float], payload: dict) -> None:
        from qdrant_client import models as qm

        self.client.upsert(collection_name=self.collection, wait=True,
                           points=[qm.PointStruct(id=memory_id, vector=vector, payload=payload)])

    def delete(self, memory_ids: list[str]) -> None:
        from qdrant_client import models as qm

        if memory_ids:
            self.client.delete(collection_name=self.collection, wait=True,
                               points_selector=qm.PointIdsList(points=list(memory_ids)))

    def search(self, vector: list[float], scopes: list[str] | None, limit: int,
               threshold: float) -> list[tuple[str, float]]:
        from qdrant_client import models as qm

        flt = None
        if scopes:
            flt = qm.Filter(must=[qm.FieldCondition(key="scope", match=qm.MatchAny(any=scopes))])
        res = self.client.query_points(collection_name=self.collection, query=vector,
                                       query_filter=flt, limit=limit, score_threshold=threshold,
                                       with_payload=False)
        return [(str(p.id), float(p.score)) for p in res.points]

    def all_ids(self) -> set[str]:
        ids: set[str] = set()
        offset = None
        while True:
            points, offset = self.client.scroll(collection_name=self.collection, limit=512,
                                                offset=offset, with_payload=False, with_vectors=False)
            ids.update(str(p.id) for p in points)
            if offset is None:
                return ids


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class LocalIndex:
    def __init__(self, db: Database):
        if db.backend != "sqlite":
            raise ValueError("LocalIndex requires the sqlite backend")
        self.db = db

    def ensure(self, dim: int) -> None:
        row = self.db.query_one("SELECT vector_json FROM memory_vector LIMIT 1")
        if row and len(json.loads(row["vector_json"])) != dim:
            raise RuntimeError("dim mismatch: local memory vectors were built with another model")

    def upsert(self, memory_id: str, vector: list[float], payload: dict) -> None:
        self.db.execute(
            "INSERT INTO memory_vector (memory_id, scope, vector_json) VALUES (?, ?, ?) "
            "ON CONFLICT (memory_id) DO UPDATE SET scope = excluded.scope, "
            "vector_json = excluded.vector_json",
            (memory_id, payload["scope"], json.dumps(vector)))

    def delete(self, memory_ids: list[str]) -> None:
        for mid in memory_ids:
            self.db.execute("DELETE FROM memory_vector WHERE memory_id = ?", (mid,))

    def search(self, vector: list[float], scopes: list[str] | None, limit: int,
               threshold: float) -> list[tuple[str, float]]:
        if scopes:
            marks = ",".join("?" * len(scopes))
            rows = self.db.query(f"SELECT memory_id, vector_json FROM memory_vector "
                                 f"WHERE scope IN ({marks})", scopes)
        else:
            rows = self.db.query("SELECT memory_id, vector_json FROM memory_vector")
        scored = [(r["memory_id"], _cosine(vector, json.loads(r["vector_json"]))) for r in rows]
        scored = [s for s in scored if s[1] >= threshold]
        return sorted(scored, key=lambda s: s[1], reverse=True)[:limit]

    def all_ids(self) -> set[str]:
        return {r["memory_id"] for r in self.db.query("SELECT memory_id FROM memory_vector")}
