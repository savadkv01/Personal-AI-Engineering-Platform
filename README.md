# Personal AI Engineering Platform (PAIEP)

> An enterprise-grade, open-source, offline-first Personal AI Engineering Platform that runs primarily on a local laptop and evolves into a personal AI operating system.

[![Status](https://img.shields.io/badge/status-architecture--phase-blue)]()
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
| 02 | Requirements Analysis | ⏳ Pending approval of 01 | — |
| 03 | Market Research | ⏳ | — |
| 04 | Feasibility Study (Models) | ⏳ | — |
| 05 | Enterprise Architecture | ⏳ | — |
| 06 | Technology Selection | ⏳ | — |
| 07 | Agent Ecosystem | ⏳ | — |
| 08 | Knowledge & Memory Architecture | ⏳ | — |
| 09 | VS Code Integration | ⏳ | — |
| 10 | Implementation Roadmap | ⏳ | — |
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
├── docs/
│   ├── phases/           # Full documentation per phase
│   └── adr/              # Architecture Decision Records
├── architecture/         # Diagrams and architecture artifacts
├── implementation/       # Milestone specs, validation, rollback plans
├── docker/               # Compose files and container definitions
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

## 7. Current Status

**Phase 01 (Project Vision) is drafted and awaiting your approval.**
No further phases will be started automatically.
