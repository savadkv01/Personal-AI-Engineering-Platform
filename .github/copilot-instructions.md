# GitHub Copilot Instructions — Personal AI Engineering Platform (PAIEP)

These instructions apply to the **entire repository**. They govern how any AI agent
(GitHub Copilot, Continue, Cline, Roo Code, etc.) should behave when working in this
workspace. Individual phase prompts live in [`.github/prompts/`](prompts/) and can be
run independently.

---

## 1. Project Context

PAIEP is a **design-first**, enterprise-grade, open-source, **offline-first** Personal AI
Engineering Platform intended to run primarily on a local laptop and grow into a personal
AI operating system. It is built through **12 gated phases**. The primary output of the
project is **professional documentation and reusable prompt files** — not application code
(until the architecture is approved).

Target environment: **VS Code**, **Linux / WSL2 / Ubuntu**, **Docker + Docker Compose**.
Everything possible runs locally; cloud is optional.

---

## 2. Golden Rules (Always Apply)

1. **Phase gating.** Work on **one phase at a time**. Finish the phase, then **STOP** and
   wait for explicit approval. **Never** start the next phase automatically.
2. **Design before code.** Do **not** write implementation code during architecture phases
   (01–09, 12). Code appears only inside approved implementation milestones (Phase 10+).
3. **Compare, never assert.** Never recommend a technology without a comparison. Every
   recommendation must state: **Why · Benefits · Drawbacks · Alternatives · Complexity ·
   Cost · Hardware impact · Future scalability.**
4. **Document everything.** Prefer Markdown professional enough for GitHub.
5. **Reversible steps.** Every implementation step must be small, independent, testable,
   documented, and reversible (with a rollback plan).

---

## 3. Required Output Standards

Every phase deliverable should include, where relevant:

- Markdown documentation (clear headings, tables, links)
- **Mermaid diagrams** (architecture, flow, sequence, ERD as appropriate)
- Folder structures (fenced `text` blocks)
- Technology comparison tables
- **Architecture Decision Records (ADRs)** in `docs/adr/` (format: `NNNN-title.md`)
- Best practices, Risks, Assumptions, Future improvements, References

### ADR format

```markdown
# ADR NNNN: <title>
- Status: Proposed | Accepted | Superseded
- Date: YYYY-MM-DD
- Context: <why this decision is needed>
- Decision: <what was chosen>
- Alternatives: <options considered + trade-offs>
- Consequences: <benefits, drawbacks, follow-ups>
```

---

## 4. Repository Layout

```text
.github/prompts/   # Executable, independent prompt files (01..12)
docs/phases/       # Full documentation per phase
docs/adr/          # Architecture Decision Records
architecture/      # Diagrams and architecture artifacts
implementation/    # Milestone specs, validation, rollback plans
docker/            # Compose files and container definitions
memory/            # Long-term & session memory design/artifacts
agents/            # Agent definitions and collaboration specs
knowledge/         # Knowledge base, notes, book library index
rag/               # RAG pipelines and configuration
models/            # Model profiles, quantization notes
benchmarks/        # Evaluation harnesses and results
experiments/       # Scratch / research experiments
```

- Phase documentation → `docs/phases/NN-<slug>.md`
- Phase prompt → `.github/prompts/NN-<slug>.prompt.md`
- Decisions → `docs/adr/NNNN-<slug>.md`

---

## 5. Hardware Profiles (design for all four)

| Profile | Spec | Use |
|---------|------|-----|
| A | 16 GB RAM, CPU only | Entry laptop |
| B | 32 GB RAM, consumer GPU | Prosumer |
| C | Workstation | Heavy local dev |
| D | Home Server | Always-on multi-agent host |

Always give scalability guidance per profile.

### Primary target machine (detected — build for this first)

The actual development machine is documented in
[`docs/setup/environment.md`](../docs/setup/environment.md) and is the **first-class target**:

- **HP EliteBook 840 G7** · Windows 11 Pro · WSL2 (Ubuntu 22.04/24.04) · Docker Desktop 29.1.3 + Compose v2.
- **Intel Core i7-10610U (4C/8T)** · **32 GB RAM** · **Intel UHD integrated GPU only (no CUDA/ROCm)** · ~485 GB free.
- Effective profile: **"A+" hybrid** — 32 GB RAM (like Profile B) but **CPU-only inference** (like Profile A).

**Implications:** default to CPU-optimized runtimes (Ollama / llama.cpp); treat GPU features as
"Profile B–D / future"; model sweet spot is **7B–8B quantized (Q4_K_M/Q5_K_M)**; everything must
stay offline-capable. Design for Profiles A–D, but ensure it runs on this machine now.

---

## 6. Writing Style

- Beginner friendly but production inspired.
- Explain trade-offs; avoid hype.
- Use relative Markdown links between docs.
- Keep tables scannable; keep diagrams readable.
- Cite references at the end of each document.

---

## 7. Stop Condition

At the end of **every** phase, output a short **"Phase N complete"** summary listing the
files created/updated, then explicitly **STOP** and request approval before continuing.
