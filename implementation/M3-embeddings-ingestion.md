# M3 — Embeddings & Ingestion

> **Milestone:** M3 · **Layer:** Data & Retrieval · **Anchor:** O4 (FR-020/021),
> [Phase 08](../docs/phases/08-knowledge-memory.md) ·
> **Prompt:** [`.github/prompts/implementation/M3-embeddings-ingestion.prompt.md`](../.github/prompts/implementation/M3-embeddings-ingestion.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-07-20) · **Author role:** AI Engineer + Data Engineer

> ✅ **Implemented.** An idempotent ingestion pipeline (`load → chunk → embed → upsert`) writes vectors +
> provenance into Qdrant using `nomic-embed-text` (dim 768), driven by `config/embeddings.yaml` and run via
> `scripts/ingest.py` (container profile `ingest`). Validated on the primary machine (see **Execution Results**).

---

## Objectives & Scope

Stand up the **embedding model** and an **ingestion pipeline** — the *write* path only: **load → chunk →
embed → upsert** vectors + metadata into Qdrant ([Phase 06 §4/§5](../docs/phases/06-technology-selection.md),
[Phase 05 §7](../docs/phases/05-enterprise-architecture.md)). **No retrieval/generation** (that is M4).

**In scope**
- Embedding via **`nomic-embed-text`** on the M1 runtime (or a dedicated embedding service).
- **Loaders** (PDF / EPUB / Markdown / source) + a **chunking strategy** (size/overlap) per Phase 08.
- **Idempotent upsert** with stable IDs (re-ingest creates no duplicates).
- **Metadata + provenance** written to Qdrant payloads: `source`, `chunk_index`, `scope`, `tags`,
  `ingested_at`, `checksum`; a small **book-library catalog** in `knowledge/`.
- Ingest a **sample corpus** from `knowledge/` for validation.

**Out of scope:** query-time retrieval, re-rank, grounded answers (M4); memory (M5); agents (M6).

## Prerequisites

- **M1** (runtime + embedding model) and **M2** (Qdrant collections + payload conventions) complete.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Embedding config | `config/embeddings.yaml` |
| Loaders + ingestion pipeline | `rag/loaders/`, `rag/ingest/` |
| Ingest CLI (bulk/incremental) | `scripts/ingest.py` |
| Book-library catalog | `knowledge/library/index.md` |
| Setup doc | `docs/setup/03-embeddings-ingestion.md` |

## Validation Checklist

- [x] Embedding **dimension matches** the M2 collection vector size. → `nomic-embed-text` = **768**; pipeline + embedder abort on mismatch.
- [x] Sample corpus ingests without errors; vector count matches expected chunks. → 5 files → **5 chunks** in `kb_docs` (`points_count=5`).
- [x] Re-running ingestion is **idempotent** (no duplicates). → re-run = `ingested=0 skipped=5`; `--force` kept `points_count=5` (stable IDs overwrite).
- [x] Metadata + provenance stored and queryable. → payload has `scope/source/tags/doc_type/chunk_index/checksum/title/text/embed_model/embed_dim/ingested_at`.
- [x] A manual similarity query returns relevant chunks. → “network disabled” query → top hit `offline-first.md` (score 0.616).
- [x] **Offline smoke:** ingest local files with network disabled. → ingest runs only on the internal `backend` net; forced re-embed succeeded with no egress.

## Execution Results (2026-07-20)

Run on the primary machine (HP EliteBook 840 G7, i7-10610U, CPU-only) via Docker Desktop/WSL2.

| Area | Outcome |
|------|---------|
| Pipeline | [`rag/ingest/`](../rag/ingest/) (loaders → chunking → embedder → pipeline) + CLI [`scripts/ingest.py`](../scripts/ingest.py) |
| Config | [`config/embeddings.yaml`](../config/embeddings.yaml) (service, chunking, ext→collection routing); dim/model locked to [`config/index-catalog.yaml`](../config/index-catalog.yaml) |
| Runner | `ingest` Compose profile, image `paiep_ingest` (python:3.11-slim; `llama-index-core`, `qdrant-client`, `pypdf`, `EbookLib`); backend-only |
| Embedding | Ollama `nomic-embed-text` via `/api/embed`, batched; **dim 768** verified vs. collection |
| Corpus | 5 Markdown files under [`knowledge/`](../knowledge/) → `kb_docs`; **5 chunks**, provenance stored |
| Idempotency | re-run skipped all 5; `--force` re-embed kept count at 5 (deterministic `uuid5(source, chunk_index)` IDs) |
| Sanity query | embed(“network disabled”) → search `kb_docs` → `offline-first.md` (0.616) > `paiep-vision.md` (0.468) |
| Offline | ingest container on internal `backend` network (no egress); embed+upsert succeeded |

**Deviations / notes (recorded):**

- **Direct `qdrant-client` upsert** (not the LlamaIndex vector store) so payloads match the M2 conventions
  exactly (`scope`/`source`/`tags` indexed) and IDs stay deterministic for idempotency. LlamaIndex is used
  only for sentence-aware chunking.
- **Module layout:** loaders live inside the `rag/ingest/` package (not a separate `rag/loaders/`); simpler
  single import surface for the pipeline + CLI.
- **Sample corpus is Markdown only** (no copyrighted binaries committed, per `knowledge/README.md`). PDF/EPUB
  loaders are implemented + lazy-imported; `repo_code` routing is exercised by pointing `ingest` at source
  dirs (`--collection repo_code`).
- **Embedding task prefixes** and hybrid/re-rank tuning deferred to M4/Phase 11.

## Rollback Strategy

- Drop/recreate the ingested collection contents (re-ingestable from `knowledge/` sources).
- Disable ingestion entry points; the M2 store itself remains.
- Revert `rag/loaders/`, `rag/ingest/`, `scripts/ingest.py` via `git restore`.

## Documentation to Produce

- Chunking/embedding/provenance design in `docs/setup/03-embeddings-ingestion.md` + `rag/README.md`.
- Confirm embedding model + dim in the M2 index catalog (guards the re-embed risk).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Dimension | compare model dim vs collection | equal |
| Functional | ingest one file per type | chunks + provenance in Qdrant |
| Idempotency | re-run ingest | unchanged files skipped, no dupes |
| Sanity | manual similarity query | relevant chunks returned |
| Offline | disable network | success |

## Troubleshooting Notes

- **Dimension mismatch:** recreate the collection if the embedding model changed (M2 catalog).
- **Slow embedding on CPU (Profile A):** batch embeds; ingest incrementally / off-peak.
- **Token/context limits:** cap chunk size to the embedder's window.
- **Encoding/format issues:** clean PDF/EPUB headers/footers before bulk ingest.

## Hardware Profiles

- **A:** small corpora; slower embedding.
- **A+:** full sample corpus in batches.
- **B/C:** GPU-accelerated embeddings shorten ingest.
- **D:** scheduled bulk/periodic re-index via **Prefect** (future,
  [Phase 06 §8](../docs/phases/06-technology-selection.md)).
