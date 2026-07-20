# Book Library Index

> Catalog of books and long-form references ingested into the knowledge base
> (`kb_docs`). **Only books you own or are licensed to use** may be ingested,
> and **copyrighted full text is never committed** to this repo — originals and
> derived full text live in the git-ignored `paiep_kb` volume. This index holds
> only metadata + your own notes/summaries (see [`knowledge/README.md`](../README.md)).

## How ingestion uses this

`scripts/ingest.py` routes `.pdf`/`.epub` files to the `kb_docs` collection with
`doc_type = book`, chunking at ~1024 tokens (see
[`config/embeddings.yaml`](../../config/embeddings.yaml)). Provenance (`source`,
`checksum`, `ingested_at`) is stored on every chunk for citation and incremental
re-ingest.

## Catalog

| Title | Author | Format | Owned/Licensed | Scope | Tags | Notes |
|-------|--------|--------|----------------|-------|------|-------|
| _(none yet)_ | | | | | | Add rows as you ingest owned books. |

> The M3 validation corpus uses the Markdown notes under
> [`knowledge/notes/`](../notes/) — no copyrighted binaries are committed.
