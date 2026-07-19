# RAG — Seed Design Notes

> Seed notes for the retrieval-augmented generation pipeline. Full design:
> [`docs/phases/08-knowledge-memory.md`](../docs/phases/08-knowledge-memory.md). Stack:
> LlamaIndex + Qdrant + nomic-embed-text ([ADR 0007](../docs/adr/0007-reference-stack.md),
> [ADR 0009](../docs/adr/0009-vector-store-and-memory.md)).

## Pipeline stages
`ingest → chunk → embed → index → retrieve → re-rank → assemble` (see Phase 08 §3).

## Defaults (starting points — tune in M1)

| Knob | Default | Notes |
|------|---------|-------|
| Chunking | Recursive/structural; code-aware for repos | ~512–1024 tokens, ~10–15% overlap |
| Embedding model | `nomic-embed-text` (dim 768) | Fixed per collection |
| Retrieval | Hybrid (vector + keyword) | top-k 4–8 on CPU |
| Re-ranking | Optional / off on Profile A | Small re-ranker when latency allows |
| Context assembly | Dedupe + budget-aware + cite | Retrieved text = data, not instructions |

## Collections
`kb_docs` (notes/docs/books) · `repo_code` (code) · `memory_semantic` (long-term memory). One embedding
model per collection; record `embed_model`/`embed_dim`.

## Safety
Sanitize ingested content; delimit as data (OWASP LLM01). Offline by default; `web.fetch` opt-in only.

## Tuning backlog (M1 / Phase 11)
- Measure recall vs. chunk size/overlap and top-k.
- Fusion weights for hybrid search.
- Cross-encoder re-rank cost/benefit on CPU vs. GPU.
