"""Persona loader: CrewAI-style YAML (role/goal/backstory) + PAIEP tier/tools/scope/guardrails."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from agents.tools.policy import TOOL_NAMES

PERSONA_DIR = Path(__file__).resolve().parents[1] / "personas"
TIERS = ("general", "coding", "reasoning", "draft")
OUTPUTS = ("plan", "text", "docs", "code", "review")
MEMORY_TYPES = ("fact", "preference", "decision", "entity", "progress", "task_summary", "note")


@dataclass
class Persona:
    name: str
    role: str
    goal: str
    backstory: str
    tier: str
    tools: list[str]
    fs_scope: dict[str, list[str]] = field(default_factory=lambda: {"read": [], "write": []})
    memory_write_types: list[str] = field(default_factory=list)
    output: str = "text"
    routing_keywords: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    personas: list[str] = field(default_factory=list)
    max_tool_steps: int = 2
    enabled: bool = True
    spec: str = ""

    @property
    def is_reviewer(self) -> bool:
        return self.output == "review"

    @property
    def can_write(self) -> bool:
        return "fs.write" in self.tools and bool(self.fs_scope.get("write"))

    def summary(self) -> dict:
        return {"name": self.name, "role": self.role, "enabled": self.enabled, "tier": self.tier,
                "output": self.output, "tools": self.tools, "write_scope": self.fs_scope.get("write", []),
                "personas": self.personas}


def _validate(p: Persona, path: Path) -> None:
    errs = []
    if p.tier not in TIERS:
        errs.append(f"tier '{p.tier}' not in {TIERS}")
    if p.output not in OUTPUTS:
        errs.append(f"output '{p.output}' not in {OUTPUTS}")
    bad = [t for t in p.tools if t not in TOOL_NAMES]
    if bad:
        errs.append(f"unknown tools {bad}")
    badm = [t for t in p.memory_write_types if t not in MEMORY_TYPES]
    if badm:
        errs.append(f"unknown memory types {badm}")
    if p.memory_write_types and "memory.write" not in p.tools:
        errs.append("memory_write_types set but memory.write not allowed")
    if p.fs_scope.get("write") and "fs.write" not in p.tools:
        errs.append("write scope set but fs.write not allowed")
    if p.is_reviewer and p.can_write:
        errs.append("review personas must be read-only")
    if errs:
        raise ValueError(f"invalid persona {path.name}: " + "; ".join(errs))


def load_personas(directory: str | Path | None = None) -> dict[str, Persona]:
    out: dict[str, Persona] = {}
    for path in sorted(Path(directory or PERSONA_DIR).glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        scope = raw.get("fs_scope") or {}
        p = Persona(
            name=raw["name"], role=raw["role"], goal=raw["goal"], backstory=raw.get("backstory", ""),
            tier=raw.get("tier", "general"), tools=list(raw.get("tools") or []),
            fs_scope={"read": list(scope.get("read") or []), "write": list(scope.get("write") or [])},
            memory_write_types=list(raw.get("memory_write_types") or []),
            output=raw.get("output", "text"),
            routing_keywords=[k.lower() for k in raw.get("routing_keywords") or []],
            guardrails=list(raw.get("guardrails") or []), personas=list(raw.get("personas") or []),
            max_tool_steps=int(raw.get("max_tool_steps", 2)), enabled=bool(raw.get("enabled", True)),
            spec=raw.get("spec", ""),
        )
        _validate(p, path)
        if p.name in out:
            raise ValueError(f"duplicate persona name '{p.name}'")
        out[p.name] = p
    if "supervisor" not in out:
        raise ValueError("persona catalog must define 'supervisor'")
    return out
