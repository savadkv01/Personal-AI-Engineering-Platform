---
mode: agent
description: "Implementation M8 — UI: local web UI (e.g., Open WebUI / AnythingLLM) wired to runtime, RAG, and agents. Reversible."
---

# Implementation Milestone M8 — User Interface

> **Precondition:** M7 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **Software Engineer** adding a local UI layer.

## Objective
Deploy the Phase 06-selected Open WebUI as an optional local client connected to the M1 gateway and
existing RAG, memory, and agent services — for use outside the editor.

## Prerequisites
- M1 (runtime), M4 (RAG), M5 (memory), M6 (agents) running.
- Phase 06 UI decision and Phase 09 UX considerations.

## Scope
- **In:** UI service in Compose, connection to runtime + PAIEP APIs, basic auth for local use.
- **Out:** public exposure / remote access hardening (M10).

## Tasks
1. Add the UI service to `docker/docker-compose.yml` behind an optional profile, bound only to
   loopback, with persistent data and a stable secret key.
2. Connect the UI to the M1 gateway. Bridge existing MCP tools with MCPO rather than reimplementing
   PAIEP APIs.
3. Configure conversations, model selection, and RAG/agent access in the UI.
4. Require local authentication. Since Open WebUI can invoke OpenAPI tools without MCP annotations,
   expose only read tools and proposal-only agent run; keep agent approve/reject unavailable to the
   model and require an explicit CLI approval.
5. Document startup, admin setup, tool use, validation and rollback in `docs/setup/08-ui.md`.

## Deliverables
- Updated `docker/docker-compose.yml`; `docs/setup/08-ui.md`.

## Validation Checklist
- [ ] UI is reachable locally and lists available local models.
- [ ] A chat completes through the UI using the local runtime (offline).
- [ ] RAG-grounded and agent-driven responses work from the UI; agent proposals remain pending
      until separately approved by a human.
- [ ] UI settings/data persist across restarts.

## Expected Outputs
- A usable local UI for chatting, RAG, and running agents without the editor.

## Rollback Plan
- Stop the UI and MCPO services; backend services (M1–M7) remain unaffected. Keep the data volume
  unless the user explicitly requests deletion.

## Troubleshooting
- CORS/endpoint config, model list empty, volume/permission issues, port conflicts.

## Documentation to Update
- `docs/setup/08-ui.md`.

## Testing
- Perform chat, RAG query, and agent task through the UI; verify persistence.

## STOP
Output **"Milestone M8 complete"**, list files, confirm validation, then **STOP** and wait for approval.
