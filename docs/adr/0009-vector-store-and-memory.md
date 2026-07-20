# ADR 0009: Vector Store & Memory Architecture

- **Status:** Accepted (schema/strategy defaults; tune in M1/M5) · **Vector store landed in M2 (2026-07-20)**
- **Date:** 2026-07-19

## Context
[Phase 08 — Knowledge & Memory Architecture](../phases/08-knowledge-memory.md) designs the RAG pipeline,
vector database, and memory subsystems. The [reference stack](0007-reference-stack.md) already selected
**Qdrant** (vectors), **PostgreSQL** (structured/state), **LlamaIndex** (RAG), and **nomic-embed-text**
(embeddings). This ADR fixes the **concrete data design**: collections, payload schema, hybrid retrieval,
and the **memory model** (session vs. long-term, consolidation, forgetting) — under CPU-only constraints
(CON-001), offline/privacy (NFR-010/020), and model-agnostic/modular goals (NFR-023/024).

## Decision
1. **Vector store = Qdrant** with three collections: `kb_docs`, `repo_code`, `memory_semantic` — each with a
   **single fixed embedding model** (nomic-embed-text, dim 768) recorded per collection; changing it requires
   a **full re-embed** of that collection.
2. **Payload schema** carries provenance and filters: `source_id`, `scope` (`global`/`project:<name>`),
   `doc_type`, `path/uri`, `title`, `tags`, `lang`, `symbol`, `chunk_idx`, `content_hash`,
   `embed_model`/`embed_dim` — enabling scope/type/tag filtering (FR-012, FR-025).
3. **Retrieval = hybrid** (vector + keyword) with **small top-k (4–8)** and an **optional light re-ranker**
   (off on Profile A). Multi-query/HyDE opt-in only. Context assembly dedupes, respects the token budget,
   and **cites** sources; retrieved text is inserted as **data, not instructions** (LLM01, [ADR 0006](0006-security-model.md)).
4. **Chunking = recursive/structural** by default (~512–1024 tokens, ~10–15% overlap), **code-aware** for
   repos; semantic chunking reserved for GPU/Profile-D.
5. **Memory = dual-store**: **PostgreSQL** holds canonical, user-editable records (`memory_item`, `session_*`,
   catalog, locks); **Qdrant** (`memory_semantic`) holds embeddings for semantic recall referencing `memory_id`.
6. **Session vs long-term:** session memory lives in LangGraph state + Postgres and is **summarized then
   evicted** at task end; **salient** facts are **promoted** (async) to long-term (never blocking responses).
7. **Consolidation & forgetting:** deduplicate (hash + similarity), summarize, confidence + reinforce-on-use;
   **decay / TTL / supersede / user-delete / scope-prune**. **User can view/edit/delete** any memory (FR-013);
   deletes **cascade** to Qdrant.
8. **Profile A consolidation:** may replace Qdrant+Postgres with **SQLite (+ pgvector-style / embedded)** to
   minimize services; the LlamaIndex interface keeps this swappable (NFR-023).

## Alternatives Considered
- **pgvector only (no Qdrant).** One engine, simpler ops, but weaker payload filtering / ANN tuning for
  mixed KB+memory workloads. **Kept as the Profile-A / consolidation fallback**, not the A+ default.
- **Chroma.** Simplest DX; good for the first spike, weaker scaling/filtering. **Spike/fallback only.**
- **Milvus / Weaviate.** Powerful at scale but heavy for a 32 GB laptop. **Deferred** (revisit on Profile D).
- **Single memory store (transcripts only).** Simple but bloats context, poor recall precision, no
  editable structured facts. **Rejected** for the dual-store model.
- **Mem0 / framework memory abstraction.** Convenient, but adds a dependency and hides control. **Deferred**;
  revisit if it removes real work.
- **Semantic chunking as default.** Best coherence but extra embedding passes are costly on CPU. **Reserved**
  for GPU/high-value corpora.

## Consequences
**Benefits**
- One vector engine serves KB, repo, and semantic memory with rich filtering (scope/project isolation).
- Durable, **user-editable** memory with citations; async promotion protects CPU latency (NFR-001).
- Model-agnostic/swappable via LlamaIndex; clear provenance enables incremental re-ingest (FR-024).
- Explicit forgetting policy keeps recall precise and RAM bounded.

**Drawbacks**
- Two engines to keep consistent (mitigated: catalog as source of truth; cascade deletes; reconciliation).
- Embedding-model change is expensive (full re-embed) — deliberate migration only.
- Hybrid + re-rank tuning (fusion weights, thresholds) requires measurement (M1).

**Follow-ups**
- Validate chunk size/overlap, top-k, fusion weights, and re-rank cost/benefit in the **M1 spike** (Phase 10).
- Finalize **memory scope + retention/summarization** policy in **M5** (Phase 08 follow-up).
- Pin exact Qdrant/Postgres schemas + Profile-A consolidation choice at implementation.
- Add **scheduled re-index/consolidation** (Prefect) and a **cross-encoder re-ranker** on Profile B–D.
- Add a **reconciliation job** to detect/repair dangling vectors vs. catalog.

## Implementation Notes — M2 (2026-07-20)

The **vector-store** half of this ADR is now implemented and validated on the primary machine (Qdrant
only; Postgres/memory land in M5).

- **Pinned version:** `qdrant/qdrant:v1.12.6` (Compose `vectordb` profile; backend-private, REST `6333` /
  gRPC `6334` published on loopback only). Telemetry disabled; state in the `paiep_vectors` named volume.
- **Collections created (all `nomic-embed-text`, dim `768`, `Cosine`):** `kb_docs`, `repo_code`,
  `memory_semantic` — matching decision #1.
- **Indexed payload fields (`keyword`):** `scope` (`global` | `project:<name>`), `source`, `tags`. These are
  the filter-critical subset of the full payload schema (decision #2); the remaining fields
  (`title`, `chunk_idx`, `content_hash`, `embed_model`/`embed_dim`, …) are stored on points as ingestion
  lands in M3, and promoted to indexes only as query patterns require.
- **Source of truth:** [`config/index-catalog.yaml`](../../config/index-catalog.yaml) records
  `collection → embed_model + dim + distance`; [`scripts/qdrant-init.sh`](../../scripts/qdrant-init.sh)
  creates collections + indexes idempotently from it (dependency-free, offline).
- **Validated:** `/healthz` OK; insert + **filtered search** by `scope` returned only the matching point;
  data **persisted** across `down`/`up`; reachable from the **internet-isolated** `backend` network
  (egress `Network is unreachable`, Qdrant reachable). See
  [`implementation/M2-vector-db.md`](../../implementation/M2-vector-db.md) → Execution Results.

