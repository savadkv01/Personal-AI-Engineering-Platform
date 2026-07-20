# M4 Benchmarks — Retrieval Quality (recall@k)

> Anchor: [M4 milestone](../../implementation/M4-rag-pipeline.md) ·
> [ADR 0007](../../docs/adr/0007-reference-stack.md) ·
> [ADR 0009](../../docs/adr/0009-vector-store-and-memory.md)
>
> **Measured, not invented.** Every number here comes from [`eval.py`](eval.py) run
> against the live M3 index. Raw JSON per run lives in [`results/`](results/).

## What is measured

| Metric | Definition | Source |
|--------|-----------|--------|
| recall@k | Fraction of labeled questions whose **expected source file** appears in the top-k retrieved chunks | [`eval.py`](eval.py) over [`qa.yaml`](qa.yaml) |
| top score | Cosine score of the best chunk per question | Qdrant `search` |
| citation accuracy (`--answers`) | Fraction of questions whose grounded answer cites the expected source | full query path |

Retrieval-only by default (fast, deterministic); pass `--answers` to also generate
grounded answers and check citations (slow on CPU).

## How to run

```bash
# M3 index must be populated first:
docker compose --profile ingest run --rm ingest knowledge --scope global --tags paiep,seed

# Retrieval recall@k (JSON):
docker compose --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py --json

# Include answer-citation accuracy (slow):
docker compose --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py --answers
```

## Environment

| Field | Value |
|-------|-------|
| Machine | HP EliteBook 840 G7 — Intel Core i7-10610U (4C/8T), 32 GB RAM, CPU-only |
| OS / runtime | Windows 11 + WSL2 · Docker Desktop 29.6.1 / Compose v2 |
| Retrieval | Qdrant v1.12.6 (`kb_docs`, Cosine, dim 768) |
| Embeddings | Ollama 0.6.2 · `nomic-embed-text` |
| Profile | A+ (32 GB RAM, CPU-only) |

## Results

Labeled set: 5 questions over the seed corpus ([`qa.yaml`](qa.yaml)); `k = 4`
(config `top_k`).

| Set | Questions | k | recall@k |
|-----|-----------|---|----------|
| seed corpus | 5 | 4 | **1.0** (5/5) |

Per-question top score (2026-07-20): 0.691 / 0.710 / 0.722 / 0.636 / 0.734.
Every expected source appeared in the top-k. Raw JSON:
[`results/`](results/).

**Reading the numbers.** recall@4 = 1.0 on a small, unambiguous seed corpus is
expected and confirms the retrieval path (query embedding → filtered Qdrant
search) is wired correctly end-to-end — it is **not** a claim about production
recall. Grow [`qa.yaml`](qa.yaml) and the corpus (and add harder distractors) to
turn this into a meaningful regression signal in Phase 11.
