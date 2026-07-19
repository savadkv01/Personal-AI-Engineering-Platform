# M1 — LLM Runtime + Integration Spike

> **Milestone:** M1 · **Layer:** Foundation · **Anchor:** [ADR 0004](../docs/adr/0004-default-model-selection.md),
> [ADR 0007](../docs/adr/0007-reference-stack.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-07-19) · **Author role:** MLOps + Principal Software Engineer

> ✅ **Implemented.** Ollama runtime, OpenAI-compatible nginx gateway, model-pull tooling,
> a measured CPU benchmark harness, and a thin Ollama→LlamaIndex→Qdrant spike are in place and
> validated on the primary machine (see **Execution Results** below).

---

## Objectives & Scope

Stand up **local inference** and the **API gateway**, pull the **default models**, capture the **first CPU
benchmarks**, and prove a **thin end-to-end vertical slice** through the reference stack.

**In scope**
- **Ollama** service ([Phase 06 §2](../docs/phases/06-technology-selection.md)) on `127.0.0.1:11434`.
- **API Gateway** (OpenAI-compatible seam, [Phase 05 §2.2](../docs/phases/05-enterprise-architecture.md)) on
  `127.0.0.1:8080/v1`; auth + concurrency limit stubs.
- Pull **default models** ([ADR 0004](../docs/adr/0004-default-model-selection.md)): a 7–8B Q4_K_M chat/coding
  model + `nomic-embed-text`.
- **Benchmark harness** (feeds Phase 11): tokens/s, first-token latency, RAM use — **measured, not invented**.
- **Thin spike:** minimal Ollama → LlamaIndex → Qdrant → Continue path over a tiny corpus to validate the
  stack early ([ADR 0007](../docs/adr/0007-reference-stack.md)). Deep versions of the vector DB, ingestion,
  and RAG come in M2/M3/M4.

**Out of scope:** production RAG, memory, agents, full ingestion.

## Prerequisites

- **M0** complete (Compose skeleton, volumes, loopback).

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Ollama service (Compose profile) | `docker/docker-compose.yml` |
| Gateway service + config | `docker/gateway/`, `docker/docker-compose.yml` |
| Model pull script + tiers config | `scripts/pull-models.sh`, `config/models.yaml` |
| Benchmark harness + results | `benchmarks/m1/` |
| Spike script | `experiments/m1-spike/` |
| Pinned versions + results | append to [ADR 0004](../docs/adr/0004-default-model-selection.md), [ADR 0007](../docs/adr/0007-reference-stack.md) |

## Validation Checklist

- [x] `GET http://127.0.0.1:11434/api/tags` lists pulled models. → served at **:11435** on this machine (11434 taken by a native host Ollama); lists `qwen2.5-coder:7b` + `nomic-embed-text`.
- [x] `POST http://127.0.0.1:8080/v1/chat/completions` returns a valid OpenAI-shaped response. → gateway on **:8081**; returns `chat.completion` (content "Pong"), HTTP 200.
- [x] Gateway routes chat and embeddings to Ollama; concurrency limit enforced. → chat + embeddings both 200 with token; 401 without token; `limit_conn` cap = `GATEWAY_MAX_CONCURRENCY`.
- [x] Benchmarks recorded (tokens/s, first-token latency, peak RAM) for the default model on the primary machine. → see [`benchmarks/m1/README.md`](../benchmarks/m1/README.md).
- [x] Spike returns a **citation-backed** answer over the tiny corpus end-to-end. → PASS; answer cited `paiep-overview.md` + `paiep-stack.md`.
- [x] **Offline smoke:** after models are pulled, everything works with network disabled. → from the internet-isolated `backend` network: egress `HTTP 000`, gateway chat `HTTP 200`.

## Execution Results (2026-07-19)

Run on the primary machine (HP EliteBook 840 G7, i7-10610U, CPU-only) via Docker Desktop/WSL2.

| Area | Outcome |
|------|---------|
| Runtime | Ollama **0.6.2** container (`paiep_ollama`), models in `paiep_models` volume |
| Models | `qwen2.5-coder:7b` (Q4_K_M, 4.7 GB) + `nomic-embed-text` (274 MB) |
| Gateway | `nginx:1.27-alpine` seam on `127.0.0.1:8081`; bearer-token auth + `limit_conn` |
| Benchmark | median **3.58 tok/s**, TTFT **0.388 s**, peak RAM **5081 MiB** (200-token runs) |
| Spike | Ollama→LlamaIndex→Qdrant `v1.12.6`; citation-backed answer, exit 0 |
| Offline | internal `backend` network proven internet-isolated; inference still 200 |

**Deviations from the original plan (recorded):**

- **Ports:** gateway on **8081** and Ollama on **11435** (not 8080/11434). `GATEWAY_HOST_PORT=8081`
  matches the reserved-ports table in `docker/.env.example`; a **native Windows Ollama already owned
  11434**, so the container publishes 11435 to coexist. The in-container port stays 11434, so the
  gateway/spike are unaffected. All host ports remain loopback-bound.
- **Chat model:** used **`qwen2.5-coder:7b`** as the single 7B chat/coding default (ADR 0004) rather
  than a separate general model — keeps the CPU-only footprint lean for M1.
- **Throughput** (~3.5 tok/s) is lower than a bare-metal expectation: Docker Desktop/WSL2 caps RAM at
  ~15.5 GiB and exposes 4 cores (saturated at ~400 %). Interactive latency, not RAM, is the binding
  constraint — exactly as [ADR 0004](../docs/adr/0004-default-model-selection.md) predicted.
- **Spike deps:** `llama-index-readers-file` was added to the spike requirements (needed by
  `SimpleDirectoryReader`). The M0 `ping` service is still running and can now be retired.

## Rollback Strategy

- Disable the `inference`/`gateway` Compose profiles; `down` those services (M0 skeleton remains).
- Remove pulled models via `ollama rm` or delete the `models` volume (re-pullable, so reversible).
- Revert gateway config via `git restore`. No downstream data depends on M1 yet.

## Documentation to Produce

- Benchmark results table in `benchmarks/m1/README.md` (confirms/updates [ADR 0004](../docs/adr/0004-default-model-selection.md)).
- Gateway endpoint + model-tier docs; update [Phase 06 §2](../docs/phases/06-technology-selection.md) if choices shift.

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Smoke | health + `/api/tags` | model list, `200` |
| Contract | schema-check `/v1/chat/completions` | valid OpenAI payload |
| Performance | benchmark harness | recorded tokens/s + latency (no invented numbers) |
| Integration (spike) | run spike script | grounded answer with citation |
| Offline | disable network, re-run smoke/spike | success |

## Troubleshooting Notes

- **Slow first token:** model cold-load; keep model warm (`keep_alive`) or preload on startup.
- **OOM on 8B:** drop to 7B Q4_K_M or smaller context; monitor with `docker stats`.
- **Gateway 502:** confirm Ollama healthy and gateway upstream URL uses the container network name.
- **Embeddings dim mismatch:** record model+dim now for M2/M3 index catalog.

## Hardware Profiles

- **A (16 GB):** single 7B Q4_K_M; expect lower tokens/s.
- **A+ primary:** 7–8B Q4_K_M/Q5_K_M sweet spot, CPU-only — the reference benchmark target.
- **B/C:** enable GPU offload; larger/faster models.
- **D:** optional **vLLM** behind the same gateway later ([ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md)).
