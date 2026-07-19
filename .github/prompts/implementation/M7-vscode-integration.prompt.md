---
mode: agent
description: "Implementation M7 — VS Code integration: Continue/Cline/Roo + MCP servers exposing PAIEP tools; Copilot coexistence. Reversible."
---

# Implementation Milestone M7 — VS Code Integration

> **Precondition:** M6 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **Developer Experience Engineer** wiring PAIEP into VS Code.

## Objective
Connect VS Code assistants (Continue / Cline / Roo Code) to the local runtime and expose PAIEP
capabilities (RAG, memory, agents, git) via **MCP servers**, coexisting with GitHub Copilot.

## Prerequisites
- M1 (runtime), M4 (RAG), M5 (memory), M6 (agents) running.
- Phase 09 integration design and MCP server plan.

## Scope
- **In:** assistant configuration, MCP server(s) for filesystem/git/RAG/memory/agents,
  `.vscode/` workspace config, coexistence guidance.
- **Out:** end-user UI (M8).

## Tasks
1. Configure Continue/Cline/Roo to use the local M1 endpoint and selected models.
2. Implement/expose **MCP servers** for PAIEP tools (RAG query, memory, agent tasks, git, fs).
3. Add recommended `.vscode/settings.json`, `extensions.json`, and prompt/instructions files.
4. Document **Copilot coexistence** (when to use which; privacy boundaries).
5. Provide per-profile (A–D) guidance on what runs comfortably in-editor.

## Deliverables
- MCP server config/code; `.vscode/` recommendations; `docs/setup/07-vscode-integration.md`.

## Validation Checklist
- [ ] An assistant completes a prompt using the local model (offline).
- [ ] MCP tools are discoverable and callable from the VS Code client.
- [ ] A RAG/memory/agent action works through the editor.
- [ ] Copilot and PAIEP coexist without conflicts.

## Expected Outputs
- In-editor access to local models plus PAIEP RAG/memory/agent tools via MCP.

## Rollback Plan
- Remove MCP server config and revert `.vscode/` changes; backend services (M1–M6) unaffected.

## Troubleshooting
- MCP server not detected, auth/port issues, model endpoint mismatch, extension version conflicts.

## Documentation to Update
- `docs/setup/07-vscode-integration.md`; `.vscode/` docs.

## Testing
- Exercise each MCP tool from the editor; confirm offline operation.

## STOP
Output **"Milestone M7 complete"**, list files, confirm validation, then **STOP** and wait for approval.
