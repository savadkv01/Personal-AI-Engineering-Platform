"""paiep-tools MCP server: the M6 agent orchestrator from the editor.

Each tool shells out (argv, no shell) to ``scripts/agent-cli.py --json ...`` so the
orchestrator keeps its own runtime, checkpoints and guardrails (tool policy, quality gate,
HITL). ``agent_run`` starts a task in the background and returns its id at once (chains
take minutes on CPU); poll ``agent_status``; nothing is written to the workspace until
``agent_approve`` (destructive -> the client asks the human). Tasks are bound to the
workspace + scope that started them (``TaskRegistry``): status/approve/reject/list only see
this workspace's own tasks.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .common import REPO_ROOT, Ctx, Denied, truncate

AGENT_CLI = REPO_ROOT / "scripts" / "agent-cli.py"
_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
DIFF_LIMIT = 6000


def _cli_runner(argv: list[str], timeout: int) -> tuple[int, str, str]:
    res = subprocess.run([sys.executable, str(AGENT_CLI), "--json", *argv], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
    return res.returncode, res.stdout, res.stderr


def _cli_spawn(argv: list[str], log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # The child inherits its own copy of the handle; close ours so each run leaks nothing.
    with open(log_path, "a", encoding="utf-8") as fh:
        return subprocess.Popen([sys.executable, str(AGENT_CLI), "--json", *argv], stdout=fh,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


class TaskRegistry:
    """Binds each agent task to the workspace + scope whose MCP server started it.

    All MCP containers share one /data volume and see their workspace as /workspace, so a
    bare task id would let project B read A's diffs or approve A's proposals into B's tree.
    Records are append-only JSONL (one line per task) so separate server processes agree.
    """

    def __init__(self, path: Path | None):
        self.path = path
        self.mem: dict[str, dict] = {}
        self.lock = threading.Lock()

    def add(self, task_id: str, workspace: str, scope: str) -> None:
        rec = {"task_id": task_id, "workspace": workspace, "scope": scope}
        with self.lock:
            self.mem[task_id] = rec
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec) + "\n")

    def _records(self):
        with self.lock:
            yield from list(self.mem.values())
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def get(self, task_id: str) -> dict | None:
        return next((r for r in self._records() if r.get("task_id") == task_id), None)

    def ids(self, workspace: str, scope: str) -> set[str]:
        return {r["task_id"] for r in self._records()
                if r.get("workspace") == workspace and r.get("scope") == scope and r.get("task_id")}


def summarize(v: dict, approve_via_tools: bool = True) -> dict:
    """Compact, model-friendly task view (diffs truncated)."""
    out = {k: v.get(k) for k in ("task_id", "status", "task", "scope", "method", "reason", "clarify")
           if v.get(k) not in (None, "", [])}
    if v.get("plan"):
        out["plan"] = [f"{s['agent']}: {s.get('goal', '')}" for s in v["plan"]]
    if v.get("results"):
        out["steps"] = [{"agent": r.get("agent"), "status": r.get("status"), "severity": r.get("severity"),
                         "files": [p.get("path") for p in r.get("proposals", [])]} for r in v["results"]]
    req = v.get("approval_request")
    if req:
        out["approval_request"] = {
            "reviews": [{"agent": r.get("agent"), "severity": r.get("severity"),
                         "summary": (r.get("summary") or "")[:300]} for r in req.get("reviews", [])],
            "issues": req.get("issues", []),
            "proposals": [{"path": p.get("path"), "new": p.get("new"), "by": p.get("by"),
                           "diff": truncate(p.get("diff") or "", DIFF_LIMIT, "diff truncated")}
                          for p in req.get("proposals", [])],
            "actions": req.get("actions", []),
            "memory": req.get("memory", []),
        }
        out["next"] = ("show the plan, reviews and diffs to the user; then agent_approve(task_id) "
                       "or agent_reject(task_id)" if approve_via_tools else
                       "show the plan, reviews and diffs to the user; the user approves or rejects "
                       "with the local M6 CLI (agents approve|reject <task_id>), not from chat")
    for k in ("applied", "test_results"):
        if v.get(k):
            out[k] = v[k]
    if v.get("final"):
        out["final"] = truncate(v["final"], 4000)
    return out


def register(server: MCPServer, ctx: Ctx) -> None:
    cfg = ctx.cfg.server("paiep-tools")
    approve_enabled = bool(cfg.get("approve", cfg.get("run", False)))
    reject_enabled = bool(cfg.get("reject", cfg.get("run", False)))
    run: Callable[[list[str], int], tuple[int, str, str]] = ctx.deps.get("agent_cli", _cli_runner)
    spawn = ctx.deps.get("agent_spawn", _cli_spawn)
    status_to = int(cfg.get("status_timeout_s", 120))
    running: dict[str, object] = {}
    running_lock = threading.RLock()
    log_dir = (ctx.cfg.audit_dir or Path.home() / ".paiep" / "mcp-audit") / "agent-runs"
    registry = ctx.deps.get("agent_registry") or TaskRegistry(
        ctx.cfg.audit_dir / "agent-runs" / "tasks.jsonl" if ctx.cfg.audit_dir else None)
    workspace = ctx.cfg.workspace_id

    def call(argv: list[str], timeout: int = status_to):
        rc, out, err = run(argv, timeout)
        try:
            data = json.loads(out) if out.strip() else None
        except json.JSONDecodeError:
            data = None
        if data is None:
            raise ValueError(f"agent CLI failed (exit {rc}): {(err or out).strip()[-1500:]}")
        return rc, data

    def task_id_ok(task_id: str) -> str:
        if not _ID_RE.match(task_id or ""):
            raise Denied(f"invalid task id '{task_id}'")
        return task_id

    def owned(task_id: str) -> str:
        """Only tasks started by agent_run in THIS workspace + scope are visible/approvable."""
        tid = task_id_ok(task_id)
        rec = registry.get(tid)
        if not rec or rec.get("workspace") != workspace or rec.get("scope") != ctx.scope:
            raise Denied(f"task '{tid}' was not started from this workspace/scope "
                         "(use the agent CLI for tasks started elsewhere)")
        return tid

    def scope_matches(view: dict) -> None:
        if view.get("scope") not in (None, ctx.scope):
            raise Denied(f"task scope '{view.get('scope')}' does not match this workspace ({ctx.scope})")

    def alive() -> list[str]:
        with running_lock:
            for tid in [t for t, p in running.items() if p.poll() is not None]:
                running.pop(tid)
            return list(running)

    def agent_personas() -> list[dict]:
        """List the enabled agent personas (role, model tier, write scope)."""
        return call(["personas"])[1]

    def agent_route(task: str) -> dict:
        """Show the supervisor's plan (which agents, in order) without running anything."""
        if not task.strip():
            raise ValueError("task is empty")
        return call(["route", "--scope", ctx.scope, "--", task], timeout=600)[1]

    def agent_status(task_id: str) -> dict:
        """Status of an agent task; when awaiting approval: plan, reviews and proposed diffs."""
        tid = owned(task_id)
        rc, out, _err = run(["status", tid], status_to)
        try:
            v = json.loads(out) if out.strip() else {"status": "unknown"}
        except json.JSONDecodeError:
            v = {"status": "unknown"}
        if v.get("status") == "unknown":
            if tid in alive():
                return {"task_id": tid, "status": "running", "note": "planning; poll again shortly"}
            log_path = log_dir / f"{tid}.log"
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-1500:] if log_path.exists() else ""
            return {"task_id": tid, "status": "unknown", "log_tail": tail}
        scope_matches(v)
        s = summarize(v, approve_enabled)
        if tid in alive() and s.get("status") not in ("awaiting_approval",):
            s["status"] = "running"
        return s

    def agent_list() -> list[dict]:
        """Recent agent tasks started from this workspace + scope (newest first)."""
        rows = call(["list"])[1]
        if not isinstance(rows, list):
            return rows
        mine = registry.ids(workspace, ctx.scope)
        return [r for r in rows if r.get("task_id") in mine][:20]

    for fn, title in ((agent_personas, "List agent personas"), (agent_route, "Plan a task (dry run)"),
                      (agent_status, "Agent task status"), (agent_list, "Recent agent tasks")):
        ctx.tool(server, "paiep-tools", fn, title=title)
    def agent_run(task: str, agent: str = "") -> dict:
        """Start a multi-agent task in the background (plan -> specialists -> review gate ->
        approval). Returns a task_id immediately; poll agent_status (minutes on CPU)."""
        if not task.strip():
            raise ValueError("task is empty")
        if agent and not _NAME_RE.match(agent):
            raise Denied(f"invalid agent name '{agent}'")
        with running_lock:
            busy = alive()
            if len(busy) >= int(cfg.get("max_running", 1)):
                raise Denied(f"an agent task is already running ({busy[0]}); "
                             "wait for it (CPU: one chain at a time)")
            argv = ["run", "--scope", ctx.scope, "--no-prompt"]
            if agent:
                argv += ["--agent", agent]
            tid = str(uuid.uuid4())
            registry.add(tid, workspace, ctx.scope)
            running[tid] = spawn([*argv, "--task-id", tid, "--", task], log_dir / f"{tid}.log")
        return {"task_id": tid, "status": "started", "scope": ctx.scope,
                "next": ("poll agent_status(task_id) every ~30-60 s; changes need agent_approve"
                         if approve_enabled else "poll agent_status(task_id); review proposals and "
                         "approve only via the local M6 CLI")}

    def agent_approve(task_id: str, paths: list[str] | None = None, run_tests: bool = True) -> dict:
        """Approve a task awaiting approval: APPLIES its proposed file changes (optionally only
        `paths`) and runs its queued test actions. Only tasks started from this workspace."""
        tid = owned(task_id)
        _rc, view = call(["status", tid])
        scope_matches(view)
        argv = ["approve", tid]
        for p in paths or []:
            if not p or p.startswith("-"):
                raise Denied(f"invalid path '{p}'")
            argv += ["--path", p]
        if not run_tests:
            argv.append("--no-tests")
        rc, v = call(argv, timeout=int(cfg.get("approve_timeout_s", 1800)))
        return summarize(v)

    def agent_reject(task_id: str) -> dict:
        """Reject a task awaiting approval (nothing is written). Only tasks from this workspace."""
        return summarize(call(["reject", owned(task_id)])[1])

    if cfg.get("run", False):
        ctx.tool(server, "paiep-tools", agent_run, title="Start an agent task", read_only=False)
    if approve_enabled:
        ctx.tool(server, "paiep-tools", agent_approve, title="Approve + apply an agent task",
                 read_only=False, destructive=True)
    if reject_enabled:
        ctx.tool(server, "paiep-tools", agent_reject, title="Reject an agent task", read_only=False)
    def stop_running() -> None:
        with running_lock:
            for proc in running.values():
                if proc.poll() is None:
                    proc.terminate()

    ctx.closers.append(stop_running)
