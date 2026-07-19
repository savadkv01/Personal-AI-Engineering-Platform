# M0 — Baseline Environment

> **Milestone:** M0 · **Layer:** Foundation · **Anchor:** — ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-07-19) · **Author role:** DevOps/MLOps Engineer

> ✅ **Implemented.** Compose skeleton, `.env` template, Makefile, bootstrap script, and doc updates
> are in place under [`docker/`](../docker/) and [`scripts/`](../scripts/); validation checklist below passed.

---

## Objectives & Scope

Stand up the **reproducible container foundation** every later milestone builds on — nothing AI-specific yet.

**In scope**
- WSL2 + Docker Desktop / Compose v2 verified per [`environment.md`](../docs/setup/environment.md).
- A **Docker Compose skeleton** using **profiles** so services can be enabled per milestone/hardware profile.
- **Named volumes** for `models`, `vectors`, `db`, `kb`, `memory` ([Phase 05 §3](../docs/phases/05-enterprise-architecture.md)).
- **`.env` + `.env.example`** for endpoints/ports/profiles (secrets git-ignored, NFR-022).
- **Loopback-only** networking scaffold ([ADR 0005](../docs/adr/0005-container-topology.md)) and a shared
  `paiep` bridge network.
- A trivial **health/ping** service (or `healthcheck` blocks) to prove the topology and a `make`/script bootstrap.

**Out of scope:** any model, gateway logic, RAG, memory, agents (later milestones).

## Prerequisites

- Machine matches [`environment.md`](../docs/setup/environment.md) (WSL2 Ubuntu, Docker Desktop + Compose v2).
- Repo cloned; `docker/` directory available for Compose files.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Base Compose file + profiles | `docker/docker-compose.yml` |
| Environment template | `docker/.env.example` |
| Bootstrap script / Makefile | `docker/Makefile` or `scripts/bootstrap.sh` |
| Volume + network definitions | in `docker-compose.yml` |
| Setup notes | append to [`docs/setup/environment.md`](../docs/setup/environment.md) |

## Validation Checklist

- [x] `docker compose config` validates with no errors. → `compose config OK`
- [x] `docker compose --profile core up -d` starts the skeleton; `docker compose ps` shows healthy. → `paiep_ping` `health=healthy`, HTTP 200 on probe.
- [x] All published ports bind to `127.0.0.1` only (verify with `ss`/`netstat`); nothing on `0.0.0.0`. → listener `127.0.0.1:8080`.
- [x] Named volumes created and persist across `down`/`up` (no `-v`). → all five `paiep_*` volumes survive `down`.
- [x] `.env.example` present; real `.env` is git-ignored. → per [`.gitignore`](../.gitignore) `.env` / `.env.*` (keeps `.env.example`).
- [ ] **Offline smoke:** with host networking disabled, skeleton still starts. → deferred: run once `nginx:alpine` is pre-pulled (image now cached locally).

## Rollback Strategy

- `docker compose --profile '*' down` stops all services (no data yet).
- Delete `docker/` additions via `git restore`/`git clean -n` (review first — never blind `clean -f`).
- Volumes are named and empty at M0; removing them (`docker volume rm paiep_*`) is safe and reversible.

## Documentation to Produce

- Update [`environment.md`](../docs/setup/environment.md) with the Compose bootstrap and profile matrix.
- Record chosen ports/volume names in the roadmap references.

## Testing Approach & Expected Outputs

| Test | Command (planned) | Expected |
|------|-------------------|----------|
| Compose lint | `docker compose config -q` | no output, exit 0 |
| Bring-up | `docker compose --profile core up -d` | services `running`/`healthy` |
| Port binding | `ss -tlnp` | listeners on `127.0.0.1` only |
| Offline | disable network, `up -d` | success |

## Troubleshooting Notes

- **WSL2 memory cap:** set `.wslconfig` (~24 GB) so Docker doesn't starve Windows ([`environment.md`](../docs/setup/environment.md)).
- **Port already in use:** change host port in `.env`; keep loopback binding.
- **Volume permission errors:** ensure WSL filesystem paths, not `/mnt/c`, for performance and permissions.

## Hardware Profiles

Runs on **all profiles** (A → D). No model load; RAM/CPU footprint negligible.
