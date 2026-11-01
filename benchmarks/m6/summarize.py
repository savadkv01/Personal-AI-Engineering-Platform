#!/usr/bin/env python3
"""Summarise M6 agent task traces (JSONL audit trail) into latency/budget metrics.

  docker compose --profile agents run --rm --entrypoint python agents \
    /workspace/benchmarks/m6/summarize.py <task_id> [<task_id> ...] [--save]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
from datetime import datetime, timezone


def summarize(events: list[dict]) -> dict:
    start = next((e for e in events if e["kind"] == "task.start"), {})
    end = next((e for e in reversed(events) if e["kind"] == "task.end"), {})
    calls = [e for e in events if e["kind"] == "llm.call"]
    appr = [e for e in events if e["kind"] in ("approval.request", "approval.decision")]
    per_agent: dict[str, dict] = {}
    for c in calls:
        a = per_agent.setdefault(c["agent"], {"calls": 0, "secs": 0.0, "prompt_tokens": 0,
                                              "completion_tokens": 0})
        a["calls"] += 1
        a["secs"] = round(a["secs"] + c["latency_ms"] / 1000, 1)
        a["prompt_tokens"] += c.get("prompt_tokens", 0)
        a["completion_tokens"] += c.get("completion_tokens", 0)
    # Machine time excludes the human approval wait.
    wait = (appr[1]["t"] - appr[0]["t"]) if len(appr) >= 2 else 0.0
    total = (end.get("t", 0) - start.get("t", 0)) if end and start else None
    return {
        "task_id": start.get("task_id"), "task": start.get("task", "")[:120], "status": end.get("status"),
        "agent_steps": end.get("agent_steps"), "llm_calls": len(calls),
        "machine_secs": round(total - wait, 1) if total is not None else None,
        "llm_secs": round(sum(c["latency_ms"] for c in calls) / 1000, 1),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in calls),
        "max_call_secs": round(max((c["latency_ms"] for c in calls), default=0) / 1000, 1),
        "policy_denials": sum(1 for e in events if e["kind"] == "policy.deny"),
        "tool_calls": sum(1 for e in events if e["kind"] == "tool.call"),
        "applied": end.get("applied", []), "per_agent": per_agent,
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="m6-summarize")
    ap.add_argument("task_ids", nargs="+")
    ap.add_argument("--dir", default=os.environ.get("AGENT_TRACE_DIR", "/data/agent-traces"))
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    rows = []
    for tid in args.task_ids:
        p = pathlib.Path(args.dir) / f"{tid}.jsonl"
        evs = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        rows.append(summarize(evs))
    print(json.dumps(rows, indent=2))
    if args.save:
        here = pathlib.Path(__file__).resolve().parent
        out = here / "results" / f"task-latency_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"  # noqa: UP017
        out.write_text(json.dumps(rows, indent=2))
        print(f"saved {out.relative_to(here.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
