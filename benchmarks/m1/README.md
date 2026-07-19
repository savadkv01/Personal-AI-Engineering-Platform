# M1 Benchmarks — Local CPU Inference

> Anchor: [M1 milestone](../../implementation/M1-llm-runtime.md) ·
> [ADR 0004](../../docs/adr/0004-default-model-selection.md) ·
> [ADR 0007](../../docs/adr/0007-reference-stack.md)
>
> **Measured, not invented.** Every number here comes from [`bench.py`](bench.py)
> run on the primary machine. Raw JSON per run lives in [`results/`](results/).

## What is measured

| Metric | Definition | Source |
|--------|-----------|--------|
| First-token latency (TTFT) | Wall-clock from request send to first streamed token | `bench.py` stream timing |
| Throughput (tokens/s) | `eval_count / eval_duration` | Ollama `/api/generate` metrics |
| Prompt eval / load time | Prompt ingest + model load durations | Ollama metrics |
| Peak RAM | Max `MemUsage` of `paiep_ollama` sampled during the run | `docker stats` |

Median across `--runs` (default 3, after `--warmup` 1) is reported; warm-up
excludes cold model load from the steady-state numbers.

## How to run

```bash
# Stack + models must be up first:
docker compose --profile gateway up -d
scripts/pull-models.sh

# Benchmark the default chat model (reads CHAT_MODEL from docker/.env):
benchmarks/m1/run-bench.sh
# or explicitly:
benchmarks/m1/run-bench.sh qwen2.5-coder:7b 3
```

## Environment

| Field | Value |
|-------|-------|
| Machine | HP EliteBook 840 G7 — Intel Core i7-10610U (4C/8T), 32 GB RAM, CPU-only |
| OS / runtime | Windows 11 + WSL2 (Ubuntu 22.04) · Docker Desktop 29.1.3 / Compose v2 |
| Runtime | Ollama 0.6.2 (container `paiep_ollama`), llama.cpp backend |
| Profile | A+ (32 GB RAM, CPU-only) |

## Results

Default prompt (see `bench.py`): a small Python coding task, generation capped
at 200 tokens per run (`--num-predict 200`); 1 warm-up + 3 measured runs.
Throughput is Ollama's `eval_count / eval_duration` (pure generation rate).

| Model | Median tokens/s | Median TTFT (s) | Peak RAM (MiB) |
|-------|-----------------|-----------------|----------------|
| qwen2.5-coder:7b (Q4_K_M) | 3.58 | 0.388 | 5081 |

Per-run (2026-07-19): 3.58 / 3.45 / 3.69 tok/s; TTFT 0.278 / 0.388 / 0.482 s.
Raw JSON: [`results/`](results/). Warm-up cold-load was ~75 s (excluded from
steady-state); warm TTFT is sub-second thanks to `OLLAMA_KEEP_ALIVE`.

**Reading the numbers.** ~3.5 tok/s is the honest steady-state for a 7B Q4_K_M
model on this CPU-only i7-10610U (4 physical cores, all saturated at ~400 %)
inside Docker Desktop/WSL2 (RAM capped at ~15.5 GiB by the default WSL config).
It confirms the [ADR 0004](../../docs/adr/0004-default-model-selection.md)
premise that **interactive latency — not memory — is the binding constraint**:
short prompts feel responsive (sub-second TTFT), but long generations are slow.
Levers: smaller/draft models, `Q4` over `Q5`, speculative decoding, more WSL
cores/RAM, or GPU (Profiles B–D).

