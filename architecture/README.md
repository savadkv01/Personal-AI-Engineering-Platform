# Architecture Diagrams — Index

> Central index of PAIEP architecture diagrams. Diagrams are authored as **Mermaid** inside the
> phase documents (so they render on GitHub and stay in sync with their narrative) and referenced
> here for reuse. As diagrams stabilize they may be exported to `.svg`/`.png` in this folder.

## Enterprise Architecture (Phase 05)

Full narrative + diagrams: [`docs/phases/05-enterprise-architecture.md`](../docs/phases/05-enterprise-architecture.md)

| # | View | Diagram type | Source (section) |
|---|------|--------------|------------------|
| 1 | Logical Architecture | flowchart | [Phase 05 §2](../docs/phases/05-enterprise-architecture.md#2-view-1--logical-architecture) |
| 2 | Physical Architecture | flowchart | [Phase 05 §3](../docs/phases/05-enterprise-architecture.md#3-view-2--physical-architecture) |
| 3 | Deployment Architecture | flowchart | [Phase 05 §4](../docs/phases/05-enterprise-architecture.md#4-view-3--deployment-architecture) |
| 4 | Security Architecture | flowchart | [Phase 05 §5](../docs/phases/05-enterprise-architecture.md#5-view-4--security-architecture) |
| 5 | AI Architecture | flowchart | [Phase 05 §6](../docs/phases/05-enterprise-architecture.md#6-view-5--ai-architecture) |
| 6 | Knowledge Architecture | flowchart | [Phase 05 §7](../docs/phases/05-enterprise-architecture.md#7-view-6--knowledge-architecture) |
| 7 | Data Flow | sequence | [Phase 05 §8](../docs/phases/05-enterprise-architecture.md#8-view-7--data-flow-request--response--memory) |
| 8 | Agent Collaboration | flowchart | [Phase 05 §9](../docs/phases/05-enterprise-architecture.md#9-view-8--agent-collaboration-high-level) |

## Related decisions

- [ADR 0005 — Container Topology](../docs/adr/0005-container-topology.md)
- [ADR 0006 — Security Model](../docs/adr/0006-security-model.md)
- [ADR 0100 — GPU & Reuse Strategy](../docs/adr/0100-gpu-and-reuse-strategy.md)

## Conventions

- Author diagrams in Mermaid inside the relevant phase/ADR doc.
- Mark **optional/future** edges (cloud, GPU, LAN) with dashed styling.
- Keep node labels short; put detail in the accompanying tables.
