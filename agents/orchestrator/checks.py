"""Deterministic quality checks (no model calls) used by the planner and the gate.

- ``requested_files``: NEW repo files named in the request (they must be produced).
- ``assign_requested``: who should create each file (planned builder whose write scope
  covers it, preferring docs personas for Markdown and code personas otherwise).
- ``gate_issues``: missing requested files, Python syntax errors, destructive shrinks.

Small local models often drop part of a multi-file request or put a document in the
wrong field; these checks catch that cheaply and drive the bounded remediation round.
"""
from __future__ import annotations

import re

_PATH = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.(?:py|md|txt|yaml|yml|json|toml|sh|sql|cfg|ini))\b")
_DOC_EXTS = (".md", ".txt")


def requested_files(task: str, policy) -> list[str]:
    out: list[str] = []
    for raw in _PATH.findall(task or ""):
        rel = policy.normalize(raw)
        if not rel or policy.denied(rel) or (policy.root / rel).exists() or rel in out:
            continue
        out.append(rel)
    return out


def _covers(persona, path: str) -> bool:
    from agents.tools.policy import glob_match

    return persona.can_write and any(glob_match(path, g) for g in persona.fs_scope.get("write", []))


def _rank(persona, path: str) -> int:
    if path.endswith(_DOC_EXTS):
        if persona.output != "docs":
            return 2
        return 0 if {"readme", "documentation", "docs"} & set(persona.routing_keywords) else 1
    return 0 if persona.output == "code" else 1


def assign_requested(paths: list[str], plan: list[dict], personas: dict) -> dict[str, str]:
    """path -> persona name (planned builders first, then any enabled persona)."""
    planned = []
    for s in plan:
        p = personas.get(s["agent"])
        if p and p not in planned:
            planned.append(p)
    others = [p for p in personas.values() if p.enabled and p.name != "supervisor" and p not in planned]
    out = {}
    for path in paths:
        for pool in (planned, others):
            cands = sorted((p for p in pool if _covers(p, path)), key=lambda p: _rank(p, path))
            if cands:
                out[path] = cands[0].name
                break
    return out


def syntax_errors(proposals: list[dict]) -> list[dict]:
    errs = []
    for p in proposals:
        if p["path"].endswith(".py"):
            try:
                compile(p["content"], p["path"], "exec", dont_inherit=True)
            except SyntaxError as exc:
                errs.append({"path": p["path"], "by": p["by"],
                             "finding": f"{p['path']}: syntax error line {exc.lineno}: {exc.msg}"})
    return errs


def destructive_changes(proposals: list[dict], ratio: float = 0.5, min_bytes: int = 200) -> list[dict]:
    out = []
    for p in proposals:
        old = int(p.get("old_bytes") or 0)
        new = len(p["content"].encode())
        if old >= min_bytes and new < old * ratio:
            out.append({"path": p["path"], "by": p["by"],
                        "finding": f"Destructive change: {p['path']} shrinks from {old} to {new} bytes — "
                                   "keep the existing content and only change what the request needs."})
    return out


def gate_issues(requested: dict[str, str], proposals: list[dict]) -> list[dict]:
    """[{path, by, finding}] — `by` is the persona responsible for fixing it."""
    proposed = {p["path"] for p in proposals}
    issues = [{"path": path, "by": who,
               "finding": f"Requested file {path} was not produced — create it with complete content."}
              for path, who in requested.items() if path not in proposed]
    return issues + syntax_errors(proposals) + destructive_changes(proposals)
