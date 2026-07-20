#!/usr/bin/env python3
"""PAIEP ingestion CLI (M3).

Thin host/container entry point: ensures the repo root is importable, then
delegates to ``rag.ingest.cli.main``. Run inside the Docker ``ingest`` service
(reproducible, offline) or directly if the deps in
``rag/ingest/requirements.txt`` are installed locally.

  docker compose --profile ingest run --rm ingest knowledge --scope global
  python scripts/ingest.py knowledge --dry-run
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rag.ingest.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
