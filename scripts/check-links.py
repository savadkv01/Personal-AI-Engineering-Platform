#!/usr/bin/env python3
"""Check that relative Markdown links resolve to existing files (stdlib only).

  python scripts/check-links.py          # exit 1 and list broken links if any
"""
from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv"}
LINK = re.compile(r"\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def links(md: Path):
    in_fence = False
    for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield from LINK.findall(line)


def main() -> int:
    broken = []
    for md in sorted(ROOT.rglob("*.md")):
        if SKIP_DIRS.intersection(md.relative_to(ROOT).parts):
            continue
        for target in links(md):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = urllib.parse.unquote(target.split("#", 1)[0])
            if path and not (md.parent / path).exists():
                broken.append(f"{md.relative_to(ROOT).as_posix()}: {target}")
    for b in broken:
        print(f"BROKEN {b}")
    print(f"[check-links] {len(broken)} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
