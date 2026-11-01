"""Runtime: wires config, personas, policy, tools, model router, memory, checkpointer, trace.

``Runtime`` is dependency-injected so tests can pass fakes; ``open_runtime()`` builds the
real one (fail-soft: memory and KB are optional, the model gateway is required).
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

from langgraph.types import Command

from agents.tools.policy import ToolPolicy, load_policy
from agents.tools.registry import ToolRuntime

from .checkpoint import open_checkpointer, resolve_backend
from .config import AgentsConfig, load_agents_config
from .graph import build_graph
from .llm import ChatClient, ModelRouter, load_router_config
from .personas import load_personas
from .trace import TraceSink

log = logging.getLogger("paiep.agents")
RECURSION_LIMIT = 60


@dataclass
class Runtime:
    cfg: AgentsConfig
    personas: dict
    policy: ToolPolicy
    llm: object
    trace: TraceSink
    checkpointer: object
    memory: object | None = None
    rag_search: object | None = None
    closers: list = field(default_factory=list)

    def __post_init__(self):
        self.tools = ToolRuntime(self.policy, memory=self.memory, rag_search=self.rag_search,
                                 trace=self.trace, include_global=self.cfg.context.include_global)
        self.graph = build_graph(self, self.checkpointer)

    # ------------------------------------------------------------------ API
    def _config(self, task_id: str) -> dict:
        return {"configurable": {"thread_id": task_id}, "recursion_limit": RECURSION_LIMIT}

    def start(self, task: str, *, scope: str = "global", agent: str | None = None,
              task_id: str | None = None, on_update=None) -> dict:
        task_id = task_id or str(uuid.uuid4())
        self.trace.bind(task_id)
        self.trace("task.start", {"task": task, "scope": scope, "agent_override": agent})
        init = {"task": task, "scope": scope, "task_id": task_id, "agent_override": agent,
                "started_t": time.time()}
        self._drive(init, task_id, on_update)
        return self.view(task_id)

    def resume(self, task_id: str, *, approved: bool, paths: list[str] | None = None,
               run_tests: bool = True, on_update=None) -> dict:
        self.trace.bind(task_id)
        v = self.view(task_id)
        if v["status"] != "awaiting_approval":
            raise ValueError(f"task {task_id} is not awaiting approval (status: {v['status']})")
        self._drive(Command(resume={"approved": approved, "paths": paths or None, "run_tests": run_tests}),
                    task_id, on_update)
        return self.view(task_id)

    def _drive(self, inp, task_id: str, on_update) -> None:
        for chunk in self.graph.stream(inp, self._config(task_id), stream_mode="updates"):
            if on_update:
                for node, upd in chunk.items():
                    on_update(node, upd)

    def view(self, task_id: str) -> dict:
        snap = self.graph.get_state(self._config(task_id))
        values = dict(snap.values or {})
        if not values:
            return {"task_id": task_id, "status": "unknown"}
        pending = [i.value for t in snap.tasks for i in (t.interrupts or [])]
        status = "awaiting_approval" if pending else values.get("status", "running")
        return {"task_id": task_id, "status": status, "task": values.get("task"),
                "scope": values.get("scope"), "plan": values.get("plan", []), "method": values.get("method"),
                "results": values.get("results", []), "proposals": values.get("proposals", []),
                "actions": values.get("actions", []), "denied": values.get("denied", []),
                "applied": values.get("applied", []), "test_results": values.get("test_results", []),
                "messages": values.get("messages", []), "llm_calls": values.get("llm_calls", 0),
                "reason": values.get("reason", ""), "clarify": values.get("clarify", ""),
                "requested": values.get("requested", {}), "gate_issues": values.get("gate_issues", []),
                "approval_request": pending[0] if pending else None, "final": values.get("final", "")}

    def close(self) -> None:
        for c in self.closers:
            try:
                c()
            except Exception:  # noqa: BLE001
                pass


def _rag_search_fn():
    from rag.query.config import load_query_config
    from rag.query.retriever import retrieve

    qcfg = load_query_config()

    def search(query: str, scope: str | None, limit: int) -> list[dict]:
        hits = retrieve(query, qcfg, scope=scope, limit=limit, include_global=True)
        return [{"source": h.source, "text": h.text, "score": round(h.score, 3)} for h in hits]

    return search


def open_runtime(*, checkpoint: str | None = None, with_memory: bool = True) -> Runtime:
    cfg = load_agents_config()
    personas = load_personas()
    policy = load_policy()
    rcfg = load_router_config()
    client = ChatClient(rcfg)
    client.router = ModelRouter(rcfg, client.list_models() or None)

    memory, closers, mem_backend, dsn = None, [], None, None
    if with_memory:
        try:
            from memory.service import open_service

            memory = open_service()
            mem_backend, dsn = memory.cfg.backend, memory.cfg.dsn
            closers.append(memory.close)
        except Exception as exc:  # noqa: BLE001
            log.warning("memory unavailable, agents run without it: %s", exc)
    try:
        rag = _rag_search_fn()
    except Exception as exc:  # noqa: BLE001
        log.warning("knowledge base unavailable: %s", exc)
        rag = None

    backend = checkpoint or cfg.checkpoint_backend
    if backend == "auto" and mem_backend is None:
        try:  # commands that skip memory still follow the configured memory backend
            from memory.service.config import load_memory_config

            mcfg = load_memory_config(with_embed=False)
            mem_backend, dsn = mcfg.backend, mcfg.dsn
        except Exception:  # noqa: BLE001
            pass
    backend = resolve_backend(cfg, mem_backend) if backend == "auto" else backend
    if backend == "postgres" and not dsn:
        from memory.service.config import load_memory_config

        dsn = load_memory_config(with_embed=False).dsn
    saver, close_saver = open_checkpointer(backend, dsn=dsn, schema=cfg.postgres_schema,
                                           sqlite_path=cfg.sqlite_path)
    closers.insert(0, close_saver)
    return Runtime(cfg=cfg, personas=personas, policy=policy, llm=client, trace=TraceSink(cfg.trace_dir),
                   checkpointer=saver, memory=memory, rag_search=rag, closers=closers)
