#!/usr/bin/env python3
"""PAIEP M5 memory benchmark — write latency, async sync time, recall latency + hit@k.

Uses an isolated scope (``project:m5-bench``) and deletes everything it creates.

  docker compose --profile memory run --rm --entrypoint python memory /app/benchmarks/m5/bench.py
  ... /app/benchmarks/m5/bench.py --threads 4 --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from memory.service import open_service  # noqa: E402

SCOPE = "project:m5-bench"


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 1)


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(prog="m5-bench")
    ap.add_argument("--set", default=str(here / "memories.yaml"))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--threads", type=int, default=4, help="concurrent recall workers (load)")
    ap.add_argument("--rounds", type=int, default=3, help="recall passes over the query set")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)

    spec = yaml.safe_load(open(args.set, encoding="utf-8"))
    svc = open_service()
    created: list[str] = []
    try:
        # 1) writes: remember() returns after the SQL insert; vectors sync on the worker.
        key_to_id: dict[str, str] = {}
        write_ms = []
        t_all = time.perf_counter()
        for m in spec["memories"]:
            t0 = time.perf_counter()
            item = svc.remember(m["content"], type=m.get("type", "fact"), scope=SCOPE)
            write_ms.append((time.perf_counter() - t0) * 1000)
            key_to_id[m["key"]] = item.memory_id
            created.append(item.memory_id)
        svc.flush()
        sync_total_s = time.perf_counter() - t_all

        # 2) recall quality (hit@k) — sequential, scope-isolated
        hits, rows = 0, []
        for q in spec["queries"]:
            res = svc.recall(q["q"], scope=SCOPE, top_k=args.k, include_global=False)
            got = [r.item.memory_id for r in res]
            hit = key_to_id[q["expect"]] in got
            hits += hit
            rows.append({"q": q["q"], "expect": q["expect"], "hit": hit,
                         "top_score": round(res[0].score, 3) if res else None})
        neg = [svc.recall(q, scope=SCOPE, top_k=args.k, include_global=False)
               for q in spec.get("negatives", [])]
        false_pos = sum(1 for r in neg if r)

        # 3) recall latency under concurrent load
        lat: list[float] = []
        lock = threading.Lock()
        queries = [q["q"] for q in spec["queries"]] * args.rounds

        def worker(chunk: list[str]) -> None:
            local = open_service()
            try:
                for q in chunk:
                    t0 = time.perf_counter()
                    local.recall(q, scope=SCOPE, top_k=args.k)
                    with lock:
                        lat.append((time.perf_counter() - t0) * 1000)
            finally:
                local.close()

        threads = [threading.Thread(target=worker, args=(queries[i::args.threads],))
                   for i in range(args.threads)]
        t_load = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        load_s = time.perf_counter() - t_load
        consistent = svc.check()["consistent"]
    finally:
        for mid in created:
            svc.delete(mid)
        svc.close()

    n = len(spec["queries"])
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "backend": svc.cfg.backend, "vectors": svc.cfg.vector_backend,
        "embed_model": svc.cfg.embed.model if svc.cfg.embed else None,
        "memories": len(created), "queries": n, "k": args.k,
        "write_ms_p50": pct(write_ms, 50), "write_ms_p95": pct(write_ms, 95),
        "write_plus_async_sync_total_s": round(sync_total_s, 2),
        "hit_at_k": round(hits / n, 4) if n else 0.0,
        "negatives": len(spec.get("negatives", [])), "negative_false_positives": false_pos,
        "recall_threads": args.threads, "recall_requests": len(lat),
        "recall_ms_p50": pct(lat, 50), "recall_ms_p95": pct(lat, 95),
        "recall_throughput_rps": round(len(lat) / load_s, 1) if load_s else None,
        "consistent_after": consistent,
    }
    if not args.no_save:
        out = here / "results" / f"memory-bench_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"  # noqa: UP017
        out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
        summary["saved"] = str(out.relative_to(here.parent.parent))

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, indent=2))
    else:
        for r in rows:
            print(f"  [{'OK ' if r['hit'] else 'MISS'}] {r['q']}  (top={r['top_score']})")
        for k, v in summary.items():
            print(f"  {k:32} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
