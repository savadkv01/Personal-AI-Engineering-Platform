---
mode: agent
description: "Implementation M1 — Local LLM runtime: serve a local model (per Phase 04/06 choice) and expose an API. Testable and reversible."
---

# Implementation Milestone M1 — Local LLM Runtime

> **Precondition:** M0 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are an **MLOps Engineer** standing up the local model serving layer only.

## Objective
Run the chosen LLM runtime (e.g., Ollama / llama.cpp / LocalAI per Phase 06) as a container,
pull the default model(s) from Phase 04, and expose a reachable local API.

## Prerequisites
- M0 baseline running.
- Phase 04 default model selection and Phase 06 runtime decision.
- Sufficient disk for model weights; GPU passthrough configured if applicable (Profile B–D).
- **This machine is CPU-only** (see [`docs/setup/environment.md`](../../../docs/setup/environment.md)):
  use a CPU runtime (Ollama / llama.cpp), skip GPU config, and target **7B–8B Q4_K_M/Q5_K_M** models.

## Scope
- **In:** runtime service in Compose, model pull/warm-up, health check, smoke test.
- **Out:** RAG, agents, memory, UI.

## Tasks
1. Add the LLM runtime service to `docker/compose.yaml` (volume for models, port, healthcheck,
   optional GPU config).
2. Provide a documented way to pull the default model(s) and a chat/completion smoke test.
3. Add per-profile guidance (which model tier per Profile A–D; quantization notes).
4. Document API endpoint(s) other milestones will consume.

## Deliverables
- Updated `docker/compose.yaml`; `docs/setup/01-llm-runtime.md`; a smoke-test script/command.

## Validation Checklist
- [ ] Runtime container is healthy.
- [ ] Default model pulls successfully and is cached in a named volume.
- [ ] A completion/chat request returns a valid response locally (offline).
- [ ] Resource usage recorded for the tested hardware profile.

## Expected Outputs
- A working local inference endpoint returning model output with no internet dependency.

## Rollback Plan
- Remove the runtime service from Compose and delete its named volume
  (`docker compose down` + `docker volume rm <model_volume>`). M0 remains intact.

## Troubleshooting
- GPU not detected; insufficient RAM/VRAM for chosen quant; slow first-token on CPU (Profile A);
  model tag mismatch.

## Documentation to Update
- `docs/setup/01-llm-runtime.md`; note endpoint in architecture docs.

## Testing
- Run the smoke test; record latency and tokens/sec for the profile.

## STOP
Output **"Milestone M1 complete"**, list files, confirm validation, then **STOP** and wait for approval.
