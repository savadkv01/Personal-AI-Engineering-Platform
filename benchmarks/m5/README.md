# M5 Benchmarks — Memory Service

> Anchor: [M5 milestone](../../implementation/M5-memory.md) ·
> [ADR 0009](../../docs/adr/0009-vector-store-and-memory.md) ·
> [Setup 05](../../docs/setup/05-memory.md)
>
> **Measured, not invented.** Every number comes from [`bench.py`](bench.py) run against the live
> stack. Raw JSON per run lives in [`results/`](results/).

## What is measured

| Metric | Definition |
|--------|-----------|
| `write_ms_p50/p95` | Latency of `remember()` — the SQL insert only; embedding runs on the async worker |
| `write_plus_async_sync_total_s` | Wall time to write all memories **and** drain the vector outbox |
| `hit_at_k` | Fraction of labeled queries whose expected memory is in the top-k (scope-isolated) |
| `negative_false_positives` | Off-topic queries that recalled anything (threshold sanity) |
| `recall_ms_p50/p95` | End-to-end recall latency (embed query + vector search + SQL hydrate) under N concurrent threads |
| `consistent_after` | `check()` — SQL store and vector index agree after the run |

The run uses an isolated scope (`project:m5-bench`) and **deletes everything it creates**.

## How to run

```bash
cd docker
docker compose --profile memory run --rm --entrypoint python memory /app/benchmarks/m5/bench.py
# options: --k 3 --threads 4 --rounds 3 --json --no-save
```

## Environment

| Field | Value |
|-------|-------|
| Machine | HP EliteBook 840 G7 — i7-10610U (4C/8T), 32 GB RAM, CPU-only |
| Runtime | Windows 11 + WSL2 · Docker Desktop 29.6.1 / Compose v2 |
| Stores | Postgres 16.14 (`paiep_db`) + Qdrant v1.12.6 (`memory_semantic`, Cosine, dim 768) |
| Embeddings | Ollama 0.6.2 · `nomic-embed-text` |
| Profile | A+ |

## Results (2026-10-31)

Labeled set: 10 memories / 10 queries / 3 negatives ([`memories.yaml`](memories.yaml)); `k = 3`,
`score_threshold = 0.5`, 4 concurrent recall threads × 3 rounds.

| Metric | Value |
|--------|-------|
| hit@3 | **1.0** (10/10) |
| negative false positives | **0 / 3** |
| write latency p50 / p95 | **4.0 ms / 13.1 ms** (non-blocking) |
| write + async vector sync (10 items) | 1.47 s |
| recall latency p50 / p95 (4 threads) | 357 ms / 1544 ms |
| recall throughput | 6.6 req/s |
| consistent after run | ✅ |

Single-threaded interactive recall measured 44–106 ms during validation; the p95 under load is
dominated by Ollama **serialising embedding requests on CPU** (Profile A+). On Profile B–D the
embedding call — not Postgres/Qdrant — is what speeds up.

**Threshold calibration.** With `nomic-embed-text`, relevant memories scored **0.51–0.79**, unrelated
ones **≤ 0.42** — hence `recall.score_threshold: 0.5`. The weakest true match
("does the platform need internet access?" → 0.507) sits close to the line: paraphrase-heavy queries
may need 0.45, at the cost of more noise. Re-measure when the embedding model changes.

**Reading the numbers.** A small, distinct labeled set confirms wiring and calibration end-to-end; it
is not a production recall claim. Grow [`memories.yaml`](memories.yaml) with near-miss distractors in
Phase 11.
