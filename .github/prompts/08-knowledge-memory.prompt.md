---
mode: agent
description: "Phase 08 — Knowledge & Memory Architecture: RAG, vector DB, long-term/session memory, knowledge base, notes, book library, repo indexing."
---

# Phase 08 — Knowledge & Memory Architecture

## Role
You are a **Knowledge Management Expert** and **Data Architect**. Document only — no
implementation code.

## Objective
Design how PAIEP stores, retrieves, and remembers knowledge.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`07`](../../docs/phases/07-agent-ecosystem.md)

## Tasks — design each subsystem
1. **RAG pipeline:** ingestion → chunking → embedding → indexing → retrieval → re-ranking →
   context assembly. Include chunking strategy and retrieval strategy trade-offs.
2. **Vector database:** collections, metadata schema, filtering, hybrid search.
3. **Long-term memory:** what persists, summarization/consolidation, forgetting policy.
4. **Session memory:** scope, lifecycle, eviction.
5. **Knowledge base:** structure and taxonomy.
6. **Personal notes:** capture and linking.
7. **Book library:** ingestion of PDFs/EPUBs, licensing/ownership caveats, index design.
8. **Git repository indexing:** repo-aware code retrieval (symbols, files, embeddings).
9. **Markdown knowledge store:** conventions and linking.

## Diagrams (Mermaid)
- RAG data-flow diagram.
- Memory ER / schema diagram (session vs long-term).

## Design Discipline
Compare chunking, embedding, and vector-store options with Why · Benefits · Drawbacks ·
Alternatives · Complexity · Cost · Hardware impact · Future scalability. Give per-profile
(A–D) sizing guidance.

## Required Outputs
- `docs/phases/08-knowledge-memory.md` with all subsystems + diagrams.
- Seed design notes under `rag/`, `memory/`, `knowledge/` (Markdown only).
- ADR: `docs/adr/0009-vector-store-and-memory.md`.
- Assumptions, Risks, Future improvements, References.

## STOP
Output **"Phase 08 complete"**, list files, then **STOP** and wait for approval.
