"""Shared MCP plumbing: config, scope, path policy, audit trail and tool registration.

Every PAIEP MCP tool is registered through ``Ctx.tool`` which
  * runs the (sync) implementation in a worker thread (slow backends never block the
    stdio loop),
  * turns ``Denied`` into an MCP tool error ``DENIED: ...`` (``isError=true``),
  * writes one JSONL audit record per call (server, tool, sanitized args, outcome, ms);
    free-text arguments (file content, memories, queries, tasks) are logged only as
    length + sha256 so forgetting a memory leaves no plaintext copy behind,
  * sets MCP tool annotations (readOnly / destructive) so clients ask before side effects.
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anyio
import yaml
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from agents.tools.policy import Decision, ToolPolicy, glob_match

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "mcp.yaml"
SERVER_NAMES = ("fs", "git", "rag", "memory", "paiep-tools")
_SCOPE_RE = re.compile(r"^(global|project:[A-Za-z0-9][A-Za-z0-9._-]{0,63})$")
# Arguments that carry user/model free text: never written to the audit log in plaintext.
REDACTED_ARGS = frozenset({"content", "query", "question", "task"})
# Host filesystems where `.ENV` opens `.env` (Windows, default macOS): match globs case-insensitively.
CASE_INSENSITIVE_FS = os.name == "nt" or sys.platform == "darwin"

log = logging.getLogger("paiep.mcp")


class Denied(Exception):
    """A policy refusal. Reported to the client as ``DENIED: <reason>``."""


def validate_scope(scope: str) -> str:
    if not _SCOPE_RE.match(scope or ""):
        raise ValueError(f"invalid scope '{scope}' (expected global | project:<name>)")
    return scope


@dataclass
class McpConfig:
    root: Path
    scope: str
    deny_globs: list[str]
    write_deny_globs: list[str]
    skip_dirs: set[str]
    limits: dict[str, int]
    servers: dict[str, dict]
    audit_dir: Path | None
    max_arg_chars: int = 300
    workspace_id: str = ""      # host identity of the workspace (agent tasks are bound to it)

    def server(self, name: str) -> dict:
        return self.servers.get(name) or {}

    def enabled(self, name: str) -> bool:
        return bool(self.server(name).get("enabled", False))

    def scopes(self, name: str, key: str) -> list[str]:
        """Expand ``${scope}`` in a server's scope list (deduplicated, order kept)."""
        out: list[str] = []
        for s in self.server(name).get(key) or []:
            s = self.scope if s == "${scope}" else s
            if s not in out:
                out.append(s)
        return out


def _writable_dir(path: Path) -> Path | None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return path
    except OSError:
        return None


def load_mcp_config(path: str | None = None, *, root: str | None = None,
                    scope: str | None = None) -> McpConfig:
    with open(path or os.environ.get("MCP_CONFIG") or DEFAULT_CONFIG, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    ws = raw.get("workspace") or {}
    root_dir = root or os.environ.get("MCP_WORKSPACE") or ws.get("root") or os.getcwd()
    if not Path(root_dir).is_dir():
        log.warning("workspace %s not found; using the current directory", root_dir)
        root_dir = os.getcwd()
    scope = validate_scope(scope or os.environ.get("PAIEP_SCOPE") or raw.get("default_scope") or "global")
    audit = raw.get("audit") or {}
    audit_dir = None
    fallback = str(Path.home() / ".paiep" / "mcp-audit")
    candidates = (os.environ.get("MCP_AUDIT_DIR"), audit.get("dir"), fallback)
    for cand in candidates:
        if cand and (audit_dir := _writable_dir(Path(cand))):
            break
    if audit_dir is None:
        raise OSError(f"could not create a writable MCP audit directory from {candidates}")
    limits = {k: int(ws[k]) for k in ("max_read_bytes", "max_write_bytes", "max_list_entries",
                                      "max_search_files", "max_search_results") if k in ws}
    root_path = Path(root_dir).resolve()
    return McpConfig(
        root=root_path, scope=scope,
        deny_globs=list(ws.get("deny_globs") or []),
        write_deny_globs=list(ws.get("write_deny_globs") or []),
        skip_dirs=set(ws.get("skip_dirs") or []),
        limits={"max_read_bytes": 40000, "max_write_bytes": 60000, "max_list_entries": 300,
                "max_search_files": 4000, "max_search_results": 50, **limits},
        servers=raw.get("servers") or {}, audit_dir=audit_dir,
        max_arg_chars=int(audit.get("max_arg_chars", 300)),
        # Containers all see /workspace; Compose passes the host path so tasks stay per-workspace.
        workspace_id=os.environ.get("PAIEP_WORKSPACE_ID") or root_path.as_posix(),
    )


# ------------------------------------------------------------------ path policy
@dataclass
class ClientPersona:
    """The editor client seen through the M6 policy: one 'persona' with fs scopes."""
    name: str
    tools: list[str]
    fs_scope: dict[str, list[str]]
    memory_write_types: list[str] = field(default_factory=list)


class PathPolicy:
    """M6 ``ToolPolicy`` (normalisation, traversal/symlink guards, deny globs) + MCP write denies."""

    def __init__(self, cfg: McpConfig):
        fs = cfg.server("fs")
        write = bool(fs.get("write", False))
        self.cfg = cfg
        self.policy = ToolPolicy(
            tools={"fs.read": {"enabled": True}, "fs.write": {"enabled": write}},
            root=cfg.root, deny_globs=cfg.deny_globs,
            max_read_bytes=cfg.limits["max_read_bytes"], max_write_bytes=cfg.limits["max_write_bytes"],
            max_list_entries=cfg.limits["max_list_entries"])
        self.persona = ClientPersona(
            name="mcp-client", tools=["fs.read"] + (["fs.write"] if write else []),
            fs_scope={"read": list(fs.get("read_scope") or ["**"]),
                      "write": list(fs.get("write_scope") or [])})

    @property
    def root(self) -> Path:
        return self.policy.root

    @staticmethod
    def _hit(rel: str, globs: list[str]) -> str | None:
        if CASE_INSENSITIVE_FS:
            rel = rel.lower()
            return next((g for g in globs if glob_match(rel, g.lower())), None)
        return next((g for g in globs if glob_match(rel, g)), None)

    def _host_guard(self, rel: str) -> str:
        """Close host-filesystem aliases the POSIX globs cannot see (host-Python launches):
        case-insensitive names, NTFS streams (`.env::$DATA`) and trailing dots/spaces (`.env.`)."""
        if os.name == "nt" and any(":" in p or p != p.rstrip(". ") for p in rel.split("/") if p != "."):
            raise Denied(f"path '{rel}' uses a Windows alias (stream or trailing dot/space)")
        hit = self._hit(rel, self.cfg.deny_globs)
        if hit:
            raise Denied(f"path '{rel}' is protected by deny glob '{hit}'")
        return rel

    def read(self, path: str) -> str:
        d = self.policy.check_read(self.persona, path)
        if not d:
            raise Denied(d.reason)
        return self._host_guard(d.path)

    def write(self, path: str, content: str) -> str:
        d: Decision = self.policy.check_write(self.persona, path, content)
        if not d:
            raise Denied(d.reason)
        rel = self._host_guard(d.path)
        hit = self._hit(rel, self.cfg.write_deny_globs)
        if hit:
            raise Denied(f"path '{rel}' is read-only for MCP clients (write deny glob '{hit}')")
        return rel

    def hidden(self, rel: str) -> bool:
        """Excluded from listings/search: denied paths and noise directories."""
        return bool(self._hit(rel, self.cfg.deny_globs)) or any(
            p in self.cfg.skip_dirs for p in rel.split("/"))

    def abs(self, rel: str) -> Path:
        return self.policy.abs_path(rel)


# ------------------------------------------------------------------------ audit
class Audit:
    def __init__(self, directory: Path | None, max_arg_chars: int = 300):
        self.dir = directory
        self.max = max_arg_chars
        self.events: list[dict] = []          # in-memory copy for tests

    def _arg(self, key: str, v):
        if isinstance(v, str) and (key in REDACTED_ARGS or len(v) > self.max):
            return {"chars": len(v), "sha256": hashlib.sha256(v.encode()).hexdigest()[:16]}
        return v

    def __call__(self, server: str, tool: str, args: dict, outcome: str, ms: int,
                 scope: str, detail: str = "") -> None:
        ev = {"ts": datetime.now(timezone.utc).isoformat(), "server": server, "tool": tool,  # noqa: UP017
              "scope": scope, "args": {k: self._arg(k, v) for k, v in args.items()},
              "outcome": outcome, "ms": ms}
        if detail:
            ev["detail"] = detail[:300]
        self.events.append(ev)
        if self.dir:
            try:
                with open(self.dir / f"{ev['ts'][:10]}.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(ev, default=str) + "\n")
            except OSError as exc:
                log.warning("audit write failed: %s", exc)


# ---------------------------------------------------------------------- context
@dataclass
class Ctx:
    cfg: McpConfig
    audit: Audit
    paths: PathPolicy
    deps: dict = field(default_factory=dict)      # injected backends (tests / lazy singletons)
    closers: list[Callable[[], None]] = field(default_factory=list)

    @property
    def scope(self) -> str:
        return self.cfg.scope

    def tool(self, server: MCPServer, server_name: str, fn: Callable, *, title: str,
             read_only: bool = True, destructive: bool = False) -> None:
        """Register ``fn`` (sync, returns str | dict | list) as an audited MCP tool."""
        name = fn.__name__

        @functools.wraps(fn)
        async def wrapper(**kwargs):
            t0 = time.monotonic()
            try:
                out = await anyio.to_thread.run_sync(functools.partial(fn, **kwargs))
            except Denied as exc:
                self.audit(server_name, name, kwargs, "denied", _ms(t0), self.scope, str(exc))
                raise ToolError(f"DENIED: {exc}") from None
            except ToolError as exc:
                self.audit(server_name, name, kwargs, "error", _ms(t0), self.scope, str(exc))
                raise
            except Exception as exc:  # noqa: BLE001 - surface as a tool error, never crash the server
                log.exception("tool %s failed", name)
                self.audit(server_name, name, kwargs, "error", _ms(t0), self.scope, repr(exc))
                raise ToolError(f"error: {type(exc).__name__}: {exc}") from None
            self.audit(server_name, name, kwargs, "ok", _ms(t0), self.scope)
            return out if isinstance(out, str) else json.dumps(out, indent=1, default=str)

        server.add_tool(wrapper, name=name, title=title, structured_output=False,
                        annotations=ToolAnnotations(title=title, read_only_hint=read_only,
                                                    destructive_hint=destructive if not read_only else None,
                                                    open_world_hint=False))

    def close(self) -> None:
        for c in reversed(self.closers):
            try:
                c()
            except Exception as exc:  # noqa: BLE001
                log.warning("MCP backend cleanup failed: %s", exc)


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def build_ctx(cfg: McpConfig | None = None, deps: dict | None = None) -> Ctx:
    cfg = cfg or load_mcp_config()
    return Ctx(cfg=cfg, audit=Audit(cfg.audit_dir, cfg.max_arg_chars), paths=PathPolicy(cfg),
               deps=dict(deps or {}))


def truncate(text: str, limit: int, note: str = "truncated") -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… [{note}: {len(text) - limit} more chars]"
