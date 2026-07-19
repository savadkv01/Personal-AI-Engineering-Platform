# M3 — Embeddings & Ingestion

> **Milestone:** M3 · **Layer:** Data & Retrieval · **Anchor:** O4 (FR-020/021),
> [Phase 08](../docs/phases/08-knowledge-memory.md) ·
> **Prompt:** [`.github/prompts/implementation/M3-embeddings-ingestion.prompt.md`](../.github/prompts/implementation/M3-embeddings-ingestion.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** AI Engineer + Data Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M3 is explicitly requested.

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

- [ ] Embedding **dimension matches** the M2 collection vector size.
- [ ] Sample corpus ingests without errors; vector count matches expected chunks.
- [ ] Re-running ingestion is **idempotent** (no duplicates).
- [ ] Metadata + provenance (source, chunk index, scope, tags, timestamps, checksum) is stored and queryable.
- [ ] A manual similarity query returns relevant chunks (sanity check only; full RAG is M4).
- [ ] **Offline smoke:** ingest local files with network disabled.

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
