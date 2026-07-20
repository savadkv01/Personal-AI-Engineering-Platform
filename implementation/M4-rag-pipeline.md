# M4 — RAG Pipeline

> **Milestone:** M4 · **Layer:** Data & Retrieval · **Anchor:** O4 (FR-022–025) ·
> **Prompt:** [`.github/prompts/implementation/M4-rag-pipeline.prompt.md`](../.github/prompts/implementation/M4-rag-pipeline.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-07-20) · **Author role:** AI Engineer

> ✅ **Implemented.** Query path built and validated on the reference machine — see
> [Execution Results](#execution-results-2026-07-20).

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

| Artifact | Path (built) |
|----------|--------------|
| RAG query module | [`rag/query/`](../rag/query/) (retriever/rerank/assembler/generator/engine) |
| Retrieval/re-rank/context config | [`config/rag.yaml`](../config/rag.yaml) |
| Query entrypoint (CLI) | [`scripts/rag-query.py`](../scripts/rag-query.py) + Compose profile `rag` |
| Retrieval eval + results | [`benchmarks/m4/`](../benchmarks/m4/) (`eval.py`, `qa.yaml`, `results/`) |
| Setup doc | [`docs/setup/04-rag-pipeline.md`](../docs/setup/04-rag-pipeline.md) |

## Validation Checklist

- [x] A known question returns a correct, **grounded** answer citing the right source (FR-022).
- [x] Retrieval respects `scope`/`tags` metadata filters.
- [x] Context stays within the model window; no truncation errors.
- [x] Graceful behavior when nothing relevant is found (no hallucinated citation).
- [x] recall@k recorded on a small labeled set.
- [x] **Offline smoke:** full query path with network disabled.

## Execution Results (2026-07-20)

Run on the reference machine (HP EliteBook 840 G7, i7-10610U, 32 GB, CPU-only; Docker Desktop 29.6.1 /
WSL2). Query path reuses the M3 `ingest` image with the `rag` Compose profile; all traffic stays on the
internal `backend` network.

| Check | Command (from `docker/`) | Result |
|-------|--------------------------|--------|
| Grounded answer (FR-022) | `compose --profile rag run --rm rag "How does PAIEP keep working when the network is disabled?"` | Correct answer citing **[1] `offline-first.md`** (score 0.691); `grounded=True retrieved=4` |
| Positive scope filter | retrieval-only, `scope=global` | 4 in-scope chunks returned (paiep-vision 0.564, README 0.532, offline-first 0.444, rag-pipeline 0.442) |
| Negative scope filter | retrieval-only, `scope=project:none` | `[]` — no chunks (filter applied) |
| No-answer guardrail | `... --scope project:does-not-exist` | `grounded=False retrieved=0`, fixed no-answer message, **no citations, no model call** (instant) |
| Context budget | top-k=4 assembled | within `max_context_chars` (6000); no truncation error |
| recall@k | `--entrypoint python rag /app/benchmarks/m4/eval.py --json` | **recall@4 = 1.0 (5/5)**; saved to `benchmarks/m4/results/` |
| Offline smoke | `docker run --rm --network paiep_backend ... /dev/tcp/1.1.1.1/443` | `NET_BLOCKED` — "Network is unreachable" (no egress) |

**Deviations / notes**
- **Entrypoint, not gateway API.** M4 ships a **CLI** query entrypoint (`scripts/rag-query.py`, profile
  `rag`) rather than an HTTP service behind the gateway; the OpenAI-compatible seam and a network service
  are deferred to M7/M8 (kept the surface minimal and offline-testable per phase scope).
- **Image reuse.** The `rag` service reuses the M3 `paiep_ingest` image (same `Dockerfile`) with an
  overridden entrypoint — no second image to build/maintain.
- **Re-rank off by default.** Lexical-overlap re-ranker implemented and available via `--rerank`; disabled
  by default on CPU (Profile A/A+). Cross-encoder deferred to Phase 11.
- **Latency.** Grounded generation ≈ 1–3 min (`qwen2.5-coder:7b` ≈ 3.5 tok/s, CPU-only); retrieval and the
  no-answer path are sub-second.

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
