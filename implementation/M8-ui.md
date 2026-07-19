# M8 — User Interface

> **Milestone:** M8 · **Layer:** Experience · **Anchor:** O6 (optional web client),
> [Phase 05 §2](../docs/phases/05-enterprise-architecture.md) ·
> **Prompt:** [`.github/prompts/implementation/M8-ui.prompt.md`](../.github/prompts/implementation/M8-ui.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** Software Engineer

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M8 is explicitly requested.

---

## Objectives & Scope

Deploy a **local web UI** (per [Phase 06](../docs/phases/06-technology-selection.md), e.g. **Open WebUI** /
AnythingLLM) wired to the runtime, RAG, memory, and agents — a client for use **outside the editor**.

**In scope**
- UI service in Compose (behind a profile) with a **persistent volume** for config/data.
- Connect to the M1 gateway endpoint and the PAIEP **RAG (M4) / memory (M5) / agent (M6)** APIs.
- Conversations, **model selection**, and RAG/agent access configured in the UI.
- **Simple local (single-user) auth**; documented access.

**Out of scope:** observability (M9); public exposure / remote-access hardening (M10).

## Prerequisites

- **M1** (runtime), **M4** (RAG), **M5** (memory), **M6** (agents) running.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| UI service (Compose profile) | `docker/docker-compose.yml` |
| UI config + persistent volume | `docker/ui/` |
| Setup doc | `docs/setup/08-ui.md` |

## Validation Checklist

- [ ] UI is reachable on loopback and lists available local models.
- [ ] A chat completes through the UI using the local runtime (**offline**).
- [ ] RAG-grounded and agent-driven responses work from the UI.
- [ ] UI settings/data **persist** across restarts.
- [ ] Local auth gates access; no `0.0.0.0` exposure.

## Rollback Strategy

- Disable the `ui` Compose profile and `down` the service; core stack (M1–M6) is unaffected.
- Remove the UI volume (non-critical config/history) — reversible.
- Revert `docker/ui/` and Compose additions via `git restore`.

## Documentation to Produce

- UI setup, model selection, RAG/agent wiring, and local-auth notes in `docs/setup/08-ui.md`.

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Smoke | open UI, list models | models visible |
| Functional | chat via UI | response via local runtime |
| Integration | RAG + agent query via UI | grounded / agent-driven answer |
| Persistence | restart, reopen | settings/history retained |
| Offline | disable network | success |

## Troubleshooting Notes

- **UI can't reach runtime:** use the container network name/gateway URL, not `localhost` inside containers.
- **No models listed:** confirm the M1 endpoint + API compatibility.
- **RAM pressure:** UI is optional on Profile A — enable transiently.
- **Auth misconfig:** verify single-user credentials in `.env` (git-ignored).

## Hardware Profiles

- **A:** UI optional; enable when needed.
- **A+:** run alongside the stack within the RAM budget.
- **B/C:** comfortable continuously.
- **D:** shared UI for multiple users over LAN (with M10 hardening).
