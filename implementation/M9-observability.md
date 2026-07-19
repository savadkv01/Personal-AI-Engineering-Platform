# M9 — Observability (Monitoring, Logging, Tracing)

> **Milestone:** M9 · **Layer:** Ops · **Anchor:** O8 (FR-066/007),
> [Phase 06 §9](../docs/phases/06-technology-selection.md) ·
> **Prompt:** [`.github/prompts/implementation/M9-observability.prompt.md`](../.github/prompts/implementation/M9-observability.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** DevOps/MLOps Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M9 is explicitly requested.

---

## Objectives & Scope

Add **monitoring, logging, and LLM/agent tracing** to make the platform debuggable and measurable
([Phase 06 §9](../docs/phases/06-technology-selection.md), e.g. **Langfuse** for LLM traces + optional
**Prometheus + Grafana + Loki** for metrics/logs). Feeds the Phase 11 evaluation harness.

**In scope**
- Metrics collection + **dashboards** (latency, tokens/sec, resource usage).
- **Centralized, structured logs** (searchable).
- **LLM/agent tracing** (prompt, tokens, latency, tool calls) across gateway, RAG (M4), agents (M6).
- A few **starter alert rules**.
- Per-profile (A–D) overhead notes; all behind Compose profiles, **off by default on Profile A**.

**Out of scope:** security hardening / release (M10).

## Prerequisites

- Core services **M1–M8** running (basic health available since M1; full signal needs M6 + M8).

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Monitoring/logging/tracing services | `docker/docker-compose.yml`, `docker/monitoring/` |
| Dashboards + alert rules | `docker/monitoring/dashboards/`, `docker/monitoring/alerts/` |
| Tracing hooks | gateway/agent/RAG instrumentation |
| Setup doc | `docs/setup/09-observability.md` |

## Validation Checklist

- [ ] Metrics visible in dashboards for runtime, RAG, and agents.
- [ ] Centralized logs are searchable.
- [ ] Traces capture end-to-end request/agent flows (tokens, latency, tool calls).
- [ ] At least one **alert fires** correctly in a test condition.
- [ ] Observability **disabled by default on Profile A**; enabling is a single profile flag.
- [ ] **Offline smoke:** dashboards + traces work with network disabled.

## Rollback Strategy

- Disable the `observability` Compose profile; core stack keeps running (tracing is optional).
- Remove Langfuse/Grafana/Loki volumes (trace/log history is non-critical) — reversible.
- Revert `docker/monitoring/` and tracing hooks via `git restore`.

## Documentation to Produce

- Observability setup, dashboards, and trace usage in `docs/setup/09-observability.md`.
- Verify **Grafana AGPL / Langfuse** license terms at pinning ([Phase 06 §9](../docs/phases/06-technology-selection.md)).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Metrics | run flows, open dashboard | live runtime/RAG/agent metrics |
| Logs | search structured logs | relevant entries found |
| Tracing | run agent flow, open Langfuse | trace with tokens/latency/tools |
| Alerting | trigger test condition | alert fires |
| Resource | obs on/off delta | recorded RAM overhead |
| Offline | disable network | success |

## Troubleshooting Notes

- **RAM pressure:** keep obs off on A/A+ unless debugging (optional by design).
- **Missing traces:** ensure hooks wrap gateway + agent + RAG call sites.
- **Grafana license:** verify AGPL acceptability; otherwise Prometheus/Loki only.
- **Port clashes:** all UIs on distinct loopback ports.

## Hardware Profiles

- **A:** observability **off** by default; enable transiently to debug.
- **A+:** enable selectively; watch RAM budget.
- **B/C:** run continuously with headroom.
- **D:** central observability + retained traces over time.
