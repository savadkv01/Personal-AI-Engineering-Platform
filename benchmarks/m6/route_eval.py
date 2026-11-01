#!/usr/bin/env python3
"""PAIEP M6 routing eval — supervisor routing accuracy + planner latency (no execution).

  docker compose --profile agents run --rm --entrypoint python agents \
    /workspace/benchmarks/m6/route_eval.py [--json] [--no-save]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from agents.orchestrator.runtime import open_runtime  # noqa: E402
from agents.orchestrator.supervisor import plan_task  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(prog="m6-route-eval")
    ap.add_argument("--set", default=str(here / "routes.yaml"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)

    routes = yaml.safe_load(open(args.set, encoding="utf-8"))["routes"]
    rt = open_runtime(checkpoint="memory", with_memory=False)
    rows, hits = [], 0
    try:
        for r in routes:
            t0 = time.perf_counter()
            out = plan_task(rt, r["task"], "project:paiep")
            secs = round(time.perf_counter() - t0, 1)
            got = out["steps"][0]["agent"] if out["steps"] else None
            ok = got == r["expect"]
            hits += ok
            rows.append({"task": r["task"], "expect": r["expect"], "got": got, "ok": ok,
                         "plan": [s["agent"] for s in out["steps"]], "method": out["method"], "secs": secs})
            if not args.json:
                mark = "OK " if ok else "MISS"
                print(f"  [{mark}] {secs:6.1f}s {got!s:<21} <- {r['task'][:70]}", flush=True)
    finally:
        rt.close()

    calls = [e for e in rt.trace.events if e["kind"] == "llm.call"]
    secs = sorted(x["secs"] for x in rows)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "model": calls[0]["model"] if calls else None, "n": len(rows),
        "routing_accuracy": round(hits / len(rows), 3) if rows else 0.0,
        "llm_plans": sum(1 for x in rows if x["method"] == "llm"),
        "planner_secs_median": secs[len(secs) // 2] if secs else None,
        "planner_secs_max": secs[-1] if secs else None,
        "prompt_tokens_median": sorted(c["prompt_tokens"] for c in calls)[len(calls) // 2] if calls else None,
    }
    if not args.no_save:
        out = here / "results" / f"route-eval_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"  # noqa: UP017
        out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
        summary["saved"] = str(out.relative_to(here.parent.parent))
    print(json.dumps({"summary": summary, "rows": rows} if args.json else summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
