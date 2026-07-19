---
mode: agent
description: "Implementation M3 — Embeddings & ingestion: local embedding model plus an ingestion pipeline (chunk→embed→index). Reversible."
---

# Implementation Milestone M3 — Embeddings & Ingestion

> **Precondition:** M2 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are an **AI Engineer** building the ingestion path only (no retrieval/generation yet).

## Objective
Run a local embedding model and an ingestion pipeline that chunks documents, embeds them, and
indexes vectors + metadata into the vector DB.

## Prerequisites
- M1 (runtime) + M2 (vector DB) running.
- Phase 08 chunking/embedding strategy; Phase 04 embedding-model choice.

## Scope
- **In:** embedding service/model, chunking, ingestion job, idempotent re-ingest, metadata.
- **Out:** query-time retrieval and answer generation (M4).

## Tasks
1. Provision the local embedding model (via the M1 runtime or a dedicated embedding service).
2. Implement an ingestion pipeline: load → chunk → embed → upsert (with stable IDs + metadata).
3. Ensure re-ingestion is **idempotent** (no duplicates on re-run).
4. Ingest a small sample corpus from `knowledge/` for validation.
5. Confirm embedding dimension matches the M2 collection vector size.

## Deliverables
- Ingestion pipeline code under the agreed module; `docs/setup/03-embeddings-ingestion.md`;
  sample corpus reference in `knowledge/`.

## Validation Checklist
- [ ] Embedding dimension matches vector DB collection.
- [ ] Sample corpus ingests without errors; vector count matches expected chunks.
- [ ] Re-running ingestion does not create duplicates (idempotent upsert).
- [ ] Metadata (source, chunk index, timestamps) is stored and queryable.

## Expected Outputs
- Vector DB populated with sample knowledge, ready for retrieval in M4.

## Rollback Plan
- Delete the created collection contents (or drop/recreate the collection) and remove ingestion
  code. M2 store remains; no downstream dependency yet.

## Troubleshooting
- Dimension mismatch; token/context limits during embedding; slow embedding on CPU (Profile A);
  encoding/format issues in source docs.

## Documentation to Update
- `docs/setup/03-embeddings-ingestion.md`; `rag/` pipeline notes.

## Testing
- Ingest, then run a manual similarity query to confirm relevant chunks return.

## STOP
Output **"Milestone M3 complete"**, list files, confirm validation, then **STOP** and wait for approval.
