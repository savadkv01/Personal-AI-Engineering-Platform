---
mode: agent
description: "Implementation M2 — Vector database: deploy the chosen vector store, define collections/schema, verify persistence. Reversible."
---

# Implementation Milestone M2 — Vector Database

> **Precondition:** M1 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **Data Architect** deploying the vector store only.

## Objective
Stand up the chosen vector database (e.g., Qdrant / Chroma / pgvector per Phase 06) with
persistent storage and a defined collection/metadata schema.

## Prerequisites
- M0 + M1 running.
- Phase 08 knowledge/memory design (collections, metadata schema) and Phase 06 vector-DB choice.

## Scope
- **In:** vector DB service, persistent volume, collection/schema creation, connectivity test.
- **Out:** embeddings/ingestion (M3), RAG retrieval (M4).

## Tasks
1. Add the vector DB service to `docker/compose.yaml` with a named volume and healthcheck.
2. Create the initial collection(s) and metadata schema from Phase 08.
3. Provide a connectivity + create/read smoke test.
4. Document connection details for downstream milestones.

## Deliverables
- Updated `docker/compose.yaml`; `docs/setup/02-vector-db.md`; schema definition notes; smoke test.

## Validation Checklist
- [ ] Vector DB container healthy and reachable locally.
- [ ] Collection(s) created with the intended distance metric and vector size.
- [ ] Data persists across `docker compose down`/`up` (volume retained).
- [ ] Basic insert + query round-trip succeeds.

## Expected Outputs
- A persistent, queryable vector store with the agreed schema.

## Rollback Plan
- Remove the service and its named volume; downstream milestones not yet built, so rollback is clean.

## Troubleshooting
- Vector size mismatch vs embedding model (coordinate with M3); volume permissions; port conflicts.

## Documentation to Update
- `docs/setup/02-vector-db.md`; `rag/` and `memory/` design notes with concrete schema.

## Testing
- Insert a few dummy vectors and query them; verify persistence after a restart.

## STOP
Output **"Milestone M2 complete"**, list files, confirm validation, then **STOP** and wait for approval.
