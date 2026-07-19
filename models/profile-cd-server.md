# Profile C/D — High-end Workstation / Home Server

> ≥24 GB VRAM, always-on. Source: [Phase 04 feasibility study](../docs/phases/04-feasibility-study.md).
> Tags/licenses ⚠ verify at Phase 06. Aligns with the home-AI-server path in
> [ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md).

## What this profile unlocks
- **30B-class** quantized models on a single 24 GB GPU; **70B** on large/multi-GPU.
- **vLLM** for high concurrency — several personas served simultaneously.
- Always-on shared backend for all workspaces (Profile D roadmap).

## Recommendations

| Role | Model | Quant | Notes |
|------|-------|:-----:|-------|
| General | Qwen2.5 32B (72B on big/multi-GPU) | Q4_K_M / Q5_K_M | ~19–20 GB weights @ Q4 for 32B |
| Coding | Qwen2.5-Coder 32B | Q4_K_M | Top open coding quality |
| Reasoning | DeepSeek-R1 (larger distills / full where feasible) | Q4_K_M | Heavy reasoning tasks |
| Embeddings | mxbai-embed-large / nomic-embed-text | — | Higher-quality retrieval |

## Serving notes
- Prefer **vLLM** (PagedAttention, continuous batching) for throughput and multi-user concurrency.
- Laptop becomes a **thin client** to shared LAN endpoints.
- Design the topology and reuse model in **Phase 12 / milestone M7**.
