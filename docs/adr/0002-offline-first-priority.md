# ADR 0002: Offline-First as the Overriding Priority

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
PAIEP handles **private code, notes, and a personal knowledge base**, runs on a machine the owner
fully controls, and aims to have **zero mandatory operating cost**. The [Phase 01 Vision](../phases/01-project-vision.md)
names *offline-first* as a top guiding principle, and the [Phase 02 requirements](../phases/02-requirements-analysis.md)
elevate several offline/privacy items to **Must** (NFR-010, NFR-011, NFR-020, NFR-040).

At the same time, cloud LLMs are more capable, and GPU/home-server acceleration is attractive
(see [ADR 0100](0100-gpu-and-reuse-strategy.md)). We must decide how strongly offline capability
governs the architecture when it competes with quality, speed, or convenience.

The primary machine is **CPU-only** (HP EliteBook 840 G7, 32 GB RAM — see
[environment.md](../setup/environment.md)), which reinforces a local, resource-conscious default.

## Decision
Make **offline-first the overriding architectural priority**:

1. **All core workflows must function with the network disabled** — inference, memory, RAG,
   persona agents, and VS Code assistance (NFR-010).
2. **No core feature may have a mandatory cloud dependency** (NFR-011); cloud/GPU/home-server are
   **opt-in enhancements**, never prerequisites (FR-006).
3. **All personal data is stored locally** by default (NFR-020); nothing leaves the device unless
   the user explicitly enables an outbound path.
4. When offline capability conflicts with raw quality or convenience, **offline capability wins**
   for the default configuration; higher-quality online paths may be added as optional profiles.
5. **Zero mandatory cost** follows directly (NFR-040): the default stack is free to operate.

## Alternatives Considered
- **Cloud-first (best quality).** Highest capability, but violates privacy, cost, and ownership
  goals and fails when offline. **Rejected as default.**
- **Hybrid with cloud as default, offline as fallback.** Good quality, but makes cloud a de-facto
  dependency and risks silent data egress. **Rejected as default** (kept as optional profile).
- **Offline-only (no cloud ever).** Maximally private, but forecloses useful optional burst/GPU
  paths on the roadmap. **Rejected** as too rigid.
- **Offline-first with opt-in online enhancements (chosen).** Preserves privacy, cost, and
  ownership while leaving a documented path to more power.

## Consequences
**Benefits**
- Strong privacy and data ownership; works anywhere, no connectivity required.
- Zero mandatory cost; predictable behavior.
- Forces a resource-conscious, CPU-friendly design that fits the primary machine.

**Drawbacks**
- Default output quality is bounded by local, quantized models.
- CPU-only latency constrains long agent chains (mitigated by concurrency limits and the
  home-server path in ADR 0100).
- Extra design effort to keep every core feature offline-capable and to isolate optional online paths.

**Follow-ups**
- Quantify offline latency/quality targets in **Phase 04**.
- Keep optional online paths (cloud burst, GPU, home server) cleanly separated behind config
  (**Phase 06/07**, ADR 0100).
- Verify offline operation as an acceptance test in **Phase 11**.
