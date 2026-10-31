"""Memory domain types."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime

MEMORY_TYPES = ("fact", "preference", "decision", "entity", "progress", "task_summary", "note")
STATUSES = ("active", "archived", "superseded", "merged", "expired")
TURN_ROLES = ("user", "assistant", "fact", "system")

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def validate_scope(scope: str) -> str:
    if scope == "global" or (scope.startswith("project:") and len(scope) > len("project:")):
        return scope
    raise ValueError(f"scope must be 'global' or 'project:<name>', got {scope!r}")


@dataclass
class MemoryItem:
    memory_id: str
    type: str
    scope: str
    content: str
    content_hash: str
    confidence: float
    status: str
    vector_status: str
    created_at: datetime
    updated_at: datetime
    last_reinforced_at: datetime
    tags: list[str] = field(default_factory=list)
    source: str | None = None
    superseded_by: str | None = None
    reinforce_count: int = 0
    expires_at: datetime | None = None

    @classmethod
    def from_row(cls, r: dict) -> MemoryItem:
        return cls(
            memory_id=r["memory_id"], type=r["type"], scope=r["scope"], content=r["content"],
            content_hash=r["content_hash"], confidence=float(r["confidence"]), status=r["status"],
            vector_status=r["vector_status"], created_at=r["created_at"], updated_at=r["updated_at"],
            last_reinforced_at=r["last_reinforced_at"], tags=json.loads(r.get("tags_json") or "[]"),
            source=r.get("source"), superseded_by=r.get("superseded_by"),
            reinforce_count=int(r.get("reinforce_count") or 0), expires_at=r.get("expires_at"),
        )

    def effective_confidence(self, now: datetime, half_life_days: float,
                             exempt_types: list[str]) -> float:
        """Confidence decayed by time since last reinforcement (computed, never compounded)."""
        if self.type in exempt_types or half_life_days <= 0:
            return self.confidence
        days = max(0.0, (now - self.last_reinforced_at).total_seconds() / 86400)
        return self.confidence * 0.5 ** (days / half_life_days)

    def as_dict(self) -> dict:
        return {
            "memory_id": self.memory_id, "type": self.type, "scope": self.scope,
            "content": self.content, "tags": self.tags, "source": self.source,
            "confidence": round(self.confidence, 4), "status": self.status,
            "superseded_by": self.superseded_by, "vector_status": self.vector_status,
            "reinforce_count": self.reinforce_count,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
            "last_reinforced_at": self.last_reinforced_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Recalled:
    item: MemoryItem
    score: float

    def as_dict(self) -> dict:
        return {"score": round(self.score, 4), **self.item.as_dict()}


@dataclass
class Session:
    session_id: str
    scope: str
    status: str
    created_at: datetime
    updated_at: datetime
    task_id: str | None = None
    expires_at: datetime | None = None
    summary_memory_id: str | None = None

    @classmethod
    def from_row(cls, r: dict) -> Session:
        return cls(session_id=r["session_id"], scope=r["scope"], status=r["status"],
                   created_at=r["created_at"], updated_at=r["updated_at"], task_id=r.get("task_id"),
                   expires_at=r.get("expires_at"), summary_memory_id=r.get("summary_memory_id"))

    def as_dict(self) -> dict:
        return {"session_id": self.session_id, "task_id": self.task_id, "scope": self.scope,
                "status": self.status, "summary_memory_id": self.summary_memory_id,
                "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
                "expires_at": self.expires_at.isoformat() if self.expires_at else None}


@dataclass
class Turn:
    turn_id: str
    session_id: str
    seq: int
    role: str
    content: str
    created_at: datetime

    @classmethod
    def from_row(cls, r: dict) -> Turn:
        return cls(turn_id=r["turn_id"], session_id=r["session_id"], seq=int(r["seq"]),
                   role=r["role"], content=r["content"], created_at=r["created_at"])

    def as_dict(self) -> dict:
        return {"seq": self.seq, "role": self.role, "content": self.content,
                "created_at": self.created_at.isoformat()}
