"""CLI for the memory service. Wrapped by ``scripts/memory-cli.py``.

  memory add "Prefer pytest over unittest" --type preference --scope project:paiep
  memory recall "which test framework?" --scope project:paiep
  memory list --scope global            memory edit <id> --content "..."
  memory delete <id>                    memory supersede <id> "newer fact"
  memory session start --scope project:paiep
  memory session add <sid> fact "The API uses port 8081"
  memory session close <sid> [--summarize]
  memory maintain [--dry-run]           memory check [--repair]
  memory migrate status|up|down         memory stats
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from .config import load_memory_config
from .db import Database, applied_versions, migrate_down, migrate_up
from .models import MEMORY_TYPES, TURN_ROLES
from .service import MemoryService


def _tags(s: str | None) -> list[str] | None:
    return None if s is None else [t.strip() for t in s.split(",") if t.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="memory", description="PAIEP memory service (M5).")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--config", default=None, help="memory config overlay (default: MEMORY_CONFIG)")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("migrate", help="schema migrations")
    m.add_argument("action", choices=["status", "up", "down"])
    m.add_argument("--steps", type=int, default=1, help="down: migrations to revert")

    a = sub.add_parser("add", help="remember a long-term memory")
    a.add_argument("content")
    a.add_argument("--type", default="fact", choices=MEMORY_TYPES)
    a.add_argument("--scope", default="global")
    a.add_argument("--tags", default=None)
    a.add_argument("--confidence", type=float, default=None)
    a.add_argument("--ttl-days", type=float, default=None)

    ls = sub.add_parser("list", help="list memories")
    ls.add_argument("--scope", default=None)
    ls.add_argument("--type", default=None, choices=MEMORY_TYPES)
    ls.add_argument("--status", default="active", help="active|archived|superseded|merged|expired|all")
    ls.add_argument("--limit", type=int, default=50)

    g = sub.add_parser("get", help="show one memory")
    g.add_argument("memory_id")

    e = sub.add_parser("edit", help="edit a memory (FR-013)")
    e.add_argument("memory_id")
    e.add_argument("--content")
    e.add_argument("--type", choices=MEMORY_TYPES)
    e.add_argument("--scope")
    e.add_argument("--tags")
    e.add_argument("--confidence", type=float)
    e.add_argument("--status", choices=["active", "archived"])
    e.add_argument("--clear-expiry", action="store_true")

    s = sub.add_parser("supersede", help="replace a memory with a newer one (keeps history)")
    s.add_argument("memory_id")
    s.add_argument("content")

    d = sub.add_parser("delete", help="hard-delete a memory + its vector (FR-013)")
    d.add_argument("memory_id")

    r = sub.add_parser("recall", help="semantic, scope-filtered recall")
    r.add_argument("query")
    r.add_argument("--scope", default=None)
    r.add_argument("--top-k", type=int, default=None)
    r.add_argument("--threshold", type=float, default=None)
    r.add_argument("--no-global", action="store_true", help="exclude global memories from project recall")

    ar = sub.add_parser("archive-scope", help="archive all memories of a scope (project done)")
    ar.add_argument("scope")

    mt = sub.add_parser("maintain", help="apply the forgetting policy")
    mt.add_argument("--dry-run", action="store_true")

    sub.add_parser("sync", help="drain pending vector writes (outbox)")
    ck = sub.add_parser("check", help="SQL store vs vector index consistency")
    ck.add_argument("--repair", action="store_true")
    sub.add_parser("stats", help="counts by status/scope/session")

    ss = sub.add_parser("session", help="session memory")
    ssub = ss.add_subparsers(dest="scmd", required=True)
    st = ssub.add_parser("start")
    st.add_argument("--scope", default="global")
    st.add_argument("--task-id", default=None)
    sa = ssub.add_parser("add")
    sa.add_argument("session_id")
    sa.add_argument("role", choices=TURN_ROLES)
    sa.add_argument("content")
    sh = ssub.add_parser("show")
    sh.add_argument("session_id")
    sc = ssub.add_parser("close", help="consolidate to long-term + evict turns")
    sc.add_argument("session_id")
    sc.add_argument("--summarize", action="store_true", default=None, help="LLM summary (slow on CPU)")
    sl = ssub.add_parser("list")
    sl.add_argument("--status", default=None, choices=["open", "closed", "expired"])
    return p


def _emit(args, data, text: str | None = None) -> None:
    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(text if text is not None else json.dumps(data, indent=2, default=str))


def _fmt_item(d: dict, score: float | None = None) -> str:
    lead = f"{score:.3f} " if score is not None else ""
    return (f"{lead}{d['memory_id']}  [{d['type']}/{d['scope']}] conf={d['confidence']} "
            f"status={d['status']}\n    {d['content']}")


def _migrate(args) -> int:
    cfg = load_memory_config(args.config, with_embed=False)
    target = cfg.sqlite_path if cfg.backend == "sqlite" else cfg.dsn
    db = Database(cfg.backend, target)
    try:
        if args.action == "up":
            done = migrate_up(db, datetime.now(timezone.utc))  # noqa: UP017
            _emit(args, {"applied": done}, f"[memory] applied: {done or 'none (up to date)'}")
        elif args.action == "down":
            done = migrate_down(db, args.steps)
            _emit(args, {"reverted": done}, f"[memory] reverted: {done or 'none'}")
        else:
            v = applied_versions(db)
            _emit(args, {"backend": cfg.backend, "applied": v}, f"[memory] {cfg.backend} applied={v}")
    finally:
        db.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "migrate":
        return _migrate(args)

    svc = MemoryService(load_memory_config(args.config))
    try:
        return _dispatch(args, svc)
    except KeyError as exc:
        print(f"[memory] not found: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"[memory] {exc}", file=sys.stderr)
        return 2
    finally:
        svc.close()  # flushes async vector writes before exit


def _dispatch(args, svc: MemoryService) -> int:
    if args.cmd == "add":
        t0 = time.perf_counter()
        item = svc.remember(args.content, type=args.type, scope=args.scope, tags=_tags(args.tags),
                            confidence=args.confidence, ttl_days=args.ttl_days)
        ms = (time.perf_counter() - t0) * 1000
        _emit(args, {**item.as_dict(), "write_ms": round(ms, 2)},
              f"[memory] stored {item.memory_id} ({ms:.1f} ms; vector sync async)")
    elif args.cmd == "list":
        items = svc.list_items(scope=args.scope, type=args.type,
                               status=None if args.status == "all" else args.status, limit=args.limit)
        data = [i.as_dict() for i in items]
        _emit(args, data, "\n".join(_fmt_item(d) for d in data) or "(no memories)")
    elif args.cmd == "get":
        item = svc.get(args.memory_id)
        if item is None:
            raise KeyError(args.memory_id)
        _emit(args, item.as_dict())
    elif args.cmd == "edit":
        item = svc.edit(args.memory_id, content=args.content, type=args.type, scope=args.scope,
                        tags=_tags(args.tags), confidence=args.confidence, status=args.status,
                        clear_expiry=args.clear_expiry)
        _emit(args, item.as_dict(), "[memory] updated\n" + _fmt_item(item.as_dict()))
    elif args.cmd == "supersede":
        item = svc.supersede(args.memory_id, args.content)
        _emit(args, item.as_dict(), f"[memory] {args.memory_id} superseded by {item.memory_id}")
    elif args.cmd == "delete":
        ok = svc.delete(args.memory_id)
        _emit(args, {"deleted": ok}, f"[memory] deleted={ok}")
        return 0 if ok else 2
    elif args.cmd == "recall":
        t0 = time.perf_counter()
        hits = svc.recall(args.query, scope=args.scope, top_k=args.top_k, threshold=args.threshold,
                          include_global=False if args.no_global else None)
        ms = (time.perf_counter() - t0) * 1000
        data = {"query": args.query, "scope": args.scope, "recall_ms": round(ms, 1),
                "results": [h.as_dict() for h in hits]}
        text = "\n".join(_fmt_item(h.item.as_dict(), h.score) for h in hits) or "(no matches)"
        _emit(args, data, f"{text}\n[memory] {len(hits)} result(s) in {ms:.0f} ms")
    elif args.cmd == "archive-scope":
        n = svc.archive_scope(args.scope)
        _emit(args, {"archived": n}, f"[memory] archived {n} memories in {args.scope}")
    elif args.cmd == "maintain":
        _emit(args, svc.maintain(dry_run=args.dry_run))
    elif args.cmd == "sync":
        n = svc.sync_pending()
        _emit(args, {"synced": n}, f"[memory] synced {n} pending item(s)")
    elif args.cmd == "check":
        rep = svc.check(repair=args.repair)
        _emit(args, rep)
        return 0 if rep["consistent"] or rep["repaired"] else 1
    elif args.cmd == "stats":
        _emit(args, svc.stats())
    elif args.cmd == "session":
        return _session(args, svc)
    return 0


def _session(args, svc: MemoryService) -> int:
    if args.scmd == "start":
        s = svc.start_session(scope=args.scope, task_id=args.task_id)
        _emit(args, s.as_dict(), s.session_id)
    elif args.scmd == "add":
        t = svc.add_turn(args.session_id, args.role, args.content)
        _emit(args, t.as_dict(), f"[memory] turn {t.seq} ({t.role}) added")
    elif args.scmd == "show":
        s = svc.get_session(args.session_id)
        if s is None:
            raise KeyError(args.session_id)
        turns = [t.as_dict() for t in svc.get_turns(args.session_id)]
        text = "\n".join(f"  {t['seq']:>3} {t['role']:<9} {t['content']}" for t in turns)
        _emit(args, {**s.as_dict(), "turns": turns},
              f"{s.session_id} [{s.scope}] status={s.status}\n{text or '  (no turns)'}")
    elif args.scmd == "close":
        _emit(args, svc.close_session(args.session_id, summarize=args.summarize))
    elif args.scmd == "list":
        data = [s.as_dict() for s in svc.list_sessions(status=args.status)]
        text = "\n".join(f"{d['session_id']}  {d['status']:<7} {d['scope']}  {d['updated_at']}"
                         for d in data)
        _emit(args, data, text or "(no sessions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
