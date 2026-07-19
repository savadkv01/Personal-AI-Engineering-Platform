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
Deploy a local web UI (per Phase 06, e.g., Open WebUI / AnythingLLM / custom) connected to the
LLM runtime, RAG, memory, and agents — for use outside the editor.

## Prerequisites
- M1 (runtime), M4 (RAG), M5 (memory), M6 (agents) running.
- Phase 06 UI decision and Phase 09 UX considerations.

## Scope
- **In:** UI service in Compose, connection to runtime + PAIEP APIs, basic auth for local use.
- **Out:** public exposure / remote access hardening (M10).

## Tasks
1. Add the UI service to `docker/compose.yaml` with a persistent volume for its config/data.
2. Connect the UI to the M1 endpoint and PAIEP RAG/memory/agent APIs.
3. Configure conversations, model selection, and RAG/agent access in the UI.
4. Add simple local authentication (single-user) and document access.

## Deliverables
- Updated `docker/compose.yaml`; `docs/setup/08-ui.md`.

## Validation Checklist
- [ ] UI is reachable locally and lists available local models.
- [ ] A chat completes through the UI using the local runtime (offline).
- [ ] RAG-grounded and agent-driven responses work from the UI.
- [ ] UI settings/data persist across restarts.

## Expected Outputs
- A usable local UI for chatting, RAG, and running agents without the editor.

## Rollback Plan
- Remove the UI service and its volume; backend services (M1–M7) unaffected.

## Troubleshooting
- CORS/endpoint config, model list empty, volume/permission issues, port conflicts.

## Documentation to Update
- `docs/setup/08-ui.md`.

## Testing
- Perform chat, RAG query, and agent task through the UI; verify persistence.

## STOP
Output **"Milestone M8 complete"**, list files, confirm validation, then **STOP** and wait for approval.
