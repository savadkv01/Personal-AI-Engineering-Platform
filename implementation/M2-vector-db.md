# M2 — Vector Database

> **Milestone:** M2 · **Layer:** Data & Retrieval · **Anchor:** [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** Data Engineer + MLOps

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M2 is explicitly requested.

---

## Objectives & Scope

Stand up **Qdrant** as the shared vector store for **both RAG and semantic memory**, with consistent
**collection** and **payload-filter** conventions so scope/tag filtering works later.

**In scope**
- **Qdrant** service ([Phase 06 §6](../docs/phases/06-technology-selection.md)) on `127.0.0.1` with a named
  `vectors` volume.
- **Collection schema conventions:** vector size = embedding dim (nomic = 768), distance metric, and an
  **index catalog** recording `collection → embedding_model + dim` (guards the re-embed risk).
- **Payload-filter conventions** for `scope` (global/project), `source`, `tags` — used by ingestion/RAG
  (M3/M4) and memory (M5), realizing FR-012/021.
- A small **client wrapper/config** so LlamaIndex (M3) and memory (M5) share one connection contract.

**Out of scope:** ingestion, chunking, embeddings orchestration (M3/M4), memory logic (M5).

## Prerequisites

- **M1** complete (embedding model available so dims are known).

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Qdrant service (Compose profile) | `docker/docker-compose.yml` |
| Collection bootstrap script | `scripts/qdrant-init.sh` or `rag/qdrant/` |
| Index/collection catalog | `config/index-catalog.yaml` |
| Payload-filter conventions doc | `rag/README.md` |

## Validation Checklist

- [ ] Qdrant health (`GET http://127.0.0.1:6333/healthz`) returns OK.
- [ ] Collections created with correct vector dim (matches M1 embedding model).
- [ ] Insert + filtered search by `scope`/`tags` returns expected points.
- [ ] Index catalog records `collection → model + dim`.
- [ ] Data persists across `down`/`up` (named volume).
- [ ] **Offline smoke:** works with network disabled.

## Rollback Strategy

- Disable the `vectordb` Compose profile and `down` the service.
- Drop collections via API, or remove the `vectors` volume (re-creatable from ingestion, so reversible).
- Revert scripts/config via `git restore`.

## Documentation to Produce

- Collection/payload conventions in `rag/README.md`.
- Confirm/append [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) with pinned Qdrant version + schema.

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Smoke | `/healthz` | `200`/OK |
| Functional | insert + filtered query | correct points returned |
| Regression | re-run M1 spike | still green |
| Offline | disable network | success |

## Troubleshooting Notes

- **Dim mismatch on upsert:** collection dim must equal embedding dim; recreate collection if the model changed.
- **Slow search:** tune HNSW params; keep payload indexes on filtered fields (`scope`, `tags`).
- **Volume growth:** index size scales with dim × chunks — monitor disk (485 GB budget).

## Hardware Profiles

- **A/A+:** comfortable on CPU/RAM; modest footprint.
- **B/C:** unchanged (vector search is CPU-fine); benefits indirectly from faster embeddings.
- **D:** Qdrant scales to a server/cluster; alternative **pgvector** consolidation noted in
  [ADR 0009](../docs/adr/0009-vector-store-and-memory.md).
