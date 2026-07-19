# Personal AI Engineering Platform (PAIEP)

> An enterprise-grade, open-source, offline-first Personal AI Engineering Platform that runs primarily on a local laptop and evolves into a personal AI operating system.

[![Status](https://img.shields.io/badge/status-architecture--phase-blue)]()
[![Phases](https://img.shields.io/badge/phases-10%2F12%20drafted-blue)]()
[![License](https://img.shields.io/badge/license-TBD-lightgrey)]()
[![Offline First](https://img.shields.io/badge/offline-first-success)]()
[![Open Source](https://img.shields.io/badge/stack-open--source-brightgreen)]()

---

## 1. What Is This?

PAIEP is a **design-first** project. Before any code is written, the platform is
fully architected, documented, and planned through a sequence of **12 gated phases**.
Each phase produces professional Markdown documentation, Mermaid diagrams, technology
comparisons, Architecture Decision Records (ADRs), and one or more **reusable, independently
executable prompt files**.

The end goal is a modular, local-first AI platform that can act as an AI Software Engineer,
Data Engineer, Solution Architect, Technical Writer, Research Assistant, and more —
comparable in ambition to GitHub Copilot Agent while remaining fully open and extensible.

---

## 2. Guiding Principles

| Principle | Meaning |
|-----------|---------|
| **Offline first** | Everything possible runs locally; cloud is optional. |
| **Open source** | Prefer permissively licensed, community-backed tools. |
| **Modular** | Components are swappable without redesigning the platform. |
| **Documented** | Every decision is recorded with why / benefits / drawbacks / alternatives. |
| **Beginner friendly** | Clear onboarding, validation checklists, rollback plans. |
| **Future proof** | Ready to expand into robotics, EO, ROS2, Kubernetes, fine-tuning. |
| **Reversible** | Each implementation step can be rolled back safely. |

---

## 3. Phase Roadmap (Gated)

> **Rule:** Implementation does **not** begin until architecture is approved. Each phase
> must finish and be approved before the next begins.

| # | Phase | Status | Deliverables |
|---|-------|--------|--------------|
| 01 | Project Vision | ✅ Drafted | [docs](docs/phases/01-project-vision.md) · [prompt](.github/prompts/01-project-vision.prompt.md) |
| 02 | Requirements Analysis | ✅ Drafted | [docs](docs/phases/02-requirements-analysis.md) · [prompt](.github/prompts/02-requirements-analysis.prompt.md) |
| 03 | Market Research | ✅ Drafted | [docs](docs/phases/03-market-research.md) · [prompt](.github/prompts/03-market-research.prompt.md) |
| 04 | Feasibility Study (Models) | ✅ Drafted | [docs](docs/phases/04-feasibility-study.md) · [prompt](.github/prompts/04-feasibility-study.prompt.md) |
| 05 | Enterprise Architecture | ✅ Drafted | [docs](docs/phases/05-enterprise-architecture.md) · [prompt](.github/prompts/05-enterprise-architecture.prompt.md) |
| 06 | Technology Selection | ✅ Drafted | [docs](docs/phases/06-technology-selection.md) · [prompt](.github/prompts/06-technology-selection.prompt.md) |
| 07 | Agent Ecosystem | ✅ Drafted | [docs](docs/phases/07-agent-ecosystem.md) · [prompt](.github/prompts/07-agent-ecosystem.prompt.md) |
| 08 | Knowledge & Memory Architecture | ✅ Drafted | [docs](docs/phases/08-knowledge-memory.md) · [prompt](.github/prompts/08-knowledge-memory.prompt.md) |
| 09 | VS Code Integration | ✅ Drafted | [docs](docs/phases/09-vscode-integration.md) · [prompt](.github/prompts/09-vscode-integration.prompt.md) |
| 10 | Implementation Roadmap | ✅ Drafted | [docs](docs/phases/10-implementation-roadmap.md) · [prompt](.github/prompts/10-implementation-roadmap.prompt.md) |
| 11 | Testing & Benchmarking | ⏳ | — |
| 12 | Future Roadmap | ⏳ | — |

> **Implementation is split into milestones.** Phase 10 is delivered as small, reversible
> milestone prompts (M0 → M10) in
> [.github/prompts/implementation/](.github/prompts/implementation/README.md), each with its own
> validation checklist and rollback plan. These run only after the architecture is approved.

---

## 4. Repository Structure

```text
Personal-AI-Engineering-Platform/
├── .github/
│   └── prompts/          # Executable, independent prompt files (01..12)
│       └── implementation/   # Milestone prompts (M0..M10)
├── docs/
│   ├── phases/           # Full documentation per phase
│   ├── adr/              # Architecture Decision Records
│   └── setup/            # Environment & tuning notes
├── architecture/         # Diagrams and architecture artifacts
├── implementation/       # Milestone specs, validation, rollback plans (M0..M10)
├── docker/               # Compose files and container definitions
├── config/               # Model registry and platform configuration
├── scripts/              # Bootstrap and model-pull helper scripts
├── memory/               # Long-term & session memory design/artifacts
├── agents/               # Agent definitions and collaboration specs
├── knowledge/            # Knowledge base, notes, book library index
├── rag/                  # RAG pipelines and configuration
├── models/               # Model profiles, quantization notes
├── benchmarks/           # Evaluation harnesses and results
└── experiments/          # Scratch / research experiments
```

---

## 5. Target Environment

- **IDE:** VS Code
- **OS:** Linux · WSL2 · Ubuntu
- **Containers:** Docker · Docker Compose
- **Execution:** Local first, cloud optional

### Hardware Profiles

| Profile | Spec | Intended Use |
|---------|------|--------------|
| A | 16 GB RAM, CPU only | Entry laptop |
| B | 32 GB RAM, consumer GPU | Prosumer laptop/desktop |
| C | Workstation | Heavy local development |
| D | Home Server | Always-on multi-agent host |

> **Primary target machine (detected):** HP EliteBook 840 G7 · i7-10610U (4C/8T) · 32 GB RAM ·
> Intel UHD integrated GPU only (**CPU-only inference**) · WSL2 + Docker Desktop. It is an
> **"A+" hybrid** (Profile B's RAM, Profile A's compute). Full details and tuning:
> [docs/setup/environment.md](docs/setup/environment.md).

---

## 6. How to Use the Prompt Files

Each file in `.github/prompts/` is **self-contained** and can be executed independently
against an AI agent. They encode the role, context, tasks, output standards, and stop
conditions for that phase.

---

## 7. Architecture Decision Records (ADRs)

Key decisions are recorded in [docs/adr/](docs/adr/):

| ADR | Decision |
|-----|----------|
| [0001](docs/adr/0001-design-first-gated-phases.md) | Design-first, gated phases |
| [0002](docs/adr/0002-offline-first-priority.md) | Offline-first priority |
| [0003](docs/adr/0003-build-vs-adopt.md) | Build vs. adopt — integrate building blocks |
| [0004](docs/adr/0004-default-model-selection.md) | Default local model selection |
| [0005](docs/adr/0005-container-topology.md) | Container topology (one Compose stack, two networks) |
| [0006](docs/adr/0006-security-model.md) | Security model (local-first + least-privilege tools) |
| [0007](docs/adr/0007-reference-stack.md) | Reference technology stack |
| [0008](docs/adr/0008-agent-orchestration.md) | Agent orchestration (supervisor/router) |
| [0009](docs/adr/0009-vector-store-and-memory.md) | Vector store & memory architecture |
| [0010](docs/adr/0010-vscode-integration-strategy.md) | VS Code integration strategy |
| [0011](docs/adr/0011-delivery-milestones.md) | Delivery milestones (M0–M10) |
| [0100](docs/adr/0100-gpu-and-reuse-strategy.md) | GPU acceleration & multi-workspace reuse |

---

## 8. Current Status

**Phases 01–10 are drafted** (architecture complete through the implementation roadmap),
each with documentation, Mermaid diagrams, and ADRs. Phase 10 breaks delivery into small,
reversible milestones (M0–M10) with per-milestone specs in
[implementation/](implementation/) and prompts in
[.github/prompts/implementation/](.github/prompts/implementation/README.md). **Milestone
execution awaits approval** before any implementation begins. No further phases start
automatically.
