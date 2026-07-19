# ADR 0007: Reference Technology Stack

- **Status:** Accepted (defaults; re-verify licenses/versions at pinning and validate in M1)
- **Date:** 2026-07-19

## Context
[Phase 06 — Technology Selection](../phases/06-technology-selection.md) compared open-source options
for every platform layer against the MoSCoW **Musts** ([Phase 02](../phases/02-requirements-analysis.md)),
under the constraints of a **CPU-only, 32 GB** primary machine (CON-001, [environment.md](../setup/environment.md)),
**offline-first** (NFR-010/011), **permissive licenses** (CON-003), and **modularity** (NFR-023/024).
The strategy is fixed by [ADR 0003](0003-build-vs-adopt.md): **integrate best-in-class building blocks**
behind a thin, model-agnostic layer, not build engines. This ADR records the chosen **end-to-end stack**.

## Decision
Adopt the following **reference stack** (all local, offline-capable, permissively licensed unless flagged ⚠):

| Layer | Choice | Fallback / future |
|-------|--------|-------------------|
| LLM runtime | **Ollama** (on **llama.cpp**) | LocalAI; **vLLM** for GPU (Profiles B–D) |
| Agent framework | **LangGraph** (control) + **CrewAI** (personas) | — (AutoGen rejected: maintenance mode) |
| RAG orchestration | **LlamaIndex** | txtai (minimal); LangChain |
| Embeddings | **nomic-embed-text** | bge-small; mxbai-embed-large |
| Vector DB | **Qdrant** | pgvector (consolidate); Chroma (spike) |
| Memory | **PostgreSQL** (state/structured) + **Qdrant** (semantic) | SQLite (Profile A) |
| Workflow orchestration | **None now** (LangGraph handles agent flows) | Prefect (scheduled jobs) |
| Monitoring | **Langfuse** (LLM tracing) + optional Prometheus/Grafana | — |
| Logging | **Structured JSON stdout → OpenTelemetry** | Loki |
| Security | **[ADR 0006](0006-security-model.md) model** (`.env`/secrets, gateway token, loopback, tool sandbox) | Vault (future) |
| UI | **Open WebUI** (optional; VS Code is primary) | AnythingLLM |
| VS Code | **Continue** + **Cline**, bridged via **MCP** | Roo Code |

**Binding contract:** all components communicate via the **OpenAI-compatible API** at the gateway seam,
so models/runtimes/clients remain hot-swappable (O2/FR-002, [Phase 05 §2.2](../phases/05-enterprise-architecture.md#2-view-1--logical-architecture)).

## Alternatives Considered
- **vLLM as the primary runtime:** GPU-centric; poor fit on a CPU-only machine → **future** (B–D) only.
- **AutoGen as the agent foundation:** in **maintenance mode** (Phase 03) → rejected; LangGraph+CrewAI chosen.
- **Single agent library:** simpler but couples control and ergonomics; the layered pair keeps both clean.
- **pgvector-only (no Qdrant):** fewer engines, but weaker payload filtering for RAG+memory → kept as the
  consolidation **fallback**, not the default.
- **Heavyweight workflow engine (Temporal/Airflow):** over-engineering for one user → deferred (Prefect if needed).
- **Custom VS Code extension / custom UI:** violates "integrate, don't build" ([ADR 0003](0003-build-vs-adopt.md)) → rejected.
- **All-in-one platform (AnythingLLM/Dify) as core:** sacrifices modularity/multi-persona → reference/front-end only.

## Consequences
**Benefits**
- Coherent, permissively licensed, **offline-first** stack that runs on the primary machine today.
- Modular and swappable via the OpenAI-API seam (NFR-023/024); resilient to any single project's decline.
- Reuses mature clients (Continue/Cline) and engines (Ollama/LlamaIndex/Qdrant) — effort focused on glue + personas.
- Clear per-profile (A–D) scale-up path without redesign.

**Drawbacks**
- Multiple dependencies to track for license/maintenance (⚠ Open WebUI branding, Grafana/Loki AGPL, n8n).
- Two data engines (Qdrant + Postgres) to keep consistent (or consolidate to pgvector on Profile A).
- Two agent libraries require a disciplined role split (LangGraph=control, CrewAI=personas).
- CPU latency bounds multi-agent depth until a GPU/home server exists.

**Follow-ups**
- Validate the stack with the **M1 integration spike** (Ollama + LlamaIndex + Qdrant + Continue) in Phase 10.
- Pin exact **versions + SPDX license IDs** in a licenses-of-record file at first implementation.
- Re-verify ⚠ terms (Open WebUI branding, Grafana/Loki AGPL, Langfuse non-core, n8n) before enabling those components.
- Define **persona configs + tool policies** (Phase 07) and **memory scope/retention** (Phase 08 / M5).
- Add the **vLLM / Profile-D** Compose overrides ([ADR 0005](0005-container-topology.md), [ADR 0100](0100-gpu-and-reuse-strategy.md)).
