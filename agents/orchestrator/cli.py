"""CLI for the agent orchestrator. Wrapped by ``scripts/agent-cli.py``.

  agent personas [--all]                     agent route "task"
  agent run "task" [--scope project:x] [--agent software_engineer] [--no-prompt]
  agent approve <task_id> [--path p ...] [--no-tests]      agent reject <task_id>
  agent status <task_id>    agent trace <task_id>    agent list
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .runtime import open_runtime
from .supervisor import plan_task


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent", description="PAIEP multi-agent orchestrator (M6).")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("personas", help="list personas")
    ps.add_argument("--all", action="store_true", help="include disabled personas")
    r = sub.add_parser("route", help="show the supervisor's plan without running it")
    r.add_argument("task")
    r.add_argument("--scope", default="global")
    run = sub.add_parser("run", help="run a task through the supervisor")
    run.add_argument("task")
    run.add_argument("--scope", default="global", help="global | project:<name>")
    run.add_argument("--agent", default=None, help="skip planning; send to one persona")
    run.add_argument("--no-prompt", action="store_true",
                     help="never ask interactively; leave approval pending")
    a = sub.add_parser("approve", help="approve pending changes and apply them")
    a.add_argument("task_id")
    a.add_argument("--path", action="append", default=None, help="approve only these paths (repeatable)")
    a.add_argument("--no-tests", action="store_true", help="do not run queued test actions")
    rj = sub.add_parser("reject", help="reject pending changes (nothing is written)")
    rj.add_argument("task_id")
    st = sub.add_parser("status", help="show a task")
    st.add_argument("task_id")
    tr = sub.add_parser("trace", help="print a task's audit trail")
    tr.add_argument("task_id")
    sub.add_parser("list", help="recent tasks")
    return p


def _progress(node: str, upd) -> None:
    if not isinstance(upd, dict):
        return
    if node == "plan":
        steps = " -> ".join(s["agent"] for s in upd.get("plan", [])) or "(none)"
        clarify = f" | clarify: {upd['clarify']}" if upd.get("clarify") else ""
        print(f"[plan] {upd.get('method')}: {steps}{clarify}", flush=True)
    elif node == "execute" and upd.get("results"):
        r = upd["results"][-1]
        sev = f" severity={r['severity']}" if r.get("severity") not in (None, "none") else ""
        print(f"[{r['agent']}] {r['status']}{sev} | {r['llm_calls']} call(s) | "
              f"{r['latency_ms'] / 1000:.0f}s | "
              f"files={[p['path'] for p in r['proposals']]} denied={len(r['denied'])}", flush=True)
    elif node == "execute" and upd.get("truncated"):
        print(f"[budget] {upd.get('reason')}", flush=True)
    elif node == "gate" and upd.get("gate_scheduled"):
        issues = upd.get("gate_issues") or []
        print(f"[gate] scheduled: {upd['gate_scheduled']}"
              + (f" | issues: {issues}" if issues else ""), flush=True)


def _print_approval(v: dict) -> None:
    req = v["approval_request"] or {}
    print("\n=== approval required ===")
    for r in req.get("reviews", []):
        print(f"  review {r['agent']}: severity={r['severity']} — {r['summary'][:200]}")
    for issue in req.get("issues", []):
        print(f"  ⚠️ open gate issue: {issue}")
    for p in req.get("proposals", []):
        print(f"\n--- {p['path']} ({'new' if p['new'] else 'modified'}, by {p['by']})")
        print(p["diff"] or "(no diff)")
    for a in req.get("actions", []):
        print(f"  action: {a['tool']} {a['target']} (by {a['by']})")
    for m in req.get("memory", []):
        print(f"  memory: [{m['type']}] {m['content'][:160]} (by {m['by']})")
    print(f"\nApprove: agent approve {v['task_id']}    Reject: agent reject {v['task_id']}")


def _emit(args, v: dict) -> None:
    if args.json:
        print(json.dumps({k: val for k, val in v.items() if k != "messages"}, indent=2, default=str))
        return
    if v["status"] == "awaiting_approval":
        _print_approval(v)
    elif v.get("final"):
        print("\n" + v["final"])
    print(f"\n[agent] task={v['task_id']} status={v['status']} llm_calls={v.get('llm_calls', 0)}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    rt = open_runtime(with_memory=args.cmd not in ("personas", "trace", "list"))
    try:
        return _dispatch(args, rt)
    except ValueError as exc:
        print(f"[agent] {exc}", file=sys.stderr)
        return 2
    finally:
        rt.close()


def _dispatch(args, rt) -> int:
    if args.cmd == "personas":
        rows = [p.summary() for p in rt.personas.values() if args.all or p.enabled]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                flag = "" if r["enabled"] else "  (disabled)"
                print(f"{r['name']:<21} {r['tier']:<9} {r['output']:<6} {','.join(r['personas']):<12} "
                      f"write={r['write_scope'] or 'read-only'}{flag}")
        return 0
    if args.cmd == "route":
        out = plan_task(rt, args.task, args.scope)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"[route] method={out['method']}")
            for s in out["steps"]:
                print(f"  -> {s['agent']}: {s['goal']}")
            if out["clarify"]:
                print(f"  clarify: {out['clarify']}")
        return 0
    if args.cmd == "run":
        v = rt.start(args.task, scope=args.scope, agent=args.agent,
                     on_update=None if args.json else _progress)
        if v["status"] == "awaiting_approval" and not args.no_prompt and not args.json and sys.stdin.isatty():
            _print_approval(v)
            ans = input("\nApply these changes? [y/N] ").strip().lower()
            v = rt.resume(v["task_id"], approved=ans in ("y", "yes"), on_update=_progress)
        _emit(args, v)
        return 0 if v["status"] in ("completed", "awaiting_approval") else 1
    if args.cmd in ("approve", "reject"):
        v = rt.resume(args.task_id, approved=args.cmd == "approve", paths=getattr(args, "path", None),
                      run_tests=not getattr(args, "no_tests", False),
                      on_update=None if args.json else _progress)
        _emit(args, v)
        return 0 if v["status"] in ("completed", "rejected") else 1
    if args.cmd == "status":
        v = rt.view(args.task_id)
        if v["status"] == "unknown":
            print(f"[agent] unknown task {args.task_id}", file=sys.stderr)
            return 2
        _emit(args, v)
        return 0
    if args.cmd == "trace":
        evs = rt.trace.read(args.task_id)
        if args.json:
            print(json.dumps(evs, indent=2, default=str))
        else:
            for e in evs:
                extra = {k: v for k, v in e.items() if k not in ("ts", "t", "task_id", "kind")}
                print(f"{e['ts'][11:19]} {e['kind']:<17} {json.dumps(extra, default=str)[:220]}")
        return 0 if evs else 2
    if args.cmd == "list":
        rows = rt.trace.tasks()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows[:30]:
                print(f"{r['task_id']}  {r['status']:<18} {(r['started'] or '')[:19]}  {r['task'][:70]}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
