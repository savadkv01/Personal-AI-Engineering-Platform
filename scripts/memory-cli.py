#!/usr/bin/env python3
"""PAIEP memory CLI (M5) — CRUD, recall, sessions, retention, consistency.

Thin entry point: puts the repo root on sys.path, then delegates to
``memory.service.cli.main``.

  docker compose --profile memory run --rm memory add "Prefer pytest" --type preference
  docker compose --profile memory run --rm memory recall "test framework?" --scope project:paiep
  python scripts/memory-cli.py --json stats
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from memory.service.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
