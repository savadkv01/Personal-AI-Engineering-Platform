# Profile A / A+ — CPU-only Models

> Small laptop (16 GB, CPU) and the **primary "A+" machine** (32 GB RAM, CPU-only).
> Source: [Phase 04 feasibility study](../docs/phases/04-feasibility-study.md). Tags/licenses ⚠ verify at Phase 06.

## Constraint
CPU-only inference. The limiting factor is **interactive latency**, not RAM. Prefer **Q4_K_M**;
step to **Q5_K_M** only if first-token/throughput stays acceptable. Keep headroom on the ~24 GB
WSL allocation for KV-cache + services.

## Profile A — 16 GB laptop (also the floor)

| Role | Model | Quant | Approx. weights |
|------|-------|:-----:|:---------------:|
| General | Llama 3.2 3B / Qwen2.5 3B | Q4_K_M | ~2 GB |
| Coding | Qwen2.5-Coder 3B | Q4_K_M | ~2 GB |
| Draft | SmolLM2 1.7B / Llama 3.2 1B | Q4_K_M | <1 GB |

Avoid models >7B on a 16 GB machine.

## Profile A+ — 32 GB CPU-only (PRIMARY, build first) ⭐

| Role | Model | Quant | Approx. weights |
|------|-------|:-----:|:---------------:|
| **General (default)** | **Qwen2.5 7B Instruct** | Q4_K_M (→ Q5_K_M) | ~4.5–5 GB |
| **Coding (default)** | **Qwen2.5-Coder 7B** | Q4_K_M | ~4.5 GB |
| Reasoning (optional) | Phi-4 / DeepSeek-R1 distill ~7–8B | Q4_K_M | ~5 GB |
| Draft / speculative | Llama 3.2 1B / SmolLM2 | Q4_K_M | <1 GB |
| Embeddings | nomic-embed-text | — | small |

**Stretch (non-interactive):** 13–14B @ Q4_K_M (~8–9 GB weights) for higher quality when you can wait.

## Why these
- **Permissive licenses** where possible (Qwen2.5/Qwen2.5-Coder Apache-2.0 ⚠, Mistral Apache-2.0,
  Granite Apache-2.0, Phi MIT) reduce legal risk vs. custom-licensed options.
- Strong **GGUF + Ollama** support; easy to pull and swap.
- 7–8B Q4 gives the best **quality-vs-latency** balance on this CPU.

## Alternatives
- Mistral 7B / Granite 3 8B (permissive, efficient) as general/coding swaps.
- Gemma 2/3 (strong quality) — note the **custom Gemma license** ⚠.

> Benchmarks (tokens/s, first-token latency, coding/RAG quality) to be measured in **M1**.
