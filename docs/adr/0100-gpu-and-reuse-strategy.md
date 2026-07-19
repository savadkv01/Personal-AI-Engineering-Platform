# ADR 0100: GPU Acceleration & Multi-Workspace Reuse Strategy

- **Status:** Proposed (revisit in Phase 04 and Phase 12)
- **Date:** 2026-07-19

## Context
The primary machine (HP EliteBook 840 G7, i7-10610U, 32 GB RAM) is **CPU-only** with integrated
Intel UHD graphics and **no internal GPU-upgrade path**. We need a direction for (a) optional GPU
acceleration and (b) reusing the agentic setup across multiple workspaces without duplicating
infrastructure. See [`docs/setup/environment.md`](../setup/environment.md).

## Decision
1. **Default: run CPU-only** on the laptop for development and orchestration, targeting
   **7B–8B quantized (Q4_K_M/Q5_K_M)** models via a CPU runtime (Ollama / llama.cpp).
2. **Preferred acceleration path: a LAN "home AI server"** (Profile D) — a used desktop/mini-PC
   with a **≥12 GB VRAM** GPU — rather than an internal upgrade or eGPU. The laptop becomes a
   thin client to shared services.
3. **eGPU (Thunderbolt 3) is a fallback**, contingent on confirming the unit has Thunderbolt 3.
4. **Reuse model:** run backend services once as shared Docker containers; distribute per-workspace
   config via a **template repo/cookiecutter**. Formalized in milestone M7.

## Alternatives Considered
- **Internal discrete GPU:** not possible on this chassis.
- **eGPU over TB3:** feasible (~$400–$800) but adds cost/complexity and is bandwidth-limited;
  kept as fallback.
- **Cloud GPU:** rejected as the default (violates offline-first / cost-free goals); may remain an
  optional burst path.
- **Per-workspace duplicated services:** rejected (wasteful RAM/disk on a 32 GB machine).

## Consequences
- **Benefits:** zero token cost today; clear, low-risk upgrade path; scalable to Profile D; one
  shared backend serves all workspaces.
- **Drawbacks:** CPU-only latency/throughput limits long agent chains; local model quality is below
  cloud frontier models; home-server option is a future hardware purchase.
- **Follow-ups:** validate model tiers in Phase 04; confirm Thunderbolt 3 on the 840 G7; design the
  home-server topology and template-repo mechanism in Phase 12 / M7.
