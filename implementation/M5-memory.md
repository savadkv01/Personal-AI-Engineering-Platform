# M5 — Memory Service

> **Milestone:** M5 · **Layer:** Cognition · **Anchor:** O3 (FR-010–014),
> [Phase 08](../docs/phases/08-knowledge-memory.md), [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) ·
> **Prompt:** [`.github/prompts/implementation/M5-memory.prompt.md`](../.github/prompts/implementation/M5-memory.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-10-31) · **Author role:** AI Engineer + Data Engineer

> ✅ **Implemented.** Built and validated on the reference machine — see
> [Execution Results](#execution-results-2026-10-31).

---

## Objectives & Scope

Build the **Memory Service**: durable **structured state** in **Postgres** + **semantic recall** via
**Qdrant** ([Phase 06 §7](../docs/phases/06-technology-selection.md),
[Phase 05 §6/§8](../docs/phases/05-enterprise-architecture.md)), with **scope**, **CRUD**, and **retention**.

**In scope**
- **Postgres** service (metadata/state + structured memory); **SQLite** substitute path for Profile A.
- **Memory schema:** facts/preferences, run state, scope column (**global/project**, FR-012), timestamps.
- **Semantic recall** via Qdrant memory collection (payload-filtered by scope).
- **User CRUD** on memories (FR-013) and a **retention/summarization** policy (finalized here per
  [Phase 08 / M5](../docs/phases/08-knowledge-memory.md)).
- **Async memory updates** so recall/writes don't block interactive latency
  ([Phase 05 §8](../docs/phases/05-enterprise-architecture.md), NFR-004).
- **Session memory** + consolidation into long-term, and memory retrieval into the **M4 context**
  ([M5 prompt](../.github/prompts/implementation/M5-memory.prompt.md)).

**Out of scope:** agent orchestration / agent-specific memory routing and task locks (M6), editor UX (M7).

## Prerequisites

- **M1** (embeddings) and **M2** (Qdrant conventions, `memory_semantic` collection) complete; **M4** for
  the RAG integration.

## Deliverables

| Artifact | Path (built) |
|----------|--------------|
| Postgres service + `memory` CLI service (Compose profiles `memory`, `rag`) | [`docker/docker-compose.yml`](../docker/docker-compose.yml) |
| Memory schema + reversible migrations (Postgres + SQLite) | [`memory/migrations/`](../memory/migrations/) |
| Memory service module (CRUD, recall, sessions, consolidation, forgetting, outbox, check) | [`memory/service/`](../memory/service/) |
| Memory CLI | [`scripts/memory-cli.py`](../scripts/memory-cli.py) |
| Retention/summarization policy | [`config/memory.yaml`](../config/memory.yaml) |
| SQLite substitute config (Profile A) | [`config/memory.profile-a.yaml`](../config/memory.profile-a.yaml) |
| RAG integration (memory in context, sessions) | [`rag/query/engine.py`](../rag/query/engine.py), [`config/rag.yaml`](../config/rag.yaml) `memory:`, [`scripts/rag-query.py`](../scripts/rag-query.py) |
| Unit tests (offline) | [`tests/test_memory.py`](../tests/test_memory.py), [`tests/test_query.py`](../tests/test_query.py) |
| Benchmark + results | [`benchmarks/m5/`](../benchmarks/m5/) |
| Docs | [`docs/setup/05-memory.md`](../docs/setup/05-memory.md), [`memory/README.md`](../memory/README.md) |

## Validation Checklist

- [x] Write/read facts + preferences to Postgres; run state persists.
- [x] Semantic recall returns relevant memories filtered by **scope** (global vs project, FR-012).
- [x] User can **list/edit/delete** memories (FR-013).
- [x] Retention policy prunes/summarizes per config; no unbounded growth.
- [x] Postgres + Qdrant memory stay **consistent** (consistency check passes).
- [x] **Offline smoke:** recall + CRUD with network disabled.
- [x] Session facts written/retrievable; consolidation promotes them; memory context improves answers
      within the context budget (M5 prompt checklist).

## Execution Results (2026-10-31)

Reference machine (HP EliteBook 840 G7, i7-10610U, 32 GB, CPU-only; Docker Desktop 29.6.1 / WSL2).
Postgres `16.14-alpine` + Qdrant `v1.12.6` + Ollama `0.6.2` (`nomic-embed-text`, `qwen2.5-coder:7b`).

| Check | Result |
|-------|--------|
| Migrations | `migrate up` applied `0001_init` on Postgres; **up → down → up** on a throwaway DB reversible |
| CRUD (FR-013) | add/list/get/edit/supersede/delete OK; edit re-embeds; delete removes row **and** vector |
| Write latency | **4 ms p50 / 13 ms p95** — embedding/upsert async (outbox); 10 items fully synced in 1.5 s |
| Scoped recall (FR-012) | `project:paiep` → paiep + global; `--no-global` → paiep only; `project:atlas` never leaked |
| Recall quality | **hit@3 = 1.0** (10/10), **0/3** off-topic false positives; relevant 0.51–0.79 vs unrelated ≤ 0.42 |
| Recall latency | 44–106 ms single-threaded; p50 357 ms / p95 1.5 s under 4 concurrent threads (CPU embedding) |
| Dedup | exact duplicate → reinforced (no new row); punctuation paraphrase → `merged`; related-but-different preference **not** merged |
| Sessions | 4 turns → close promoted the `fact` turn + `remember:` turn, evicted 4 turns; promoted fact recalled from a new session |
| LLM summary (opt-in) | `session close --summarize` → `task_summary` memory in **79 s** (CPU) |
| Retention | TTL item → `expired` via `maintain` (dry-run reported identically without changes) |
| Consistency | injected missing vector + ghost point → `check` flagged both; `--repair` → `consistent: true` |
| Persistence | full `compose down` / `up` → identical stats, recall OK, consistent |
| Cross-session RAG | answer cited **two memories** from different sources (global preference + fact promoted from an earlier session) — 125 s |
| Multi-turn RAG | follow-up "which formatter for *that* language?" resolved via session history → cited edited preference — 55 s |
| Reinforce-on-use | cited memory confidence 0.70 → 0.85 |
| Offline smoke | `memory` container on `backend`: `Network is unreachable`; recall + CRUD OK |
| Profile A | SQLite + local vectors with `--no-deps` (no Postgres/Qdrant): add/recall/check OK, 80 ms recall |
| Regression | M4 recall@4 = **1.0**; no-answer guardrail unchanged; **67** unit tests + ruff green |

Validation data was removed afterwards via the rollback path (`migrate down` → `up` → `check --repair`).

**Deviations / notes**
- **Schema lives in `memory/migrations/`** (one source of truth per dialect) rather than a separate
  `memory/schema/`; the ERD is in [Phase 08 §12.2](../docs/phases/08-knowledge-memory.md).
- **Not built (M6 scope):** `task_lock`, `session_artifact`, `project`, `source` tables from the Phase 08
  ERD. Sessions hold turns only; agent locks/artifacts arrive with orchestration.
- **Async = in-process outbox worker**, not a separate queue service: rows carry `vector_status`, a daemon
  thread drains it, and `sync`/`check --repair` recover after crashes. Fits one-user/one-host; a Prefect /
  queue worker is the Profile D upgrade.
- **Consolidation is deterministic by default** (explicit `fact` turns + `remember:`/`note:` prefixes); the
  LLM summary is opt-in because it costs ~1 min per session on CPU. Automatic salience detection by the
  Supervisor is M6.
- **Decay is computed, not stored** (`confidence × 0.5^(days/half-life)`), so `maintain` is idempotent.
- **Profile A** uses SQLite + a brute-force local vector index (fine below ~20k memories) instead of
  pgvector, so it needs no extra services.
- **`maintain` is manual / externally scheduled** until the M6/M9 scheduler exists.
- **Documents vs memory scope:** M4 document retrieval still filters `scope` **exactly**; memory recall
  adds `global` to project queries. Aligning document retrieval is a candidate M6 change.

## Rollback Strategy

- Disable memory in RAG (`config/rag.yaml memory.enabled: false` or `rag-query --no-memory`) → pure M4.
- `memory migrate down` (versioned, reversible; back up `paiep_db` first), then `memory check --repair`
  to clear vectors — validated on 2026-10-31.
- Remove the `postgres`/`memory` services; revert `memory/`, `config/memory*.yaml` via `git restore`.
  M1–M4 remain functional.

## Documentation to Produce

- [x] Memory schema, scope model, retention policy — [`memory/README.md`](../memory/README.md),
      [`docs/setup/05-memory.md`](../docs/setup/05-memory.md).
- [x] Memory-scope + retention decision finalised — [ADR 0009](../docs/adr/0009-vector-store-and-memory.md)
      (M5 implementation notes).

## Testing Approach & Expected Outputs

| Test | Method | Result |
|------|--------|--------|
| Functional | CRUD + recall scenarios (unit + live) | correct, scope-filtered results |
| Consistency | `memory check` (Postgres vs Qdrant), injected drift | detected + repaired |
| Performance | [`benchmarks/m5/bench.py`](../benchmarks/m5/bench.py) | writes non-blocking; recall latency recorded |
| Regression | M4 eval + unit tests | green |
| Offline | `backend` network egress probe | blocked; service works |

## Troubleshooting Notes

- **Store drift:** `memory check --repair`; Postgres is the source of truth for facts, Qdrant for recall.
- **Recall pollution:** raise `memory.score_threshold`, scope memories to projects, run `maintain`.
- **Latency spikes:** writes are already async; recall cost is the CPU embedding call.
- **Profile A:** use `memory.profile-a.yaml` (SQLite) to avoid running Postgres/Qdrant on 16 GB.
- More in [`docs/setup/05-memory.md` §7](../docs/setup/05-memory.md#7-troubleshooting).

## Hardware Profiles

- **A:** **SQLite** + local vectors; `recall.top_k: 3`, cap 2000 items.
- **A+:** full **Postgres + Qdrant** memory (validated).
- **B/C:** unchanged; faster embeds speed recall + writes.
- **D:** shared memory backend; move the outbox worker + `maintain` to a scheduler.
