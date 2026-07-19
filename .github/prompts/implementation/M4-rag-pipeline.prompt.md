---
mode: agent
description: "Implementation M4 — RAG pipeline: retrieval + optional re-rank + context assembly + grounded generation. Reversible."
---

# Implementation Milestone M4 — RAG Pipeline

> **Precondition:** M3 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are an **AI Engineer** wiring retrieval to generation.

## Objective
Build an end-to-end RAG query path: embed query → retrieve top-k → (optional) re-rank →
assemble context → generate grounded answer with citations.

## Prerequisites
- M1 (runtime), M2 (vector DB), M3 (populated index) running.
- Phase 08 retrieval/re-rank/context-assembly design.

## Scope
- **In:** query embedding, retrieval, optional re-ranking, prompt/context assembly, grounded
  answer with source citations, a query entrypoint (CLI or API).
- **Out:** multi-agent orchestration (M6), UI (M8).

## Tasks
1. Implement query embedding + top-k retrieval with metadata filters.
2. Add optional re-ranking (justify inclusion vs cost per Phase 08).
3. Assemble context within the model's context budget; include citations.
4. Expose a query entrypoint (CLI or local API) for testing.
5. Add basic guardrails: handle empty retrieval, oversized context, and no-answer cases.

## Deliverables
- RAG query module; `docs/setup/04-rag-pipeline.md`; example queries + outputs.

## Validation Checklist
- [ ] A known question returns a correct, grounded answer citing the right source.
- [ ] Retrieval respects metadata filters.
- [ ] Context stays within the model context window; no truncation errors.
- [ ] Graceful behavior when nothing relevant is found.

## Expected Outputs
- Grounded answers with citations from the local knowledge base, fully offline.

## Rollback Plan
- Remove the RAG query module; M1–M3 remain functional independently.

## Troubleshooting
- Poor recall (chunking/embeddings), context overflow, irrelevant citations, latency on Profile A.

## Documentation to Update
- `docs/setup/04-rag-pipeline.md`; `rag/` retrieval-strategy notes.

## Testing
- Curate a small Q/A set; measure answer relevance and citation correctness.

## STOP
Output **"Milestone M4 complete"**, list files, confirm validation, then **STOP** and wait for approval.
