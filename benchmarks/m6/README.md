# M6 Benchmarks — Agent Routing & Chain Latency

> Anchor: [M6 milestone](../../implementation/M6-agents.md) · [ADR 0008](../../docs/adr/0008-agent-orchestration.md) ·
> [Setup 06](../../docs/setup/06-agents.md)
>
> **Measured, not invented.** Numbers come from [`route_eval.py`](route_eval.py) and from task traces via
> [`summarize.py`](summarize.py), run on the live stack. Raw JSON lives in [`results/`](results/).

## What is measured

| Metric | Source | Definition |
|--------|--------|-----------|
| routing accuracy | `route_eval.py` over [`routes.yaml`](routes.yaml) | first planned specialist == labeled persona |
| planner latency | `route_eval.py` | wall time of one supervisor planning call (cold vs. prompt-cache warm) |
| chain latency | `summarize.py <task_id>` | machine time per task (excludes the human approval wait), per-agent calls/tokens/seconds |
| prompt processing | direct Ollama probe | cold prompt tokens/s on the reference CPU |

```bash
cd docker
docker compose --profile agents run --rm --entrypoint python agents /workspace/benchmarks/m6/route_eval.py
docker compose --profile agents run --rm --no-deps --entrypoint python agents \
  /workspace/benchmarks/m6/summarize.py <task_id> [...] --save
```

## Environment

| Field | Value |
|-------|-------|
| Machine | HP EliteBook 840 G7 — i7-10610U (4C/8T), 32 GB RAM, CPU-only |
| Runtime | Windows 11 + WSL2 · Docker Desktop 29.6.1 · Ollama 0.6.2 (`OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=8192`) |
| Model | `qwen2.5-coder:7b` (Q4_K_M) for every tier (only model installed on Profile A+) |
| Path | agents → gateway (`/v1`, JSON-schema output) → Ollama |

## Results (2026-11-01)

### Routing (8 labeled tasks, 5 enabled specialists)

| Planner prompt | Accuracy | Planner latency |
|----------------|----------|-----------------|
| v1: catalog of goals + "use reviewer only when asked" | **0.625** (5/8) | cold 89.5 s · warm 13.6–29.6 s |
| v2: catalog with "Use for: <keywords>" + 6 few-shot examples (config) | **1.0** (8/8) | cold 102.6 s · warm 12.4–17.4 s (median 15.9 s) |

v1 misrouted "draft an ADR" and "review the changes" to `software_engineer`, and a README summary to
`architect`. Few-shot examples live in the cached system prompt, so they cost tokens only on the first
(cold) call; the eval set is disjoint from the examples.

### Prompt processing on the reference CPU

| Probe | Result |
|-------|--------|
| 2,487-token cold prompt (single slot) | 389 s → **≈ 6.4 tokens/s** |
| ~4,200-token prompt via gateway | did not finish within the 600 s gateway timeout |
| Same-prefix follow-up (cache hit) | 1,527 tokens in 2.9 s (only the new suffix is processed) |
| Generation (M1) | ≈ 3.5 tokens/s |

M1's 64-token benchmark repeated an identical prompt, so it measured cached, not cold, prompt processing.
**Every 1,000 cold prompt tokens costs ~2.5 minutes** on this machine — the dominant M6 design constraint.

### Task chains

| Task | Status | Calls | Prompt / output tokens | Machine time | Slowest call |
|------|--------|-------|------------------------|--------------|--------------|
| Grounded answer, `--agent architect` | completed | 2 | 1,314 / 198 | **156 s** | 113 s |
| Code + test + README, v1 runtime | rejected by human | 8 | 7,316 / 1,370 | 1,041 s | 243 s |
| Code + test + README, v2 runtime | **completed** | 6 | 5,916 / 1,008 | **1,065 s (17.8 min)** | 242 s |

Per agent (v2): supervisor 115 s (cold) · software_engineer 261 s (2 calls) · documentation_writer 242 s ·
reviewer 219 s · security 225 s. All calls stayed below the 600 s gateway timeout.

v1 → v2 changes driven by the v1 run: requested-file tracking + deterministic gate checks, proposals visible
to later builders, docs salvage, test-target validation, reviewers without tool turns (−2 calls).

## Reading the numbers

- On Profile A+ a single grounded agent answer takes **~2–3 minutes**; a full build → document → review →
  security chain takes **~15–20 minutes** before approval. That is acceptable for background tasks with a
  human approval step, not for interactive chat (use M4 RAG for that).
- Latency is dominated by **cold prompt processing**; keeping prompts small and prefix-stable matters more
  than output caps. GPU profiles (B–D) remove most of this cost.
- A 7B model is a **weak reviewer**: in v1 both gate reviewers passed an obviously broken regex. M6
  therefore relies on deterministic checks + human approval, not on model review alone (see M6 results).
