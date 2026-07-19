---
mode: agent
description: "Implementation M6 — Agent ecosystem: agent framework, orchestration, and first specialized agents. Reversible."
---

# Implementation Milestone M6 — Agent Ecosystem

> **Precondition:** M5 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are an **AI Platform Architect / Software Engineer** implementing the multi-agent layer.

## Objective
Stand up the agent framework and orchestration from Phase 07, plus an initial set of
specialized agents that use RAG (M4) and memory (M5).

## Prerequisites
- M4 (RAG) and M5 (memory) running.
- Phase 07 agent specs, orchestration pattern, communication contract, shared-memory design.

## Scope
- **In:** agent framework, orchestrator/router, 3–4 starter agents (e.g., Architect, Software
  Engineer, Documentation Writer, Reviewer), tool access, guardrails.
- **Out:** full 14-agent roster (add incrementally), UI (M8).

## Tasks
1. Integrate the chosen agent framework (Phase 06) into Compose/services.
2. Implement the orchestration pattern (supervisor/router or peer-to-peer) from Phase 07.
3. Implement the inter-agent communication contract and shared-memory access.
4. Build 3–4 starter agents with clear tools, model tiers, and guardrails.
5. Provide a task entrypoint (CLI/API) to run a representative cross-agent task.

## Deliverables
- Agent framework integration + starter agents; `docs/setup/06-agents.md`; specs under `agents/`.

## Validation Checklist
- [ ] Orchestrator routes a task to the correct agent(s).
- [ ] Agents can call permitted tools and read/write shared memory.
- [ ] A representative multi-agent task completes end to end.
- [ ] Guardrails prevent out-of-scope tool use.

## Expected Outputs
- A working multi-agent flow that solves a representative task using RAG + memory.

## Rollback Plan
- Remove agent services/modules; RAG and memory (M4/M5) continue to work standalone.

## Troubleshooting
- Routing loops, tool permission errors, context/token overflow across hand-offs, non-determinism.

## Documentation to Update
- `docs/setup/06-agents.md`; per-agent specs in `agents/`.

## Testing
- Run the representative task; verify hand-offs, tool use, and memory updates.

## STOP
Output **"Milestone M6 complete"**, list files, confirm validation, then **STOP** and wait for approval.
