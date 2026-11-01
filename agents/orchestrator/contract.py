"""Inter-agent communication contract (Phase 07 §5).

Every hand-off is a ``request`` message carrying enforced ``constraints``; every
agent result is a ``response`` (or ``review`` / ``block``). Messages carry
references (paths, memory ids, citations), not payloads, and live in the LangGraph
state (persisted by the checkpointer) and the JSONL trace.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

INTENTS = ("request", "response", "review", "handoff", "status", "block", "clarify")
STATUSES = ("ok", "partial", "failed", "blocked")
SEVERITIES = ("none", "info", "low", "med", "high")
_SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def severity_at_least(sev: str | None, threshold: str) -> bool:
    return _SEV_RANK.get(sev or "none", 0) >= _SEV_RANK.get(threshold, 4)


def message(*, task_id: str, sender: str, to: str, intent: str, goal: str = "",
            parent_id: str | None = None, inputs: list[str] | None = None,
            constraints: dict | None = None, artifacts: list[str] | None = None,
            status: str | None = None, severity: str | None = None,
            citations: list[str] | None = None, context_refs: list[str] | None = None) -> dict:
    if intent not in INTENTS:
        raise ValueError(f"intent must be one of {INTENTS}")
    return {
        "msg_id": str(uuid.uuid4()), "task_id": task_id, "parent_id": parent_id,
        "from": sender, "to": to, "intent": intent, "goal": goal,
        "inputs": inputs or [], "context_refs": context_refs or [],
        "constraints": constraints or {}, "artifacts": artifacts or [],
        "status": status, "severity": severity, "citations": citations or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
    }
