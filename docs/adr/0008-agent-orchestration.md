# ADR 0008: Agent Orchestration — Supervisor/Router with Bounded Chains

- **Status:** Accepted
- **Date:** 2026-07-19

## Context
[Phase 07 — Agent Ecosystem](../phases/07-agent-ecosystem.md) designs fifteen agents (one Supervisor +
fourteen specialists) realizing the Phase 01 personas (P1–P14). They must collaborate on the **CPU-only
primary machine**, where **interactive latency is the binding constraint** (CON-001, NFR-001/004) and the
platform must stay **offline-first** and **least-privilege** ([ADR 0006](0006-security-model.md)). The
[reference stack](0007-reference-stack.md) provides **LangGraph** (control/state) + **CrewAI** (declarative
personas). We must decide the orchestration pattern and its guardrails.

## Decision
Adopt a **supervisor/router orchestration** with **bounded, mostly-sequential chains**:

1. **Supervisor/Planner** decomposes each request, issues sub-task **contracts** (goal, inputs,
   `allowed_tools`, `fs_scope`, token/step budgets), routes to specialists, resolves conflicts, and
   aggregates the result. It never executes code itself.
2. **Default quality gate for code tasks:** Build (SE/DE/AI) → **Testing** → **Reviewer** → **Security** →
   **Documentation**. The **Security Agent holds a hard veto** on high-severity findings.
3. **Structured message contract** (described in Phase 07 §5): agents pass **references, not payloads**,
   always attach **citations**, and the runtime **enforces** `constraints` (not advisory).
4. **Least-privilege tools** per agent (default-deny; `shell`/`web.fetch`/`container` opt-in), per
   [ADR 0006](0006-security-model.md).
5. **Bounded execution:** explicit step/token budgets and low concurrency (1–2 models hot) protect CPU
   interactivity (NFR-004); the Supervisor truncates and returns partial + reason if budgets are exceeded.
6. **Shared memory:** PostgreSQL (state/structured) + Qdrant (semantic); session→long-term promotion is
   **async and curated**; Knowledge Manager owns KB writes; Architect/Supervisor own decision records.
7. **Config-driven agents:** Markdown seed specs now ([`agents/`](../../agents/)) → CrewAI YAML later
   (add/adjust an agent = config change, not a rewrite; NFR-024).

## Alternatives Considered
- **Peer-to-peer / blackboard.** Flexible and emergent, but unbounded inter-agent chatter is **costly and
  slow on CPU** and hard to debug/trace. **Rejected now**; a **bounded peer sub-graph under the supervisor**
  is a future option on GPU/Profile-D.
- **Static pipeline (fixed DAG).** Simple and predictable, but too rigid for varied tasks (design vs. build
  vs. research). **Rejected** as the sole model (used implicitly as the default quality gate).
- **Single monolithic agent.** Lowest overhead, but loses specialization, guardrail granularity, and
  reviewability. **Rejected**; kept only as a low-RAM fallback for trivial tasks (Profile A).
- **AutoGen-style group chat.** Attractive ergonomics, but AutoGen is in **maintenance mode** (Phase 03) and
  group chat is chatty on CPU. **Rejected** as the foundation.

## Consequences
**Benefits**
- Explicit, debuggable, **bounded** agent chains → predictable latency/cost on the CPU-only machine.
- One place for guardrails, conflict resolution, and tracing (Langfuse).
- Least-privilege by construction; Security veto contains unsafe actions and prompt-injection fallout.
- Config-driven agents preserve modularity/swappability (NFR-023/024).

**Drawbacks**
- Supervisor is a coordination **bottleneck / single point** (mitigated: keep it thin; persist state to resume).
- Two agent libraries (LangGraph + CrewAI) require a disciplined role split (control vs. persona ergonomics).
- Sequential chains limit throughput until GPU/Profile-D adds concurrency.

**Follow-ups**
- Formalize CrewAI **YAML** persona configs from the Markdown seeds (implementation, Phase 10+).
- Add **HITL checkpoints** (LangGraph) for high-risk actions (push, container down, deletes).
- Finalize **memory scope + retention/summarization** (Phase 08 / M5).
- Add **agent-quality evaluation** (task success, review precision) via Langfuse + Phase 11 benchmarks.
- Introduce **bounded peer sub-graphs** once concurrency budget allows (Profiles B–D).
