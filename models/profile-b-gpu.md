# Profile B — Mid-range Workstation (Consumer GPU)

> 32 GB RAM + consumer GPU (~12–16 GB VRAM). Source:
> [Phase 04 feasibility study](../docs/phases/04-feasibility-study.md). Tags/licenses ⚠ verify at Phase 06.

## What the GPU unlocks
- Larger models fully in VRAM with **much higher throughput** than CPU.
- **vLLM** becomes a viable high-throughput serving option (CUDA).
- Longer contexts and multiple concurrent personas become practical.

## Recommendations

| Role | Model | Quant | Notes |
|------|-------|:-----:|-------|
| General | Qwen2.5 14B | Q4_K_M / Q5_K_M | Fits ≥12 GB VRAM; use 7B for max speed |
| Coding | Qwen2.5-Coder 14B | Q4_K_M | Strong open coder |
| Reasoning | DeepSeek-R1 distill 14B / Phi-4 | Q4_K_M | Reasoning-focused |
| Embeddings | nomic-embed-text / bge-base | — | CPU or GPU |

## Notes
- **VRAM ≥ 12 GB** is the key threshold (runs 7B–13B fully on GPU) per [ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md).
- Keep CPU-only fallbacks configured so the platform still works if the GPU is unavailable (offline-first).
