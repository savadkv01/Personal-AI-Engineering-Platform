"""Offline tests for the M6 agent layer (fake LLM / memory / KB, in-memory checkpointer)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from agents.orchestrator import agent as agent_mod
from agents.orchestrator import checks, supervisor
from agents.orchestrator.config import load_agents_config
from agents.orchestrator.contract import message, severity_at_least
from agents.orchestrator.llm import ChatResult, ModelRouter, RouterConfig, load_router_config, parse_json
from agents.orchestrator.personas import load_personas
from agents.orchestrator.runtime import Runtime
from agents.orchestrator.trace import TraceSink
from agents.tools.policy import glob_match, load_policy
from rag.query.retriever import _build_filter

ENABLED = {"supervisor", "architect", "software_engineer", "documentation_writer", "reviewer", "security"}


# --- fakes ---------------------------------------------------------------------

class FakeLLM:
    """Scripted replies keyed by persona role; records every call."""

    def __init__(self, script: dict[str, list]):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls: list[dict] = []

    def complete(self, messages, *, tier, schema=None, max_tokens=None):
        system = messages[0]["content"]
        m = re.match(r"You are the (.+?) (agent in PAIEP|of PAIEP)", system)
        who = m.group(1) if m else "?"
        self.calls.append({"who": who, "tier": tier, "schema": schema, "system": system,
                           "user": messages[-1]["content"]})
        queue = self.script.get(who) or []
        reply = queue.pop(0) if len(queue) > 1 else (queue[0] if queue else {})
        if callable(reply):
            reply = reply(messages)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return ChatResult(text=text, data=parse_json(text), model="fake-7b", tier=tier,
                          prompt_tokens=100, completion_tokens=50, latency_ms=5.0)


class FakeMemory:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.remembered: list[dict] = []

    def recall(self, query, *, scope=None, top_k=3, include_global=None):
        return self.hits[:top_k]

    def remember(self, content, *, type, scope, source=None, **kw):
        mid = f"mem-{len(self.remembered) + 1:04d}-0000"
        self.remembered.append({"content": content, "type": type, "scope": scope, "source": source})
        return SimpleNamespace(memory_id=mid)


def fake_rag(query, scope, limit):
    text = "PAIEP runs every service on an internal Docker network with no internet egress."
    return [{"source": "knowledge/notes/offline-first.md", "score": 0.7, "text": text}][:limit]


def final(summary="done", status="ok", **kw) -> dict:
    out = {"action": "final", "tool": "", "tool_input": "", "summary": summary, "status": status,
           "citations": kw.pop("citations", [])}
    out.update(kw)
    return out


def plan(*steps, clarify="") -> dict:
    return {"steps": [{"agent": a, "goal": g} for a, g in steps], "clarify": clarify}


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "docs").mkdir(parents=True)
    (ws / "docker").mkdir()
    (ws / "docker" / ".env").write_text("GATEWAY_TOKEN=super-secret\n")
    (ws / "README.md").write_text("# Demo repo\nOffline-first platform.\n")
    (ws / "experiments").mkdir()
    return ws


@pytest.fixture
def policy(workspace):
    return load_policy(root=str(workspace))


@pytest.fixture
def personas():
    return load_personas()


def make_rt(policy, personas, script, *, memory=None, **cfg_over):
    cfg = load_agents_config()
    for k, v in cfg_over.items():
        if k in ("max_agent_steps", "max_llm_calls", "max_tool_steps_per_agent"):
            cfg.budgets = replace(cfg.budgets, **{k: v})
        else:
            setattr(cfg, k, v)
    cfg.trace_dir = ""
    return Runtime(cfg=cfg, personas=personas, policy=policy, llm=FakeLLM(script), trace=TraceSink(None),
                   checkpointer=InMemorySaver(), memory=memory if memory is not None else FakeMemory(),
                   rag_search=fake_rag)


def kinds(rt) -> list[str]:
    return [e["kind"] for e in rt.trace.events]


# --- personas + config ----------------------------------------------------------

def test_persona_catalog_loads_and_is_consistent(personas):
    assert len(personas) == 15
    assert {p.name for p in personas.values() if p.enabled} == ENABLED
    for p in personas.values():
        if p.is_reviewer:
            assert not p.can_write and not p.fs_scope["write"]
    sup = personas["supervisor"]
    assert "fs.write" not in sup.tools and "shell" not in sup.tools
    assert all(p.role and p.goal and p.backstory for p in personas.values())


def test_invalid_persona_rejected(tmp_path):
    (tmp_path / "supervisor.yaml").write_text(
        "name: supervisor\nrole: S\ngoal: g\ntier: general\ntools: []\n")
    (tmp_path / "bad.yaml").write_text("name: bad\nrole: B\ngoal: g\ntier: general\ntools: [rm.rf]\n")
    with pytest.raises(ValueError, match="unknown tools"):
        load_personas(tmp_path)


def test_agents_and_router_config_load():
    cfg = load_agents_config()
    assert cfg.budgets.max_agent_steps >= 3 and cfg.gate.veto == ["security"]
    assert cfg.gate.is_code("experiments/x.py") and not cfg.gate.is_code("docs/x.md")
    rc = load_router_config()
    assert rc.kind == "openai" and rc.default_model


# --- policy (least privilege) --------------------------------------------------

@pytest.mark.parametrize("path,pattern,ok", [
    ("docs/a/b.md", "docs/**", True), ("docs", "docs/**", True), ("docsx/a.md", "docs/**", False),
    (".env", "**/.env", True), ("docker/.env", "**/.env", True), ("a/b.env.bak", "**/.env.*", False),
    ("experiments/x/y.md", "experiments/**/*.md", True), ("experiments/y.md", "experiments/**/*.md", True),
    ("experiments/y.py", "experiments/**/*.md", False),
])
def test_glob_match(path, pattern, ok):
    assert glob_match(path, pattern) is ok


def test_tools_default_deny_and_global_kill_switch(policy, personas):
    se, dev, rev = personas["software_engineer"], personas["devops_agent"], personas["reviewer"]
    assert policy.tool_allowed(se, "fs.write")
    assert policy.tool_allowed(se, "fs.write").approval is True
    assert not policy.tool_allowed(rev, "fs.write")                       # not in allow-list
    assert "shell" in dev.tools and not policy.tool_allowed(dev, "shell")  # globally disabled
    assert "disabled by policy" in policy.tool_allowed(dev, "shell").reason
    assert not policy.tool_allowed(se, "web.fetch")
    assert not policy.tool_allowed(se, "rm.rf")


@pytest.mark.parametrize("path", ["../outside.md", "/etc/passwd", "docs/../../x.md", "docker/.env", ".env",
                                  ".git/config", "config/tool-policy.yaml", "agents/personas/x.yaml",
                                  "agents/tools/policy.py", "rag/query/engine.py"])
def test_documentation_writer_cannot_write_outside_scope(policy, personas, path):
    assert not policy.check_write(personas["documentation_writer"], path, "x")


def test_scoped_write_and_size_limit(policy, personas):
    dw = personas["documentation_writer"]
    d = policy.check_write(dw, "docs/notes/new.md", "# hi")
    assert d and d.path == "docs/notes/new.md" and d.approval
    assert policy.check_write(dw, "docs\\win\\path.md", "x").path == "docs/win/path.md"
    big = "x" * (policy.max_write_bytes + 1)
    assert "max_write_bytes" in policy.check_write(dw, "docs/big.md", big).reason
    assert not policy.check_read(dw, "docker/.env")
    assert policy.check_read(dw, "README.md")


def test_symlink_escape_blocked(policy, personas, workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, workspace / "docs" / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this platform")
    assert not policy.check_write(personas["documentation_writer"], "docs/link/evil.md", "x")


# --- tool runtime ------------------------------------------------------------------

def test_read_tools_and_denials_are_traced(policy, personas):
    rt = make_rt(policy, personas, {})
    rev = personas["reviewer"]
    ok = rt.tools.call(rev, "fs.read", "README.md", scope="global")
    assert ok.ok and "Demo repo" in ok.text
    secret = rt.tools.call(rev, "fs.read", "docker/.env", scope="global")
    assert secret.denied and "super-secret" not in secret.text
    listing = rt.tools.call(rev, "fs.read", ".", scope="global")
    assert "README.md" in listing.text and ".env" not in listing.text
    assert rt.tools.call(rev, "fs.write", "docs/x.md", scope="global").denied
    assert rt.tools.call(personas["devops_agent"], "shell", "rm -rf /", scope="global").denied
    assert rt.tools.call(rev, "vcs", "push origin main", scope="global").denied
    assert kinds(rt).count("policy.deny") == 4


def test_memory_write_is_typed_and_scoped(policy, personas):
    mem = FakeMemory()
    rt = make_rt(policy, personas, {}, memory=mem)
    arch = personas["architect"]
    assert rt.tools.memory_write(arch, "decision", "Use Qdrant", scope="project:x", task_id="t")["written"]
    assert not rt.tools.memory_write(arch, "preference", "x", scope="global", task_id="t")["written"]
    rev = personas["reviewer"]
    assert not rt.tools.memory_write(rev, "fact", "x", scope="global", task_id="t")["written"]
    assert mem.remembered == [{"content": "Use Qdrant", "type": "decision", "scope": "project:x",
                               "source": "agent:architect:t"}]


def test_apply_write_rechecks_policy(policy, personas, workspace):
    rt = make_rt(policy, personas, {})
    se = personas["software_engineer"]
    assert rt.tools.apply_write(se, "experiments/a.py", "x = 1")["applied"]
    assert (workspace / "experiments" / "a.py").read_text() == "x = 1\n"
    assert not rt.tools.apply_write(se, "docker/.env", "pwned")["applied"]
    assert "super-secret" in (workspace / "docker" / ".env").read_text()


# --- router + parsing ------------------------------------------------------------------

def test_model_router_resolves_tiers_with_fallback():
    rc = RouterConfig(profiles={"cpu": {"general": "g", "coding": "c", "reasoning": "r"}},
                      fallback={"reasoning": ["coding", "general"]}, default_model="d", profile="cpu")
    assert ModelRouter(rc).resolve("reasoning") == "r"
    assert ModelRouter(rc, {"c", "g"}).resolve("reasoning") == "c"
    assert ModelRouter(rc, {"x"}).resolve("reasoning") == "d"
    gpu = RouterConfig(profiles={"cpu": {"general": "g"}}, profile="gpu")
    assert ModelRouter(gpu).resolve("general") == "g"


def test_parse_json_tolerates_wrapping():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('Sure:\n```json\n{"a": 2}\n```') == {"a": 2}
    assert parse_json("nope") is None


def test_output_schema_matches_persona_capabilities(personas):
    se = agent_mod.output_schema(personas["software_engineer"], ["fs.read"])["properties"]
    assert "files" in se and "run_tests" in se and "severity" not in se
    rv = agent_mod.output_schema(personas["reviewer"], [])["properties"]
    assert "files" not in rv and "severity" in rv and rv["action"]["enum"] == ["final"]


def test_trace_reserved_fields_cannot_be_overwritten(tmp_path):
    sink = TraceSink(str(tmp_path))
    sink.bind("t1")
    sink("gate", {"kind": "evil", "task_id": "other", "x": 1})
    ev = sink.read("t1")[0]
    assert (ev["kind"], ev["task_id"], ev["x"]) == ("gate", "t1", 1)
    sink("approval.request", {})
    assert sink.tasks()[0]["status"] == "awaiting_approval"
    sink("task.end", {"status": "completed"})
    assert sink.tasks()[0]["status"] == "completed"


def test_contract_messages():
    m = message(task_id="t", sender="supervisor", to="reviewer", intent="request", goal="g",
                constraints={"allowed_tools": ["fs.read"]})
    assert m["intent"] == "request" and m["constraints"]["allowed_tools"] == ["fs.read"] and m["msg_id"]
    with pytest.raises(ValueError):
        message(task_id="t", sender="a", to="b", intent="gossip")
    assert severity_at_least("high", "high") and not severity_at_least("med", "high")


def test_rag_filter_include_global():
    f = _build_filter("project:x", None, include_global=True)
    assert f.must[0].match.any == ["project:x", "global"]
    assert _build_filter("project:x", None).must[0].match.value == "project:x"
    assert _build_filter("global", None, include_global=True).must[0].match.value == "global"


# --- supervisor routing ------------------------------------------------------------------

def test_llm_plan_is_validated_and_capped(policy, personas):
    rt = make_rt(policy, personas, {"Supervisor / Planner": [plan(
        ("software_engineer", "write code"), ("software_engineer", "dup"), ("data_engineer", "disabled"),
        ("documentation_writer", "docs"), ("architect", "design"), ("reviewer", "extra"))]})
    out = supervisor.plan_task(rt, "task", "global")
    assert out["method"] == "llm"
    assert [s["agent"] for s in out["steps"]] == ["software_engineer", "documentation_writer", "architect"]
    schema = rt.llm.calls[0]["schema"]["properties"]["steps"]["items"]["properties"]["agent"]["enum"]
    assert set(schema) == ENABLED - {"supervisor"}


def test_planner_prompt_includes_examples_and_use_for(policy, personas):
    rt = make_rt(policy, personas, {"Supervisor / Planner": [plan(("architect", "x"))]})
    rt.cfg.examples = [{"request": "Write an ADR", "plan": ["architect"]},
                       {"request": "Run the pipeline", "plan": ["data_engineer"]}]   # disabled persona
    supervisor.plan_task(rt, "task", "global")
    system = rt.llm.calls[0]["system"]
    assert '"Write an ADR" -> architect' in system and "Run the pipeline" not in system
    assert "Use for: design, architecture" in system
    rt.llm.calls.clear()
    supervisor.plan_task(rt, "another task", "global")
    assert rt.llm.calls[0]["system"] == system          # stable => cached prefix across tasks


def test_planner_clarify_and_fallback(policy, personas):
    rt = make_rt(policy, personas, {"Supervisor / Planner": [plan(clarify="Which file?")]})
    assert supervisor.plan_task(rt, "do the thing", "global")["clarify"] == "Which file?"
    rt = make_rt(policy, personas, {"Supervisor / Planner": ["not json at all"]})
    out = supervisor.plan_task(rt, "fix the bug in this python function", "global")
    assert out["method"] == "keyword-fallback" and out["steps"][0]["agent"] == "software_engineer"


@pytest.mark.parametrize("task,agent", [
    ("Write a README guide for the memory service", "documentation_writer"),
    ("Implement a python function to parse dates", "software_engineer"),
    ("Compare two vector databases and draft an ADR", "architect"),
    ("Please review this change", "reviewer"),
    ("Is there a secret leaked? security check", "security"),
])
def test_keyword_router(personas, task, agent):
    assert supervisor.keyword_plan(task, personas)[0]["agent"] == agent


# --- graph: end-to-end flows ------------------------------------------------------------

DOC = "docs/notes/offline.md"


def docs_script(review_sev="low"):
    return {
        "Supervisor / Planner": [plan(("documentation_writer", f"Write {DOC}"))],
        "Documentation Writer": [final("Wrote the note [1].", citations=[1, 2, 99],
                                       files=[{"path": DOC, "content": "# Offline\nNo egress [1].\n"}],
                                       memory=[{"type": "note", "content": "Offline note exists"}])],
        "Code Reviewer": [final("Looks good.", severity=review_sev, findings=["minor wording"])],
    }


def test_docs_task_gate_approval_apply(policy, personas, workspace):
    mem = FakeMemory([SimpleNamespace(item=SimpleNamespace(type="preference", memory_id="abcd1234-x",
                                                           content="Prefer concise docs"), score=0.8)])
    rt = make_rt(policy, personas, docs_script(), memory=mem)
    v = rt.start("Write a note about offline mode", scope="project:paiep", task_id="t-docs")

    assert v["status"] == "awaiting_approval"
    assert [r["agent"] for r in v["results"]] == ["documentation_writer", "reviewer"]   # gate added reviewer
    assert not (workspace / DOC).exists()                                                # nothing written yet
    req = v["approval_request"]
    assert req["proposals"][0]["path"] == DOC and "+# Offline" in req["proposals"][0]["diff"]
    assert v["results"][0]["citations"] == ["memory:preference/abcd1234", "knowledge/notes/offline-first.md"]
    assert "Prefer concise docs" in rt.llm.calls[1]["user"]   # memory in context
    assert "# Offline" in rt.llm.calls[2]["user"]             # reviewer sees proposed content

    v = rt.resume("t-docs", approved=True)
    assert v["status"] == "completed"
    assert (workspace / DOC).read_text().startswith("# Offline")
    assert [a["path"] for a in v["applied"] if a["applied"]] == [DOC]
    types = [m["type"] for m in mem.remembered]
    assert types == ["note", "task_summary"] and mem.remembered[1]["scope"] == "project:paiep"
    assert mem.remembered[0]["source"] == "agent:documentation_writer:t-docs"
    assert mem.remembered[1]["content"].endswith(f"Files changed: {DOC}.")
    assert "Wrote the note" not in mem.remembered[1]["content"]       # no model-claimed outcome
    intents = [m["intent"] for m in v["messages"]]
    assert intents.count("request") == 2 and "review" in intents and intents[-1] == "response"
    for k in ("task.start", "plan", "handoff", "llm.call", "gate", "approval.request",
              "approval.decision", "apply.write", "task.end"):
        assert k in kinds(rt)
    gate_ev = next(e for e in rt.trace.events if e["kind"] == "gate")
    assert gate_ev["change_kind"] == "docs" and gate_ev["scheduled"] == ["reviewer"]
    with pytest.raises(ValueError):
        rt.resume("t-docs", approved=True)


def test_reject_writes_nothing(policy, personas, workspace):
    mem = FakeMemory()
    rt = make_rt(policy, personas, docs_script(), memory=mem)
    rt.start("Write a note", task_id="t-rej")
    assert mem.remembered == []                    # persona memory is only proposed before approval
    v = rt.resume("t-rej", approved=False)
    assert v["status"] == "rejected" and not (workspace / DOC).exists()
    assert mem.remembered == []                    # rejected task leaves no memories behind


def test_claimed_change_without_proposal_is_called_out(policy, personas):
    s = {"Supervisor / Planner": [plan(("documentation_writer", "x"))],
         "Documentation Writer": [final("I have updated rag/query/engine.py as requested.")]}
    mem = FakeMemory()
    v = make_rt(policy, personas, s, memory=mem).start("Update the engine", task_id="t-claim")
    assert v["status"] == "completed" and "No file changes were proposed" in v["final"]
    assert mem.remembered[-1]["content"].endswith("No files changed.")


@pytest.mark.parametrize("approved", [True, False])
def test_agent_memory_writes_need_approval(policy, personas, approved):
    mems = [{"type": "decision", "content": "Use Qdrant"}, {"type": "preference", "content": "x"}]
    s = {"Supervisor / Planner": [plan(("architect", "decide"))],
         "Solution & Data Architect": [final("Use Qdrant.", memory=mems)]}
    mem = FakeMemory()
    rt = make_rt(policy, personas, s, memory=mem)
    v = rt.start("Pick a vector DB", task_id=f"t-mem-{approved}")
    assert v["status"] == "awaiting_approval" and mem.remembered == []
    want = [{"by": "architect", "type": "decision", "content": "Use Qdrant"}]
    assert v["approval_request"]["memory"] == want
    assert any(d["path"] == "memory:preference" for d in v["denied"])          # type not allowed
    v = rt.resume(f"t-mem-{approved}", approved=approved)
    if approved:
        assert [m["type"] for m in mem.remembered] == ["decision", "task_summary"]
        assert v["status"] == "completed"
    else:
        assert mem.remembered == [] and v["status"] == "rejected"


def test_partial_approval_by_path(policy, personas, workspace):
    s = docs_script()
    s["Documentation Writer"] = [final("two files", files=[
        {"path": "docs/a.md", "content": "A"}, {"path": "docs/b.md", "content": "B"}])]
    rt = make_rt(policy, personas, s)
    rt.start("two docs", task_id="t-part")
    v = rt.resume("t-part", approved=True, paths=["docs/b.md"])
    assert (workspace / "docs" / "b.md").exists() and not (workspace / "docs" / "a.md").exists()
    assert v["status"] == "partial"


def code_script(security_sev="none", tests_target="experiments/m6_demo"):
    code = "def slugify(t: str) -> str:\n    return '-'.join(t.lower().split())\n"
    test = ("from textutils import slugify\n\n\ndef test_slugify():\n"
            "    assert slugify('Hello World') == 'hello-world'\n")
    return {
        "Supervisor / Planner": [plan(("software_engineer", "Add slugify"))],
        "Software Engineer": [final("Added slugify + test.", run_tests=tests_target, files=[
            {"path": "experiments/m6_demo/textutils.py", "content": code},
            {"path": "experiments/m6_demo/test_textutils.py", "content": test}])],
        "Code Reviewer": [final("Fine.", severity="low", findings=[])],
        "Security Reviewer": [final("Issue found." if security_sev == "high" else "No issues.",
                                    severity=security_sev, findings=["eval() on user input"]
                                    if security_sev == "high" else [])],
    }


def test_code_task_runs_full_gate_and_tests_after_approval(policy, personas, workspace):
    rt = make_rt(policy, personas, code_script())
    v = rt.start("Add a slugify helper", task_id="t-code")
    assert [r["agent"] for r in v["results"]] == ["software_engineer", "reviewer", "security"]
    assert v["actions"] == [{"tool": "test.run", "target": "experiments/m6_demo", "by": "software_engineer"}]
    v = rt.resume("t-code", approved=True)
    assert (workspace / "experiments" / "m6_demo" / "textutils.py").exists()
    assert v["test_results"][0]["passed"] is True, v["test_results"][0].get("output")
    assert v["status"] == "completed"


def test_security_veto_blocks_before_approval(policy, personas, workspace):
    rt = make_rt(policy, personas, code_script(security_sev="high"))
    v = rt.start("Add a slugify helper", task_id="t-veto")
    assert v["status"] == "blocked" and "security veto" in v["reason"]
    assert v["approval_request"] is None and "approval.request" not in kinds(rt)
    assert not (workspace / "experiments" / "m6_demo").exists()


def test_remediation_round_then_pass(policy, personas, workspace):
    s = docs_script()
    s["Documentation Writer"] = [final("v1", files=[{"path": DOC, "content": "# v1 wrong\n"}]),
                                 final("v2", files=[{"path": DOC, "content": "# v2 fixed\n"}])]
    s["Code Reviewer"] = [final("Wrong facts.", severity="high", findings=["claims internet access"]),
                          final("Fixed.", severity="low")]
    rt = make_rt(policy, personas, s)
    v = rt.start("note", task_id="t-rem")
    assert [r["agent"] for r in v["results"]] == ["documentation_writer", "reviewer",
                                                   "documentation_writer", "reviewer"]
    assert "claims internet access" in rt.llm.calls[3]["user"]           # findings passed to builder
    assert "# v1 wrong" in rt.llm.calls[3]["user"]                        # builder sees its own proposal
    assert v["approval_request"]["proposals"][0]["diff"].count("v2 fixed") == 1
    rt.resume("t-rem", approved=True)
    assert (workspace / DOC).read_text().startswith("# v2 fixed")


def test_unresolved_review_blocks_after_max_rounds(policy, personas, workspace):
    s = docs_script(review_sev="high")
    rt = make_rt(policy, personas, s)
    v = rt.start("note", task_id="t-unres")
    assert v["status"] == "blocked" and "unresolved" in v["reason"]
    assert len(v["results"]) == 4 and not (workspace / DOC).exists()


def test_out_of_scope_proposal_is_denied_and_reported(policy, personas, workspace):
    s = {"Supervisor / Planner": [plan(("documentation_writer", "edit engine"))],
         "Documentation Writer": [final("tried", files=[{"path": "rag/query/engine.py", "content": "x"},
                                                        {"path": "docker/.env", "content": "TOKEN=1"}])]}
    rt = make_rt(policy, personas, s)
    v = rt.start("Change the RAG engine", task_id="t-scope")
    assert v["status"] == "completed" and v["proposals"] == [] and v["approval_request"] is None
    assert {d["path"] for d in v["denied"]} == {"rag/query/engine.py", "docker/.env"}
    assert "denied" in v["final"]
    assert (workspace / "docker" / ".env").read_text() == "GATEWAY_TOKEN=super-secret\n"


def test_agent_read_tool_loop_and_secret_denial(policy, personas):
    s = {"Supervisor / Planner": [plan(("architect", "Summarise the README"))],
         "Solution & Data Architect": [
             {**final(""), "action": "tool", "tool": "fs.read", "tool_input": "docker/.env"},
             {**final(""), "action": "tool", "tool": "fs.read", "tool_input": "README.md"},
             final("The README says it is offline-first [2].", citations=[2])]}
    rt = make_rt(policy, personas, s, max_tool_steps_per_agent=2)
    v = rt.start("Summarise the README", task_id="t-loop")
    r = v["results"][0]
    assert r["llm_calls"] == 3 and [t["tool"] for t in r["tool_calls"]] == ["fs.read", "fs.read"]
    assert r["tool_calls"][0]["denied"] and "super-secret" not in json.dumps(v, default=str)
    assert r["citations"] == ["README.md"]
    last_schema = rt.llm.calls[-1]["schema"]["properties"]["action"]["enum"]
    assert last_schema == ["final"]                                       # forced final turn
    # Prompt-cache friendly: identical system prompt, and each turn only appends to the user prompt.
    turns = [c for c in rt.llm.calls if c["who"] == "Solution & Data Architect"]
    assert len({c["system"] for c in turns}) == 1
    stable = turns[0]["user"].rsplit("\n\n", 1)[0]
    assert all(c["user"].startswith(stable) for c in turns)
    assert "[2] (README.md)" in turns[2]["user"]


def test_budgets_truncate_and_never_apply(policy, personas, workspace):
    s = docs_script()
    s["Supervisor / Planner"] = [plan(("documentation_writer", "a"), ("architect", "b"))]
    s["Solution & Data Architect"] = [final("design")]
    rt = make_rt(policy, personas, s, max_agent_steps=1)
    v = rt.start("note", task_id="t-budget")
    assert v["status"] == "partial" and "budget" in v["reason"]
    assert v["approval_request"] is None and not (workspace / DOC).exists()


def test_llm_call_budget_stops_chain(policy, personas):
    s = docs_script()
    rt = make_rt(policy, personas, s, max_llm_calls=2)
    v = rt.start("note", task_id="t-llm")
    assert v["status"] == "partial" and "model call budget" in v["reason"]
    assert len(rt.llm.calls) <= 2


def test_tool_turns_respect_budget(policy, personas):
    s = {"Supervisor / Planner": [plan(("architect", "x"))],
         "Solution & Data Architect": [{**final(""), "action": "tool", "tool": "fs.read",
                                        "tool_input": "README.md"}, final("answer")]}
    rt = make_rt(policy, personas, s)   # config: max_tool_steps_per_agent = 1
    v = rt.start("x", task_id="t-tools")
    assert v["results"][0]["llm_calls"] == 2 and v["results"][0]["summary"] == "answer"


def test_invalid_json_from_agent_fails_softly(policy, personas):
    s = {"Supervisor / Planner": [plan(("architect", "x"))], "Solution & Data Architect": ["garbage"]}
    v = make_rt(policy, personas, s).start("x", task_id="t-bad")
    assert v["results"][0]["status"] == "failed" and v["status"] == "partial"


def test_override_and_disabled_agent(policy, personas):
    s = {"Solution & Data Architect": [final("direct answer")]}
    rt = make_rt(policy, personas, s)
    v = rt.start("design", agent="architect", task_id="t-ovr")
    assert v["method"] == "override" and v["status"] == "completed" and len(rt.llm.calls) == 1
    v = rt.start("x", agent="devops_agent", task_id="t-dis")
    assert v["status"] == "blocked" and "disabled" in v["reason"]


def test_clarify_short_circuits(policy, personas):
    rt = make_rt(policy, personas, {"Supervisor / Planner": [plan(clarify="Which project?")]})
    v = rt.start("do it", task_id="t-clar")
    assert v["status"] == "clarify" and "Which project?" in v["final"] and v["results"] == []


# --- deterministic gate checks (M6 live-run findings) -------------------------------

def test_requested_files_and_assignment(policy, personas, workspace):
    task = ("Create experiments/demo/util.py plus experiments/demo/test_util.py, update README.md, "
            "document it in experiments/demo/README.md; never touch docker/.env or ../x.py")
    req = checks.requested_files(task, policy)
    assert req == ["experiments/demo/util.py", "experiments/demo/test_util.py", "experiments/demo/README.md"]
    plan_steps = [{"agent": "software_engineer"}, {"agent": "documentation_writer"}]
    assert checks.assign_requested(req, plan_steps, personas) == {
        "experiments/demo/util.py": "software_engineer", "experiments/demo/test_util.py": "software_engineer",
        "experiments/demo/README.md": "documentation_writer"}
    # Not planned: the best enabled persona is chosen (docs file -> documentation_writer).
    assert checks.assign_requested(["docs/new.md"], [{"agent": "software_engineer"}], personas) == {
        "docs/new.md": "documentation_writer"}


def test_syntax_and_missing_file_issues():
    props = [{"path": "a/x.py", "by": "software_engineer", "content": "def f(:\n  pass\n"},
             {"path": "a/ok.py", "by": "software_engineer", "content": "x = 1\n"}]
    issues = checks.gate_issues({"a/x.py": "software_engineer", "a/t.py": "software_engineer"}, props)
    found = [i["finding"] for i in issues]
    assert any("a/t.py was not produced" in f for f in found)
    assert any(f.startswith("a/x.py: syntax error line 1") for f in found)
    assert len(issues) == 2


TASK3 = ("Create experiments/m6_demo/textutils.py with slugify and a test "
         "experiments/m6_demo/test_textutils.py, then write experiments/m6_demo/README.md")
GOOD = "def slugify(t: str) -> str:\n    return '-'.join(t.lower().split())\n"
TEST = "from textutils import slugify\n\n\ndef test_s():\n    assert slugify('A B') == 'a-b'\n"
README = ("# m6 demo\n\nUse `slugify('Hello World')` to get `hello-world`. It lowercases the text and "
          "joins the words with single hyphens.\n\n## Test\n\nRun `pytest experiments/m6_demo`.\n")


def test_missing_requested_files_trigger_fix_round_then_pass(policy, personas, workspace):
    s = {"Supervisor / Planner": [plan(("software_engineer", "slugify"), ("documentation_writer", "readme"))],
         "Software Engineer": [final("only the module", files=[
             {"path": "experiments/m6_demo/textutils.py", "content": GOOD}]),
             final("added test", files=[{"path": "experiments/m6_demo/textutils.py", "content": GOOD},
                                         {"path": "experiments/m6_demo/test_textutils.py", "content": TEST}],
                   run_tests="experiments/m6_demo/test_textutils.py::test_s")],
         "Documentation Writer": [final(README)],                  # document returned in summary
         "Code Reviewer": [final("ok", severity="low")], "Security Reviewer": [final("ok", severity="none")]}
    rt = make_rt(policy, personas, s)
    v = rt.start(TASK3, task_id="t-req")
    agents = [r["agent"] for r in v["results"]]
    assert agents == ["software_engineer", "documentation_writer", "software_engineer", "reviewer",
                      "security"]
    assert v["requested"]["experiments/m6_demo/README.md"] == "documentation_writer"
    first_se = next(c for c in rt.llm.calls if c["who"] == "Software Engineer")
    assert "FILES YOU MUST CREATE" in first_se["user"] and "test_textutils.py" in first_se["user"]
    dw = next(c for c in rt.llm.calls if c["who"] == "Documentation Writer")
    assert "FILES PROPOSED EARLIER" in dw["user"] and "def slugify" in dw["user"]   # sees the code
    readme = next(p for p in v["proposals"] if p["path"].endswith("README.md"))
    assert readme.get("salvaged") and readme["content"].startswith("# m6 demo")
    assert v["actions"] == [{"tool": "test.run", "target": "experiments/m6_demo/test_textutils.py",
                             "by": "software_engineer"}]
    assert v["gate_issues"] == [] and "salvage" in kinds(rt)
    v = rt.resume("t-req", approved=True)
    assert v["status"] == "completed", v["final"]
    assert v["test_results"][0]["passed"], v["test_results"][0].get("output")


def test_unfixed_issues_reach_approval_as_partial(policy, personas, workspace):
    s = {"Supervisor / Planner": [plan(("software_engineer", "slugify"))],
         "Software Engineer": [final("module", files=[{"path": "experiments/m6_demo/textutils.py",
                                                       "content": "def broken(:\n"}])],
         "Code Reviewer": [final("ok", severity="low")], "Security Reviewer": [final("ok", severity="none")]}
    rt = make_rt(policy, personas, s)
    v = rt.start("Create experiments/m6_demo/textutils.py", task_id="t-syn")
    agents = [r["agent"] for r in v["results"]]
    assert agents == ["software_engineer", "software_engineer", "reviewer", "security"]
    assert any("syntax error" in i for i in v["gate_issues"])
    assert any("syntax error" in i for i in v["approval_request"]["issues"])
    v = rt.resume("t-syn", approved=False)
    assert v["status"] == "rejected"


def test_invalid_test_target_denied(policy, personas):
    s = {"Supervisor / Planner": [plan(("software_engineer", "x"))],
         "Software Engineer": [final("x", files=[{"path": "experiments/a.py", "content": GOOD}],
                                     run_tests="tests/nope/test_a.py::test_x")],
         "Code Reviewer": [final("ok")], "Security Reviewer": [final("ok")]}
    v = make_rt(policy, personas, s).start("x", task_id="t-tt")
    assert v["actions"] == []
    assert any("does not exist and was not proposed" in d["reason"] for d in v["denied"])


def test_invented_test_prefix_is_repaired():
    known = {"experiments/m6_demo/test_textutils.py", "experiments/m6_demo/textutils.py"}
    fix = agent_mod._repair_target
    want = "experiments/m6_demo/test_textutils.py"
    assert fix("tests/experiments/m6_demo/test_textutils.py", known) == want
    assert fix("experiments/m6_demo", known) == "experiments/m6_demo"
    assert fix("tests/other/test_x.py", known) == "tests/other/test_x.py"
    assert agent_mod._test_target(" a/b.py::test_c ") == "a/b.py"


def test_fs_read_sees_proposed_overlay(policy, personas):
    rt = make_rt(policy, personas, {})
    obs = rt.tools.call(personas["reviewer"], "fs.read", "experiments/new.py", scope="global",
                        overlay={"experiments/new.py": "x = 42\n"})
    assert obs.ok and "x = 42" in obs.text and "not yet applied" in obs.text
    assert not rt.tools.call(personas["reviewer"], "fs.read", "experiments/new.py", scope="global").ok


EXISTING = "# Guide\n\n" + "\n".join(f"Line {i}: important existing content." for i in range(20)) + "\n"


def test_blind_overwrite_of_existing_file_is_denied(policy, personas, workspace):
    (workspace / "docs" / "guide.md").write_text(EXISTING)
    rewrite = final("rewrote", files=[{"path": "docs/guide.md", "content": "# Guide\nshort\n"}])
    s = {"Supervisor / Planner": [plan(("documentation_writer", "update guide"))],
         "Documentation Writer": [rewrite]}
    v = make_rt(policy, personas, s).start("Update docs/guide.md", task_id="t-blind")
    assert v["proposals"] == [] and v["approval_request"] is None
    assert any("read it with fs.read" in d["reason"] for d in v["denied"])


def test_read_then_destructive_rewrite_is_flagged(policy, personas, workspace):
    (workspace / "docs" / "guide.md").write_text(EXISTING)
    short = {"path": "docs/guide.md", "content": "# Guide\nshort\n"}
    read = {**final(""), "action": "tool", "tool": "fs.read", "tool_input": "docs/guide.md"}
    s = {"Supervisor / Planner": [plan(("documentation_writer", "update guide"))],
         "Documentation Writer": [read, final("rewrote", files=[short])],
         "Code Reviewer": [final("ok", severity="low")]}
    rt = make_rt(policy, personas, s)
    v = rt.start("Update docs/guide.md", task_id="t-shrink")
    assert [r["agent"] for r in v["results"]] == ["documentation_writer", "documentation_writer", "reviewer"]
    assert v["proposals"][0]["old_bytes"] == len(EXISTING.encode())
    assert any(i.startswith("Destructive change: docs/guide.md") for i in v["approval_request"]["issues"])
    assert rt.resume("t-shrink", approved=False)["status"] == "rejected"
    assert (workspace / "docs" / "guide.md").read_text() == EXISTING
