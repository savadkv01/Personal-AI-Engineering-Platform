"""Tool implementations behind the policy.

Read tools (rag.retrieve, memory.read, fs.read, vcs) run immediately inside an agent's
bounded loop. Side-effecting tools (fs.write, test.run) are never executed in-chain:
agents *propose* them, and ``apply_write`` / ``run_tests`` run only after the quality
gate and human approval. shell / container / web.fetch are denied unless enabled
(they are disabled in M6). Every call returns an ``Observation`` and is traced.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

from .policy import ToolPolicy

TOOL_HELP = {
    "rag.retrieve": "search the knowledge base; tool_input = search query",
    "memory.read": "recall long-term memories; tool_input = query",
    "fs.read": "read a file or list a directory; tool_input = repo-relative path",
    "vcs": "read-only git; tool_input = 'status' | 'diff [path]' | 'log'",
}


@dataclass
class Observation:
    tool: str
    tool_input: str
    ok: bool
    text: str
    denied: bool = False
    sources: list[dict] = field(default_factory=list)   # [{source, text, score}] for citations

    def as_dict(self) -> dict:
        return {"tool": self.tool, "input": self.tool_input, "ok": self.ok, "denied": self.denied,
                "text": self.text[:500]}


class ToolRuntime:
    def __init__(self, policy: ToolPolicy, *, memory=None,
                 rag_search: Callable[[str, str | None, int], list[dict]] | None = None,
                 trace: Callable[[str, dict], None] | None = None,
                 include_global: bool = True):
        self.policy = policy
        self.memory = memory
        self.rag_search = rag_search
        self._trace = trace or (lambda kind, data: None)
        self.include_global = include_global

    # ------------------------------------------------------------- dispatcher
    def call(self, persona, tool: str, tool_input: str, *, scope: str | None,
             limit: int = 3, overlay: dict[str, str] | None = None) -> Observation:
        """``overlay``: path -> proposed (not yet applied) content, visible to fs.read in-task."""
        d = self.policy.tool_allowed(persona, tool)
        if not d:
            return self._deny(persona, tool, tool_input, d.reason)
        if d.approval:
            return self._deny(persona, tool, tool_input,
                              f"'{tool}' needs approval: propose it in your final answer instead")
        try:
            if tool == "rag.retrieve":
                obs = self._rag(tool_input, scope, limit)
            elif tool == "memory.read":
                obs = self._memory_read(tool_input, scope, limit)
            elif tool == "fs.read":
                obs = self._fs_read(persona, tool_input, overlay or {})
            elif tool == "vcs":
                obs = self._vcs(persona, tool_input)
            else:  # enabled but not executable in-chain (shell/container/web.fetch)
                return self._deny(persona, tool, tool_input, f"'{tool}' has no in-chain executor")
        except Exception as exc:  # noqa: BLE001 - tools must never crash the chain
            obs = Observation(tool, tool_input, False, f"error: {exc}")
        self._trace("tool.call", {"agent": persona.name, **obs.as_dict()})
        return obs

    def _deny(self, persona, tool: str, tool_input: str, reason: str) -> Observation:
        self._trace("policy.deny", {"agent": persona.name, "tool": tool, "input": tool_input,
                                    "reason": reason})
        return Observation(tool, tool_input, False, f"DENIED: {reason}", denied=True)

    # ------------------------------------------------------------- read tools
    def _rag(self, query: str, scope: str | None, limit: int) -> Observation:
        if self.rag_search is None:
            return Observation("rag.retrieve", query, False, "knowledge base unavailable")
        hits = self.rag_search(query, scope, limit)
        if not hits:
            return Observation("rag.retrieve", query, True, "no relevant knowledge-base passages")
        text = "\n".join(f"- ({h['source']}) {h['text'][:400]}" for h in hits)
        return Observation("rag.retrieve", query, True, text, sources=hits)

    def _memory_read(self, query: str, scope: str | None, limit: int) -> Observation:
        if self.memory is None:
            return Observation("memory.read", query, False, "memory service unavailable")
        hits = self.memory.recall(query, scope=scope, top_k=limit, include_global=self.include_global)
        srcs = [{"source": f"memory:{h.item.type}/{h.item.memory_id[:8]}", "text": h.item.content,
                 "score": round(h.score, 3), "memory_id": h.item.memory_id} for h in hits]
        if not srcs:
            return Observation("memory.read", query, True, "no relevant memories")
        return Observation("memory.read", query, True,
                           "\n".join(f"- ({s['source']}) {s['text']}" for s in srcs), sources=srcs)

    def _fs_read(self, persona, path: str, overlay: dict[str, str]) -> Observation:
        d = self.policy.check_read(persona, path)
        if not d:
            return self._deny(persona, "fs.read", path, d.reason)
        if d.path in overlay:
            text = overlay[d.path][: self.policy.max_read_bytes]
            src = {"source": f"{d.path} (proposed)", "text": text[:700], "score": None}
            return Observation("fs.read", path, True, f"(proposed in this task, not yet applied)\n{text}",
                               sources=[src])
        target = self.policy.abs_path(d.path)
        if target.is_dir():
            entries = []
            for p in sorted(target.iterdir()):
                rel = f"{d.path}/{p.name}" if d.path != "." else p.name
                if p.name.startswith(".") or self.policy.denied(rel):
                    continue
                entries.append(p.name + ("/" if p.is_dir() else ""))
                if len(entries) >= self.policy.max_list_entries:
                    entries.append("…")
                    break
            return Observation("fs.read", path, True, f"{d.path}/: " + ", ".join(entries))
        if not target.is_file():
            return Observation("fs.read", path, False, f"'{d.path}' does not exist")
        data = target.read_bytes()[: self.policy.max_read_bytes]
        text = data.decode("utf-8", errors="replace")
        return Observation("fs.read", path, True, text,
                           sources=[{"source": d.path, "text": text[:700], "score": None}])

    def _vcs(self, persona, tool_input: str) -> Observation:
        parts = (tool_input or "status").split()
        sub, rest = parts[0], parts[1:]
        allowed = self.policy.spec("vcs").get("subcommands", ["status", "diff", "log"])
        if sub not in allowed:
            return self._deny(persona, "vcs", tool_input, f"git '{sub}' not allowed (read-only: {allowed})")
        argv = ["git", "--no-pager", sub]
        if sub == "status":
            argv += ["--short", "--branch"]
        elif sub == "log":
            argv += ["--oneline", "-15"]
        elif sub == "diff":
            argv += ["--stat"] if not rest else []
            for p in rest[:5]:
                d = self.policy.check_read(persona, p)
                if not d:
                    return self._deny(persona, "vcs", tool_input, d.reason)
                argv += ["--", d.path]
        res = subprocess.run(argv, cwd=self.policy.root, capture_output=True, text=True, timeout=20,
                             check=False)
        out = (res.stdout or res.stderr or "(no output)")[: self.policy.max_read_bytes]
        return Observation("vcs", tool_input, res.returncode == 0, out)

    # ------------------------------------------------ approved side effects
    def apply_write(self, persona, path: str, content: str) -> dict:
        """Re-check policy at apply time, then write. Called only after approval."""
        d = self.policy.check_write(persona, path, content)
        if not d:
            self._trace("policy.deny", {"agent": persona.name, "tool": "fs.write", "input": path,
                                        "reason": d.reason, "phase": "apply"})
            return {"path": path, "applied": False, "reason": d.reason}
        target = self.policy.abs_path(d.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        rec = {"path": d.path, "applied": True, "created": not existed, "bytes": len(content.encode())}
        self._trace("apply.write", {"agent": persona.name, **rec})
        return rec

    def run_tests(self, persona, target: str) -> dict:
        d = self.policy.tool_allowed(persona, "test.run")
        if not d:
            return {"target": target, "ran": False, "reason": d.reason}
        r = self.policy.check_read(persona, target or "tests")
        if not r:
            return {"target": target, "ran": False, "reason": r.reason}
        spec = self.policy.spec("test.run")
        argv = list(spec.get("command") or ["python", "-m", "pytest", "-q"]) + [r.path]
        try:
            res = subprocess.run(argv, cwd=self.policy.root, capture_output=True, text=True,
                                 timeout=int(spec.get("timeout_s", 300)), check=False)
            out = (res.stdout + res.stderr)[-3000:]
            rec = {"target": r.path, "ran": True, "exit_code": res.returncode,
                   "passed": res.returncode == 0, "output": out}
        except subprocess.TimeoutExpired:
            rec = {"target": r.path, "ran": True, "exit_code": None, "passed": False,
                   "output": "timed out"}
        self._trace("apply.test", {"agent": persona.name, **{k: v for k, v in rec.items() if k != "output"}})
        return rec

    def memory_write(self, persona, mtype: str, content: str, *, scope: str, task_id: str) -> dict:
        d = self.policy.tool_allowed(persona, "memory.write")
        if not d:
            self._trace("policy.deny", {"agent": persona.name, "tool": "memory.write", "reason": d.reason})
            return {"written": False, "reason": d.reason}
        if mtype not in persona.memory_write_types:
            reason = f"{persona.name} may not write memory type '{mtype}' ({persona.memory_write_types})"
            self._trace("policy.deny", {"agent": persona.name, "tool": "memory.write", "reason": reason})
            return {"written": False, "reason": reason}
        if self.memory is None:
            return {"written": False, "reason": "memory service unavailable"}
        item = self.memory.remember(content, type=mtype, scope=scope,
                                    source=f"agent:{persona.name}:{task_id}")
        rec = {"written": True, "memory_id": item.memory_id, "type": mtype}
        self._trace("memory.write", {"agent": persona.name, **rec})
        return rec
