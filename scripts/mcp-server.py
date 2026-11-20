#!/usr/bin/env python3
"""PAIEP MCP server launcher (M7) — stdio servers for VS Code clients.

Thin entry point: puts the repo root on sys.path, then delegates to
``integration.mcp.server.main``.

  docker compose --profile mcp run --rm -T mcp-local fs     # fs / git (no network)
  docker compose --profile mcp run --rm -T mcp rag          # rag / memory / paiep-tools
  python scripts/mcp-server.py all --list                   # capability check
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from integration.mcp.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
