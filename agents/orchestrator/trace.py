"""JSONL audit trail per task (one file per thread id). Langfuse arrives in M9."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path


class TraceSink:
    def __init__(self, directory: str | None):
        self.dir = Path(directory) if directory else None
        self.events: list[dict] = []          # in-memory copy (tests / CLI summaries)
        self.task_id: str | None = None
        if self.dir:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.dir = None

    def bind(self, task_id: str) -> None:
        self.task_id = task_id

    def __call__(self, kind: str, data: dict) -> None:
        # Reserved fields are written last so event data can never overwrite them.
        ev = {**data, "ts": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
              "t": round(time.time(), 3), "task_id": self.task_id, "kind": kind}
        self.events.append(ev)
        if self.dir and self.task_id:
            with open(self.dir / f"{self.task_id}.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, default=str) + "\n")

    def read(self, task_id: str) -> list[dict]:
        if not self.dir:
            return [e for e in self.events if e.get("task_id") == task_id]
        p = self.dir / f"{task_id}.jsonl"
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    def tasks(self) -> list[dict]:
        """Latest status per task, newest first."""
        if not self.dir:
            return []
        out = []
        for p in self.dir.glob("*.jsonl"):
            evs = self.read(p.stem)
            if not evs:
                continue
            start = next((e for e in evs if e["kind"] == "task.start"), evs[0])
            last = next((e for e in reversed(evs) if e["kind"] in ("task.end", "approval.request")), None)
            if last is None:
                status = "running"
            elif last["kind"] == "approval.request":
                status = "awaiting_approval"
            else:
                status = last.get("status", "unknown")
            out.append({"task_id": p.stem, "started": start.get("ts"), "task": start.get("task", ""),
                        "status": status})
        return sorted(out, key=lambda r: r["started"] or "", reverse=True)
