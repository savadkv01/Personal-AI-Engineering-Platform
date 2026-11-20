"""Offline tests for the M7 MCP servers (in-process MCP client; fake RAG/memory/agent backends)."""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from mcp.client import Client

from agents.orchestrator.cli import build_parser
from integration.mcp import tools as tools_mod
from integration.mcp.common import build_ctx, load_mcp_config, validate_scope
from integration.mcp.server import build_server

ID = "0b7c6f8e-1d2a-4c3b-9e8f-7a6b5c4d3e2f"
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
    (root / ".env").write_text("TOKEN=hello-secret\n", encoding="utf-8")
    (root / ".vscode").mkdir()
    (root / ".vscode" / "settings.json").write_text("{}\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("hello\n", encoding="utf-8")
    return root


def make(ws, names, *, deps=None, scope="project:demo", servers=None, tmp=None):
    cfg = load_mcp_config(root=str(ws), scope=scope)
    cfg.audit_dir = None
    if servers:
        cfg = replace(cfg, servers={**cfg.servers, **servers})
    ctx = build_ctx(cfg, deps)
    return ctx, build_server(names, ctx)


def call(server, tool, **args):
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(tool, args)
            return r.is_error, r.content[0].text if r.content else ""
    return asyncio.run(go())


def tool_names(server):
    async def go():
        async with Client(server) as c:
            return {t.name: t for t in (await c.list_tools()).tools}
    return asyncio.run(go())


# --- config / registration -----------------------------------------------------

def test_scope_validation():
    assert validate_scope("project:my-repo") == "project:my-repo"
    for bad in ("project:", "proj:x", "project:../x", "global;rm"):
        with pytest.raises(ValueError):
            validate_scope(bad)


def test_schemas_and_annotations(ws):
    _, server = make(ws, ["fs", "git"])
    tools = tool_names(server)
    assert "path" in tools["fs_read"].input_schema["properties"]
    assert tools["fs_read"].annotations.read_only_hint is True
    assert tools["fs_apply_write"].annotations.destructive_hint is True
    assert not any(n.startswith(("git_push", "git_commit")) for n in tools)


def test_disabled_tools_are_not_registered(ws):
    _, server = make(ws, ["fs", "memory", "paiep-tools"], deps={"memory": object()},
                     servers={"fs": {"enabled": True, "write": False},
                              "memory": {"enabled": True, "write": False, "forget": False},
                              "paiep-tools": {"enabled": True, "run": False}})
    names = set(tool_names(server))
    assert {"fs_read", "memory_recall", "agent_status"} <= names
    assert not names & {"fs_propose_write", "fs_apply_write", "memory_remember", "memory_forget",
                        "agent_run", "agent_approve"}


def test_agent_approval_tools_can_be_omitted_for_automatic_tool_call_clients(ws):
    _, server = make(ws, ["paiep-tools"], deps={"agent_cli": lambda *_: (0, "[]", "")},
                     servers={"paiep-tools": {"enabled": True, "run": True,
                                               "approve": False, "reject": False}})
    names = set(tool_names(server))
    assert "agent_run" in names and "agent_status" in names
    assert "agent_approve" not in names and "agent_reject" not in names


def test_ui_mcp_config_exposes_only_search_recall_and_unapproved_agent_run(ws):
    cfg = load_mcp_config(path=str(REPO / "config" / "mcp-ui.yaml"), root=str(ws), scope="project:demo")
    cfg.audit_dir = None
    ctx = build_ctx(cfg, {"agent_cli": lambda *_: (0, "[]", ""),
                          "agent_spawn": lambda *_: SimpleNamespace(poll=lambda: None,
                                                                     terminate=lambda: None)})
    server = build_server(["rag", "memory", "paiep-tools"], ctx)
    names = set(tool_names(server))
    assert {"rag_search", "memory_recall", "memory_list", "agent_run",
            "agent_status", "agent_list"} <= names
    assert not names & {"rag_answer", "memory_remember", "memory_forget", "agent_approve", "agent_reject",
                        "fs_apply_write", "fs_propose_write"}
    err, out = call(server, "agent_run", task="review only")
    assert not err and "approve only via the local M6 CLI" in json.loads(out)["next"]


# --- fs ------------------------------------------------------------------------

def test_fs_read_and_denials(ws):
    ctx, server = make(ws, ["fs"])
    err, text = call(server, "fs_read", path="src/app.py")
    assert not err and "return 'hi'" in text
    for path in (".env", "../outside.txt", "src/../../x", ".git/config"):
        err, text = call(server, "fs_read", path=path)
        assert err and "DENIED" in text, path
    _, page = call(server, "fs_read", path="src/app.py", offset=10, max_bytes=8)
    assert "bytes 10-18" in page and "more: offset=18" in page
    assert [e["outcome"] for e in ctx.audit.events].count("denied") == 4


def test_fs_list_and_search_hide_secrets_and_noise(ws):
    _, server = make(ws, ["fs"])
    _, listing = call(server, "fs_list", path=".", depth=2)
    assert "src/app.py" in listing and ".env" not in listing and "node_modules" not in listing
    _, found = call(server, "fs_search", query="hello")
    assert "src/app.py:1:" in found
    assert ".env" not in found and "secret" not in found and "node_modules" not in found


def test_fs_two_step_write(ws):
    ctx, server = make(ws, ["fs"])
    err, out = call(server, "fs_propose_write", path="src/new.py", content="X = 1\n")
    prop = json.loads(out)
    assert not err and prop["new_file"] and "+X = 1" in prop["diff"]
    assert not (ws / "src" / "new.py").exists()           # proposal writes nothing
    err, out = call(server, "fs_apply_write", proposal_id=prop["proposal_id"])
    assert not err and json.loads(out)["created"]
    assert (ws / "src" / "new.py").read_text(encoding="utf-8") == "X = 1\n"
    err, out = call(server, "fs_apply_write", proposal_id=prop["proposal_id"])   # single use
    assert err and "DENIED" in out
    # audit logs content as length + hash, never the content itself (even when short)
    big = "Y = 2\n" * 100
    call(server, "fs_propose_write", path="src/big.py", content=big)
    assert isinstance(ctx.audit.events[-1]["args"]["content"], dict)
    call(server, "fs_propose_write", path="src/small.py", content="Z = 3\n")
    assert ctx.audit.events[-1]["args"]["content"]["chars"] == 6
    assert "Z = 3" not in json.dumps(ctx.audit.events)


def test_fs_write_refuses_non_utf8_and_leaves_no_temp_files(ws):
    _, server = make(ws, ["fs"])
    (ws / "src" / "latin1.txt").write_bytes("caf\xe9\n".encode("latin-1"))
    err, out = call(server, "fs_propose_write", path="src/latin1.txt", content="cafe\n")
    assert err and "not valid UTF-8" in out
    _, out = call(server, "fs_propose_write", path="src/app.py", content="X = 'é'\r\n")
    assert not call(server, "fs_apply_write", proposal_id=json.loads(out)["proposal_id"])[0]
    assert (ws / "src" / "app.py").read_bytes() == "X = 'é'\r\n".encode()
    assert not list((ws / "src").glob("*.mcp-tmp"))


@pytest.mark.skipif(os.name != "nt", reason="Windows host-filesystem aliases")
def test_fs_windows_aliases_cannot_reach_secrets(ws):
    _, server = make(ws, ["fs"])
    for path in (".ENV", ".env::$DATA", ".env.", ".Env "):
        err, out = call(server, "fs_read", path=path)
        assert err and "DENIED" in out, path
    err, out = call(server, "fs_propose_write", path=".VSCODE/settings.json", content="{}\n")
    assert err and "DENIED" in out


def test_fs_write_conflict_and_write_denies(ws):
    _, server = make(ws, ["fs"])
    _, out = call(server, "fs_propose_write", path="src/app.py", content="def hello():\n    return 'yo'\n")
    pid = json.loads(out)["proposal_id"]
    (ws / "src" / "app.py").write_text("changed meanwhile\n", encoding="utf-8")
    err, out = call(server, "fs_apply_write", proposal_id=pid)
    assert err and "changed since the proposal" in out
    for path in (".vscode/settings.json", ".env", "config/mcp.yaml"):
        err, out = call(server, "fs_propose_write", path=path, content="x\n")
        assert err and "DENIED" in out, path
    (ws / "src" / "large.txt").write_text("x" * 60001, encoding="utf-8")
    err, out = call(server, "fs_propose_write", path="src/large.txt", content="small\n")
    assert err and "exceeds max_write_bytes" in out


# --- git -----------------------------------------------------------------------

def _git(ws, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=ws, check=True,
                   capture_output=True)


@pytest.fixture
def repo(ws):
    _git(ws, "init", "-q", "-b", "main")
    _git(ws, "add", "-f", "src/app.py", ".env")
    _git(ws, "commit", "-q", "-m", "init")
    (ws / "src" / "app.py").write_text("def hello():\n    return 'changed'\n", encoding="utf-8")
    (ws / ".env").write_text("TOKEN=new-secret\n", encoding="utf-8")
    return ws


def test_git_read_tools_exclude_secrets(repo):
    _, server = make(repo, ["git"])
    _, status = call(server, "git_status")
    assert "## main" in status
    _, diff = call(server, "git_diff")
    assert "changed" in diff and "secret" not in diff
    _, show = call(server, "git_show", rev="HEAD")
    assert "init" in show and "hello-secret" not in show
    err, out = call(server, "git_diff", path=".env")
    assert err and "DENIED" in out
    (repo / "src" / ".env").write_text("TOKEN=old\n", encoding="utf-8")
    _git(repo, "add", "-f", "src/.env")
    _git(repo, "commit", "-q", "-m", "nested")
    (repo / "src" / ".env").write_text("TOKEN=nested-secret\n", encoding="utf-8")
    for path in (".", "src"):                     # directory pathspecs keep the secret excludes
        _, diff = call(server, "git_diff", path=path)
        assert "changed" in diff and "secret" not in diff, path
    _, log = call(server, "git_log", limit=5)
    assert "init" in log


def test_git_rejects_option_injection_and_creates_branch(repo):
    _, server = make(repo, ["git"])
    for rev in ("--output=/tmp/x", "-p", "HEAD;rm"):
        err, out = call(server, "git_show", rev=rev)
        assert err and "DENIED" in out, rev
    err, out = call(server, "git_create_branch", name="-D")
    assert err and "DENIED" in out
    err, out = call(server, "git_create_branch", name="feature/mcp", switch=True)
    assert not err
    _, branches = call(server, "git_branches")
    assert "* feature/mcp" in branches


# --- rag -----------------------------------------------------------------------

def test_rag_scope_enforced_and_results_numbered(ws):
    seen = {}

    def fake_search(query, scope, limit, tags, include_global):
        seen.update(scope=scope, limit=limit, include_global=include_global)
        return [{"source": "knowledge/notes/a.md", "title": "a", "scope": "global", "score": 0.81,
                 "chunk_index": 0, "text": "Offline first."}]

    answer_args = []

    def fake_answer(question, scope, include_global):
        answer_args.append((question, scope, include_global))
        return {"answer": scope}

    _, server = make(ws, ["rag"], deps={"rag_search": fake_search, "rag_answer": fake_answer})
    err, out = call(server, "rag_search", query="offline?", limit=99)
    assert not err and "[1] knowledge/notes/a.md" in out
    assert seen == {"scope": "project:demo", "limit": 8, "include_global": True}
    err, out = call(server, "rag_search", query="x", scope="project:other")
    assert err and "DENIED" in out
    err, out = call(server, "rag_search", query="x", scope="Workspace")
    assert not err and seen["scope"] == "project:demo"
    err, out = call(server, "rag_answer", question="q", scope="global")
    assert not err and json.loads(out) == {"answer": "global"}
    assert answer_args == [("q", "global", True)]


# --- memory --------------------------------------------------------------------

class FakeMemory:
    def __init__(self):
        now = datetime(2026, 11, 20)
        self.items = {
            "m-own": SimpleNamespace(memory_id="m-own", type="fact", scope="project:demo", content="own",
                                     tags=[], confidence=0.6, source="user", updated_at=now),
            "m-other": SimpleNamespace(memory_id="m-other", type="fact", scope="project:other",
                                       content="other", tags=[], confidence=0.6, source="user",
                                       updated_at=now),
        }
        self.calls = []

    def recall(self, query, **kw):
        self.calls.append(("recall", kw))
        return [SimpleNamespace(item=self.items["m-own"], score=0.9)]

    def remember(self, content, **kw):
        self.calls.append(("remember", kw))
        return replace_ns(self.items["m-own"], content=content, scope=kw["scope"])

    def get(self, mid):
        return self.items.get(mid)

    def delete(self, mid):
        return self.items.pop(mid, None) is not None


def replace_ns(ns, **kw):
    return SimpleNamespace(**{**vars(ns), **kw})


def test_memory_scoped_reads_writes_and_forget(ws):
    mem = FakeMemory()
    _, server = make(ws, ["memory"], deps={"memory": mem})
    err, out = call(server, "memory_recall", query="anything")
    assert not err and json.loads(out)[0]["memory_id"] == "m-own"
    assert mem.calls[0][1]["scope"] == "project:demo" and mem.calls[0][1]["include_global"] is True
    err, out = call(server, "memory_remember", content="Prefer pytest", type="preference")
    assert not err and mem.calls[-1][1]["scope"] == "project:demo"
    err, out = call(server, "memory_remember", content="x", type="task_summary")
    assert err and "DENIED" in out
    err, out = call(server, "memory_forget", memory_id="m-other")
    assert err and "DENIED" in out and "m-other" in mem.items
    err, out = call(server, "memory_forget", memory_id="m-own")
    assert not err and "m-own" not in mem.items


# --- paiep-tools ---------------------------------------------------------------

class FakeProc:
    def __init__(self):
        self.done = None

    def poll(self):
        return self.done

    def terminate(self):
        self.done = -15


def test_agent_tools_drive_the_cli(ws):
    calls, spawned = [], []

    def runner(argv, timeout):
        calls.append(argv)
        view = {"task_id": ID, "status": "awaiting_approval", "task": "t", "plan": [],
                "approval_request": {"reviews": [{"agent": "reviewer", "severity": "none", "summary": "ok"}],
                                     "proposals": [{"path": "src/x.py", "new": True, "by": "se",
                                                    "diff": "+" * 9000}]}}
        if argv[0] == "approve":
            view = {"task_id": ID, "status": "completed", "applied": [{"path": "src/x.py", "applied": True}]}
        return 0, json.dumps(view), ""

    def spawn(argv, log_path):
        spawned.append(argv)
        return FakeProc()

    _, server = make(ws, ["paiep-tools"], deps={"agent_cli": runner, "agent_spawn": spawn})
    err, out = call(server, "agent_run", task="--help me add a helper")
    started = json.loads(out)
    assert not err and started["status"] == "started"
    argv = spawned[0]
    assert argv[-2:] == ["--", "--help me add a helper"]          # task can never become an option
    assert argv[argv.index("--scope") + 1] == "project:demo" and "--no-prompt" in argv
    err, out = call(server, "agent_run", task="second")
    assert err and "already running" in out
    err, out = call(server, "agent_status", task_id=started["task_id"])
    s = json.loads(out)
    assert s["status"] == "awaiting_approval" and len(s["approval_request"]["proposals"][0]["diff"]) < 6200
    err, out = call(server, "agent_approve", task_id=started["task_id"], paths=["src/x.py"], run_tests=False)
    assert not err and json.loads(out)["status"] == "completed"
    assert calls[-1] == ["approve", started["task_id"], "--path", "src/x.py", "--no-tests"]
    for bad in ({"task_id": "../../etc"}, {"task_id": started["task_id"], "paths": ["--all"]}):
        err, out = call(server, "agent_approve", **bad)
        assert err and "DENIED" in out


def test_agent_tasks_are_bound_to_their_workspace_and_scope(ws, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    registry = tools_mod.TaskRegistry(tmp_path / "tasks.jsonl")         # shared, like /data
    calls = []

    def runner(argv, timeout):
        calls.append(argv)
        if argv[0] == "list":
            return 0, json.dumps([{"task_id": t, "status": "awaiting_approval"} for t in (tid, ID)]), ""
        return 0, json.dumps({"task_id": argv[1], "status": "awaiting_approval", "scope": "project:demo"}), ""

    deps = {"agent_cli": runner, "agent_spawn": lambda argv, log: FakeProc(), "agent_registry": registry}
    _, mine = make(ws, ["paiep-tools"], deps=deps)
    tid = json.loads(call(mine, "agent_run", task="t")[1])["task_id"]
    _, rows = call(mine, "agent_list")
    assert [r["task_id"] for r in json.loads(rows)] == [tid]           # CLI-started ID is hidden
    # A second workspace (fresh process, same shared registry) cannot see or act on the task;
    # same workspace in another scope cannot either.
    _, elsewhere = make(other, ["paiep-tools"], deps={**deps, "agent_registry": tools_mod.TaskRegistry(
        tmp_path / "tasks.jsonl")})
    _, other_scope = make(ws, ["paiep-tools"], deps=deps, scope="project:other")
    for server in (elsewhere, other_scope):
        for tool in ("agent_status", "agent_approve", "agent_reject"):
            err, out = call(server, tool, task_id=tid)
            assert err and "not started from this workspace" in out, tool
        assert json.loads(call(server, "agent_list")[1]) == []
    assert not any(c[0] in ("approve", "reject") for c in calls)
    err, _ = call(mine, "agent_status", task_id=tid)
    assert not err


def test_agent_run_concurrency_limit_is_atomic(ws):
    spawned = []

    def spawn(argv, log_path):
        time.sleep(0.1)                         # widen the race between the check and spawn
        spawned.append(argv)
        return FakeProc()

    _, server = make(ws, ["paiep-tools"], deps={"agent_spawn": spawn})

    async def concurrent_calls():
        async with Client(server) as c:
            return await asyncio.gather(
                c.call_tool("agent_run", {"task": "first"}),
                c.call_tool("agent_run", {"task": "second"}),
            )

    results = asyncio.run(concurrent_calls())
    assert len(spawned) == 1
    assert sum(not r.is_error for r in results) == 1
    denied = next(r for r in results if r.is_error)
    assert "already running" in denied.content[0].text


def test_agent_summary_and_cli_task_id():
    s = tools_mod.summarize({"task_id": ID, "status": "completed", "final": "done", "messages": ["x"]})
    assert s == {"task_id": ID, "status": "completed", "final": "done"}
    args = build_parser().parse_args(["--json", "run", "--scope", "project:demo", "--no-prompt",
                                      "--task-id", ID, "--", "-dash task"])
    assert args.task_id == ID and args.task == "-dash task" and args.json


def test_agent_summary_points_ui_to_cli_when_approve_tools_disabled():
    pending = {"task_id": ID, "status": "awaiting_approval", "approval_request": {"proposals": []}}
    assert "agent_approve(" in tools_mod.summarize(pending)["next"]
    ui_next = tools_mod.summarize(pending, approve_via_tools=False)["next"]
    assert "agent_approve(" not in ui_next and "CLI" in ui_next


# --- workspace template (cookiecutter) -----------------------------------------

def _render(tmp_path, **extra):
    from cookiecutter.main import cookiecutter

    out = cookiecutter(str(REPO / "templates" / "workspace"), no_input=True, output_dir=str(tmp_path),
                       extra_context={"project_name": "Demo App", "paiep_home": str(REPO), **extra})
    return Path(out)


def test_workspace_template_renders_valid_scoped_configs(tmp_path):
    ws = _render(tmp_path)
    assert ws.name == "demo-app"
    for p in ws.rglob("*"):
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "__PAIEP" not in text and "{%" not in text, p
    mcp_yaml = (ws / ".continue/mcpServers/paiep.yaml").read_text(encoding="utf-8")
    servers = yaml.safe_load(mcp_yaml)["mcpServers"]
    local = servers[0]
    assert local["command"] == "docker-compose" and local["args"][-3:] == ["mcp-local", "fs", "git"]
    assert local["env"] == {"PAIEP_WORKSPACE": ws.resolve().as_posix(), "PAIEP_SCOPE": "project:demo-app"}
    assert Path(local["args"][1]).is_file()                       # the real PAIEP compose file
    models = yaml.safe_load((ws / ".continue/models/paiep.yaml").read_text(encoding="utf-8"))["models"]
    assert "apiKey" not in models[0]                                   # see template: digit-only tokens
    assert models[0]["requestOptions"]["headers"]["authorization"] == \
        "Bearer ${{ secrets.PAIEP_GATEWAY_TOKEN }}"                     # secret by reference only
    assert 600_000 < models[0]["requestOptions"]["timeout"] < 2_147_483   # ms; see template comment
    cline = json.loads((ws / ".paiep/cline_mcp_settings.json").read_text(encoding="utf-8"))["mcpServers"]
    auto = {t for s in cline.values() for t in s["autoApprove"]}
    assert not auto & {"fs_apply_write", "memory_forget", "memory_remember", "agent_run", "agent_approve",
                       "git_create_branch"}
    assert not (ws / ".vscode/mcp.json").exists() and not (ws / ".roo").exists()   # privacy default


def test_workspace_template_sensitive_variant_and_validation(tmp_path):
    from cookiecutter.exceptions import FailedHookException

    ws = _render(tmp_path, copilot="disabled", agent_client="roo", compose_cli="docker compose")
    settings = (ws / ".vscode/settings.json").read_text(encoding="utf-8")
    assert '"chat.disableAIFeatures": true' in settings
    assert not (ws / ".github/copilot-instructions.md").exists() and not (ws / ".clinerules").exists()
    roo = json.loads((ws / ".roo/mcp.json").read_text(encoding="utf-8"))["mcpServers"]["paiep"]
    assert roo["command"] == "docker" and roo["args"][0] == "compose"
    with pytest.raises(FailedHookException):
        _render(tmp_path / "bad", project_name="x", memory_scope="project:../etc")


def test_workspace_template_copilot_mcp_is_explicit_opt_in(tmp_path):
    ws = _render(tmp_path, copilot_mcp="yes", inline_provider="copilot")
    text = (ws / ".vscode/mcp.json").read_text(encoding="utf-8")
    config = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))
    assert set(config["servers"]) == {"paiep-local", "paiep"}
    settings = (ws / ".vscode/settings.json").read_text(encoding="utf-8")
    assert '"github.copilot.enable": { "*": true }' in settings
    assert '"continue.enableTabAutocomplete": false' in settings
