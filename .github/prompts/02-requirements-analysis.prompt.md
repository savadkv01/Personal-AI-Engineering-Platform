---
mode: agent
description: "Phase 02 — Requirements Analysis: functional, non-functional, and constraints for PAIEP."
---

# Phase 02 — Requirements Analysis

## Role
You are a **Principal Software Engineer** and **Solution Architect** performing rigorous
requirements engineering. Design and document only — no implementation code.

## Objective
Translate the Phase 01 vision into a complete, testable set of **requirements**.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phase: [`docs/phases/01-project-vision.md`](../../docs/phases/01-project-vision.md)

## Tasks
1. **Functional requirements (FR):** enumerate capabilities (software dev, data engineering,
   AI/prompt engineering, docs, architecture design, learning, knowledge management,
   research, multi-agent collaboration, local RAG, long-term memory, repo-aware coding,
   markdown/technical doc generation, project generation, code/design/security review,
   testing assistance). Give each a stable ID (`FR-001`…).
2. **Non-functional requirements (NFR):** performance, offline-first, privacy/security,
   modularity, extensibility, portability, observability, maintainability, cost. IDs `NFR-001`…
3. **Constraints:** hardware profiles A–D, open-source licensing, local-first, VS Code, Docker.
4. **Assumptions & dependencies.**
5. **Requirements traceability:** map each requirement to the vision persona/objective it serves.
6. **Prioritization** using **MoSCoW** (Must/Should/Could/Won't-for-now).
7. Provide a **requirements-to-capability** Mermaid diagram.

## Required Outputs
- `docs/phases/02-requirements-analysis.md` with FR/NFR tables, constraints, MoSCoW,
  traceability matrix, Mermaid diagram, Assumptions, Risks, Future improvements, References.
- ADR: `docs/adr/0002-offline-first-priority.md`.

## Definition of Done
- Every requirement has an ID, priority, and traces to a vision element.
- Tables are scannable; diagram renders.

## STOP
Output **"Phase 02 complete"**, list files, then **STOP** and wait for approval.
