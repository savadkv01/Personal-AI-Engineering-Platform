# M5 — Memory Service

> **Milestone:** M5 · **Layer:** Cognition · **Anchor:** O3 (FR-010–014),
> [Phase 08](../docs/phases/08-knowledge-memory.md), [ADR 0009](../docs/adr/0009-vector-store-and-memory.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** AI Engineer + Data Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M5 is explicitly requested.

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

**Out of scope:** agent orchestration (M6), editor UX (M7).

## Prerequisites

- **M1** (embeddings) and **M2** (Qdrant conventions) complete. Independent of M3/M4 (can run in parallel).

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Postgres service (Compose profile) | `docker/docker-compose.yml` |
| Memory schema + migrations | `memory/schema/`, `memory/migrations/` |
| Memory service module (CRUD + recall) | `memory/service/` |
| Retention/summarization policy | `config/memory.yaml` |
| SQLite substitute config (Profile A) | `config/memory.profile-a.yaml` |
| Memory design docs | `memory/README.md` |

## Validation Checklist

- [ ] Write/read facts + preferences to Postgres; run state persists.
- [ ] Semantic recall returns relevant memories filtered by **scope** (global vs project, FR-012).
- [ ] User can **list/edit/delete** memories (FR-013).
- [ ] Retention policy prunes/summarizes per config; no unbounded growth.
- [ ] Postgres + Qdrant memory stay **consistent** (consistency check passes).
- [ ] **Offline smoke:** recall + CRUD with network disabled.

## Rollback Strategy

- Disable the `memory`/`postgres` Compose profiles; orchestrator falls back to stateless sessions.
- Migrations are **versioned + reversible** (down-migrations); drop the memory Qdrant collection if needed.
- Revert `memory/` via `git restore`; data lives in named volumes (backup before destructive changes — M9).

## Documentation to Produce

- Memory schema, scope model, retention policy in `memory/README.md`.
- Finalize memory-scope decision referenced in [Phase 01](../docs/phases/01-project-vision.md) /
  [Phase 08](../docs/phases/08-knowledge-memory.md); update [ADR 0009](../docs/adr/0009-vector-store-and-memory.md).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Functional | CRUD + recall scenarios | correct, scope-filtered results |
| Consistency | Postgres vs Qdrant check | no drift |
| Performance | recall latency under load | non-blocking (async), recorded |
| Regression | re-run M1–M3 checks | green |
| Offline | disable network | success |

## Troubleshooting Notes

- **Store drift:** run consistency reconciliation; treat Postgres as source of truth for facts, Qdrant for recall.
- **Recall pollution:** tune scope filters + retention; summarize stale memories.
- **Latency spikes:** ensure writes are async/queued off the request path.
- **Profile A:** prefer SQLite to avoid running Postgres on 16 GB.

## Hardware Profiles

- **A:** **SQLite** substitute; recall over a small memory collection.
- **A+:** full **Postgres + Qdrant** memory.
- **B/C:** unchanged; faster embeds speed recall writes.
- **D:** shared memory backend; retention/summarization scale on server.
