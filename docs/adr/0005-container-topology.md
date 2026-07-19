# ADR 0005: Container Topology — One Compose Stack, Two Networks

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
[Phase 05 — Enterprise Architecture](../phases/05-enterprise-architecture.md) defines the backend as a
set of capability services (gateway, orchestrator, inference, RAG, embeddings, memory, vector DB,
metadata DB, observability). The runtime substrate is **VS Code + WSL2/Ubuntu + Docker Desktop
(Compose v2)** on a **CPU-only, 32 GB** laptop (CON-005, CON-001, [environment.md](../setup/environment.md)),
and the backend must run **once** and serve **many workspaces** (O7, FR-062), stay **offline-first**
(NFR-010), and remain **reversible/reproducible** (NFR-031, FR-064).

We must decide how to package and connect these services.

## Decision
Package the entire backend as a **single Docker Compose stack** (`paiep`) with **two networks** and
**named volumes**:

1. **`edge` network (host-exposed):** only the `gateway` (and optional `open-webui`) bind to the host,
   on **`127.0.0.1`** — never `0.0.0.0`.
2. **`backend` network (internal only):** `orchestrator`, `inference`, `rag`, `memory`, `vectordb`,
   `metadb`, `observability` — not reachable from the host or LAN.
3. **Named volumes** for all state: `paiep_models`, `paiep_vectors`, `paiep_db`, `paiep_kb`,
   `paiep_memory` (documented backup priorities in Phase 05 §4.2).
4. **Config via env + Compose overrides/profiles:** profiles A–D diverge (models, GPU reservations,
   remote endpoints) **without forking** the base stack.
5. **Co-locate early, split later:** logically distinct services may share a container initially
   (e.g., RAG + Embeddings) and split when a real need appears — interfaces stay stable (NFR-023).
6. **Profile-D split:** a Compose override runs `inference` (+`vectordb`) on a LAN server while the
   laptop runs gateway/orchestrator (aligns with [ADR 0100](0100-gpu-and-reuse-strategy.md)).

## Alternatives Considered
- **Kubernetes / k3s from the start.** Multi-node, self-healing, but heavy operational overhead for a
  single laptop and one user. **Rejected now**; kept as a documented long-term horizon.
- **Bare processes on the host / in WSL.** Lightest, but no isolation, poor reproducibility, and
  fragile offline setup. **Rejected.**
- **One flat Docker network.** Simpler, but every data service is reachable from the host surface,
  weakening the trust boundary. **Rejected** in favor of edge/backend split.
- **Separate Compose file per service.** Maximum independence, but loses one-command lifecycle and
  makes cross-service wiring error-prone. **Rejected** in favor of one stack + overrides.

## Consequences
**Benefits**
- One-command, reversible lifecycle (`up`/`down`); reproducible and version-controlled (NFR-031).
- Network segmentation limits blast radius and keeps data services off the host-facing surface.
- Env/override-driven profiles (A–D) without forking; same stack deploys to a Profile-D server.
- Offline-first: no service requires the network to start.

**Drawbacks**
- Compose is **single-host**; true multi-node needs the Profile-D split or a future orchestrator.
- Large stacks require discipline (naming, healthchecks, dependency order) to stay legible.
- Co-location decisions must be revisited as load grows.

**Follow-ups**
- Author the concrete `docker-compose.yml` + `override` files in the implementation milestones
  (Phase 10+), with healthchecks and `127.0.0.1` bindings.
- Define resource limits consistent with the ~24 GB WSL2 cap (environment.md §5).
- Add the Profile-B/C GPU reservation override and the Profile-D LAN override.
- Finalize the concrete services (vector DB, agent framework, editor client) in Phase 06.
