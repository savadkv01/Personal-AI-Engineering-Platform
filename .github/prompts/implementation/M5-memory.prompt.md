---
mode: agent
description: "Implementation M5 — Memory: session + long-term memory with consolidation and retrieval. Reversible."
---

# Implementation Milestone M5 — Memory (Session + Long-Term)

> **Precondition:** M4 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **Data Architect / AI Engineer** implementing the memory subsystem.

## Objective
Implement session memory and long-term memory with write, retrieval, consolidation, and a
forgetting/eviction policy, integrated with the RAG context.

## Prerequisites
- M2 (vector DB) and M4 (RAG) running.
- Phase 08 memory design (schemas, lifecycle, consolidation, forgetting).

## Scope
- **In:** session store, long-term store, consolidation job, memory retrieval into context,
  eviction/forgetting policy.
- **Out:** agent-specific memory routing (refined in M6).

## Tasks
1. Implement **session memory** (scope, lifecycle, eviction).
2. Implement **long-term memory** (persistent store, metadata, retrieval).
3. Add a **consolidation/summarization** step from session → long-term.
4. Integrate memory retrieval into the M4 context assembly.
5. Implement a **forgetting/eviction** policy with clear rules.

## Deliverables
- Memory modules; `docs/setup/05-memory.md`; schema notes under `memory/`.

## Validation Checklist
- [ ] Session facts are written and retrievable within a session.
- [ ] Consolidation promotes durable facts to long-term memory.
- [ ] Long-term memory persists across restarts.
- [ ] Forgetting/eviction removes stale/low-value entries per policy.
- [ ] Memory context improves answers without exceeding context budget.

## Expected Outputs
- Context-aware responses that reflect remembered facts across sessions.

## Rollback Plan
- Disable memory integration in M4 and drop memory collections/tables; M1–M4 remain intact.

## Troubleshooting
- Memory bloat / context overflow; stale or conflicting memories; consolidation over-summarizing.

## Documentation to Update
- `docs/setup/05-memory.md`; `memory/` design notes.

## Testing
- Multi-turn scenario proving recall across sessions; verify eviction behavior.

## STOP
Output **"Milestone M5 complete"**, list files, confirm validation, then **STOP** and wait for approval.
