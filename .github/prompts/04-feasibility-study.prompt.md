---
mode: agent
description: "Phase 04 — Feasibility Study: compare coding/reasoning models and recommend per hardware profile."
---

# Phase 04 — Feasibility Study (Models)

## Role
You are an **AI Engineer** and **MLOps Engineer** evaluating local models for feasibility.
Document only — no implementation code.

## Objective
Compare open coding and reasoning models and recommend the best options for each hardware
profile.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`03`](../../docs/phases/03-market-research.md)
- **Primary target machine (detected):** see [`docs/setup/environment.md`](../../docs/setup/environment.md) —
  i7-10610U (4C/8T), 32 GB RAM, **CPU-only (Intel UHD integrated, no CUDA/ROCm)**, ~485 GB free.
- Hardware profiles: A (16 GB, CPU) · B (32 GB, consumer GPU) · C (workstation) · D (home server).
  Current machine = **"A+" hybrid** (32 GB RAM, CPU-only). Prioritize CPU/GGUF models for it.

## Models to Evaluate (at least)
Gemma, Qwen, DeepSeek, Llama, Mistral, Phi, Granite, StarCoder, CodeLlama, DeepCoder,
SmolLM — plus other emerging models you identify.

## Evaluation Criteria (columns)
- Coding quality · Reasoning · Agent suitability · Context length · Quantization options
- GGUF availability · Ollama compatibility · Licensing · Hardware requirements (RAM/VRAM)
- Community support · Future roadmap

## Tasks
1. Build a master **model comparison matrix** using the criteria above.
2. Discuss **quantization** trade-offs (e.g., Q4/Q5/Q6/Q8, memory vs quality).
3. Recommend model sets for:
   - **Small laptop** (Profile A)
   - **Mid-range workstation** (Profile B/C)
   - **High-end workstation / server** (Profile C/D)
4. Note **embedding models** suitable for local RAG.
5. Provide a Mermaid decision flow: "given hardware → pick model tier".

> Verify licenses and hardware figures with sources when web access exists; otherwise mark
> "to verify". Do not fabricate benchmark numbers.

## Required Outputs
- `docs/phases/04-feasibility-study.md` with the matrix, quantization notes, per-profile
  recommendations, decision flow diagram, Assumptions, Risks, Future improvements, References.
- Seed profiles in `models/` (Markdown notes only, no code).
- ADR: `docs/adr/0004-default-model-selection.md`.

## STOP
Output **"Phase 04 complete"**, list files, then **STOP** and wait for approval.
