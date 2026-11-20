"""memory MCP server: long-term memory (M5) — recall/list, scoped remember/forget.

Reads cover the workspace scope (+ global). Writes and deletes are limited to
``servers.memory.writable_scopes`` and ``write_types``; ``memory_forget`` is a hard
delete (FR-013, user-deletable) and is marked destructive so the client asks first.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .common import Ctx, Denied


def _item(i) -> dict:
    return {"memory_id": i.memory_id, "type": i.type, "scope": i.scope, "content": i.content,
            "tags": i.tags, "confidence": round(i.confidence, 2), "source": i.source,
            "updated_at": str(i.updated_at)[:19]}


def register(server: MCPServer, ctx: Ctx) -> None:
    cfg = ctx.cfg.server("memory")
    include_global = bool(cfg.get("include_global", True))
    max_results = int(cfg.get("max_results", 10))
    writable = ctx.cfg.scopes("memory", "writable_scopes") or [ctx.scope]
    write_types = list(cfg.get("write_types") or ["fact", "note"])

    def svc():
        if "memory" not in ctx.deps:
            from memory.service import open_service

            ctx.deps["memory"] = open_service()
            ctx.closers.append(ctx.deps["memory"].close)
        return ctx.deps["memory"]

    def memory_recall(query: str, limit: int = 5, types: list[str] | None = None) -> list[dict]:
        """Semantic recall of long-term memories for this workspace scope (+ global)."""
        if not query.strip():
            raise ValueError("query is empty")
        hits = svc().recall(query, scope=ctx.scope, top_k=max(1, min(int(limit), max_results)),
                            include_global=include_global, types=types or None)
        return [{**_item(h.item), "score": round(h.score, 3)} for h in hits]

    def memory_list(type: str = "", limit: int = 20) -> list[dict]:
        """List recent active memories in this workspace scope (+ global)."""
        n = max(1, min(int(limit), 100))
        scopes = [ctx.scope] + (["global"] if include_global and ctx.scope != "global" else [])
        items = [i for s in scopes for i in svc().list_items(scope=s, type=type or None, limit=n)]
        items.sort(key=lambda i: str(i.updated_at), reverse=True)
        return [_item(i) for i in items[:n]]

    for fn, title in ((memory_recall, "Recall memories"), (memory_list, "List memories")):
        ctx.tool(server, "memory", fn, title=title)

    if cfg.get("write", False):
        def memory_remember(content: str, type: str = "fact", tags: list[str] | None = None) -> dict:
            """Store a durable memory (fact/preference/decision/note) in this workspace's scope.
            Exact duplicates reinforce the existing memory."""
            if type not in write_types:
                raise Denied(f"memory type '{type}' is not writable via MCP (allowed: {write_types})")
            if ctx.scope not in writable:
                raise Denied(f"scope '{ctx.scope}' is not writable (allowed: {writable})")
            item = svc().remember(content, type=type, scope=ctx.scope, tags=tags or None, source="mcp")
            return {"stored": True, **_item(item)}

        ctx.tool(server, "memory", memory_remember, title="Remember", read_only=False, destructive=True)

    if cfg.get("forget", False):
        def memory_forget(memory_id: str) -> dict:
            """Permanently delete one memory (record + vector) in a writable scope."""
            item = svc().get(memory_id)
            if item is None:
                raise ValueError(f"unknown memory '{memory_id}'")
            if item.scope not in writable:
                raise Denied(f"memory is in scope '{item.scope}', not writable here (allowed: {writable})")
            return {"deleted": svc().delete(memory_id), "memory_id": memory_id}

        ctx.tool(server, "memory", memory_forget, title="Forget (delete) a memory",
                 read_only=False, destructive=True)
