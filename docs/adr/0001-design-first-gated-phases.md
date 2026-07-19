# ADR 0001: Design-First, Gated Phases Before Coding

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
The Personal AI Engineering Platform (PAIEP) is broad in ambition — offline LLMs, memory, RAG,
multi-persona agents, VS Code integration, and long-term horizons like robotics, earth
observation, clusters, and fine-tuning. Projects of this scope commonly fail by writing code too
early: components are built before requirements, trade-offs, and architecture are understood,
producing rework, lock-in, and undocumented decisions.

The project is also **single-operator** and **offline-first**, so the architecture and its
rationale must be self-explaining and durable over time — not held only in one person's head.

We therefore need a working method that forces understanding and documentation before
implementation. See [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md)
and the [Phase 01 Project Vision](../phases/01-project-vision.md).

## Decision
Adopt a **design-first, gated 12-phase** process:

1. **Design before code.** Phases 01–09 and 12 produce documentation, diagrams, comparisons, and
   ADRs — **no implementation code**. Code appears only in approved implementation milestones
   (Phase 10+).
2. **One phase at a time.** Each phase must be completed, reviewed, and **explicitly approved**
   before the next begins. Agents must **STOP** at each phase boundary and never auto-advance.
3. **Compare, never assert.** Every technology recommendation states Why · Benefits · Drawbacks ·
   Alternatives · Complexity · Cost · Hardware impact · Future scalability.
4. **Record decisions as ADRs** in `docs/adr/` using the standard format.
5. **Reversible implementation.** When code does begin, each step is small, independent, testable,
   documented, and reversible with a rollback plan.

## Alternatives Considered
- **Code-first / prototype-driven.** Faster initial momentum, but risks rework, undocumented
  choices, and lock-in on a broad, long-lived platform. **Rejected** as the default.
- **Big up-front design (waterfall, no gates).** Heavy single design pass with no checkpoints;
  brittle to change and hard to course-correct. **Rejected.**
- **Fully agile / no gating.** Continuous iteration with no phase boundaries; flexible but
  under-documents rationale and lets scope sprawl for a solo operator. **Rejected** as default.
- **Design-first with explicit gates (chosen).** Combines up-front understanding with iterative
  checkpoints and mandatory documentation.

## Consequences
**Benefits**
- Decisions are understood and documented before money/time is spent on code.
- Clear stop points prevent scope sprawl and enable course correction.
- ADRs create durable, self-explaining rationale for a single-operator project.
- Reusable prompt files make each phase independently executable and repeatable.

**Drawbacks**
- Slower to first running feature; documentation overhead up front.
- Requires discipline to stop at gates and to keep comparisons rigorous.

**Follow-ups**
- Track phase status in the [README roadmap](../../README.md).
- Revisit gate granularity if documentation overhead outweighs value.
- Apply the reversible-milestone rule starting at Phase 10.
