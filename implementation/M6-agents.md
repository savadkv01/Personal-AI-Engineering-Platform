# M6 — Agent Ecosystem

> **Milestone:** M6 · **Layer:** Cognition · **Anchor:** O5 (FR-030–033),
> [Phase 07](../docs/phases/07-agent-ecosystem.md), [ADR 0008](../docs/adr/0008-agent-orchestration.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** AI Engineer + Principal Software Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M6 is explicitly requested.

---

## Objectives & Scope

Build the **agent orchestration** layer: **LangGraph** for stateful control + **CrewAI** for declarative
personas ([Phase 06 §3](../docs/phases/06-technology-selection.md),
[Phase 05 §9](../docs/phases/05-enterprise-architecture.md)), wiring in RAG (M4) and memory (M5) as tools.

**In scope**
- **LangGraph orchestrator** with a **supervisor** pattern, bounded chains, and **HITL approval** gates.
- **CrewAI persona configs** (YAML) for the [Phase 07](../docs/phases/07-agent-ecosystem.md) roles
  (P1–P14) — prompt + tools + model tier + guardrails (FR-030).
- **Model router** (role → model profile, FR-003) over the gateway.
- **Tool runtime** (sandboxed file/shell/search/RAG/memory) enforcing **least privilege**
  ([ADR 0006](../docs/adr/0006-security-model.md), NFR-021); actions require approval + are traced.
- Guardrails to protect **CPU interactivity** (bounded chain length/timeouts, NFR-004).

**Out of scope:** editor integration (M7), UI (M8), observability (M9).

## Prerequisites

- **M4** (RAG) and **M5** (memory) complete — agents consume both as tools.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Orchestrator graph | `agents/orchestrator/` |
| Persona configs (YAML) | `agents/personas/` |
| Model router config | `config/router.yaml` |
| Tool runtime + policies | `agents/tools/`, `config/tool-policy.yaml` |
| Agent flow docs | `agents/README.md` |

## Validation Checklist

- [ ] Supervisor routes a task to the correct persona/model tier.
- [ ] An agent uses RAG + memory tools and returns a grounded, cited result.
- [ ] Chains are **bounded** (max steps/timeout); no runaway loops on CPU.
- [ ] Tool actions require **approval** and are **traced** (HITL, [ADR 0006](../docs/adr/0006-security-model.md)).
- [ ] Least-privilege enforced (path-scoped fs, opt-in shell) per tool policy.
- [ ] **Offline smoke:** a multi-step task completes with network disabled.

## Rollback Strategy

- Disable the `agents` module; the gateway still serves plain chat + RAG (M4).
- Personas/tools are config — remove/disable individual personas without touching the engine.
- Revert `agents/` via `git restore`; no schema changes (uses M5 memory).

## Documentation to Produce

- Orchestration/supervisor/guardrail design in `agents/README.md`.
- Persona catalog mapping P1–P14 → configs; confirm [ADR 0008](../docs/adr/0008-agent-orchestration.md).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Functional | single-persona task | correct grounded result |
| Integration | supervisor multi-agent flow | routed, bounded, cited |
| Safety | attempt disallowed tool action | blocked + approval required |
| Performance | chain latency on CPU | within bounds, recorded |
| Offline | disable network | success |

## Troubleshooting Notes

- **Slow/looping chains:** tighten step/timeout limits; use draft tier for routing, coding tier for work.
- **Tool over-permission:** default deny; enable shell/container per-persona explicitly.
- **Persona overlap:** LangGraph owns control, CrewAI owns persona ergonomics — avoid duplicating logic.
- **Token blowups:** trim context; summarize memory before injection.

## Hardware Profiles

- **A:** short, bounded chains; few concurrent agents.
- **A+:** bounded chains; 7B coding tier; the reference interactive target.
- **B/C:** longer chains + concurrency with GPU.
- **D:** many agents concurrently; longer autonomous flows.
