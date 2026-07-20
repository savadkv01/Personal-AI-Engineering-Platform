# M2 — Vector Database

> **Milestone:** M2 · **Layer:** Data & Retrieval · **Anchor:** [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-07-20) · **Author role:** Data Engineer + MLOps

> ✅ **Implemented.** Qdrant stands up under the `vectordb` Compose profile with three collections
> (`kb_docs`, `repo_code`, `memory_semantic`), the scope/source/tags payload indexes, an index catalog,
> and an idempotent bootstrap script — all validated on the primary machine (see **Execution Results**).

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

- [x] Qdrant health (`GET http://127.0.0.1:6333/healthz`) returns OK. → `healthz check passed`; container healthcheck `healthy`.
- [x] Collections created with correct vector dim (matches M1 embedding model). → `kb_docs`/`repo_code`/`memory_semantic`, size `768`, `Cosine`.
- [x] Insert + filtered search by `scope`/`tags` returns expected points. → `--verify` filtered search `scope=project:demo` → `ids=[2]` (PASS).
- [x] Index catalog records `collection → model + dim`. → [`config/index-catalog.yaml`](../config/index-catalog.yaml) (all `nomic-embed-text` / `768`).
- [x] Data persists across `down`/`up` (named volume). → collections present after `compose down` + `up` (volume `paiep_vectors`).
- [x] **Offline smoke:** works with network disabled. → reachable on internet-isolated `backend` net; egress `Network is unreachable`.

## Execution Results (2026-07-20)

Run on the primary machine (HP EliteBook 840 G7, i7-10610U, CPU-only) via Docker Desktop/WSL2.

| Area | Outcome |
|------|---------|
| Service | Qdrant **v1.12.6** (`paiep_qdrant`), `vectordb` profile; REST `6333` + gRPC `6334` on `127.0.0.1`; container health `healthy` (shell-free `/dev/tcp` probe) |
| Storage | `paiep_vectors` named volume; telemetry disabled |
| Collections | `kb_docs`, `repo_code`, `memory_semantic` — each `nomic-embed-text`, dim **768**, **Cosine** |
| Payload indexes | `scope`, `source`, `tags` (all `keyword`) on every collection |
| Bootstrap | [`scripts/qdrant-init.sh`](../scripts/qdrant-init.sh) — idempotent, dependency-free (python3 stdlib REST), driven by [`config/index-catalog.yaml`](../config/index-catalog.yaml); re-run = `0 created, 3 already present` |
| Functional | `--verify` insert of 2 points + filtered search `scope=project:demo` → only point `id=2` returned (PASS) |
| Persistence | Collections survived `compose down` (volumes kept) + `up` |
| Offline | From internal `backend` network: Qdrant reachable by name; internet egress `Network is unreachable` |

**Deviations / notes (recorded):**

- **Profile split:** Qdrant now has its own **`vectordb`** profile (the M2 owner); it also stays in the M1
  **`spike`** profile so the existing integration test is unaffected. A leftover `paiep_m1_spike` collection
  from M1 remains in the volume (harmless; recreated fresh each spike run).
- **gRPC port** `6334` published on loopback (added `QDRANT_GRPC_HOST_PORT` to `docker/.env`) for future
  high-throughput LlamaIndex/memory clients.
- **Healthcheck** uses a shell-free `bash </dev/tcp/127.0.0.1/6333` probe because the Qdrant image ships no
  `curl`/`wget` (bash **is** present).
- **Indexed subset:** only the filter-critical `scope`/`source`/`tags` are indexed now; the broader payload
  schema in [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) is attached to points during M3 ingestion
  and promoted to indexes as query patterns require.

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
