#!/usr/bin/env python3
"""PAIEP agent CLI (M6) — supervisor-routed multi-agent tasks with human approval.

Thin entry point: puts the repo root on sys.path, then delegates to
``agents.orchestrator.cli.main``.

  docker compose --profile agents run --rm agents run "Add a slugify helper in experiments/m6_demo"
  docker compose --profile agents run --rm agents approve <task_id>
  python scripts/agent-cli.py personas --all
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agents.orchestrator.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
