"""rag MCP server: read-only knowledge-base access (M4), scope-filtered.

``rag_search`` = retrieval only (embed + Qdrant, ~1 s) — the editor's own model writes the
answer. ``rag_answer`` = the full M4 pipeline (retrieve -> re-rank -> grounded, cited
answer from the local model; 1-3 min on CPU). Requested scopes must be in
``servers.rag.allowed_scopes``.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .common import Ctx, Denied

SCOPE_ALIASES = {"", "workspace", "default", "current", "this"}


def _default_search():
    from rag.query.config import load_query_config
    from rag.query.retriever import retrieve

    qcfg = load_query_config()

    def search(query: str, scope: str, limit: int, tags: list[str] | None,
               include_global: bool) -> list[dict]:
        hits = retrieve(query, qcfg, scope=scope, limit=limit, tags=tags, include_global=include_global)
        return [{"source": h.source, "title": h.title, "scope": h.scope, "score": round(h.score, 3),
                 "chunk_index": h.chunk_index, "text": h.text} for h in hits]

    return search


def _default_answer():
    from rag.query.engine import answer

    return lambda question, scope, include_global: answer(
        question, scope=scope, include_global=include_global).as_dict()


def register(server: MCPServer, ctx: Ctx) -> None:
    cfg = ctx.cfg.server("rag")
    allowed = ctx.cfg.scopes("rag", "allowed_scopes") or [ctx.scope]
    max_results = int(cfg.get("max_results", 8))
    include_global = bool(cfg.get("include_global", True))

    def scope_ok(scope: str) -> str:
        # Small models often pass the descriptive word from the docstring instead of a scope id.
        s = ctx.scope if (scope or "").strip().lower() in SCOPE_ALIASES else scope.strip()
        if s not in allowed:
            raise Denied(f"scope '{s}' is not allowed for this workspace (allowed: {allowed})")
        return s

    def backend(key: str, factory):
        if key not in ctx.deps:
            ctx.deps[key] = factory()
        return ctx.deps[key]

    def rag_search(query: str, limit: int = 5, scope: str = "", tags: list[str] | None = None) -> str:
        """Search the PAIEP knowledge base (read-only). Returns numbered passages with sources
        to cite as [n]. Leave `scope` empty: it defaults to the configured scope plus global docs.
        Only set it to an exact id such as 'global' or 'project:<name>' when the user asks."""
        if not query.strip():
            raise ValueError("query is empty")
        s = scope_ok(scope)
        k = max(1, min(int(limit), max_results))
        hits = backend("rag_search", _default_search)(query, s, k, tags or None, include_global)
        if not hits:
            return f"No relevant passages in scope '{s}'" + (" (+global)." if include_global else ".")
        lines = [f"{len(hits)} passage(s) for scope '{s}':"]
        for n, h in enumerate(hits, 1):
            lines.append(f"\n[{n}] {h['source']} (score {h['score']}, scope {h['scope']})\n{h['text'][:900]}")
        return "\n".join(lines)

    ctx.tool(server, "rag", rag_search, title="Search the PAIEP knowledge base")
    if not cfg.get("answer", False):
        return

    def rag_answer(question: str, scope: str = "") -> dict:
        """Grounded, cited answer from the LOCAL model over the knowledge base (slow on CPU:
        1-3 min). Prefer rag_search when you can write the answer yourself."""
        if not question.strip():
            raise ValueError("question is empty")
        return backend("rag_answer", _default_answer)(question, scope_ok(scope), include_global)

    ctx.tool(server, "rag", rag_answer, title="Grounded answer from the local model")
