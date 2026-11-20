#!/usr/bin/env python3
"""PAIEP MCP smoke test (M7): launch each server EXACTLY as an editor does and exercise it.

For every server: spawn over stdio (default: ``docker compose ... run --rm -T``), check the
tool list (discovery), call a read tool, and call something the policy must DENY. Optional
``--write`` adds a memory remember -> forget round trip and an fs propose (never applied);
``--deep`` adds slow local-model calls (agent_route, rag_answer).

  python scripts/mcp-smoke.py                                  # this repo, scope global
  python scripts/mcp-smoke.py --workspace ../my-repo --scope project:my-repo --write
  python scripts/mcp-smoke.py --host fs git                    # host Python instead of Docker
Requires the `mcp` package on the host (pip install -r requirements-dev.txt).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

REPO = Path(__file__).resolve().parents[1]
SERVERS = ("fs", "git", "rag", "memory", "paiep-tools")
LOCAL = {"fs", "git"}                      # run in the network-less mcp-local service


def params(name: str, args) -> StdioServerParameters:
    env = {"PAIEP_WORKSPACE": str(args.workspace), "PAIEP_SCOPE": args.scope}
    if args.host:
        script = str(REPO / "scripts" / "mcp-server.py")
        return StdioServerParameters(command=sys.executable, args=[script, name],
                                     env={**env, "MCP_WORKSPACE": str(args.workspace)})
    service = "mcp-local" if name in LOCAL else "mcp"
    compose = str(Path(args.paiep_home) / "docker" / "docker-compose.yml")
    # MCP clients spawn servers with a minimal environment: on Windows `docker compose` then
    # cannot find its plugin (needs %ProgramFiles%); Docker Desktop's docker-compose.exe can.
    cli = args.compose.split()
    return StdioServerParameters(command=cli[0], args=[*cli[1:], "-f", compose, "--profile", "mcp", "run",
                                                       "--rm", "-T", "--quiet-pull", service, name], env=env)


def probes(name: str, args) -> list[tuple[str, dict, bool]]:
    """(tool, arguments, expect_denied)"""
    other = "project:not-this-workspace"
    p = {
        "fs": [("fs_list", {"path": "."}, False), ("fs_read", {"path": "README.md", "max_bytes": 300}, False),
               ("fs_read", {"path": ".env"}, True), ("fs_read", {"path": "../outside"}, True)],
        "git": [("git_status", {}, False), ("git_log", {"limit": 3}, False),
                ("git_show", {"rev": "--output=/tmp/x"}, True)],
        "rag": [("rag_search", {"query": "What is the default chat model?", "limit": 3}, False),
                ("rag_search", {"query": "x", "scope": other}, True)],
        "memory": [("memory_list", {"limit": 3}, False),
                   ("memory_remember", {"content": "x", "type": "task_summary"}, True)],
        "paiep-tools": [("agent_personas", {}, False), ("agent_status", {"task_id": "../etc"}, True)],
    }[name]
    if args.write and name == "fs":
        p.append(("fs_propose_write", {"path": "tmp/mcp-smoke.txt", "content": "smoke\n"}, False))
        p.append(("fs_propose_write", {"path": ".vscode/mcp.json", "content": "{}"}, True))
    if args.deep and name == "paiep-tools":
        p.append(("agent_route", {"task": "Write an ADR comparing two vector databases"}, False))
    if args.deep and name == "rag":
        p.append(("rag_answer", {"question": "What is PAIEP's default chat model?"}, False))
    return p


async def check(name: str, args) -> dict:
    rec = {"server": name, "ok": True, "calls": []}
    t0 = time.perf_counter()
    async with Client(params(name, args), read_timeout_seconds=args.timeout) as c:
        tools = (await c.list_tools()).tools
        rec["startup_s"] = round(time.perf_counter() - t0, 1)
        rec["tools"] = [t.name for t in tools]
        for tool, arguments, expect_denied in probes(name, args):
            t1 = time.perf_counter()
            r = await c.call_tool(tool, arguments)
            text = r.content[0].text if r.content else ""
            denied = bool(r.is_error) and "DENIED" in text
            ok = denied if expect_denied else not r.is_error
            rec["ok"] &= ok
            rec["calls"].append({"tool": tool, "expect": "deny" if expect_denied else "ok", "pass": ok,
                                 "s": round(time.perf_counter() - t1, 1),
                                 "out": text[:160].replace("\n", " ")})
        if args.write and name == "memory":
            r = await c.call_tool("memory_remember", {"content": f"mcp smoke {time.time()}", "type": "note"})
            mid = json.loads(r.content[0].text).get("memory_id") if not r.is_error else None
            r2 = await c.call_tool("memory_forget", {"memory_id": mid or "missing"})
            ok = bool(mid) and not r2.is_error
            rec["ok"] &= ok
            rec["calls"].append({"tool": "memory_remember+forget", "expect": "ok", "pass": ok, "s": 0,
                                 "out": (r2.content[0].text if r2.content else "")[:160]})
    return rec


async def agent_e2e(args) -> dict:
    """agent_run -> poll agent_status -> agent_approve (or reject) entirely over MCP."""
    rec = {"server": "paiep-tools (agent e2e)", "ok": False, "calls": [], "tools": []}
    t0 = time.perf_counter()
    async with Client(params("paiep-tools", args), read_timeout_seconds=args.timeout) as c:
        rec["startup_s"] = round(time.perf_counter() - t0, 1)
        argv = {"task": args.agent_task, **({"agent": args.agent} if args.agent else {})}
        r = await c.call_tool("agent_run", argv)
        started = json.loads(r.content[0].text)
        tid = started["task_id"]
        rec["calls"].append({"tool": "agent_run", "expect": "ok", "pass": not r.is_error, "s": 0, "out": tid})
        status, s = "running", {}
        while status in ("running", "started") and time.perf_counter() - t0 < args.timeout:
            await asyncio.sleep(20)
            s = json.loads((await c.call_tool("agent_status", {"task_id": tid})).content[0].text)
            status = s.get("status", "unknown")
            print(f"   … {int(time.perf_counter() - t0)} s: {status}", flush=True)
        files = [p["path"] for p in (s.get("approval_request") or {}).get("proposals", [])]
        rec["calls"].append({"tool": "agent_status", "expect": "ok", "pass": status == "awaiting_approval",
                             "s": round(time.perf_counter() - t0, 1), "out": f"{status} files={files}"})
        if status == "awaiting_approval":
            for p in (s.get("approval_request") or {}).get("proposals", []):
                print(f"\n--- {p['path']} (by {p['by']})\n{p['diff'][:1500]}")
            tool = "agent_approve" if args.approve else "agent_reject"
            r = await c.call_tool(tool, {"task_id": tid})
            final = json.loads(r.content[0].text) if not r.is_error else {"error": r.content[0].text}
            rec["calls"].append({"tool": tool, "expect": "ok", "pass": not r.is_error,
                                 "s": round(time.perf_counter() - t0, 1),
                                 "out": f"{final.get('status')} applied={final.get('applied', [])}"[:160]})
        rec["ok"] = all(c["pass"] for c in rec["calls"])
        rec["task_id"] = tid
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("servers", nargs="*", help=f"subset of {', '.join(SERVERS)} (default: all)")
    ap.add_argument("--workspace", type=Path, default=REPO)
    ap.add_argument("--paiep-home", default=str(REPO))
    ap.add_argument("--scope", default="global")
    ap.add_argument("--host", action="store_true", help="run servers with host Python, not Docker")
    ap.add_argument("--compose", default="docker-compose" if sys.platform == "win32" else "docker compose",
                    help="compose CLI (default: docker-compose on Windows, 'docker compose' elsewhere)")
    ap.add_argument("--write", action="store_true", help="add reversible write probes")
    ap.add_argument("--deep", action="store_true", help="add slow local-model probes")
    ap.add_argument("--agent-task", default="", help="run this agent task end to end over MCP")
    ap.add_argument("--agent", default="", help="with --agent-task: send to one persona (skip planning)")
    ap.add_argument("--approve", action="store_true",
                    help="with --agent-task: approve (apply) the result instead of rejecting it")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    bad = set(args.servers) - set(SERVERS)
    if bad:
        ap.error(f"unknown server(s): {sorted(bad)}")
    args.servers = args.servers or list(SERVERS)
    args.workspace = args.workspace.resolve()
    results = []
    if args.agent_task:
        args.servers = []
        try:
            results.append(asyncio.run(agent_e2e(args)))
        except Exception as exc:  # noqa: BLE001
            results.append({"server": "agent e2e", "ok": False, "error": repr(exc)[:400]})
    for name in args.servers:
        try:
            results.append(asyncio.run(check(name, args)))
        except Exception as exc:  # noqa: BLE001
            results.append({"server": name, "ok": False, "error": repr(exc)[:400]})
    if args.json:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            head = f"[{'PASS' if r['ok'] else 'FAIL'}] {r['server']}"
            if "error" in r:
                print(f"{head}: {r['error']}")
                continue
            print(f"{head}: {len(r['tools'])} tools, startup {r['startup_s']} s")
            for c in r["calls"]:
                print(f"   {'ok ' if c['pass'] else 'BAD'} {c['tool']:<22} expect={c['expect']:<4} "
                      f"{c['s']:>5}s  {c['out'][:100]}")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
