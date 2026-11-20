# M7 — VS Code Integration

> **Milestone:** M7 · **Layer:** Experience · **Anchor:** O6, O7,
> [Phase 09](../docs/phases/09-vscode-integration.md), [ADR 0010](../docs/adr/0010-vscode-integration-strategy.md) ·
> **Prompt:** [`.github/prompts/implementation/M7-vscode-integration.prompt.md`](../.github/prompts/implementation/M7-vscode-integration.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented; editor UI validation pending · **Author role:** Developer Experience Architect + DevOps

> ✅ Core servers, policy, containers and workspace template are implemented. Continue/Cline UI and a successful approved agent write remain unverified; see [Execution Results](#execution-results-2026-11-20).

---

## Objectives & Scope

Deliver the **first-class VS Code experience** against the **shared backend** ([Phase 09](../docs/phases/09-vscode-integration.md)):
**Continue** (assist) + **Cline** (agent), the **MCP servers**, and a **template/cookiecutter** for
one-command workspace setup (O7).

**In scope**
- **MCP servers** ([Phase 09 §3](../docs/phases/09-vscode-integration.md)): **fs**, **git**, **rag**,
  **memory**, **paiep-tools** — local, offline, least-privilege ([ADR 0006](../docs/adr/0006-security-model.md)).
- **Continue + Cline** config targeting the gateway `http://127.0.0.1:8081/v1`; autocomplete uses a small base/FIM model.
- **Template repo / cookiecutter** distributing `.vscode/` settings, `extensions.json`, MCP declarations,
  client rules, and `.github/` instructions/prompts (secrets in git-ignored `.env`, NFR-022).
- **Copilot coexistence** guidance (one inline provider per workspace; disable on sensitive repos).

**Out of scope:** UI (M8), observability (M9), hardening/release (M10).

## Prerequisites

- **M6** (agents/orchestrator) and **M1** (gateway) complete — MCP servers bridge to them; RAG (M4) and
  memory (M5) are exposed as MCP tools.

## Deliverables

| Artifact | Path (built) |
|----------|----------------|
| MCP servers (fs/git/rag/memory/paiep-tools) | [`integration/mcp/`](../integration/mcp/) |
| Continue + Cline/Roo config templates | [`templates/workspace/`](../templates/workspace/) |
| Template repo / cookiecutter | [`templates/workspace/`](../templates/workspace/) |
| Setup doc | [`docs/setup/07-vscode-integration.md`](../docs/setup/07-vscode-integration.md) |

## Validation Checklist

- [x] Local chat completion works through the authenticated gateway; autocomplete model responds through Ollama's native API (offline).
- [ ] Continue chat/autocomplete works inside VS Code — no Continue extension is installed in this environment.
- [ ] Cline performs an approved multi-file task via MCP tools. A live task reached M6's review gate but was blocked by the Security Agent; no files were applied.
- [x] Each MCP server enforces its scope (path-scoped fs, no-push git default, read-only scoped rag,
      user-deletable memory, opt-in shell/container).
- [x] Cookiecutter scaffolds workspaces for default, sensitive (Copilot disabled) and Roo variants; generated JSON/YAML parses.
- [x] Workspace config selects one inline provider; Copilot MCP is opt-in because it exposes tool results to the cloud model.
- [x] **Offline smoke:** MCP servers are egress-blocked; all five passed stdio discovery, allowed reads and policy-denial probes.

## Execution Results (2026-11-20)

Reference machine: Windows 11 / Docker Desktop 29.9.3 / WSL2; host Python 3.13 dev venv; Docker image uses Python 3.11. Active Ollama model: `qwen2.5-coder:7b`; autocomplete: `qwen2.5-coder:1.5b-base`. On this machine the gateway is host port **8081**, and Ollama is **11435** (11434 is occupied by a host Ollama).

| Check | Result |
|-------|--------|
| MCP SDK + image | Python MCP SDK **2.3.0** pinned; shared image built successfully |
| Discovery | All five MCP servers launched by the same `docker-compose run --rm -T` path used by clients; 24 tools registered across the two editor processes |
| Scope / safety | Secret and traversal reads denied; writes are proposal→apply with stale-file conflict check and atomic replace; denied files are excluded from every git pathspec (including directory/`.` paths); RAG scope is enforced; disallowed memory writes/deletes are denied; agent tasks are bound to their workspace + scope; free-text audit arguments are hashed; no git commit/push tools |
| Live backend | `rag_search`, `memory_list`, `agent_personas` work through stdio MCP. Memory remember→forget round-trip succeeds. Authenticated gateway `/v1/chat/completions` returned `OK`; Ollama autocomplete model responded on the configured port |
| Cookiecutter | Default, sensitive (Copilot disabled), and Roo variants generated; JSON/YAML validated; project paths and project scope resolved |
| Offline / egress | Both MCP container types report `Network is unreachable` to external IPs. fs/git run with `network_mode: none`; backend MCP uses the internal Compose network |
| Tests / lint / docs | **156 passed, 1 skipped** (MCP tests incl. review regressions, plus existing suites); Ruff clean; Markdown link checker: 0 broken links; live Docker smoke re-run after the review fixes: all 5 servers PASS, audit shows memory content hashed |
| Agent workflow | `agent_run`/`agent_status` ran through MCP. The representative multi-file task reached the M6 security gate and was **blocked by a security veto**; no proposal was approved or written. This demonstrates the existing M6 gate, but is not a successful approved-write test. |
| VS Code UI | Not run: Continue/Cline/Roo extensions are not installed in the current VS Code environment |

**Notes / deviations**
- Two grouped stdio processes (fs+git with no network; rag+memory+paiep-tools on the internal network) are the default, rather than five container launches per client.
- M7 adds an optional `include_global` flag to the RAG answer API; existing callers retain the previous default (`false`).
- Copilot's `.vscode/mcp.json` is checked in for this public repository; the cookiecutter emits it only with explicit `copilot_mcp=yes`.
- **Review fixes (2026-11-20):** a code review found and fixed a reproduced `git_diff` secret leak (a directory/`.` path skipped the deny excludes), cross-workspace agent task access (status/approve/reject by bare id — B could apply A's proposals), and plaintext short audit arguments (memories/queries survived `memory_forget`). Also: atomic writes, no rewrite of non-UTF-8 files, git hooks disabled, Windows host alias guards, a log-handle leak in `agent_run`, and a non-existent `--host` flag in the docs. Each has a regression test in `tests/test_mcp.py`. See the [ADR 0010 amendment](../docs/adr/0010-vscode-integration-strategy.md#amendment--m7-implementation-2026-11-20).

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

- **Endpoint mismatch:** all clients target `127.0.0.1:8081/v1` by default (or `GATEWAY_HOST_PORT`); autocomplete uses Ollama-native (`OLLAMA_HOST_PORT`).
- **Inline-provider collision:** enable only one completion provider per workspace; disable Copilot on sensitive repos.
- **MCP feature drift:** pin client versions; run capability checks.
- **Config drift across workspaces:** regenerate from the cookiecutter rather than hand-editing.

## Hardware Profiles

- **A:** draft tier for autocomplete; single agent.
- **A+:** full Continue + Cline against local backend.
- **B/C:** faster completions/agents with GPU.
- **D:** shared backend serves many workspaces over LAN
  ([ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md), Phase 12).
