"""PAIEP ingestion pipeline (M3) — the write path: load -> chunk -> embed -> upsert.

No retrieval/generation here (that is M4). Public entry point: `pipeline.run`,
wrapped by the `scripts/ingest.py` CLI (`cli.main`).
"""
