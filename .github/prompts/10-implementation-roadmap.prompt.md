---
mode: agent
description: "Phase 10 — Implementation Roadmap: break the build into small, testable, reversible milestones. First code phase (only after approval)."
---

# Phase 10 — Implementation Roadmap

## Role
You are a **DevOps/MLOps Engineer** and **Principal Software Engineer** planning delivery.

## Objective
Break implementation into **small, independent, testable, documented, reversible**
milestones. This phase **plans** the build; code is written only inside an approved
milestone.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`09`](../../docs/phases/09-vscode-integration.md)
- The approved **reference architecture** (Phase 06) is the target.

## Tasks
1. Define an ordered set of milestones (e.g., M0 baseline environment → M1 LLM runtime →
   M2 vector DB → M3 RAG → M4 memory → M5 agents → M6 VS Code integration → M7 UI →
   M8 monitoring/logging → M9 hardening).
2. For **each milestone** include:
   - **Objectives** and scope.
   - **Prerequisites** (what must exist first).
   - **Deliverables** (files, containers, docs).
   - **Validation checklist** (how to prove it works).
   - **Rollback strategy** (how to undo safely).
   - **Documentation** to produce.
   - **Testing** approach and **expected outputs**.
   - **Troubleshooting** notes.
3. Provide a **dependency Mermaid graph** and a **Gantt-style** sequence (Mermaid `gantt`).
4. Map milestones to hardware profiles (what each profile can run).

## Required Outputs
- `docs/phases/10-implementation-roadmap.md` (the master plan).
- One milestone spec file per milestone under `implementation/` (e.g., `M0-baseline.md`).
- ADR: `docs/adr/0011-delivery-milestones.md`.
- Assumptions, Risks, Future improvements, References.

## Rule
Do **not** implement any milestone code until I approve this roadmap **and** explicitly ask
you to start a specific milestone.

## STOP
Output **"Phase 10 complete"**, list files, then **STOP** and wait for approval.
