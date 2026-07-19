# Model Profiles (`models/`)

> Seed notes from [Phase 04 — Feasibility Study](../docs/phases/04-feasibility-study.md).
> **Documentation only — no code.** Exact model tags/licenses are verified at selection (Phase 06)
> and validated by benchmarks in milestone **M1**.

These notes describe **which local models to run per hardware profile** and why. The primary
development machine is CPU-only with 32 GB RAM (profile **"A+"**) — see
[`docs/setup/environment.md`](../docs/setup/environment.md).

## Files

| File | Purpose |
|------|---------|
| [`profile-a-cpu.md`](profile-a-cpu.md) | Small laptop (16 GB CPU) **and** the primary "A+" machine (32 GB CPU-only) |
| [`profile-b-gpu.md`](profile-b-gpu.md) | Mid-range workstation (consumer GPU, 12–16 GB VRAM) |
| [`profile-cd-server.md`](profile-cd-server.md) | High-end workstation / home server (≥24 GB VRAM, always-on) |
| [`embedding-models.md`](embedding-models.md) | Embedding models for local RAG |

## Defaults at a glance (primary "A+" machine)

| Role | Model | Quant |
|------|-------|:-----:|
| General assistant | Qwen2.5 7B Instruct | Q4_K_M (→ Q5_K_M if latency OK) |
| Coding specialist | Qwen2.5-Coder 7B | Q4_K_M |
| Reasoning (optional) | Phi-4 / DeepSeek-R1 distill ~7–8B | Q4_K_M |
| Embeddings | nomic-embed-text | — |
| Draft / speculative | Llama 3.2 1B / SmolLM2 | Q4_K_M |

> Rationale, trade-offs, and per-profile alternatives are in the linked files and the
> [feasibility study](../docs/phases/04-feasibility-study.md).
