# PAIEP Phase Prompts

Each file here is a **self-contained, independently executable** prompt for one gated phase
of the Personal AI Engineering Platform. Repo-wide behavior is defined in
[`../copilot-instructions.md`](../copilot-instructions.md).

## How to run a phase

1. Open the prompt file for the phase you want (e.g., `01-project-vision.prompt.md`).
2. Run it as a prompt (VS Code: run the `.prompt.md`, or paste its contents into your agent).
3. The agent produces that phase's docs/diagrams/ADRs, then **STOPS** for your approval.
4. Approve, then run the next phase's prompt.

> **Gating rule:** phases run one at a time. Nothing auto-continues. No implementation code
> is written until the architecture is approved (Phase 10+).

## Index

| # | Prompt | Focus |
|---|--------|-------|
| 01 | [01-project-vision.prompt.md](01-project-vision.prompt.md) | Vision, personas, principles |
| 02 | [02-requirements-analysis.prompt.md](02-requirements-analysis.prompt.md) | FR/NFR, constraints, MoSCoW |
| 03 | [03-market-research.prompt.md](03-market-research.prompt.md) | Existing OSS AI platforms |
| 04 | [04-feasibility-study.prompt.md](04-feasibility-study.prompt.md) | Model comparison per profile |
| 05 | [05-enterprise-architecture.prompt.md](05-enterprise-architecture.prompt.md) | All architecture views |
| 06 | [06-technology-selection.prompt.md](06-technology-selection.prompt.md) | Stack per layer + reference arch |
| 07 | [07-agent-ecosystem.prompt.md](07-agent-ecosystem.prompt.md) | Agents, collaboration, memory |
| 08 | [08-knowledge-memory.prompt.md](08-knowledge-memory.prompt.md) | RAG, vector DB, memory, indexing |
| 09 | [09-vscode-integration.prompt.md](09-vscode-integration.prompt.md) | Continue/Cline/Roo/MCP/Copilot |
| 10 | [10-implementation-roadmap.prompt.md](10-implementation-roadmap.prompt.md) | Milestones, validation, rollback |
| 11 | [11-testing-benchmarking.prompt.md](11-testing-benchmarking.prompt.md) | Eval framework |
| 12 | [12-future-roadmap.prompt.md](12-future-roadmap.prompt.md) | Multi-year expansion |

## Implementation milestones (Phase 10 breakdown)

Phase 10 is delivered as a series of small, reversible milestone prompts. See
[`implementation/README.md`](implementation/README.md) for the full index and dependency graph.
Run them **only after** the architecture is approved, one milestone at a time (M0 → M10).
