# M7 — VS Code Integration

> **Milestone:** M7 · **Layer:** Experience · **Anchor:** O6, O7,
> [Phase 09](../docs/phases/09-vscode-integration.md), [ADR 0010](../docs/adr/0010-vscode-integration-strategy.md) ·
> **Prompt:** [`.github/prompts/implementation/M7-vscode-integration.prompt.md`](../.github/prompts/implementation/M7-vscode-integration.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** Developer Experience Architect + DevOps

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M7 is explicitly requested.

---

## Objectives & Scope

Deliver the **first-class VS Code experience** against the **shared backend** ([Phase 09](../docs/phases/09-vscode-integration.md)):
**Continue** (assist) + **Cline** (agent), the **MCP servers**, and a **template/cookiecutter** for
one-command workspace setup (O7).

**In scope**
- **MCP servers** ([Phase 09 §3](../docs/phases/09-vscode-integration.md)): **fs**, **git**, **rag**,
  **memory**, **paiep-tools** — local, offline, least-privilege ([ADR 0006](../docs/adr/0006-security-model.md)).
- **Continue + Cline** config targeting the gateway `http://127.0.0.1:8080/v1`; autocomplete on a draft tier.
- **Template repo / cookiecutter** distributing `.vscode/` settings, `extensions.json`, MCP declarations,
  client rules, and `.github/` instructions/prompts (secrets in git-ignored `.env`, NFR-022).
- **Copilot coexistence** guidance (one inline provider per workspace; disable on sensitive repos).

**Out of scope:** UI (M8), observability (M9), hardening/release (M10).

## Prerequisites

- **M6** (agents/orchestrator) and **M1** (gateway) complete — MCP servers bridge to them; RAG (M4) and
  memory (M5) are exposed as MCP tools.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| MCP servers (fs/git/rag/memory/paiep-tools) | `integration/mcp/` |
| Continue + Cline config templates | `templates/vscode/.vscode/`, client rules |
| Template repo / cookiecutter | `templates/workspace/` |
| Setup doc | `docs/setup/07-vscode-integration.md` |

## Validation Checklist

- [ ] Continue chat/autocomplete works against the gateway (offline).
- [ ] Cline performs a bounded multi-file task via MCP tools with approvals.
- [ ] Each MCP server enforces its scope (path-scoped fs, no-push git default, read-only scoped rag,
      user-deletable memory, opt-in shell/container).
- [ ] Cookiecutter scaffolds a new workspace pointing at the shared backend in one command.
- [ ] Copilot + PAIEP coexist without inline-provider collisions.
- [ ] **Offline smoke:** editor flows work with network disabled.

## Rollback Strategy

- Disable/uninstall MCP servers and remove client config — backend (M1–M6) unaffected.
- Template repo is additive; scaffolded workspaces are independent and removable.
- Revert `templates/`, `integration/mcp/` via `git restore`.

## Documentation to Produce

- MCP surface + client setup + cookiecutter usage in `docs/setup/07-vscode-integration.md`;
  confirm [ADR 0010](../docs/adr/0010-vscode-integration-strategy.md).
- Re-verify client/MCP versions at this milestone ([Phase 09](../docs/phases/09-vscode-integration.md)).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Functional | Continue chat + autocomplete | grounded responses / completions |
| Integration | Cline task via MCP | bounded, approved multi-file edit |
| Safety | disallowed fs/git action | blocked by MCP scope |
| Repeatability | cookiecutter new workspace | one-command working setup |
| Offline | disable network | success |

## Troubleshooting Notes

- **Endpoint mismatch:** all clients must target `127.0.0.1:8080/v1`; autocomplete may use Ollama-native.
- **Inline-provider collision:** enable only one completion provider per workspace; disable Copilot on sensitive repos.
- **MCP feature drift:** pin client versions; run capability checks.
- **Config drift across workspaces:** regenerate from the cookiecutter rather than hand-editing.

## Hardware Profiles

- **A:** draft tier for autocomplete; single agent.
- **A+:** full Continue + Cline against local backend.
- **B/C:** faster completions/agents with GPU.
- **D:** shared backend serves many workspaces over LAN
  ([ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md), Phase 12).
