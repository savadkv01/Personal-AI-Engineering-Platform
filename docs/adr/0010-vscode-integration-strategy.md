# ADR 0010: VS Code Integration Strategy

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
[Phase 09 — VS Code Integration](../phases/09-vscode-integration.md) designs the developer experience for
using PAIEP inside VS Code (objective **O6**), against a **shared backend serving many workspaces** (**O7**),
**offline-first** (NFR-010), and the CPU-only primary machine (CON-001). [Phase 03 §5](../phases/03-market-research.md)
and [Phase 06 §13](../phases/06-technology-selection.md) identified open, Apache-2.0, offline-capable clients
(**Continue**, **Cline**, **Roo Code**) and **MCP** as the standard tool bridge. GitHub Copilot (cloud) is
already used by the operator and must **coexist** without conflict. We must decide the client mix, the MCP
surface, the Copilot boundary, and the workspace-config approach.

## Decision
1. **Client pair:** adopt **Continue** (inline assist + autocomplete + chat) and **Cline** (agentic
   multi-file/repo tasks) as the default; **Roo Code** is a documented **alternative to Cline**, not a third
   concurrently-installed agent.
2. **Single OpenAI-compatible endpoint:** all clients target the **gateway** at
   `http://127.0.0.1:8080/v1` (loopback, [ADR 0005](0005-container-topology.md)); autocomplete may use a
   small/draft model tier ([ADR 0004](0004-default-model-selection.md)).
3. **MCP servers to expose:** **fs**, **git**, **rag**, **memory**, and **paiep-tools** — all local, offline,
   and enforcing the [ADR 0006](0006-security-model.md) least-privilege model (path-scoped fs, no-push git by
   default, read-only scoped rag, user-deletable memory, opt-in shell/container). Actions require approval and
   are traced (Langfuse).
4. **Copilot coexistence, not replacement:** PAIEP for private/offline/zero-cost/multi-persona-RAG work;
   Copilot for frontier-quality public-code suggestions. Enforce **one inline completion provider per
   workspace**; **disable Copilot on sensitive workspaces**; optionally use Copilot **BYOK → local endpoint**
   where supported (⚠ verify).
5. **Workspace config via template/cookiecutter (M7):** distribute `.vscode/` settings + `extensions.json` +
   MCP declarations + client rules + `.github/` instructions/prompts per repo, all pointing at the shared
   backend. Secrets in `.env` (git-ignored), never in settings/prompts (NFR-022).

## Alternatives Considered
- **Build a bespoke VS Code extension.** Full control, but high build/maintenance cost; violates
  "integrate, don't build" ([ADR 0003](0003-build-vs-adopt.md)). **Rejected** (revisit only if a real gap appears).
- **Single client for everything (Continue-only or Cline-only).** Simpler, but Continue's agentic and Cline's
  autocomplete stories are each weaker; the pair covers both interaction modes. **Rejected.**
- **Install Cline + Roo Code together.** Doubles agentic tooling/config with little gain and RAM cost.
  **Rejected** (Roo is an either/or alternative).
- **Direct REST from clients to services (bypass MCP).** Simpler wiring, but bypasses centralized guardrails
  and couples clients to internals. **Rejected** in favor of MCP.
- **Copilot-only or PAIEP-only.** Copilot-only loses privacy/offline/cost; PAIEP-only loses frontier quality.
  **Rejected** in favor of coexistence.

## Consequences
**Benefits**
- Covers both interaction modes (fast inline assist + agentic repo work) with maintained, permissive clients.
- One endpoint + shared MCP servers → consistent tools/context across clients and workspaces (O7, NFR-024).
- Centralized guardrails/tracing via orchestrator + MCP; privacy boundary explicit vs. Copilot.
- Zero build cost; scales to a Profile-D backend transparently.

**Drawbacks**
- Multiple extensions to configure and keep in sync (mitigated by the template/cookiecutter).
- MCP is young; per-client feature support varies (pin versions; capability checks).
- Agentic chains are slow on CPU (bound chains; draft/coding tiers; GPU/Profile-D path).
- Two AI systems (PAIEP + Copilot) require config discipline to avoid inline-provider collisions.

**Follow-ups**
- Build the **template repo / cookiecutter** and a small **custom MCP server** for PAIEP tools (M7).
- Verify **Copilot BYOK → local endpoint** support before relying on it.
- Re-evaluate **Roo Code vs. Cline** after hands-on use; consolidate on one agent.
- Add **health/status** editor integration and latency dashboards (Phase 11).
- Pin client versions + MCP capabilities at M7.
