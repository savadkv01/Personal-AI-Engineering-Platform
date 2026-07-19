---
mode: agent
description: "Implementation M0 — Baseline environment: WSL2/Ubuntu, Docker, repo hygiene, compose skeleton. Small, testable, reversible."
---

# Implementation Milestone M0 — Baseline Environment

> **Precondition:** Architecture phases 01–09 approved and Phase 10 roadmap approved.
> Follow repo rules in [`../../copilot-instructions.md`](../../copilot-instructions.md).
> This milestone is **small, independent, testable, documented, and reversible**.

## Role
You are a **DevOps Engineer** setting up the foundation only. Do not build platform features yet.

## Objective
Establish a reproducible local baseline: WSL2/Ubuntu readiness, Docker + Docker Compose,
repository hygiene, environment configuration, and an empty Compose skeleton that starts cleanly.

## Prerequisites
- VS Code with Dev Containers / WSL extensions.
- Docker Desktop or Docker Engine + Compose v2 available in WSL2.
- Approved reference architecture (Phase 06) for target service names.
- **Detected environment** (build for this): [`docs/setup/environment.md`](../../../docs/setup/environment.md)
  — WSL2 Ubuntu 22.04, Docker Desktop 29.1.3, Compose v2, 32 GB RAM, CPU-only.

## Scope
- **In:** base folders, `.gitignore`, `.env.example`, `docker/compose.yaml` (no services or a
  single healthcheck placeholder), `Makefile`/task scripts, environment doc.
- **Out:** LLM runtime, vector DB, RAG, agents (later milestones).

## Tasks
1. Create `docker/compose.yaml` with a minimal, valid structure (networks, volumes, optional
   `hello`/healthcheck placeholder service).
2. Add `.env.example` documenting required variables; ensure `.env` is git-ignored.
3. Add `Makefile` (or `tasks.ps1`/`justfile`) with `up`, `down`, `logs`, `ps`, `validate`.
4. Document setup in `docs/setup/00-baseline.md` (WSL2, Docker, verification steps).
5. Confirm hardware-profile notes (A–D) for what the baseline needs.

## Deliverables
- `docker/compose.yaml`, `.env.example`, `Makefile` (or equivalent), `docs/setup/00-baseline.md`.

## Validation Checklist
- [ ] `docker compose -f docker/compose.yaml config` validates with no errors.
- [ ] `docker compose up -d` starts cleanly; `docker compose ps` shows healthy/placeholder.
- [ ] `docker compose down` removes everything with no orphan volumes/networks.
- [ ] `.env` is ignored by git; `.env.example` documents all variables.
- [ ] `.wslconfig` memory/CPU limits set sensibly for the 32 GB / 8-thread machine.

## Expected Outputs
- A validated compose file and a documented one-command bring-up/tear-down.

## Rollback Plan
- `docker compose down -v` and delete the files created in this milestone. No other milestone
  depends on M0 data, so rollback is clean.

## Troubleshooting
- Compose v1 vs v2 syntax; WSL2 Docker integration disabled; volume permission issues in WSL.

## Documentation to Update
- `README.md` status; `docs/setup/00-baseline.md`.

## Testing
- Run the validation checklist end to end on at least Profile A assumptions.

## STOP
Output **"Milestone M0 complete"**, list files created, confirm validation results, then **STOP**
and wait for approval before M1.
