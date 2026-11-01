"""Orchestration config: config/agents.yaml (budgets, gate, context, checkpoint)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Budgets:
    max_agent_steps: int = 6
    max_llm_calls: int = 14
    max_tool_steps_per_agent: int = 2
    task_timeout_s: float = 2400


@dataclass
class QualityGate:
    code: list[str] = field(default_factory=lambda: ["reviewer", "security"])
    docs: list[str] = field(default_factory=lambda: ["reviewer"])
    code_exts: list[str] = field(default_factory=lambda: [".py", ".sh", ".yaml", ".yml", ".toml", ".json"])
    block_on_severity: str = "high"
    veto: list[str] = field(default_factory=lambda: ["security"])
    remediate: list[str] = field(default_factory=lambda: ["reviewer"])
    max_remediation_rounds: int = 1

    def is_code(self, path: str) -> bool:
        name = path.rsplit("/", 1)[-1]
        return any(name == e or name.endswith(e) for e in self.code_exts)


@dataclass
class ContextConfig:
    rag_top_k: int = 3
    memory_top_k: int = 3
    include_global: bool = True
    chunk_chars: int = 700
    prior_chars: int = 1500
    review_chars: int = 6000


@dataclass
class AgentsConfig:
    planner: str = "llm"
    planner_tier: str = "general"
    max_plan_steps: int = 3
    examples: list[dict] = field(default_factory=list)
    budgets: Budgets = field(default_factory=Budgets)
    gate: QualityGate = field(default_factory=QualityGate)
    context: ContextConfig = field(default_factory=ContextConfig)
    task_summary: bool = True
    checkpoint_backend: str = "auto"
    postgres_schema: str = "agents"
    sqlite_path: str = "/data/agents.db"
    trace_dir: str = "/data/agent-traces"


def load_agents_config(path: str | None = None) -> AgentsConfig:
    p = Path(path or os.environ.get("AGENTS_CONFIG") or REPO_ROOT / "config" / "agents.yaml")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    sup, b, g = raw.get("supervisor") or {}, raw.get("budgets") or {}, raw.get("quality_gate") or {}
    c, ck = raw.get("context") or {}, raw.get("checkpoint") or {}
    return AgentsConfig(
        planner=sup.get("planner", "llm"),
        planner_tier=sup.get("planner_tier", "general"),
        max_plan_steps=int(sup.get("max_plan_steps", 3)),
        examples=[e for e in sup.get("examples") or [] if e.get("request") and e.get("plan")],
        budgets=Budgets(
            max_agent_steps=int(b.get("max_agent_steps", 6)),
            max_llm_calls=int(b.get("max_llm_calls", 14)),
            max_tool_steps_per_agent=int(b.get("max_tool_steps_per_agent", 2)),
            task_timeout_s=float(b.get("task_timeout_s", 2400)),
        ),
        gate=QualityGate(
            code=list(g.get("code", ["reviewer", "security"])),
            docs=list(g.get("docs", ["reviewer"])),
            code_exts=list(g.get("code_exts", [".py"])),
            block_on_severity=g.get("block_on_severity", "high"),
            veto=list(g.get("veto", ["security"])),
            remediate=list(g.get("remediate", ["reviewer"])),
            max_remediation_rounds=int(g.get("max_remediation_rounds", 1)),
        ),
        context=ContextConfig(
            rag_top_k=int(c.get("rag_top_k", 3)), memory_top_k=int(c.get("memory_top_k", 3)),
            include_global=bool(c.get("include_global", True)), chunk_chars=int(c.get("chunk_chars", 700)),
            prior_chars=int(c.get("prior_chars", 1500)), review_chars=int(c.get("review_chars", 6000)),
        ),
        task_summary=bool((raw.get("memory") or {}).get("task_summary", True)),
        checkpoint_backend=os.environ.get("AGENT_CHECKPOINT", ck.get("backend", "auto")),
        postgres_schema=ck.get("postgres_schema", "agents"),
        sqlite_path=ck.get("sqlite_path", "/data/agents.db"),
        trace_dir=os.environ.get("AGENT_TRACE_DIR", raw.get("trace_dir", "/data/agent-traces")),
    )
