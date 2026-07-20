#!/usr/bin/env python3
"""PAIEP RAG query CLI (M4).

Grounded question-answering over the local knowledge base:
  embed query -> retrieve top-k (scope/tags filters) -> (re-rank) ->
  assemble cited context -> grounded generation.

  docker compose --profile rag run --rm rag "What is PAIEP's default model?"
  docker compose --profile rag run --rm rag "..." --scope project:paiep --tags rag
  python scripts/rag-query.py "..." --collection kb_docs --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rag.query.config import load_query_config  # noqa: E402
from rag.query.engine import answer  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rag-query", description="PAIEP grounded RAG query (M4).")
    p.add_argument("question", help="the question to answer from local knowledge")
    p.add_argument("--scope", default=None, help="filter: global | project:<name>")
    p.add_argument("--tags", default="", help="comma-separated tag filter (match any)")
    p.add_argument("--collection", default=None, help="collection to query (default: kb_docs)")
    p.add_argument("--top-k", type=int, default=None, help="override top_k")
    p.add_argument("--rerank", dest="rerank", action="store_true", help="force re-rank on")
    p.add_argument("--no-rerank", dest="rerank", action="store_false", help="force re-rank off")
    p.add_argument("--show-context", action="store_true", help="print citation sources")
    p.add_argument("--json", action="store_true", help="print the answer as JSON")
    p.set_defaults(rerank=None)
    args = p.parse_args(argv)

    cfg = load_query_config()
    if args.top_k is not None:
        cfg.retrieval.top_k = args.top_k
    if args.rerank is not None:
        cfg.rerank.enabled = args.rerank
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if not args.json:
        print(f"[rag] collection={args.collection or cfg.retrieval.collection} "
              f"top_k={cfg.retrieval.top_k} rerank={cfg.rerank.enabled} "
              f"model={cfg.generation.model} scope={args.scope or '-'}")

    result = answer(args.question, scope=args.scope, tags=tags,
                    collection=args.collection, cfg=cfg)

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("\n=== answer ===")
    print(result.answer)
    if result.citations:
        print("\n=== citations ===")
        for c in result.citations:
            print(f"  [{c.n}] {c.title}  <{c.source}>  (score={c.score})")
    else:
        print("\n(no sources — answer not grounded)")
    print(f"\n[rag] grounded={result.grounded} retrieved={result.retrieved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
