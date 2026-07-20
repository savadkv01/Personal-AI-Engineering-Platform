# Setup 03 — Embeddings & Ingestion (M3)

> The **write path** of the RAG pipeline: `load → chunk → embed → upsert`. It turns local
> files into vectors + metadata in Qdrant. Retrieval/generation (the read path) is **M4**.
> Anchors: [ADR 0007](../adr/0007-reference-stack.md), [ADR 0009](../adr/0009-vector-store-and-memory.md),
> [Phase 08](../phases/08-knowledge-memory.md). Milestone: [`implementation/M3-embeddings-ingestion.md`](../../implementation/M3-embeddings-ingestion.md).

## What gets built

| Piece | Path |
|-------|------|
| Embedding + chunking + routing config | [`config/embeddings.yaml`](../../config/embeddings.yaml) |
| Ingestion package (loaders, chunking, embedder, pipeline) | [`rag/ingest/`](../../rag/ingest/) |
| Ingest CLI | [`scripts/ingest.py`](../../scripts/ingest.py) |
| Ingest runner image + service | [`rag/ingest/Dockerfile`](../../rag/ingest/Dockerfile), `docker` profile `ingest` |
| Sample corpus + book-library index | [`knowledge/notes/`](../../knowledge/notes/), [`knowledge/library/index.md`](../../knowledge/library/index.md) |

## How it works

1. **Load** — [`rag/ingest/loaders.py`](../../rag/ingest/loaders.py) reads Markdown/text (parsing YAML
   front-matter for `title`/`tags`/`scope`), source code, and — lazily — PDF (`pypdf`) and EPUB
   (`EbookLib`).
2. **Route** — file extension → `doc_type` → target collection, per
   [`config/embeddings.yaml`](../../config/embeddings.yaml) (`.md`→`kb_docs`, code→`repo_code`,
   `.pdf`/`.epub`→`kb_docs`).
3. **Chunk** — LlamaIndex `SentenceSplitter` with per-type token windows (note 512/64, book 1024/128,
   code 768/96).
4. **Embed** — batched calls to the Ollama runtime (`nomic-embed-text`, dim 768) via `/api/embed`.
   The dimension is checked against the M2 collection; a mismatch aborts (guards the re-embed risk).
5. **Upsert** — [`qdrant-client`](../../rag/ingest/pipeline.py) writes points with the M2 payload
   conventions (`scope`, `source`, `tags` + `doc_type`, `chunk_index`, `checksum`, `title`, `text`,
   `embed_model`/`embed_dim`, `ingested_at`).

### Idempotency & provenance

Each chunk's point ID is `uuid5(source, chunk_index)` and every point stores a SHA-256 `checksum` of
its source file. On re-run, unchanged files are **skipped**; changed files have their old points
deleted (by `source` filter) before fresh chunks are upserted — so edits/shrinks never leave
duplicates or orphans. Use `--force` to re-embed regardless.

## Run it

```bash
# 1) dependencies up (M1 runtime + M2 vector store)
docker compose --profile inference up -d ollama
docker compose --profile vectordb  up -d qdrant
docker compose --profile ingest    build ingest      # first time only

# 2) ingest the local corpus (idempotent; runs on the internal backend network)
docker compose --profile ingest run --rm ingest knowledge --scope global --tags paiep,seed

# variations
docker compose --profile ingest run --rm ingest knowledge --dry-run        # plan only
docker compose --profile ingest run --rm ingest rag/ingest --collection repo_code --scope project:paiep
docker compose --profile ingest run --rm ingest knowledge --force          # re-embed all
```

> The ingest container attaches only to the **internal** `backend` network (no internet egress), so
> ingestion is offline by construction. Embeddings + upserts reach `ollama` / `qdrant` by name.

## Validate

```bash
# vector count
curl -s http://127.0.0.1:6333/collections/kb_docs | grep -o '"points_count":[0-9]*'
# inspect a payload (provenance)
curl -s -X POST http://127.0.0.1:6333/collections/kb_docs/points/scroll \
  -H 'content-type: application/json' -d '{"limit":1,"with_payload":true}'
```

A manual similarity query (embed a question via Ollama, then `POST /collections/kb_docs/points/search`)
should return the most relevant note first — full retrieval/ranking lands in M4.

## Troubleshooting

- **Dimension mismatch** — the embedding model changed vs. the collection; recreate the collection
  (M2 `scripts/qdrant-init.sh`) and re-ingest. The pipeline aborts before writing.
- **Slow embedding on CPU (Profile A)** — reduce `batch_size` / ingest incrementally; embedding is the
  cost, not upsert.
- **`no text extracted`** — scanned PDFs need OCR (out of scope); EPUB needs `EbookLib`+`beautifulsoup4`.
- **`no routing rule`** — add the extension to `routing` in `config/embeddings.yaml` or pass
  `--collection`.

## Notes / backlog (Phase 11 tuning)

- Task prefixes for `nomic-embed-text` (`search_document:` / `search_query:`) and hybrid retrieval
  weights are deferred to M4/Phase 11.
- Code-aware splitting (tree-sitter) is deferred; M3 uses sentence chunking for code.
