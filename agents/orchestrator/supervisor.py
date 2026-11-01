"""Supervisor: plan/route (LLM structured routing with keyword fallback) and aggregation."""
from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9/+.-]+")


def specialists(personas: dict) -> list:
    return [p for p in personas.values() if p.enabled and p.name != "supervisor"]


def keyword_plan(task: str, personas: dict) -> list[dict]:
    """Deterministic fallback: best keyword match among enabled specialists."""
    text = " " + " ".join(_WORD.findall(task.lower())) + " "
    scored = []
    for i, p in enumerate(specialists(personas)):
        hits = sum(1 for k in p.routing_keywords if f" {k} " in text or (" " in k and k in text))
        if hits:
            scored.append((hits, -i, p.name))
    if not scored:
        fallback = "architect" if "architect" in personas and personas["architect"].enabled else \
            specialists(personas)[0].name
        return [{"agent": fallback, "goal": task}]
    scored.sort(reverse=True)
    return [{"agent": scored[0][2], "goal": task}]


def _catalog(personas: dict) -> str:
    lines = []
    for p in specialists(personas):
        writes = ", ".join(p.fs_scope.get("write", [])) or "read-only"
        use = ", ".join(p.routing_keywords[:10])
        lines.append(f"- {p.name}: {p.role}. Use for: {use}. Writes: {writes}.")
    return "\n".join(lines)


def _examples(cfg, names: list[str]) -> str:
    out = []
    for e in cfg.examples:
        steps = [a for a in e["plan"] if a in names]
        if steps:
            out.append(f"- \"{e['request']}\" -> {' then '.join(steps)}")
    return "\n".join(out)


def plan_schema(names: list[str], max_steps: int) -> dict:
    return {"type": "object", "properties": {
        "steps": {"type": "array", "maxItems": max_steps, "items": {
            "type": "object",
            "properties": {"agent": {"type": "string", "enum": names}, "goal": {"type": "string"}},
            "required": ["agent", "goal"]}},
        "clarify": {"type": "string"}}, "required": ["steps", "clarify"]}


def plan_task(rt, task: str, scope: str) -> dict:
    """Return {steps, method, clarify, llm_calls}. Never raises."""
    cfg, personas = rt.cfg, rt.personas
    names = [p.name for p in specialists(personas)]
    if cfg.planner != "llm":
        return {"steps": keyword_plan(task, personas), "method": "keyword", "clarify": "", "llm_calls": 0}
    sup = personas["supervisor"]
    examples = _examples(cfg, names)
    system = (
        f"You are the {sup.role} of PAIEP. {sup.goal} {sup.backstory}\n"
        f"Specialists:\n{_catalog(personas)}\n"
        "Rules:\n"
        f"- Use the FEWEST steps (usually 1, at most {cfg.max_plan_steps}); each step names one agent "
        "and a concrete goal that says exactly which files or outputs to produce.\n"
        "- Pick the agent whose 'Use for' best matches the user's intent: new or fixed code -> "
        "software_engineer; guides/READMEs/summaries -> documentation_writer; designs, comparisons, "
        "ADRs, data models -> architect; reviewing existing code -> reviewer; security audits -> security.\n"
        "- Never add reviewer or security just to check new changes: the quality gate does that "
        "automatically.\n"
        "- If the request is too ambiguous to act on, return no steps and a short clarify question; "
        "otherwise clarify must be \"\".\n"
        + (f"Examples:\n{examples}\n" if examples else "")
        + "Reply with ONE JSON object."
    )
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": f"SCOPE: {scope}\nREQUEST: {task}"}]
    try:
        res = rt.llm.complete(msgs, tier=cfg.planner_tier, schema=plan_schema(names, cfg.max_plan_steps),
                              max_tokens=400)
    except Exception as exc:  # noqa: BLE001
        rt.trace("llm.error", {"agent": "supervisor", "error": str(exc)})
        return {"steps": keyword_plan(task, personas), "method": "keyword-fallback", "clarify": "",
                "llm_calls": 1}
    rt.trace("llm.call", {"agent": "supervisor", "model": res.model, "tier": res.tier,
                          "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
                          "latency_ms": res.latency_ms, "final_turn": True})
    data = res.data or {}
    steps = []
    for s in data.get("steps") or []:
        agent, goal = str(s.get("agent", "")), str(s.get("goal", "")).strip()
        if agent in names and goal and not (steps and steps[-1]["agent"] == agent):
            steps.append({"agent": agent, "goal": goal})
    steps = steps[: cfg.max_plan_steps]
    clarify = str(data.get("clarify") or "").strip()
    if steps:
        return {"steps": steps, "method": "llm", "clarify": "", "llm_calls": 1}
    if clarify:
        return {"steps": [], "method": "llm", "clarify": clarify, "llm_calls": 1}
    return {"steps": keyword_plan(task, personas), "method": "keyword-fallback", "clarify": "",
            "llm_calls": 1}


def aggregate(state: dict) -> str:
    """Deterministic final answer (no extra CPU model call)."""
    status = state.get("status", "completed")
    out = [f"## Result: {status}"]
    if state.get("reason"):
        out.append(f"_Reason: {state['reason']}_")
    if state.get("clarify"):
        out.append(f"**Clarification needed:** {state['clarify']}")
    plan = state.get("plan") or []
    if plan:
        out.append(f"\n**Plan** ({state.get('method', '?')}): "
                   + " → ".join(f"{s['agent']}" for s in plan))
    cites: list[str] = []
    for r in state.get("results", []):
        sev = f", severity {r['severity']}" if r.get("severity") not in (None, "none") else ""
        out.append(f"\n### {r['agent']} ({r['status']}{sev})\n{r['summary'] or '(no summary)'}")
        for f in r.get("findings", [])[:8]:
            out.append(f"- {f}")
        for c in r.get("citations", []):
            if c not in cites:
                cites.append(c)
    applied = state.get("applied") or []
    builders_ran = any(r.get("can_write") for r in state.get("results", []))
    if applied:
        out.append("\n### Changes")
        out += [f"- {'✅ applied' if a['applied'] else '⛔ not applied'}: `{a['path']}`"
                + (f" — {a['reason']}" if not a["applied"] else "") for a in applied]
    elif state.get("proposals"):
        verb = "awaiting approval" if status == "awaiting_approval" else "not applied"
        out.append(f"\n### Proposed changes ({verb})")
        out += [f"- `{p['path']}` ({'new' if p['new'] else 'modified'}, by {p['by']}"
                + (", salvaged from summary" if p.get("salvaged") else "") + ")"
                for p in state["proposals"]]
    elif builders_ran:
        out.append("\n_No file changes were proposed; nothing was modified._")
    for d in state.get("denied") or []:
        out.append(f"- ⛔ denied `{d['path']}` ({d['by']}): {d['reason']}")
    for issue in state.get("gate_issues") or []:
        out.append(f"- ⚠️ gate: {issue}")
    for t in state.get("test_results") or []:
        out.append(f"\n### Tests `{t.get('target')}`: "
                   + ("passed" if t.get("passed") else f"FAILED/not run — {t.get('reason', '')}"))
    if cites:
        out.append("\n**Sources:** " + ", ".join(f"`{c}`" for c in cites))
    return "\n".join(out)
