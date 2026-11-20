"""git MCP server: read-mostly git on the mounted workspace.

Read: status, diff, log, show, branches. Write: create_branch (local only, approval via
the client). No commit/push tools in M7. Hardening: argv only (no shell), option-injection
checks on revs/names, ``--no-ext-diff --no-textconv``, ``core.fsmonitor=false`` and an empty
``core.hooksPath`` so repo config/hooks cannot make git execute commands, and deny-glob
pathspec excludes on every diff/log/show so output never reveals secrets (.env, keys) even
when tracked.
"""
from __future__ import annotations

import os
import re
import subprocess

from mcp.server.mcpserver import MCPServer

from .common import CASE_INSENSITIVE_FS, Ctx, Denied, truncate

_REV_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/~^@{}-]{0,99}$")
OUT_LIMIT = 30000


def register(server: MCPServer, ctx: Ctx) -> None:
    cfg = ctx.cfg.server("git")
    root = ctx.paths.root
    magic = "exclude,glob,icase" if CASE_INSENSITIVE_FS else "exclude,glob"
    excludes = [f":({magic}){g}" for g in ctx.cfg.deny_globs if not g.startswith(".git/")]

    def git(*args: str, timeout: int = 30) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat"}
        argv = ["git", "-c", "core.quotepath=off", "-c", "core.fsmonitor=false", "-c", "color.ui=never",
                "-c", f"core.hooksPath={os.devnull}", "--no-pager", *args]
        res = subprocess.run(argv, cwd=root, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout, env=env, check=False)
        if res.returncode != 0:
            raise ValueError((res.stderr or res.stdout or f"git exited {res.returncode}").strip()[:2000])
        return truncate(res.stdout, OUT_LIMIT) or "(no output)"

    def rev_ok(rev: str) -> str:
        if not _REV_RE.match(rev or ""):
            raise Denied(f"invalid revision '{rev}'")
        return rev

    def pathspec(path: str | None) -> list[str]:
        # Excludes apply to EVERY pathspec: a directory (or ".") would otherwise include
        # tracked secrets below it, e.g. git diff -- . showing a committed .env.
        return ["--", ctx.paths.read(path) if path else ".", *excludes]

    def git_status() -> str:
        """Working-tree status (short format, with branch and ahead/behind)."""
        return git("status", "--short", "--branch")

    def git_diff(path: str = "", staged: bool = False, stat: bool = False) -> str:
        """Unified diff of uncommitted changes (staged=True for the index). Secrets are excluded."""
        args = ["diff", "--no-ext-diff", "--no-textconv"]
        if staged:
            args.append("--cached")
        if stat:
            args.append("--stat")
        return git(*args, *pathspec(path or None))

    def git_log(limit: int = 15, path: str = "") -> str:
        """Recent commits (hash, date, author, subject), optionally for one path."""
        n = max(1, min(int(limit), int(cfg.get("log_max", 50))))
        return git("log", f"-n{n}", "--date=short", "--format=%h %ad %an%d %s", *pathspec(path or None))

    def git_show(rev: str = "HEAD", stat_only: bool = False) -> str:
        """Show one commit (message + patch, or --stat). Secrets are excluded from the patch."""
        args = ["show", "--no-ext-diff", "--no-textconv", "--format=fuller"]
        if stat_only:
            args.append("--stat")
        return git(*args, rev_ok(rev), *pathspec(None))

    def git_branches() -> str:
        """Local and remote-tracking branches (current marked with *)."""
        return git("branch", "--all", "--no-color", "-vv")

    srv = "git"
    for fn, title in ((git_status, "Git status"), (git_diff, "Git diff"), (git_log, "Git log"),
                      (git_show, "Git show commit"), (git_branches, "Git branches")):
        ctx.tool(server, srv, fn, title=title)
    if not cfg.get("create_branch", False):
        return

    def git_create_branch(name: str, start_point: str = "", switch: bool = False) -> str:
        """Create a LOCAL branch (optionally from start_point) and optionally switch to it.
        Never pushes."""
        if not _REV_RE.match(name or "") or name.startswith("-"):
            raise Denied(f"invalid branch name '{name}'")
        git("check-ref-format", "--branch", name)
        args = ["branch", name] + ([rev_ok(start_point)] if start_point else [])
        out = git(*args)
        if switch:
            out = git("switch", name)
        return f"created branch '{name}'" + (" and switched to it" if switch else "") + \
            (f"\n{out}" if out != "(no output)" else "")

    ctx.tool(server, srv, git_create_branch, title="Create a local git branch",
             read_only=False, destructive=True)
