"""CLI for the ingestion pipeline. Wrapped by ``scripts/ingest.py``.

Examples:
  python scripts/ingest.py knowledge --scope global --tags paiep,docs
  python scripts/ingest.py rag/ingest --collection repo_code --scope project:paiep
  python scripts/ingest.py knowledge --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .config import load_config
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest", description="PAIEP ingestion (M3).")
    default_paths = os.environ.get("INGEST_PATHS", "knowledge").split(os.pathsep)
    p.add_argument("paths", nargs="*", default=default_paths,
                   help="files/dirs to ingest (default: knowledge/)")
    p.add_argument("--scope", default="global",
                   help="payload scope: global | project:<name> (default: global)")
    p.add_argument("--tags", default="",
                   help="comma-separated tags added to every chunk")
    p.add_argument("--collection", default=None,
                   help="force a target collection (else routed by extension)")
    p.add_argument("--force", action="store_true",
                   help="re-embed even if the file checksum is unchanged")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would be ingested; no embeds/upserts")
    p.add_argument("--json", action="store_true", help="print stats as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    cfg = load_config()

    print(f"[ingest] qdrant={cfg.qdrant_url} embed={cfg.service.model} "
          f"dim={cfg.service.dim} scope={args.scope}")
    print(f"[ingest] paths={args.paths}")

    stats = run(args.paths, scope=args.scope, tags=tags,
                collection_override=args.collection, force=args.force,
                dry_run=args.dry_run, config=cfg)

    if args.json:
        print(json.dumps(stats.as_dict(), indent=2))
    else:
        print(f"[ingest] files: seen={stats.files_seen} ingested={stats.files_ingested} "
              f"skipped={stats.files_skipped} unrouted={stats.files_unrouted}")
        print(f"[ingest] chunks upserted={stats.chunks_upserted} per_collection={stats.per_collection}")
    print("[ingest] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
