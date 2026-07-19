---
mode: agent
description: "Phase 07 — Agent Ecosystem: design specialized agents, responsibilities, collaboration, communication, and shared memory."
---

# Phase 07 — Agent Ecosystem

## Role
You are an **AI Platform Architect** designing a multi-agent system. Document only — no
implementation code.

## Objective
Design the specialized agents and how they collaborate.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`06`](../../docs/phases/06-technology-selection.md)

## Agents to Design (at least)
Architect · Data Engineer · Software Engineer · AI Engineer · Documentation Writer ·
Reviewer · Refactoring Agent · Testing Agent · DevOps Agent · Security Agent · Learning
Coach · Research Assistant · Knowledge Manager · Project Planner.

## Tasks
1. For **each agent**: mission, responsibilities, inputs/outputs, tools it may use, model
   tier, guardrails, and success criteria.
2. **Collaboration model:** orchestration pattern (supervisor/router vs peer-to-peer),
   hand-off protocol, conflict resolution.
3. **Communication:** message schema/contract between agents (describe, don't code).
4. **Shared memory:** what each agent reads/writes; how session vs long-term memory is used.
5. **Diagrams (Mermaid):** agent topology, a sequence diagram of a representative task
   (e.g., "build a small data pipeline") flowing across agents.
6. Map each agent to the reference stack chosen in Phase 06.

## Design Discipline
Explain orchestration choice with Why · Benefits · Drawbacks · Alternatives · Complexity ·
Cost · Hardware impact · Future scalability.

## Required Outputs
- `docs/phases/07-agent-ecosystem.md` with per-agent specs, collaboration/communication
  model, shared-memory design, and diagrams.
- Seed agent specs under `agents/` (Markdown only).
- ADR: `docs/adr/0008-agent-orchestration.md`.
- Assumptions, Risks, Future improvements, References.

## STOP
Output **"Phase 07 complete"**, list files, then **STOP** and wait for approval.
