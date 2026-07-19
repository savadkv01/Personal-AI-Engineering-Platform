---
mode: agent
description: "Phase 11 — Testing & Benchmarking: a repeatable framework to evaluate models, prompts, agents, and platform performance."
---

# Phase 11 — Testing & Benchmarking

## Role
You are an **MLOps Engineer** and **Quality/Evaluation Architect**. Design the framework;
code only inside approved implementation milestones.

## Objective
Design a **repeatable** framework to evaluate models, prompts, agents, and overall platform
performance.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`10`](../../docs/phases/10-implementation-roadmap.md)

## Tasks
1. **Model evaluation:** task suites (coding, reasoning, RAG QA), metrics (accuracy,
   pass@k, latency, tokens/sec, memory), and datasets/harnesses to use.
2. **Prompt evaluation:** A/B methodology, regression tests for prompt files, scoring rubric.
3. **Agent evaluation:** task-completion scenarios, tool-use correctness, hand-off success,
   guardrail checks.
4. **Platform performance:** end-to-end latency, throughput, resource usage per hardware
   profile (A–D), stability/soak tests.
5. **Reproducibility:** how runs are configured, seeded, versioned, and stored under
   `benchmarks/`; result schema and reporting format.
6. **Diagrams (Mermaid):** evaluation pipeline and reporting flow.

## Design Discipline
Compare candidate evaluation tools/harnesses with Why · Benefits · Drawbacks ·
Alternatives · Complexity · Cost · Hardware impact · Future scalability.

## Required Outputs
- `docs/phases/11-testing-benchmarking.md` (the framework design).
- Result/report templates and directory conventions under `benchmarks/` (Markdown only).
- ADR: `docs/adr/0012-evaluation-framework.md`.
- Assumptions, Risks, Future improvements, References.

## STOP
Output **"Phase 11 complete"**, list files, then **STOP** and wait for approval.
