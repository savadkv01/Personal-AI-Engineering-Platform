# M6 — Agent Ecosystem

> **Milestone:** M6 · **Layer:** Cognition · **Anchor:** O5 (FR-030–033),
> [Phase 07](../docs/phases/07-agent-ecosystem.md), [ADR 0008](../docs/adr/0008-agent-orchestration.md) ·
> **Prompt:** [`.github/prompts/implementation/M6-agents.prompt.md`](../.github/prompts/implementation/M6-agents.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Implemented (validated 2026-11-01) · **Author role:** AI Engineer + Principal Software Engineer

> ✅ **Implemented.** Built and validated on the reference machine — see
> [Execution Results](#execution-results-2026-11-01).

---

## Objectives & Scope

Build the **agent orchestration** layer: **LangGraph** for stateful control with **CrewAI-style YAML
personas** ([ADR 0008 amendment](../docs/adr/0008-agent-orchestration.md#amendment--m6-implementation-2026-11-01)),
wiring in RAG (M4) and memory (M5) as tools.

**In scope**
- **LangGraph orchestrator** with a **supervisor** pattern, bounded chains, and **HITL approval** gates.
- **Persona configs** (YAML) for the [Phase 07](../docs/phases/07-agent-ecosystem.md) roles (P1–P14) —
  prompt + tools + model tier + guardrails (FR-030); a starter set enabled.
- **Model router** (role → model profile, FR-003) over the gateway.
- **Tool runtime** (scoped file/vcs/RAG/memory; shell/web/container off) enforcing **least privilege**
  ([ADR 0006](../docs/adr/0006-security-model.md), NFR-021); actions require approval + are traced.
- Guardrails to protect **CPU interactivity** (bounded chain length/timeouts, NFR-004).

**Out of scope:** editor integration (M7), UI (M8), observability/Langfuse (M9), shell/container tools (M10).

## Prerequisites

- **M1** (runtime + gateway), **M4** (RAG) and **M5** (memory) complete — agents consume them as tools.

## Deliverables

| Artifact | Path (built) |
|----------|--------------|
| Orchestrator graph (LangGraph: plan → execute → gate → approve → apply → finalize) | [`agents/orchestrator/`](../agents/orchestrator/) |
| Persona configs (15 YAML; 6 enabled) | [`agents/personas/`](../agents/personas/) |
| Model router config | [`config/router.yaml`](../config/router.yaml) |
| Tool runtime + policy | [`agents/tools/`](../agents/tools/), [`config/tool-policy.yaml`](../config/tool-policy.yaml) |
| Orchestration budgets / gate / checkpoints | [`config/agents.yaml`](../config/agents.yaml) |
| Agent CLI + Compose service `agents` | [`scripts/agent-cli.py`](../scripts/agent-cli.py), [`docker/docker-compose.yml`](../docker/docker-compose.yml) |
| Unit tests (offline, fake LLM) | [`tests/test_agents.py`](../tests/test_agents.py) |
| Routing eval + latency benchmarks | [`benchmarks/m6/`](../benchmarks/m6/) |
| Agent flow docs / setup | [`agents/README.md`](../agents/README.md), [`docs/setup/06-agents.md`](../docs/setup/06-agents.md) |
| Representative task output (agent-written, human-approved) | [`experiments/m6_demo/`](../experiments/m6_demo/) |

## Validation Checklist

- [x] Supervisor routes a task to the correct persona/model tier — **8/8** on the labeled routing set.
- [x] An agent uses RAG + memory tools and returns a grounded, cited result.
- [x] Chains are **bounded** (max steps/calls/timeout); no runaway loops on CPU.
- [x] Tool actions require **approval** and are **traced** (HITL, [ADR 0006](../docs/adr/0006-security-model.md)).
- [x] Least-privilege enforced (path-scoped fs, shell/web/container off) per tool policy.
- [x] **Offline smoke:** multi-step tasks complete with no network egress.
- [x] Agents call permitted tools and read/write shared memory; a representative multi-agent task completes
      end to end (M6 prompt checklist).

## Execution Results (2026-11-01)

Reference machine (HP EliteBook 840 G7, i7-10610U, 32 GB, CPU-only; Docker Desktop 29.6.1 / WSL2);
Ollama 0.6.2 `qwen2.5-coder:7b` for every tier via the gateway; Postgres 16.14 + Qdrant v1.12.6.

| Check | Result |
|-------|--------|
| Dependencies | LangGraph 1.2.19 + checkpointers: **26 packages** (CrewAI would add 107 incl. ChromaDB/onnxruntime + telemetry → not used; ADR 0008 amendment) |
| Routing (FR-030) | v1 prompt **5/8**; v2 ("Use for" keywords + 6 few-shot examples in config) **8/8**; planner cold 103 s, warm 12–17 s |
| Grounded single agent | `--agent architect`: 3 bullets citing `knowledge/notes/offline-first.md`, 2 calls, **156 s** |
| Representative multi-agent task | "create `textutils.py` + test + README": plan software_engineer → documentation_writer; gate added reviewer + security; **6 calls, 17.8 min**; 3 files proposed |
| HITL across processes | task paused at approval; `agent approve` from a **new container** resumed from the Postgres checkpoint, applied 3 files; generated test **passed**; factual `task_summary` saved |
| Reject path | flawed v1 proposal and a destructive docs rewrite **rejected** from new containers → nothing written |
| Least privilege (live, real mount) | `docker/.env`, `.git/config`, `../etc/passwd` reads denied; `shell`, `web.fetch`, `git push` denied; writes to `config/tool-policy.yaml`, `agents/personas/`, CI workflows, and out-of-scope `rag/query/engine.py` denied |
| Secret exfiltration attempt | security agent refused; token **not** in output |
| Offline | `agents` container (backend only): `Network is unreachable` |
| Rollback | `DROP SCHEMA agents CASCADE` → runtime recreated the 4 checkpoint tables; M5 tables untouched |
| Tests | **136** unit tests (69 agent tests) + ruff green; M4/M5 suites unchanged |

### Findings from live runs → fixes (all covered by unit tests)

| # | Observed on the real 7B/CPU stack | Fix |
|---|-----------------------------------|-----|
| 1 | Cold prompt processing ≈ **6.4 tok/s**; a ~4.2k-token prompt exceeded the 600 s gateway timeout | Lean prompts (context/review budgets), prefix-stable prompts (Ollama cache), `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=8192`, per-tier output caps |
| 2 | Planner misrouted 3/8 (ADR → engineer, review → engineer) | "Use for" catalog + config few-shot examples → 8/8 |
| 3 | Engineer dropped the requested test file (and claimed it wrote it); doc writer put the README in `summary`; doc writer couldn't see the code | Requested-file tracking + deterministic gate check with one fix round; proposals shown to later builders and readable via `fs.read`; docs salvage |
| 4 | Both 7B reviewers passed an obviously broken regex (`severity=none`) | Reviewer checklist; deterministic checks; tests run on approval; documented that the human diff review is the real gate |
| 5 | Invented test target `tests/...::test_x` | Target normalisation/repair + validation |
| 6 | Reviewers wasted a tool turn reading not-yet-written files | `fs.read` overlay of proposals; reviewers get proposals inline with 0 tool turns (−2 calls/task) |
| 7 | Docs persona proposed rewriting a 525-line doc it had only seen 400 chars of | **Read-before-overwrite** rule, max-size rule, destructive-shrink gate issue |
| 8 | A **rejected** task left a false memory ("engine.py now logs queries"), later cited | Agent memory writes are **approved with the task**; task summaries are factual only; polluted memories purged |
| 9 | Trace field `kind` overwritten by event data | Reserved trace fields always win |
| 10 | `agent list` fell back to SQLite checkpoints | Commands without memory still follow the configured memory backend |

Validation memories (seeded + agent-written) were purged afterwards; the M5 store is empty and consistent.

**Deviations / notes**
- **No CrewAI library** — CrewAI-style YAML executed by LangGraph (ADR 0008 amendment, approved).
- **Starter roster:** supervisor + architect, software_engineer, documentation_writer, reviewer, security
  enabled; the other 9 personas are defined and validated at load, enabled incrementally (M6 prompt scope).
- **Testing Agent role** is covered by builders proposing tests + approved `test.run`; a pre-approval test
  sandbox is deferred (running model-written code before approval needs container isolation — M10).
- **Supervisor aggregation is deterministic** (no extra CPU model call); task locks are unnecessary while
  chains are strictly sequential (single slot) and are deferred to concurrent profiles (B–D).
- **Tracing** is JSONL until Langfuse (M9). LangSmith tracing is forced off.
- **Latency:** ~2–3 min per agent step and ~15–20 min for build → document → review → security on A+;
  suitable for background tasks with approval, not interactive chat.

## Rollback Strategy

- Stop using the `agents` service; the gateway still serves chat and RAG (M4) + memory (M5) are unaffected.
- `DROP SCHEMA agents CASCADE` removes task state (validated); traces live in `/data/agent-traces/`.
- Personas/tools are config — disable individual personas (`enabled: false`) without touching the engine.
- Revert `agents/`, `config/{agents,router,tool-policy}.yaml` via `git restore`; approved file changes are
  ordinary working-tree edits (`git diff` / `git restore`).

## Documentation to Produce

- [x] Orchestration/supervisor/guardrail design — [`agents/README.md`](../agents/README.md).
- [x] Persona catalog P1–P14 → configs — [`agents/README.md` roster](../agents/README.md#roster).
- [x] [ADR 0008](../docs/adr/0008-agent-orchestration.md) confirmed + amended; setup guide
      [`docs/setup/06-agents.md`](../docs/setup/06-agents.md); measurements [`benchmarks/m6/`](../benchmarks/m6/README.md).

## Testing Approach & Expected Outputs

| Test | Method | Result |
|------|--------|--------|
| Functional | single-persona task (live) | grounded, cited answer |
| Integration | supervisor multi-agent flow (live + unit) | routed, bounded, gated, cited, applied after approval |
| Safety | disallowed tool/path/secret attempts (live + unit) | blocked, traced, nothing written |
| Performance | routing eval + trace summaries | recorded ([`benchmarks/m6/`](../benchmarks/m6/README.md)) |
| Offline | egress probe from `agents` | blocked; tasks succeed |

## Troubleshooting Notes

- **Slow chains:** expected on CPU — see [`docs/setup/06-agents.md` §4](../docs/setup/06-agents.md#4-cpu-performance-profile-a);
  keep `context.*` small; `--agent` skips planning.
- **Tool over-permission:** default deny; enable tools per persona **and** globally.
- **Wrong routing:** `agent route "..."`; add a `supervisor.examples` entry.
- **Token blowups / 504:** lower `context.review_chars`, `tier_options.max_tokens`.
- More in [`docs/setup/06-agents.md` §6](../docs/setup/06-agents.md#6-troubleshooting).

## Hardware Profiles

- **A:** SQLite checkpoints (auto with the Profile-A memory config); keyword planner (`planner: keyword`)
  saves a model call; short chains.
- **A+:** validated configuration above (bounded, single slot, 7B for all tiers).
- **B/C:** GPU — raise `context.*`, `max_tool_steps_per_agent`, `OLLAMA_NUM_PARALLEL`; distinct reasoning model.
- **D:** many agents concurrently; add task locks + bounded peer sub-graphs (ADR 0008 follow-up).
