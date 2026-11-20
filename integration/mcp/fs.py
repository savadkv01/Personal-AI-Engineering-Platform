"""fs MCP server: list / read / search / two-step write inside the mounted workspace.

Reads are path-scoped (deny globs hide secrets, .git, binaries). Writes are two-step:
``fs_propose_write`` returns a unified diff + proposal id (nothing touches disk), then
``fs_apply_write`` (destructive -> the client asks the human) writes it, but only if the
file is unchanged since the proposal (no lost updates).
"""
from __future__ import annotations

import difflib
import hashlib
import heapq
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .common import Ctx, Denied, truncate

DIFF_LIMIT = 12000


@dataclass
class Proposal:
    id: str
    path: str
    content: str
    base_sha: str | None        # None = file did not exist
    created: float


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def _atomic_write(target: Path, data: bytes, *, keep_mode: bool) -> None:
    """Write via a sibling temp file + rename: a crash never leaves a half-written file."""
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".mcp-tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if keep_mode:
            shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def register(server: MCPServer, ctx: Ctx) -> None:
    paths = ctx.paths
    lim = ctx.cfg.limits
    fs_cfg = ctx.cfg.server("fs")
    ttl = int(fs_cfg.get("proposal_ttl_s", 900))
    proposals: dict[str, Proposal] = {}

    def fs_list(path: str = ".", depth: int = 1) -> str:
        """List a workspace directory (depth 1-3). Secrets, .git and noise dirs are hidden."""
        rel = paths.read(path)
        base = paths.abs(rel)
        if not base.is_dir():
            raise Denied(f"'{rel}' is not a directory") if base.exists() else ValueError(f"'{rel}' not found")
        depth = max(1, min(int(depth), 3))
        out: list[str] = []
        truncated = False

        def walk(d, prefix: str, level: int) -> None:
            nonlocal truncated
            remaining = lim["max_list_entries"] - len(out)
            entries = heapq.nsmallest(remaining + 1, d.iterdir(),
                                      key=lambda x: (not x.is_dir(), x.name.lower()))
            for p in entries:
                r = f"{prefix}{p.name}" if prefix else p.name
                full = r if rel == "." else f"{rel}/{r}"
                if paths.hidden(full) or p.is_symlink():
                    continue
                if len(out) >= lim["max_list_entries"]:
                    truncated = True
                    return
                if p.is_dir():
                    out.append(f"{r}/")
                    if level < depth:
                        walk(p, f"{r}/", level + 1)
                else:
                    out.append(f"{r} ({p.stat().st_size} B)")

        walk(base, "", 1)
        more = " (limit reached)" if truncated else ""
        return f"{rel}/ — {len(out)} entries{more}\n" + "\n".join(out)

    def fs_read(path: str, offset: int = 0, max_bytes: int = 0) -> str:
        """Read a UTF-8 text file. Use offset (bytes) to page through large files."""
        rel = paths.read(path)
        target = paths.abs(rel)
        if target.is_dir():
            raise ValueError(f"'{rel}' is a directory — use fs_list")
        if not target.is_file():
            raise ValueError(f"'{rel}' does not exist")
        size = target.stat().st_size
        with target.open("rb") as fh:
            if _is_binary(fh.read(8192)):
                raise Denied(f"'{rel}' is a binary file")
            start = max(0, int(offset))
            cap = lim["max_read_bytes"] if max_bytes <= 0 else min(int(max_bytes), lim["max_read_bytes"])
            fh.seek(start)
            chunk = fh.read(cap)
        end = start + len(chunk)
        head = f"{rel} (bytes {start}-{end} of {size}, chunk sha256 {_sha(chunk)[:12]})"
        if end < size:
            head += f" — more: offset={end}"
        return head + "\n" + chunk.decode("utf-8", errors="replace")

    def fs_search(query: str, path: str = ".", glob: str = "", case_sensitive: bool = False) -> str:
        """Literal text search across workspace files (like grep -n). Optional glob, e.g. '*.py'."""
        if not query.strip():
            raise ValueError("query is empty")
        from agents.tools.policy import glob_match

        rel = paths.read(path)
        base = paths.abs(rel)
        needle = query if case_sensitive else query.lower()
        hits: list[str] = []
        scanned = 0
        if base.is_file():
            files = [base]
        else:
            def walk_files():
                for directory, dirs, names in os.walk(base, topdown=True, followlinks=False):
                    parent = Path(directory)
                    dirs[:] = sorted(d for d in dirs if not (parent / d).is_symlink()
                                     and not paths.hidden((parent / d).relative_to(paths.root).as_posix()))
                    for filename in sorted(names):
                        yield parent / filename

            files = walk_files()
        for p in files:
            if scanned >= lim["max_search_files"] or len(hits) >= lim["max_search_results"]:
                break
            if not p.is_file() or p.is_symlink():
                continue
            r = p.relative_to(paths.root).as_posix()
            if paths.hidden(r) or (glob and not (glob_match(r, glob) or glob_match(p.name, glob))):
                continue
            try:
                paths.read(r)
            except Denied:
                continue
            scanned += 1
            try:
                with p.open("rb") as fh:
                    data = fh.read(lim["max_read_bytes"] * 5)
            except OSError:
                continue
            if _is_binary(data):
                continue
            for n, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
                if needle in (line if case_sensitive else line.lower()):
                    hits.append(f"{r}:{n}: {line.strip()[:200]}")
                    if len(hits) >= lim["max_search_results"]:
                        break
        tail = " (result limit reached)" if len(hits) >= lim["max_search_results"] else ""
        return f"{len(hits)} match(es) in {scanned} file(s){tail}\n" + "\n".join(hits)

    server_name = "fs"
    ctx.tool(server, server_name, fs_list, title="List workspace directory")
    ctx.tool(server, server_name, fs_read, title="Read workspace file")
    ctx.tool(server, server_name, fs_search, title="Search workspace text")
    if not (fs_cfg.get("write") and "fs.write" in paths.persona.tools):
        return

    def _gc() -> None:
        now = time.time()
        for pid in [k for k, v in proposals.items() if now - v.created > ttl]:
            proposals.pop(pid, None)

    def fs_propose_write(path: str, content: str) -> dict:
        """Propose creating/replacing a file with COMPLETE new content. Returns a diff and a
        proposal_id; nothing is written until fs_apply_write(proposal_id) is approved."""
        _gc()
        rel = paths.write(path, content)
        target = paths.abs(rel)
        if target.is_file() and target.stat().st_size > lim["max_write_bytes"]:
            raise Denied(f"'{rel}' exceeds max_write_bytes ({lim['max_write_bytes']}); "
                         "refusing a full-file rewrite")
        old_bytes = target.read_bytes() if target.is_file() else None
        if old_bytes is not None and _is_binary(old_bytes):
            raise Denied(f"'{rel}' is a binary file")
        try:
            old = old_bytes.decode("utf-8") if old_bytes is not None else ""
        except UnicodeDecodeError:
            raise Denied(f"'{rel}' is not valid UTF-8; a full-file rewrite would alter its "
                         "other bytes") from None
        if old_bytes is not None and old == content:
            return {"path": rel, "unchanged": True, "note": "content is identical; nothing to apply"}
        diff = "".join(difflib.unified_diff(old.splitlines(keepends=True), content.splitlines(keepends=True),
                                            fromfile=f"a/{rel}" if old_bytes is not None else "/dev/null",
                                            tofile=f"b/{rel}"))
        warnings = []
        old_lines, new_lines = old.count("\n"), content.count("\n")
        if old_bytes is not None and old_lines >= 40 and new_lines < old_lines * 0.5:
            warnings.append(f"destructive shrink: {old_lines} -> {new_lines} lines; was the whole file read?")
        pid = uuid.uuid4().hex[:12]
        proposals[pid] = Proposal(pid, rel, content, _sha(old_bytes) if old_bytes is not None else None,
                                  time.time())
        return {"proposal_id": pid, "path": rel, "new_file": old_bytes is None,
                "expires_in_s": ttl, "warnings": warnings,
                "diff": truncate(diff, DIFF_LIMIT, "diff truncated"),
                "next": "show the diff to the user; call fs_apply_write(proposal_id) only after approval"}

    def fs_apply_write(proposal_id: str) -> dict:
        """Apply a proposal from fs_propose_write (writes to disk). Single use; expires."""
        _gc()
        p = proposals.pop(proposal_id, None)
        if p is None:
            raise Denied(f"unknown or expired proposal '{proposal_id}' — propose again")
        rel = paths.write(p.path, p.content)          # re-check policy at apply time
        target = paths.abs(rel)
        cur = target.read_bytes() if target.is_file() else None
        if (_sha(cur) if cur is not None else None) != p.base_sha:
            raise Denied(f"'{rel}' changed since the proposal — re-read and propose again")
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(target, p.content.encode("utf-8"), keep_mode=cur is not None)
        return {"path": rel, "applied": True, "created": cur is None, "bytes": len(p.content.encode())}

    ctx.tool(server, server_name, fs_propose_write, title="Propose a file write (diff only)",
             read_only=True)
    ctx.tool(server, server_name, fs_apply_write, title="Apply an approved file write",
             read_only=False, destructive=True)
