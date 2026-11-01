"""Tool policy (ADR 0006): default-deny tools, path-scoped file access, approval flags.

A persona may use a tool only if it is globally enabled in ``config/tool-policy.yaml``
AND listed in the persona's ``tools``. File paths are resolved inside the workspace
root (no ``..``/absolute/symlink escapes), must match one of the persona's scope globs
and none of the global ``deny_globs``.
"""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = REPO_ROOT / "config" / "tool-policy.yaml"

TOOL_NAMES = ("rag.retrieve", "memory.read", "memory.write", "fs.read", "fs.write", "vcs",
              "test.run", "shell", "container", "web.fetch")
READ_TOOLS = ("rag.retrieve", "memory.read", "fs.read", "vcs")


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    approval: bool = False
    path: str | None = None          # workspace-relative POSIX path when a path was checked

    def __bool__(self) -> bool:
        return self.allowed


def glob_match(path: str, pattern: str) -> bool:
    """fnmatch where ``*`` spans directories; ``**/`` may also match zero directories
    (``**/x`` matches ``x``; ``a/**/b`` matches ``a/b``), as in .gitignore."""
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]):
        return True
    if "/**/" in pattern and fnmatch.fnmatchcase(path, pattern.replace("/**/", "/", 1)):
        return True
    return pattern.endswith("/**") and path == pattern[:-3]


@dataclass
class ToolPolicy:
    tools: dict[str, dict]
    root: Path
    deny_globs: list[str] = field(default_factory=list)
    max_read_bytes: int = 20000
    max_write_bytes: int = 60000
    max_list_entries: int = 200

    # --- tools -------------------------------------------------------------
    def spec(self, tool: str) -> dict:
        return self.tools.get(tool) or {}

    def tool_allowed(self, persona, tool: str) -> Decision:
        if tool not in TOOL_NAMES:
            return Decision(False, f"unknown tool '{tool}'")
        spec = self.spec(tool)
        if not spec.get("enabled", False):
            return Decision(False, f"'{tool}' is disabled by policy (config/tool-policy.yaml)")
        if tool not in persona.tools:
            return Decision(False, f"'{tool}' is not in {persona.name}'s allow-list")
        return Decision(True, approval=spec.get("approval") == "required")

    # --- paths -------------------------------------------------------------
    def normalize(self, path: str) -> str | None:
        """Workspace-relative POSIX path, or None if it escapes the root."""
        raw = (path or "").strip().replace("\\", "/")
        if not raw:
            return None
        p = PurePosixPath(raw)
        if p.is_absolute():
            try:
                p = PurePosixPath(Path(raw).resolve().relative_to(self.root.resolve()).as_posix())
            except ValueError:
                return None
        parts = [x for x in p.parts if x not in ("", ".")]
        if any(x == ".." for x in parts):
            return None
        rel = "/".join(parts) or "."
        # Symlink escape: the real location must stay inside the root.
        real = (self.root / rel).resolve()
        try:
            real.relative_to(self.root.resolve())
        except ValueError:
            return None
        return rel

    def denied(self, rel: str) -> str | None:
        for g in self.deny_globs:
            if glob_match(rel, g):
                return g
        return None

    def _check(self, persona, path: str, mode: str) -> Decision:
        tool = "fs.read" if mode == "read" else "fs.write"
        d = self.tool_allowed(persona, tool)
        if not d:
            return d
        rel = self.normalize(path)
        if rel is None:
            return Decision(False, f"path '{path}' escapes the workspace")
        hit = self.denied(rel)
        if hit:
            return Decision(False, f"path '{rel}' is protected by deny glob '{hit}'", path=rel)
        scopes = persona.fs_scope.get(mode, [])
        if rel != "." and not any(glob_match(rel, g) for g in scopes):
            return Decision(False, f"path '{rel}' is outside {persona.name}'s {mode} scope {scopes}",
                            path=rel)
        if rel == "." and "**" not in scopes:
            return Decision(False, f"workspace root is outside {persona.name}'s {mode} scope", path=rel)
        return Decision(True, approval=d.approval, path=rel)

    def check_read(self, persona, path: str) -> Decision:
        return self._check(persona, path, "read")

    def check_write(self, persona, path: str, content: str) -> Decision:
        d = self._check(persona, path, "write")
        if not d:
            return d
        if d.path == "." or d.path.endswith("/"):
            return Decision(False, "write target must be a file", path=d.path)
        if (self.root / d.path).is_dir():
            return Decision(False, f"'{d.path}' is a directory", path=d.path)
        size = len(content.encode("utf-8"))
        if size > self.max_write_bytes:
            return Decision(False, f"proposal is {size} bytes > max_write_bytes {self.max_write_bytes}",
                            path=d.path)
        return d

    def abs_path(self, rel: str) -> Path:
        return self.root / rel


def load_policy(path: str | None = None, root: str | None = None) -> ToolPolicy:
    with open(path or os.environ.get("TOOL_POLICY") or DEFAULT_POLICY, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    ws = raw.get("workspace") or {}
    root_dir = root or os.environ.get("AGENT_WORKSPACE") or ws.get("root") or str(REPO_ROOT)
    if not Path(root_dir).is_dir():
        root_dir = str(REPO_ROOT)  # host runs: fall back to this checkout
    return ToolPolicy(
        tools=raw.get("tools") or {},
        root=Path(root_dir).resolve(),
        deny_globs=list(ws.get("deny_globs") or []),
        max_read_bytes=int(ws.get("max_read_bytes", 20000)),
        max_write_bytes=int(ws.get("max_write_bytes", 60000)),
        max_list_entries=int(ws.get("max_list_entries", 200)),
    )
