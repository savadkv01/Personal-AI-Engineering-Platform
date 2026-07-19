# M4 — RAG Pipeline

> **Milestone:** M4 · **Layer:** Data & Retrieval · **Anchor:** O4 (FR-022–025) ·
> **Prompt:** [`.github/prompts/implementation/M4-rag-pipeline.prompt.md`](../.github/prompts/implementation/M4-rag-pipeline.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** AI Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M4 is explicitly requested.

---

## Objectives & Scope

Build the **query path** with **LlamaIndex** ([Phase 06 §4](../docs/phases/06-technology-selection.md)):
embed query → retrieve top-k → optional re-rank → assemble context → **generate a grounded answer with
citations** ([Phase 05 §7](../docs/phases/05-enterprise-architecture.md), FR-022).

**In scope**
- Query embedding + **top-k retrieval** with **payload/metadata filters** (`scope`/`tags`).
- **Optional re-ranking** (justify inclusion vs. CPU cost per Phase 08).
- **Context assembly** within the model context budget; **citations** to source chunks.
- A **query entrypoint** (CLI or local API behind the gateway) for downstream use (M6/M7/M8).
- Guardrails: empty-retrieval, oversized-context, and no-answer handling.
- Baseline **retrieval metrics** (recall@k on a small labeled set) — measured, not invented.

**Out of scope:** multi-agent orchestration (M6), UI (M8), memory (M5).

## Prerequisites

- **M1** (runtime), **M2** (vector DB), **M3** (populated, idempotent index) complete.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| RAG query module | `rag/pipeline/`, `rag/service/` |
| Retrieval/re-rank/context config | `config/rag.yaml` |
| Query entrypoint (CLI/API) | `rag/service/` (behind gateway) |
| Retrieval eval + results | `benchmarks/m4/` |
| Setup doc | `docs/setup/04-rag-pipeline.md` |

## Validation Checklist

- [ ] A known question returns a correct, **grounded** answer citing the right source (FR-022).
- [ ] Retrieval respects `scope`/`tags` metadata filters.
- [ ] Context stays within the model window; no truncation errors.
- [ ] Graceful behavior when nothing relevant is found (no hallucinated citation).
- [ ] recall@k recorded on a small labeled set.
- [ ] **Offline smoke:** full query path with network disabled.

## Rollback Strategy

- Remove the RAG query module; **M1–M3 remain functional** independently (index stays intact).
- Revert `rag/pipeline/`, `rag/service/`, `config/rag.yaml` via `git restore`.
- No schema/data changes — nothing to migrate back.

## Documentation to Produce

- Retrieval/re-rank/grounding design in `docs/setup/04-rag-pipeline.md` + `rag/README.md`.
- Retrieval metrics in `benchmarks/m4/README.md`.

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Functional | curated Q/A set | correct, cited answers |
| Contract | query endpoint schema | valid response w/ citations |
| Filtering | scoped query | only in-scope chunks |
| Performance | recall@k | recorded metric |
| Offline | disable network | success |

## Troubleshooting Notes

- **Poor recall:** revisit chunking/embeddings (M3), top-k, or add hybrid/keyword retrieval.
- **Context overflow:** trim/re-rank; reduce top-k; summarize context.
- **Irrelevant citations:** verify metadata survives chunking; tighten filters.
- **Latency on Profile A:** smaller top-k, skip re-rank, use a faster tier.

## Hardware Profiles

- **A:** small top-k; re-rank likely skipped.
- **A+:** full pipeline; the interactive reference target.
- **B/C:** GPU speeds query embedding + re-rank.
- **D:** multiple indices; heavier re-rank models feasible.
