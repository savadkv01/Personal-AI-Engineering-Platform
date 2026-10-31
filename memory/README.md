# Memory

> PAIEP memory (M5): durable, user-editable structured memory + semantic recall.
> Setup & operations: [`docs/setup/05-memory.md`](../docs/setup/05-memory.md) ·
> Design: [Phase 08 §5–§6](../docs/phases/08-knowledge-memory.md) ·
> Decision: [ADR 0009](../docs/adr/0009-vector-store-and-memory.md).

## Layout

```text
memory/
├── migrations/
│   ├── postgres/0001_init.{up,down}.sql   # A+ default (TIMESTAMPTZ, UUID)
│   └── sqlite/0001_init.{up,down}.sql     # Profile A (TEXT ids/timestamps + memory_vector)
└── service/                               # Python package (MemoryService + CLI)
```

The migrations are the schema's single source of truth (versioned, reversible, applied
automatically on first use or via `memory migrate up|down|status`).

## Two horizons

| | Session | Long-term |
|-|---------|-----------|
| Scope | one conversation/task (`session_id`, `task_id`) | across sessions/projects |
| Store | `session` + `session_turn` | `memory_item` (+ vector in `memory_semantic`) |
| Lifetime | until closed / `ttl_hours` idle, then evicted | until superseded / merged / decayed / expired / deleted |
| Recall | recent turns as chat history (`--session`) | semantic + scope-filtered |

## What persists long-term
Facts, preferences/conventions, project decisions, entities, progress, and salient task summaries —
**not** raw transcripts. Promotion happens on session close: `fact` turns, user turns starting with
`remember:`/`note:`, and (opt-in) an LLM-written `task_summary`.

## Scope (decision finalised in M5)
`global` vs `project:<name>` — a column in Postgres and a payload filter in Qdrant (FR-012). Recalling for
a project returns that project's memories **plus global ones** (configurable); other projects never leak.
Finished projects are archived with `memory archive-scope project:<name>`.

## Retention (decision finalised in M5)
Exact + semantic dedup (0.92) · reinforce-on-use · supersede with history · TTL per item/type ·
time-decay (half-life 90 days; preferences/decisions exempt) archived below 0.2 · hard cap 5000 active
items · user delete cascades to vectors. All values live in [`config/memory.yaml`](../config/memory.yaml).

## Privacy
All local. Every memory can be listed, edited and deleted (FR-013, NFR-020); deletes remove the vector
too. Retrieved memories enter prompts as **data, not instructions** (same guard as RAG).
