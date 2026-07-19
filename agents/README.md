# Agents — Seed Specifications

> Declarative **seed specs** for PAIEP's multi-agent ecosystem. Design-only (Markdown now; CrewAI
> YAML later). Full narrative, collaboration, communication, and memory design live in
> [`docs/phases/07-agent-ecosystem.md`](../docs/phases/07-agent-ecosystem.md).

## Roster

| # | Agent | Persona(s) | Model tier | Spec |
|---|-------|-----------|-----------|------|
| 0 | Supervisor / Planner | orchestration | reasoning→general | [supervisor.md](supervisor.md) |
| 1 | Architect | P3, P4 | reasoning | [architect.md](architect.md) |
| 2 | Data Engineer | P2 | coding | [data-engineer.md](data-engineer.md) |
| 3 | Software Engineer | P1 | coding | [software-engineer.md](software-engineer.md) |
| 4 | AI Engineer | P14 | coding+reasoning | [ai-engineer.md](ai-engineer.md) |
| 5 | Documentation Writer | P5, P6 | general | [documentation-writer.md](documentation-writer.md) |
| 6 | Reviewer | P11 | coding+reasoning | [reviewer.md](reviewer.md) |
| 7 | Refactoring Agent | P1 | coding | [refactoring-agent.md](refactoring-agent.md) |
| 8 | Testing Agent | P1, P14 | coding | [testing-agent.md](testing-agent.md) |
| 9 | DevOps Agent | P13 | coding | [devops-agent.md](devops-agent.md) |
| 10 | Security Agent | P12 | reasoning | [security-agent.md](security-agent.md) |
| 11 | Learning Coach | P7 | general | [learning-coach.md](learning-coach.md) |
| 12 | Research Assistant | P8 | general+reasoning | [research-assistant.md](research-assistant.md) |
| 13 | Knowledge Manager | P9 | general+embed | [knowledge-manager.md](knowledge-manager.md) |
| 14 | Project Planner | P10, P4 | reasoning→general | [project-planner.md](project-planner.md) |

## Spec template

Each spec records: **Mission · Persona map · Responsibilities · Inputs → Outputs · Tools
(allow-list) · Model tier · Guardrails · Success criteria · Stack mapping**. Tool taxonomy, model
tiers, and guardrails are defined in [Phase 07 §1](../docs/phases/07-agent-ecosystem.md#1-how-to-read-this-document)
and [ADR 0006](../docs/adr/0006-security-model.md); orchestration in
[ADR 0008](../docs/adr/0008-agent-orchestration.md).
