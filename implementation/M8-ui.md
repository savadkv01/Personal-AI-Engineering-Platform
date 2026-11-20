# M8 — User Interface

> **Milestone:** M8 · **Layer:** Experience · **Anchor:** O6 (optional web client),
> [Phase 05 §2](../docs/phases/05-enterprise-architecture.md) ·
> **Prompt:** [`.github/prompts/implementation/M8-ui.prompt.md`](../.github/prompts/implementation/M8-ui.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** ✅ Complete — validated 2026-11-21 · **Author role:** Software Engineer

---

## Objectives & Scope

Deploy a **local web UI** (per [Phase 06](../docs/phases/06-technology-selection.md), e.g. **Open WebUI** /
AnythingLLM) wired to the runtime, RAG, memory, and agents — a client for use **outside the editor**.

**In scope**
- UI service in Compose (behind a profile) with a **persistent volume** for config/data.
- Connect to the M1 gateway endpoint and the PAIEP **RAG (M4) / memory (M5) / agent (M6)** APIs.
- Conversations, **model selection**, and RAG/agent access configured in the UI.
- **Simple local (single-user) auth**; documented access.
- The UI tool set must preserve human approval for file changes: agent proposals can be reviewed
  from the UI, but approve/reject are not exposed as model-callable tools.

**Out of scope:** observability (M9); public exposure / remote-access hardening (M10).

## Prerequisites

- **M1** (runtime), **M4** (RAG), **M5** (memory), **M6** (agents) running.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| UI service (Compose profile) | `docker/docker-compose.yml` |
| UI-safe MCP policy + persistent volumes | [`config/mcp-ui.yaml`](../config/mcp-ui.yaml) and `paiep_ui` / `paiep_memory` |
| Setup doc | `docs/setup/08-ui.md` |
| Decision record | [`docs/adr/0012-local-chat-ui.md`](../docs/adr/0012-local-chat-ui.md) |

## Validation Checklist

- [x] UI is reachable on loopback and lists available local models.
- [x] A chat completes through the UI using the local runtime (**offline**).
- [x] RAG-grounded and agent-driven responses work from the UI (agent changes stay pending CLI approval).
- [x] UI settings/data **persist** across restarts.
- [x] Local auth gates access; no `0.0.0.0` exposure.

## Rollback Strategy

- Stop `ui` and `paiep-tools-api`; the M1–M7 stack and all existing data remain unaffected.
- Keep the `paiep_ui` volume for a reversible rollback; deleting it removes accounts, chats and UI settings.
- Revert the `ui` Compose profile, `config/mcp-ui.yaml`, M8 docs and Make targets to remove the feature.

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

## Implementation Notes

- Phase 06's Open WebUI decision is retained. MCPO exposes the existing MCP tools over authenticated
  OpenAPI; a custom UI or duplicated RAG API was not added.
- `paiep-tools-api` is backend-only and requires `MCP_UI_API_KEY`. Its dedicated config exposes RAG,
  memory reads and agent run/status, but no file writes, memory writes/deletes, or agent
  approve/reject. M6 proposals remain gated and are approved only through the local CLI.
- Open WebUI settings (including the gateway connection and registered tool server) are configured
  once by the first admin and stored in `paiep_ui`. `WEBUI_SECRET_KEY` and `MCP_UI_API_KEY` must be
  generated separately and persisted in ignored `docker/.env`.
- See [setup](../docs/setup/08-ui.md) and [ADR 0012](../docs/adr/0012-local-chat-ui.md).

## Execution Results (2026-11-20)

Compose validation and the shared image build passed. MCPO starts in its isolated MCP 1.x
environment with FastAPI pinned to 0.115.12; PAIEP's MCP 2.3.0 runtime remains unchanged.

The authenticated MCPO OpenAPI endpoint returned 401 without a key and 200 with the configured
key. Its nine exposed operations are limited to RAG, memory reads and agent run/status/list/routing;
memory mutations and `agent_approve` / `agent_reject` are absent. The gateway returned the local
chat and embedding model list with authentication.

Open WebUI is healthy on loopback (`127.0.0.1:8083` in this local environment), its `/health`
endpoint returned 200, and the browser reached the first-admin account form. The local Ollama
embedding endpoint returned one 768-dimensional vector for `nomic-embed-text`. Open WebUI is
configured to use this local Ollama model, and no default Hugging Face embedding fetch was observed.
The existing UI volume's persisted RAG settings were updated to Ollama; account or password data
was not created or changed.

**Human setup (completed):** the user created the local admin account and configured the gateway
connection and the PAIEP tool server in Open WebUI. The results below cover chat, RAG, agent approval
and restart persistence.

**First live chat (2026-11-20):** the admin account and gateway connection were created and the
models listed. The first "who are you?" chat returned **504** after 600 s without a first token.
The default Open WebUI features made the request body over 16 KB (built-in tool schemas and memory
context). Title generation also queued a separate call on Ollama's single slot. Ollama also kept
processing the abandoned prompt. Fix: Compose now seeds CPU-friendly defaults (no
title/tag/follow-up/query generation, code interpreter, memories, Ollama connection or built-in
tools). The same settings were applied to the existing `paiep_ui` config, and Ollama was restarted.
A direct 37-token prompt through the gateway took 43 s including a cold model load. Two other
causes of failure: `GATEWAY_TOKEN` changed after the gateway was created (fixed by recreating it),
and the connection's default Responses API type (Ollama needs Chat Completions).

After the fix, a multi-turn chat in the UI completed through the gateway (HTTP 200). An attached
PNG produced a 1.1 MB base64 body, which the gateway rejected with 413. The default models are
text-only, so `DEFAULT_MODEL_METADATA` now also sets `vision: false`, and Open WebUI blocks image
attachments.

RAG through the UI: the model called `rag_search` (5 passages in 4.5 s) and then also `rag_answer`.
`rag_answer` ran a second LLM generation (3m54s) and correctly reported that the knowledge base does
not name the default model. The 7B model then failed to write a final answer, after ~18 min in total.
The UI policy now disables `rag_answer` (`answer: false`). The chat model answers from the
`rag_search` passages, and the bridge exposes 8 tools.

RAG retest: "which Docker networks does PAIEP use and why" returned a correct answer with citations,
sourced from `knowledge/notes/offline-first.md` (`edge` loopback seam, internal `backend` network).
The first `rag_search` call passed `scope: "workspace"` and was denied, and the model's retry with
`global` cost ~3.5 min. `rag_search` now treats empty/`workspace`/`default`/`current` as the
configured scope, and its description tells the model to leave `scope` empty (regression test
added).

Agent approval gate through the UI: a first task (adding a docstring to an existing file) was stopped
by M6 guardrails, which require reading a file before replacing it. With no proposal, it completed
and changed nothing. Task `7bfb53d7` asked the agent to create `knowledge/notes/ui-agent-test.md`. It
was routed to `documentation_writer` with a `reviewer` pass (no issues) and reached
`awaiting_approval` (~15 min on CPU). It showed the 2-line diff, and the file did not exist. The
user rejected it from the M6 CLI, the status changed to `rejected`, and no file was written. The UI
had no way to approve it.

Persistence: after `docker restart paiep_ui` (healthy, still bound to `127.0.0.1:8083`), the user
signed in again and confirmed that prior chats, the `http://gateway/v1` connection and its models,
and the **PAIEP** tool server were all retained in `paiep_ui`.

**Result: all M8 validation checks passed (2026-11-21).** Known limits: CPU-only replies take 30 s
to 1 min for plain chat and several minutes with tools; an agent task takes ~15 min to reach
approval. The 7B model sometimes uses tools poorly. Images need a vision model (out of scope).

**Post-validation tuning (2026-11-21):** a benchmark measured CPU prompt processing at ~5 tok/s
(1,968 tokens in ~410 s; AVX2 backend, other containers idle). A Continue agent-mode request with all
tool schemas was aborted by Continue's OpenAI client after its default 10 min and then retried. The
gateway `proxy_read_timeout` was raised from 600 s to 1800 s, and the workspace template sets
Continue `requestOptions.timeout: 1800000` (ms) to match.
