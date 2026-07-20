#!/usr/bin/env python3
"""PAIEP M4 retrieval eval — recall@k on a small labeled Q/A set.

For each labeled question, retrieve top-k chunks and check whether the expected
source file appears. Reports recall@k (measured, not invented). Retrieval-only
by default (fast); pass --answers to also generate grounded answers and check
that a citation is produced.

  docker compose --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py
  docker compose --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py --k 4 --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from rag.query.config import load_query_config  # noqa: E402
from rag.query.engine import answer  # noqa: E402
from rag.query.retriever import retrieve  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    p = argparse.ArgumentParser(prog="m4-eval", description="Retrieval recall@k eval.")
    p.add_argument("--qa", default=str(here / "qa.yaml"), help="labeled Q/A YAML")
    p.add_argument("--k", type=int, default=None, help="top-k (default: config top_k)")
    p.add_argument("--answers", action="store_true", help="also generate + check citations")
    p.add_argument("--json", action="store_true", help="print JSON only")
    args = p.parse_args(argv)

    cfg = load_query_config()
    k = args.k or cfg.retrieval.top_k
    with open(args.qa, encoding="utf-8") as fh:
        qa = yaml.safe_load(fh)["questions"]

    rows = []
    hits = 0
    answered_ok = 0
    for item in qa:
        q, expected = item["q"], item["expected_source"]
        chunks = retrieve(q, cfg, limit=k)
        got = [c.source for c in chunks]
        hit = expected in got
        hits += int(hit)
        row = {"q": q, "expected": expected, "hit": hit,
               "top_sources": got, "top_score": round(chunks[0].score, 4) if chunks else None}
        if args.answers:
            res = answer(q, cfg=cfg)
            cited = [c.source for c in res.citations]
            row["answer_grounded"] = res.grounded
            row["answer_cites_expected"] = expected in cited
            answered_ok += int(res.grounded and expected in cited)
        rows.append(row)

    n = len(qa)
    summary = {
        "n": n, "k": k,
        "recall_at_k": round(hits / n, 4) if n else 0.0,
        "collection": cfg.retrieval.collection,
        "embed_model": cfg.embed.model,
    }
    if args.answers:
        summary["answer_citation_accuracy"] = round(answered_ok / n, 4) if n else 0.0

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, indent=2))
        return 0

    print(f"[m4-eval] collection={summary['collection']} embed={summary['embed_model']} k={k} n={n}")
    for r in rows:
        mark = "OK " if r["hit"] else "MISS"
        print(f"  [{mark}] {r['q']}")
        print(f"         expected={r['expected']}  top={r['top_sources']}")
        if args.answers:
            print(f"         grounded={r['answer_grounded']} cites_expected={r['answer_cites_expected']}")
    print(f"\n[m4-eval] recall@{k} = {summary['recall_at_k']}  ({hits}/{n})")
    if args.answers:
        print(f"[m4-eval] answer citation accuracy = {summary['answer_citation_accuracy']}  ({answered_ok}/{n})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
