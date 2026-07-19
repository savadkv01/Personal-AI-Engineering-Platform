# ADR 0006: Security Model — Local-First Data Protection & Least-Privilege Tools

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
[Phase 05 §5](../phases/05-enterprise-architecture.md#5-view-4--security-architecture) analyzes PAIEP's
threats. Because the platform is **offline-first**, **single-operator**, and runs on a **local machine**
(NFR-010/011/020, CON-004, CON-007), the dominant risks are **not** perimeter network attacks but:

1. **Accidental data exfiltration** — a tool/agent sending private data off-device.
2. **Over-broad agent tool actions** — autonomous agents running destructive file/shell operations.
3. **Prompt injection** (OWASP LLM01) — malicious instructions embedded in ingested docs/books/web.
4. **Secret leakage** — secrets appearing in logs or prompts (NFR-022).

We must decide the security model that governs networking, tool use, data, and content handling.

## Decision
Adopt a **local-first data protection + least-privilege tool** model:

1. **Egress off by default.** No core workflow requires the network; outbound calls (cloud/LAN) are
   **explicit opt-in** only (NFR-010/011).
2. **Loopback-only exposure.** Host-facing ports bind to **`127.0.0.1`**, never `0.0.0.0`; data
   services live on an internal-only network (see [ADR 0005](0005-container-topology.md)).
3. **Least-privilege tools (default-deny).** Each persona gets an explicit **tool allow-list**; file
   ops are **path-scoped**; shell is disabled unless a persona explicitly needs it; sensitive actions
   require confirmation (NFR-021, FR-034).
4. **Retrieved content is data, not instructions.** Ingested/web content is sanitized and delimited so
   it cannot escalate into system instructions (OWASP LLM01 mitigation).
5. **Secret hygiene.** Secrets via `.env`/secret files excluded from VCS; **no secrets in logs or
   prompts**; redaction in observability (NFR-022).
6. **User-controlled data.** All personal data (KB, memory, vectors) is local; the user can
   **view/edit/delete** memories (FR-013); documented backup priorities (Phase 05 §4.2).
7. **Integrity.** Prefer official model tags/sources; pin versions; verify at selection (ADR 0003).
8. **Profile-D hardening.** When inference moves to a LAN server, **require** the gateway token,
   restrict by host/subnet, and consider TLS on the LAN link.

## Alternatives Considered
- **Trust-all local tools.** Simplest, but a single bad tool call or injected instruction could delete
  files or leak data. **Rejected.**
- **Full network perimeter security (firewalls/mTLS everywhere) as the primary model.** Misaligned with
  a single-user offline laptop; adds friction without addressing the real (tool/injection) risks.
  **Rejected** as the primary model (a subset applies on Profile D).
- **VM/gVisor isolation per tool.** Strong isolation, but heavy for a 32 GB CPU laptop. **Deferred** —
  revisit if autonomy/attack surface grows.
- **Encrypt-at-rest everything now.** Useful, but OS/volume-level encryption + local-only storage covers
  the single-operator threat; app-level crypto adds complexity. **Deferred.**

## Consequences
**Benefits**
- Directly mitigates the top risks (exfiltration, over-broad tools, injection, secret leakage).
- Preserves offline-first and privacy guarantees (NFR-010/011/020).
- Contains agent mistakes; makes growing autonomy safe and auditable.

**Drawbacks**
- Some UX friction (confirmations, path scoping, per-persona config).
- Requires a tool-authorization mechanism and disciplined content sanitization.
- Loopback-only means remote access needs a deliberate, hardened opt-in (Profile D).

**Follow-ups**
- Specify the **tool allow-list / policy** format with persona definitions (Phase 07).
- Implement gateway auth token + loopback bindings in the Compose stack (Phase 10+).
- Add log **redaction** and a secrets-handling convention to observability/config.
- Define the **Profile-D** LAN hardening override (token + subnet + TLS) (Phase 12).
- Re-verify current **OWASP Top 10** and **OWASP Top 10 for LLM Applications** editions at implementation.
