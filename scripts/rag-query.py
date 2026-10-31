#!/usr/bin/env python3
"""PAIEP RAG query CLI (M4).

Grounded question-answering over the local knowledge base:
  embed query -> retrieve top-k (scope/tags filters) -> (re-rank) ->
  assemble cited context -> grounded generation.

  docker compose --profile rag run --rm rag "What is PAIEP's default model?"
  docker compose --profile rag run --rm rag "..." --scope project:paiep --tags rag
  docker compose --profile rag run --rm rag "..." --new-session      # prints a session id
  docker compose --profile rag run --rm rag "..." --session <id>     # multi-turn + memory
  python scripts/rag-query.py "..." --collection kb_docs --json --no-memory
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rag.query.config import load_query_config  # noqa: E402
from rag.query.engine import answer  # noqa: E402


def _open_memory():
    """Open the M5 memory service; None (with a warning) if unavailable — fail-soft."""
    try:
        from memory.service import open_service

        return open_service()
    except Exception as exc:  # noqa: BLE001
        print(f"[rag] memory unavailable, continuing without it: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="rag-query", description="PAIEP grounded RAG query (M4/M5).")
    p.add_argument("question", help="the question to answer from local knowledge")
    p.add_argument("--scope", default=None, help="filter: global | project:<name>")
    p.add_argument("--tags", default="", help="comma-separated tag filter (match any)")
    p.add_argument("--collection", default=None, help="collection to query (default: kb_docs)")
    p.add_argument("--top-k", type=int, default=None, help="override top_k")
    p.add_argument("--rerank", dest="rerank", action="store_true", help="force re-rank on")
    p.add_argument("--no-rerank", dest="rerank", action="store_false", help="force re-rank off")
    p.add_argument("--no-memory", action="store_true", help="skip long-term memory recall (M4 only)")
    p.add_argument("--session", default=None, help="continue a session (history + turn logging)")
    p.add_argument("--new-session", action="store_true", help="start a session and print its id")
    p.add_argument("--show-context", action="store_true", help="print citation sources")
    p.add_argument("--json", action="store_true", help="print the answer as JSON")
    p.set_defaults(rerank=None)
    args = p.parse_args(argv)

    cfg = load_query_config()
    if args.top_k is not None:
        cfg.retrieval.top_k = args.top_k
    if args.rerank is not None:
        cfg.rerank.enabled = args.rerank
    if args.no_memory:
        cfg.memory.enabled = False
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    needs_memory = cfg.memory.enabled or args.session or args.new_session
    memory = _open_memory() if needs_memory else None
    if (args.session or args.new_session) and memory is None:
        print("[rag] sessions require the memory service (M5)", file=sys.stderr)
        return 2
    session_id = args.session
    if args.new_session:
        session_id = memory.start_session(scope=args.scope or "global").session_id

    if not args.json:
        print(f"[rag] collection={args.collection or cfg.retrieval.collection} "
              f"top_k={cfg.retrieval.top_k} rerank={cfg.rerank.enabled} "
              f"memory={memory is not None and cfg.memory.enabled} "
              f"model={cfg.generation.model} scope={args.scope or '-'}"
              + (f" session={session_id}" if session_id else ""))

    try:
        result = answer(args.question, scope=args.scope, tags=tags,
                        collection=args.collection, cfg=cfg, memory=memory, session_id=session_id)
    finally:
        if memory is not None:
            memory.close()  # flush async reinforcement / vector writes

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
    print(f"\n[rag] grounded={result.grounded} retrieved={result.retrieved} "
          f"memories={result.memories}" + (f" session={session_id}" if session_id else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
