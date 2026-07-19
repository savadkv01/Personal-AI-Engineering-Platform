# ADR 0011: Delivery Milestones

- **Status:** Proposed
- **Date:** 2026-07-19

## Context

[Phase 10 — Implementation Roadmap](../phases/10-implementation-roadmap.md) is the first code phase. Per the
repo golden rules (small, independent, testable, documented, **reversible** steps) and phase-gating
([ADR 0001](0001-design-first-gated-phases.md)), the build must be decomposed into ordered milestones that
each stand alone, prove themselves, and can be rolled back. Prior phases already **committed to specific
milestone numbers** that this ADR must preserve:

- **M1** = LLM runtime + integration spike + first CPU benchmarks
  ([ADR 0004](0004-default-model-selection.md), [ADR 0007](0007-reference-stack.md)).
- **M5** = memory service scope/retention ([Phase 08](../phases/08-knowledge-memory.md),
  [Phase 06 §7](../phases/06-technology-selection.md), [Phase 01](../phases/01-project-vision.md)).
- **M7** = VS Code integration + template/cookiecutter ([Phase 09](../phases/09-vscode-integration.md),
  [ADR 0010](0010-vscode-integration-strategy.md), [ADR 0100](0100-gpu-and-reuse-strategy.md)).

The target is the approved reference stack ([ADR 0007](0007-reference-stack.md)) on the CPU-only "A+"
primary machine, scalable across Profiles A–D.

## Decision

Adopt an **eleven-milestone (M0–M10)** delivery sequence that maps **1:1** to the executable prompts in
[`.github/prompts/implementation/`](../../.github/prompts/implementation/), each with its own spec under
[`implementation/`](../../implementation/) containing objectives, prerequisites, deliverables, a
**validation checklist**, a **rollback strategy**, docs, testing, and troubleshooting:

1. **M0** Baseline environment — WSL2 + Docker Compose skeleton, volumes, `.env`, loopback.
2. **M1** LLM runtime + spike — Ollama, gateway, default models, benchmarks, thin end-to-end slice. *(anchor)*
3. **M2** Vector database — Qdrant, collections, payload-filter conventions.
4. **M3** Embeddings & ingestion — embedding model + idempotent chunk→embed→upsert with provenance.
5. **M4** RAG pipeline — retrieve→(re-rank)→assemble→ground with citations.
6. **M5** Memory service — Postgres state + Qdrant recall, scope, CRUD, retention. *(anchor)*
7. **M6** Agent ecosystem — LangGraph orchestrator + CrewAI personas, guardrails.
8. **M7** VS Code integration — Continue + Cline, MCP servers, template/cookiecutter. *(anchor)*
9. **M8** User interface — local web UI (Open WebUI) wired to runtime/RAG/memory/agents.
10. **M9** Observability — Langfuse traces + optional Prometheus/Grafana/Loki, dashboards, alerts.
11. **M10** Hardening & release — security, resource limits, backups, one-command bring-up, v1 release.

Rules that bind every milestone: **loopback-only + offline** ([ADR 0005](0005-container-topology.md)),
**pinned versions** with license re-verification ([ADR 0007](0007-reference-stack.md)), **config over code**,
**test-before-proceed** gating, and a **documented rollback**. Milestone numbers are **frozen** to stay
consistent with prior phases and the prompt files. **No milestone code is written until this roadmap is
approved and a specific milestone is explicitly requested.**

## Alternatives Considered

- **Big-bang build (whole stack at once).** Fewer hand-offs, but violates reversibility/gating, hides failures,
  and risks over-engineering. **Rejected.**
- **Different numbering (e.g., memory=M4, agents=M5, vscode=M6).** Cleaner on paper, but **contradicts committed
  references** (M1/M5/M7) in Phases 06/08/09 and ADRs 0004/0007/0010/0100. **Rejected** to avoid doc drift.
- **Defer the integration spike until after M2–M4.** Would delay whole-stack validation; instead M1 includes a
  **thin vertical slice** to de-risk the reference stack early ([ADR 0007](0007-reference-stack.md)). **Rejected.**
- **Collapse ingestion+RAG (one milestone) and UI+observability (one milestone).** Fewer files, but breaks the
  **1:1 mapping with the executable prompts** ([`.github/prompts/implementation/`](../../.github/prompts/implementation/))
  and mixes distinct concerns (write-path vs. query-path; client vs. ops). **Rejected** to keep prompt/spec parity.
- **UI/observability as an early milestone.** Adds RAM cost before there's anything to observe; kept **optional**
  and placed at **M8 (UI)** / **M9 (observability)**. **Rejected** as early scope.

## Consequences

**Benefits**
- Each milestone is independently shippable, testable, and reversible on a single CPU laptop (CON-001/007).
- Early **M1 spike** validates the full reference stack before deep investment.
- Clear critical path (`M0→M1→M2→M3→M4→M6→M7→M10`) with **M5 parallelizable** alongside M3/M4.
- **1:1 spec↔prompt mapping** and numbering consistent with all prior phases/ADRs — no cross-doc contradictions.
- Per-profile mapping keeps the plan honest for Profiles A–D.

**Drawbacks**
- More upfront planning artifacts (eleven spec files) to maintain as versions are pinned.
- Gating adds ceremony (validate + record before proceeding) — intentional, but slower than big-bang.
- Milestone numbering is now hard to change without touching several documents.

**Follow-ups**
- On approval, execute **M0** first; record pinned versions + benchmark results back into
  [ADR 0004](0004-default-model-selection.md) / [ADR 0007](0007-reference-stack.md).
- Wire M9 traces into the **Phase 11** evaluation harness; capture the v1 release decision in a future
  `docs/adr/0014-v1-release-baseline.md` (M10).
- Revisit **Prefect** (scheduled jobs) and **vLLM** (GPU) for Profile D
  ([ADR 0100](0100-gpu-and-reuse-strategy.md)) as future milestones.
