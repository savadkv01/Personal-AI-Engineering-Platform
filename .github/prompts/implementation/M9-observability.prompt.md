---
mode: agent
description: "Implementation M9 — Observability: monitoring, logging, and tracing across the platform. Reversible."
---

# Implementation Milestone M9 — Observability (Monitoring, Logging, Tracing)

> **Precondition:** M8 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **DevOps/MLOps Engineer** adding observability.

## Objective
Add monitoring, logging, and LLM/agent tracing (per Phase 06, e.g., Prometheus + Grafana +
Loki + Langfuse/OpenTelemetry) to make the platform debuggable and measurable.

## Prerequisites
- Core services (M1–M8) running.
- Phase 06 monitoring/logging selections.

## Scope
- **In:** metrics collection, dashboards, centralized logs, request/agent tracing, basic alerts.
- **Out:** security hardening/release (M10).

## Tasks
1. Add monitoring + logging + tracing services to `docker/compose.yaml` with volumes.
2. Instrument services to emit metrics and structured logs.
3. Add LLM/agent tracing (prompt, tokens, latency, tool calls).
4. Build starter dashboards (latency, tokens/sec, resource usage) and a few alert rules.
5. Provide per-profile (A–D) notes on observability overhead.

## Deliverables
- Updated `docker/compose.yaml`; dashboard/config files; `docs/setup/09-observability.md`.

## Validation Checklist
- [ ] Metrics visible in dashboards for runtime, RAG, and agents.
- [ ] Centralized logs are searchable.
- [ ] Traces capture end-to-end request/agent flows.
- [ ] At least one alert fires correctly in a test condition.

## Expected Outputs
- Dashboards and logs/traces that explain platform behavior and performance.

## Rollback Plan
- Remove observability services and instrumentation flags; core platform unaffected.

## Troubleshooting
- Scrape target down, log volume growth, trace sampling too aggressive, dashboard datasource errors.

## Documentation to Update
- `docs/setup/09-observability.md`; link dashboards from `benchmarks/`.

## Testing
- Generate load, confirm metrics/logs/traces populate and an alert triggers.

## STOP
Output **"Milestone M9 complete"**, list files, confirm validation, then **STOP** and wait for approval.
