# ADR 0003: Build vs. Adopt — Integrate Open-Source Building Blocks

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
The [Phase 03 market research](../phases/03-market-research.md) surveyed local LLM runtimes, agent
frameworks, RAG stacks, VS Code assistants, and all-in-one platforms. Findings:

- Mature, permissively licensed building blocks exist for every individual capability
  (e.g., Ollama/llama.cpp, LangGraph/CrewAI, LlamaIndex/txtai, Continue/Cline).
- **No single tool** delivers PAIEP's full combination: a machine-wide **shared backend** serving
  **many workspaces**, an opinionated **multi-persona** roster sharing **long-term memory + KB**,
  **CPU-first/offline/zero-cost** by default, and a **design-first, documented, gated** approach.
- All-in-one platforms (Open WebUI, AnythingLLM, Dify) are powerful but bundle opinionated choices
  that would compromise modularity (NFR-023) and the multi-persona goal.

We must decide the overall strategy: **build from scratch**, **adopt one platform wholesale**, or
**integrate building blocks**.

## Decision
**Integrate best-in-class open-source building blocks behind PAIEP's own thin, modular layer.**

1. **Adopt** proven components for each capability (runtime, agents, RAG, editor client, vector DB),
   preferring **MIT/Apache-licensed, actively maintained** projects (CON-003).
2. **Standardize on the OpenAI-compatible API** as the internal lingua franca so models, runtimes,
   and clients are hot-swappable (O2 / FR-002 / NFR-024).
3. **Build only the differentiators:** the integration/glue, opinionated **engineering personas**,
   a **shared memory + knowledge service**, guardrails, and the **shared-backend + template-config**
   reuse model (O7).
4. **Reuse an existing VS Code client** (e.g., Continue/Cline) rather than building a bespoke
   extension, unless a gap forces otherwise (O6).
5. **Treat all-in-one platforms as optional front-ends/references**, not the core.
6. **Avoid** closed-source cores (e.g., LM Studio) and **maintenance-mode** foundations
   (e.g., AutoGen) without a clear exit/adapter plan.

## Alternatives Considered
- **Build everything from scratch.** Maximum control, but wasteful, slow, and reinvents mature
  engines. **Rejected.**
- **Adopt one all-in-one platform wholesale** (e.g., AnythingLLM/Dify). Fast to value, but sacrifices
  modularity, multi-persona design, and the shared-backend model; risks licensing terms.
  **Rejected as the core** (kept as optional front-end).
- **Adopt a single framework ecosystem** (e.g., LangChain-only). Convenient, but couples PAIEP to one
  vendor's roadmap and abstractions. **Rejected** in favor of adapters/modularity.
- **Integrate building blocks (chosen).** Balances speed, control, modularity, and offline/cost goals.

## Consequences
**Benefits**
- Fast progress by standing on mature engines; effort focused on real differentiators.
- Modular and swappable (NFR-023/024); resilient to any single project's decline.
- Stays offline-first, CPU-first, and zero-cost by default.

**Drawbacks**
- Integration/glue and version-compatibility become PAIEP's ongoing responsibility.
- Multiple dependencies to track for license/maintenance changes.
- Requires disciplined adapter boundaries to preserve swappability.

**Follow-ups**
- Convert the survey into a **weighted decision matrix** and make concrete selections in **Phase 06**.
- Record an SPDX **licenses-of-record** table at selection time.
- Validate the "integrate, don't build" thesis with a small **Ollama + LlamaIndex + Continue** spike
  in **Phase 04 / M1**.
- Re-verify licensing for ⚠-flagged tools (Dify, Flowise, Open WebUI) before adoption.
