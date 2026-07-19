# Memory — Seed Design Notes

> Seed notes for PAIEP memory. Full design:
> [`docs/phases/08-knowledge-memory.md`](../docs/phases/08-knowledge-memory.md) §5–§6. Stores:
> PostgreSQL (structured/state) + Qdrant (semantic) ([ADR 0009](../docs/adr/0009-vector-store-and-memory.md)).

## Two horizons

| | Session | Long-term |
|-|---------|-----------|
| Scope | current task (`task_id`) | across sessions/projects |
| Store | LangGraph state + Postgres `session_*` | Postgres `memory_item` + Qdrant `memory_semantic` |
| Lifetime | task + TTL, then evicted | until superseded/decayed/deleted |
| Recall | recent context | semantic + scope-filtered |

## What persists long-term
Facts, preferences/conventions, project decisions (ADR links), entities, learner progress, salient task
summaries — **not** raw transcripts.

## Consolidation
Capture (async, post-task) → deduplicate (hash + similarity) → summarize → promote (salient only) →
confidence + reinforce on reuse.

## Forgetting policy
Decay (low confidence + unused) · TTL (ephemeral) · supersede (keep history) · **user delete** (FR-013,
cascade to Qdrant) · scope prune (archived projects).

## Scope
`global` vs `project:<name>` via Postgres column + Qdrant payload filter (FR-012). Retention tuned in M5.

## Privacy
All local; user can view/edit/delete any memory (NFR-020). Deletes cascade to vectors.
