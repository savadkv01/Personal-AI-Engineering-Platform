# ADR 0004: Default Local Model Selection

- **Status:** Accepted (defaults; re-validate with M1 benchmarks and at Phase 06)
- **Date:** 2026-07-19

## Context
The [Phase 04 feasibility study](../phases/04-feasibility-study.md) compared open coding and
reasoning model families (Qwen, Llama, Gemma, Mistral, Phi, Granite, DeepSeek, StarCoder2,
CodeLlama, DeepCoder, SmolLM2) against the platform's constraints. The primary machine is
**CPU-only with 32 GB RAM** (profile "A+" — see [environment.md](../setup/environment.md)), where the
binding constraint is **interactive latency**, not memory. The platform must be **offline-first,
model-agnostic, and prefer permissive licenses** (see [ADR 0002](0002-offline-first-priority.md),
[ADR 0003](0003-build-vs-adopt.md)).

We need documented **default models** to build against now, without locking the platform to them.

## Decision
Adopt the following **defaults for the primary "A+" machine**, all as **GGUF via Ollama**:

1. **General assistant:** **Qwen2.5 7B Instruct** @ **Q4_K_M** (step to Q5_K_M if latency allows).
2. **Coding specialist:** **Qwen2.5-Coder 7B** @ **Q4_K_M**.
3. **Reasoning (optional):** Phi-4 or a DeepSeek-R1 distill (~7–8B) @ Q4_K_M.
4. **Embeddings:** **nomic-embed-text**.
5. **Draft / speculative:** Llama 3.2 1B / SmolLM2.
6. **Default quantization:** **Q4_K_M** for interactive use; Q5_K_M when quality matters and RAM allows.
7. **Per-profile scaling** (A / B / C-D) is documented in [`models/`](../../models/) and the feasibility study.
8. **Model-agnostic requirement stands:** defaults are swappable via config; nothing hard-codes a model.

Rationale: Qwen2.5 / Qwen2.5-Coder lead open coding/reasoning at 7B, have **permissive licenses**
(Apache-2.0, ⚠ verify per size), and strong GGUF/Ollama support — the best quality-vs-latency balance
on CPU. Fallbacks (Mistral 7B, Granite 3 8B, Llama 3.2 3B) are documented.

## Alternatives Considered
- **Codestral (22B):** excellent coder, but **MNPL license is non-production** → rejected as default.
- **CodeLlama / StarCoder2:** viable but generally surpassed by Qwen2.5-Coder for chat-style coding.
- **Gemma 2/3:** strong quality, but **custom Gemma license** needs review → kept as alternative.
- **Llama 3.x as primary:** good, but license has usage terms; Apache-licensed Qwen preferred as default.
- **13–14B as interactive default:** better quality but too slow for interactive CPU use → "stretch" only.
- **DeepSeek-Coder-V2 (MoE):** heavy on CPU; revisit with GPU/home-server.

## Consequences
**Benefits**
- Clear, permissively licensed defaults that fit the CPU-only machine with headroom.
- Consistent baseline for building memory/RAG/agents and for M1 benchmarking.
- Model-agnostic design preserved; easy to upgrade as families evolve.

**Drawbacks**
- Local 7–8B quality is below cloud frontier models (accepted per offline-first goals).
- Qualitative rankings await **measured M1 benchmarks** for confirmation.
- Fast model churn means defaults must be revisited periodically.

**Follow-ups**
- Measure tokens/s, first-token latency, coding eval, and RAG recall on the primary machine in **M1**.
- Re-verify exact model tags and licenses in **Phase 06** before adoption.
- Add speculative decoding (draft + target) to improve CPU throughput.
- Re-evaluate larger/MoE models once a GPU/home server exists (ADR 0100 / Phase 12).

## M1 Measured Results (2026-07-19)

First measured numbers on the primary machine (i7-10610U, CPU-only, Docker Desktop/WSL2),
via [`benchmarks/m1/`](../../benchmarks/m1/README.md). Ollama **0.6.2**, 200-token runs.

| Model | Quant | Median tok/s | Median TTFT | Peak RAM |
|-------|-------|--------------|-------------|----------|
| `qwen2.5-coder:7b` | Q4_K_M | 3.58 | 0.388 s | 5081 MiB |

**Findings (confirm the decision):**
- Warm **TTFT is sub-second** — short, interactive prompts feel responsive.
- Steady **~3.5 tok/s** generation confirms the premise that **interactive latency, not memory,
  is the binding constraint** on this machine (peak RAM ~5 GiB ≪ the WSL-capped ~15.5 GiB).
- The single `qwen2.5-coder:7b` default served both chat and coding cleanly and answered a
  RAG query end-to-end in the M1 spike. Defaults **stand**; revisit throughput levers
  (draft/speculative decoding, more WSL cores/RAM, or GPU on Profiles B–D).
