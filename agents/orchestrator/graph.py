"""LangGraph state machine for one task (supervisor/router, ADR 0008).

    plan ─► execute ◄─┐            (one specialist per step; budgets checked first)
              │        │
              ▼        │
             gate ─────┘            (adds Reviewer/Security after changes; bounded remediation)
              │
              ▼
           approve  ── interrupt ─► human: agent approve | reject <task>
              │
              ▼
            apply ─► finalize ─► END  (writes/tests only after approval; memory + trace)

Blocked (security veto), truncated (budget) or clarify-only tasks skip straight to
finalize, and their proposals are never applied.
"""
from __future__ import annotations

import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agent import run_agent
from .checks import assign_requested, gate_issues, requested_files
from .contract import message, severity_at_least
from .supervisor import aggregate, plan_task


class TaskState(TypedDict, total=False):
    task: str
    scope: str
    task_id: str
    agent_override: str | None
    plan: list[dict]
    method: str
    clarify: str
    step_index: int
    results: list[dict]
    proposals: list[dict]
    actions: list[dict]
    denied: list[dict]
    messages: Annotated[list[dict], operator.add]
    last_change_idx: int
    remediation_rounds: int
    check_rounds: int
    requested: dict
    gate_issues: list[str]
    gate_scheduled: list[str]
    blocked: bool
    truncated: bool
    reason: str
    llm_calls: int
    started_t: float
    approval: dict
    applied: list[dict]
    test_results: list[dict]
    status: str
    final: str
    memory_written: list[dict]


def _memory_proposals(state) -> list[tuple[str, dict]]:
    """(persona, {type, content}) memory writes proposed by agents, pending approval."""
    return [(r["agent"], m) for r in state.get("results", []) for m in r.get("memory") or []]


def build_graph(rt, checkpointer):
    cfg, personas = rt.cfg, rt.personas
    budgets, gate = cfg.budgets, cfg.gate

    # ------------------------------------------------------------------ plan
    def plan(state: TaskState) -> dict:
        task, scope = state["task"], state.get("scope") or "global"
        override = state.get("agent_override")
        if override:
            p = personas.get(override)
            if p is None or not p.enabled or p.name == "supervisor":
                return {"plan": [], "method": "override", "clarify": "",
                        "blocked": True, "reason": f"unknown or disabled agent '{override}'",
                        "step_index": 0, "llm_calls": 0}
            out = {"steps": [{"agent": override, "goal": task}], "method": "override", "clarify": "",
                   "llm_calls": 0}
        else:
            out = plan_task(rt, task, scope)
        requested = assign_requested(requested_files(task, rt.policy), out["steps"], personas)
        rt.trace("plan", {"method": out["method"], "steps": out["steps"], "clarify": out["clarify"],
                          "requested": requested})
        msg = message(task_id=state["task_id"], sender="supervisor",
                      to="user" if out["clarify"] else "supervisor",
                      intent="clarify" if out["clarify"] else "status",
                      goal=out["clarify"] or "plan: " + " -> ".join(s["agent"] for s in out["steps"]))
        return {"plan": out["steps"], "method": out["method"], "clarify": out["clarify"], "step_index": 0,
                "results": [], "proposals": [], "actions": [], "denied": [], "last_change_idx": -1,
                "remediation_rounds": 0, "check_rounds": 0, "requested": requested, "gate_issues": [],
                "gate_scheduled": [], "blocked": False, "truncated": False,
                "llm_calls": out["llm_calls"], "messages": [msg]}

    def after_plan(state: TaskState) -> str:
        return "execute" if state.get("plan") and not state.get("blocked") else "finalize"

    # --------------------------------------------------------------- execute
    def budget_reason(state: TaskState) -> str | None:
        steps = len(state.get("results", []))
        if steps >= budgets.max_agent_steps:
            return f"agent step budget exhausted ({budgets.max_agent_steps})"
        if state.get("llm_calls", 0) >= budgets.max_llm_calls:
            return f"model call budget exhausted ({budgets.max_llm_calls})"
        if time.time() - state.get("started_t", time.time()) > budgets.task_timeout_s:
            return f"task timeout ({budgets.task_timeout_s:.0f}s)"
        return None

    def execute(state: TaskState) -> dict:
        reason = budget_reason(state)
        if reason:
            rt.trace("budget.stop", {"reason": reason})
            return {"truncated": True, "reason": reason, "step_index": len(state["plan"])}
        idx = state["step_index"]
        step = state["plan"][idx]
        persona = personas[step["agent"]]
        step_budget = min(persona.max_tool_steps, budgets.max_tool_steps_per_agent)
        req = message(task_id=state["task_id"], sender="supervisor", to=persona.name, intent="request",
                      goal=step["goal"], inputs=[p["path"] for p in state.get("proposals", [])],
                      constraints={"allowed_tools": persona.tools, "fs_scope": persona.fs_scope,
                                   "step_budget": step_budget,
                                   "llm_budget": budgets.max_llm_calls - state.get("llm_calls", 0)})
        rt.trace("handoff", {"to": persona.name, "goal": step["goal"], "msg_id": req["msg_id"]})
        result = run_agent(rt, persona, step, state, budgets.max_llm_calls - state.get("llm_calls", 0))
        rt.trace("agent.result", {k: v for k, v in result.items() if k not in ("proposals",)}
                 | {"proposals": [p["path"] for p in result["proposals"]]})

        results = [*state.get("results", []), result]
        proposals = list(state.get("proposals", []))
        last_change = state.get("last_change_idx", -1)
        if result["proposals"]:
            by_path = {p["path"]: p for p in proposals}
            for p in result["proposals"]:
                by_path[p["path"]] = p          # latest proposer wins (serialised hand-offs)
            proposals = list(by_path.values())
            last_change = len(results) - 1
        upd: dict = {
            "results": results, "proposals": proposals, "last_change_idx": last_change,
            "actions": [*state.get("actions", []), *result["actions"]],
            "denied": [*state.get("denied", []), *result["denied"]],
            "step_index": idx + 1, "llm_calls": state.get("llm_calls", 0) + result["llm_calls"],
        }
        is_review = persona.is_reviewer
        intent = "review" if is_review else "response"
        if persona.name in gate.veto and severity_at_least(result.get("severity"), gate.block_on_severity):
            intent = "block"
            upd.update(blocked=True, reason=f"{persona.name} veto (severity {result['severity']}): "
                                            + "; ".join(result.get("findings", [])[:3]))
            rt.trace("veto", {"agent": persona.name, "severity": result["severity"]})
        upd["messages"] = [req, message(
            task_id=state["task_id"], sender=persona.name, to="supervisor", intent=intent,
            parent_id=req["msg_id"], goal=step["goal"], status=result["status"],
            severity=result.get("severity"), artifacts=[p["path"] for p in result["proposals"]],
            citations=result["citations"])]
        return upd

    def after_execute(state: TaskState) -> str:
        if state.get("blocked") or state.get("truncated"):
            return "finalize"
        return "execute" if state["step_index"] < len(state["plan"]) else "gate"

    # ------------------------------------------------------------------ gate
    def _fix_steps(task: str, findings_by: dict[str, list[str]], why: str) -> list[dict]:
        return [{"agent": who, "goal": f"Revise your proposed files to address the {why} for: {task}",
                 "findings": fs[:8]} for who, fs in findings_by.items()]

    def gate_node(state: TaskState) -> dict:
        proposals = state.get("proposals", [])
        plan_now = state["plan"]

        # 1) Deterministic checks first (cheap): requested files exist, Python compiles.
        issues = gate_issues(state.get("requested") or {}, proposals)
        if issues and state.get("check_rounds", 0) < gate.max_remediation_rounds:
            by: dict[str, list[str]] = {}
            for i in issues:
                by.setdefault(i["by"], []).append(i["finding"])
            steps = _fix_steps(state["task"], by, "quality-gate findings")
            rt.trace("gate", {"check": "deterministic", "issues": [i["finding"] for i in issues],
                              "scheduled": list(by)})
            return {"plan": [*plan_now, *steps], "check_rounds": state.get("check_rounds", 0) + 1,
                    "gate_scheduled": list(by), "gate_issues": [i["finding"] for i in issues]}
        open_issues = [i["finding"] for i in issues]
        if not proposals and not state.get("actions"):
            return {"gate_issues": open_issues, "gate_scheduled": []}

        # 2) Reviewers must have seen the latest changes.
        results, last = state.get("results", []), state.get("last_change_idx", -1)
        is_code = any(gate.is_code(p["path"]) for p in proposals) or bool(state.get("actions"))
        required = [n for n in (gate.code if is_code else gate.docs) if n in personas and personas[n].enabled]
        after = results[last + 1:] if last >= 0 else results
        reviewed = {r["agent"] for r in after}
        missing = [n for n in required if n not in reviewed]
        paths = ", ".join(p["path"] for p in proposals)
        if missing:
            steps = [{"agent": n, "goal": f"Review the proposed changes to {paths} against the request. "
                                         "Report concrete findings and a severity."} for n in missing]
            rt.trace("gate", {"change_kind": "code" if is_code else "docs", "scheduled": missing})
            return {"plan": [*plan_now, *steps], "gate_scheduled": missing, "gate_issues": open_issues}

        # 3) Review outcome: high severity from a remediating reviewer -> one fix round.
        bad = [r for r in after if r["agent"] in gate.remediate
               and severity_at_least(r.get("severity"), gate.block_on_severity)]
        if not bad:
            rt.trace("gate", {"change_kind": "code" if is_code else "docs", "passed": True,
                              "open_issues": open_issues})
            return {"gate_scheduled": [], "gate_issues": open_issues}
        if state.get("remediation_rounds", 0) >= gate.max_remediation_rounds:
            reason = "unresolved high-severity review findings after remediation"
            rt.trace("gate", {"passed": False, "reason": reason})
            return {"blocked": True, "reason": reason, "gate_scheduled": []}
        findings = [f for r in bad for f in r.get("findings", [])] or [r["summary"] for r in bad]
        by = {}
        for p in proposals:
            by.setdefault(p["by"], findings + open_issues)
        rounds = state.get("remediation_rounds", 0) + 1
        rt.trace("gate", {"remediation": list(by), "round": rounds})
        return {"plan": [*plan_now, *_fix_steps(state["task"], by, "review findings")],
                "remediation_rounds": rounds, "gate_scheduled": list(by), "gate_issues": open_issues}

    def after_gate(state: TaskState) -> str:
        if state.get("blocked"):
            return "finalize"
        if state["step_index"] < len(state["plan"]):
            return "execute"
        if state.get("proposals") or state.get("actions") or _memory_proposals(state):
            return "approve"
        return "finalize"

    # --------------------------------------------------------------- approve
    def approve(state: TaskState) -> dict:
        payload = {
            "task_id": state["task_id"], "task": state["task"],
            "proposals": [{"path": p["path"], "by": p["by"], "new": p["new"], "diff": p["diff"]}
                          for p in state.get("proposals", [])],
            "actions": state.get("actions", []),
            "memory": [{"by": who, **m} for who, m in _memory_proposals(state)],
            "reviews": [{"agent": r["agent"], "severity": r.get("severity"), "summary": r["summary"]}
                        for r in state.get("results", []) if personas[r["agent"]].is_reviewer],
            "issues": state.get("gate_issues", []),
        }
        rt.trace("approval.request", {"proposals": [p["path"] for p in payload["proposals"]],
                                      "actions": payload["actions"]})
        decision = interrupt(payload)
        if not isinstance(decision, dict):
            decision = {"approved": bool(decision)}
        rt.trace("approval.decision", decision)
        return {"approval": decision}

    # ----------------------------------------------------------------- apply
    def apply(state: TaskState) -> dict:
        dec = state.get("approval") or {}
        if not dec.get("approved"):
            return {"status": "rejected", "applied": [], "test_results": []}
        wanted = set(dec.get("paths") or [])
        applied = []
        for p in state.get("proposals", []):
            if wanted and p["path"] not in wanted:
                applied.append({"path": p["path"], "applied": False, "reason": "not selected"})
                continue
            applied.append(rt.tools.apply_write(personas[p["by"]], p["path"], p["content"]))
        tests = []
        if dec.get("run_tests", True):
            for a in state.get("actions", []):
                if a["tool"] == "test.run":
                    tests.append(rt.tools.run_tests(personas[a["by"]], a["target"]))
        # Agent memory writes are approved together with the changes (no false memories from
        # rejected or abandoned work); typed + scoped by the persona's memory_write_types.
        memory_written = []
        if dec.get("memory", True):
            for who, m in _memory_proposals(state):
                memory_written.append(rt.tools.memory_write(personas[who], m["type"], m["content"],
                                                            scope=state.get("scope") or "global",
                                                            task_id=state["task_id"]))
        return {"applied": applied, "test_results": tests, "memory_written": memory_written}

    # -------------------------------------------------------------- finalize
    def finalize(state: TaskState) -> dict:
        if state.get("blocked"):
            status = "blocked"
        elif state.get("clarify") and not state.get("plan"):
            status = "clarify"
        elif state.get("status") == "rejected":
            status = "rejected"
        elif state.get("truncated"):
            status = "partial"
        elif any(r["status"] in ("failed", "blocked") for r in state.get("results", [])):
            status = "partial"
        elif any(not a.get("applied") for a in state.get("applied") or []) or \
                any(not t.get("passed") for t in state.get("test_results") or []):
            status = "partial"
        elif state.get("gate_issues"):
            status = "partial"
        else:
            status = "completed"
        view = {**state, "status": status}
        final = aggregate(view)
        applied = [a["path"] for a in state.get("applied") or [] if a.get("applied")]
        mem_ids = [m["memory_id"] for m in state.get("memory_written") or [] if m.get("written")]
        if rt.memory is not None and cfg.task_summary and status in ("completed", "partial"):
            # Factual task summary only: no model-claimed outcomes (they may be wrong).
            agents = " -> ".join(r["agent"] for r in state.get("results", []))
            text = (f"Agent task ({status}): {state['task'][:200]}. Agents: {agents}. "
                    + (f"Files changed: {', '.join(applied)}." if applied else "No files changed."))
            try:
                mem_ids.append(rt.memory.remember(
                    text, type="task_summary", scope=state.get("scope") or "global",
                    source=f"agent:supervisor:{state['task_id']}").memory_id)
            except Exception as exc:  # noqa: BLE001 - memory is best-effort
                rt.trace("memory.error", {"error": str(exc)})
        rt.trace("task.end", {"status": status, "llm_calls": state.get("llm_calls", 0),
                              "agent_steps": len(state.get("results", [])),
                              "elapsed_s": round(time.time() - state.get("started_t", time.time()), 1),
                              "applied": applied, "memory_ids": mem_ids, "reason": state.get("reason", "")})
        msg_status = "ok" if status == "completed" else "blocked" if status == "blocked" else "partial"
        return {"status": status, "final": final, "messages": [message(
            task_id=state["task_id"], sender="supervisor", to="user", intent="response", status=msg_status,
            goal=state["task"], artifacts=applied)]}

    g = StateGraph(TaskState)
    g.add_node("plan", plan)
    g.add_node("execute", execute)
    g.add_node("gate", gate_node)
    g.add_node("approve", approve)
    g.add_node("apply", apply)
    g.add_node("finalize", finalize)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", after_plan, ["execute", "finalize"])
    g.add_conditional_edges("execute", after_execute, ["execute", "gate", "finalize"])
    g.add_conditional_edges("gate", after_gate, ["execute", "approve", "finalize"])
    g.add_edge("approve", "apply")
    g.add_edge("apply", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
