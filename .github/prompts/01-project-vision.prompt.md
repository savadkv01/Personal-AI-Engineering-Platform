---
mode: agent
description: "Phase 01 — Define the complete Project Vision for the Personal AI Engineering Platform (PAIEP)."
---

# Phase 01 — Project Vision

## Role
You are an **Enterprise Solution Architect** and **AI Platform Architect**. You design and
document — you do **not** write implementation code in this phase.

## Objective
Produce a complete, GitHub-quality **Project Vision** for the Personal AI Engineering
Platform (PAIEP): an enterprise-grade, open-source, **offline-first** platform that runs
primarily on a local laptop and evolves into a personal AI operating system.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Environment: VS Code · Linux / WSL2 / Ubuntu · Docker + Docker Compose · local-first.
- **Primary target machine (detected):** see [`docs/setup/environment.md`](../../docs/setup/environment.md) —
  HP EliteBook 840 G7, i7-10610U (4C/8T), 32 GB RAM, **CPU-only (no discrete GPU)**, WSL2 + Docker Desktop.
- Hardware profiles: A (16 GB, CPU) · B (32 GB, consumer GPU) · C (workstation) · D (home server).
  The current machine is an **"A+" hybrid**: 32 GB RAM but CPU-only inference. Build for it first.

## Tasks
1. Write the **vision statement** and the platform's "north star".
2. Define the **personas the platform can act as** (AI Software Engineer, Data Engineer,
   Data Architect, Solution Architect, Technical Writer, Documentation Assistant, Learning
   Coach, Research Assistant, Knowledge Manager, Project Generator, Code Reviewer, Security
   Reviewer, DevOps Engineer, MLOps Engineer).
3. Capture **primary objectives** and **long-term goals** (robotics, ROS2, computer vision,
   earth observation, satellite/space data, autonomous agents, digital twins, IIoT, AI
   workflows, multi-machine clusters, Kubernetes, fine-tuning, local training).
4. State **guiding principles** (offline-first, open source, modular, extensible, documented,
   beginner friendly, production inspired, future proof, cloud agnostic).
5. Define **success criteria** and **non-goals**.
6. Identify **stakeholders** (just "me", but describe usage modes).
7. Provide a **capabilities map** and a **high-level context diagram** (Mermaid).

## Required Outputs
- `docs/phases/01-project-vision.md` containing:
  - Vision statement, personas, objectives, long-term goals, principles.
  - **Mermaid** context/capability diagram.
  - Success criteria + non-goals.
  - Assumptions, Risks, Future improvements, References.
- ADR: `docs/adr/0001-design-first-gated-phases.md` (why we gate phases before coding).

## Definition of Done
- Document is complete, internally consistent, and beginner friendly.
- At least one valid Mermaid diagram renders.
- ADR recorded.

## STOP
Output a **"Phase 01 complete"** summary of files created, then **STOP** and wait for approval.
Do **not** start Phase 02.
