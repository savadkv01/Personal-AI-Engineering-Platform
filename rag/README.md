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

## Vector store conventions (M2)

Qdrant is the shared vector store for **both RAG and semantic memory**. Collections + payload indexes are
created idempotently by [`scripts/qdrant-init.sh`](../scripts/qdrant-init.sh) from the
[`config/index-catalog.yaml`](../config/index-catalog.yaml) registry (the single source of truth for
`collection → embed_model + dim + distance`). See [ADR 0009](../docs/adr/0009-vector-store-and-memory.md).

**Collection schema**

| Collection | Vectors | Dim | Distance | Owner |
|------------|---------|-----|----------|-------|
| `kb_docs` | `nomic-embed-text` | 768 | Cosine | RAG (M3/M4) |
| `repo_code` | `nomic-embed-text` | 768 | Cosine | RAG (M3/M4) |
| `memory_semantic` | `nomic-embed-text` | 768 | Cosine | Memory (M5) |

> A collection is permanently bound to its embedding model/dim. Changing either is a **re-embed** (drop +
> re-ingest), never an in-place edit — the catalog makes that contract explicit.

**Payload-filter conventions** — indexed (`keyword`) on every collection so scope/tag/source filtering is
fast and consistent across RAG (FR-012) and memory (FR-021):

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `scope` | keyword | `global` \| `project:<name>` | Isolate per-project vs. shared knowledge |
| `source` | keyword | file path / uri / doc-id root | Provenance + targeted deletes/re-index |
| `tags` | keyword (multi) | free-form labels | Ad-hoc slicing / retrieval biasing |

Filter example (retrieve only a project's chunks):

```json
{ "must": [ { "key": "scope", "match": { "value": "project:demo" } } ] }
```

Ingestion/RAG/memory MUST set `scope` and `source` on every point; `tags` is optional. Additional payload
(e.g. `title`, `chunk_id`, timestamps) may be attached but is not indexed unless added to the catalog.

## Ingestion — write path (M3)

The ingestion pipeline (`load → chunk → embed → upsert`) lives in [`rag/ingest/`](ingest/), is driven by
[`config/embeddings.yaml`](../config/embeddings.yaml), and is run via [`scripts/ingest.py`](../scripts/ingest.py)
(container profile `ingest`). Full guide: [`docs/setup/03-embeddings-ingestion.md`](../docs/setup/03-embeddings-ingestion.md).

- **Loaders:** Markdown/text (+ front-matter), source code, and lazy PDF/EPUB.
- **Chunking:** LlamaIndex `SentenceSplitter`; per-type windows (note 512/64, book 1024/128, code 768/96).
- **Embedding:** Ollama `nomic-embed-text` (dim 768) via `/api/embed`; dim checked against the M2 collection.
- **Idempotency:** point ID = `uuid5(source, chunk_index)` + per-file SHA-256 `checksum`; unchanged files are
  skipped, changed files are deleted-by-`source` then re-upserted (no dupes/orphans). `--force` re-embeds.
- **Offline by construction:** the ingest container attaches only to the internal `backend` network.

```bash
docker compose --profile ingest run --rm ingest knowledge --scope global --tags paiep,seed
```

## Retrieval — read path (M4)

The query pipeline (`embed query → retrieve top-k → re-rank → assemble cited context → grounded generate`)
lives in [`rag/query/`](query/), is driven by [`config/rag.yaml`](../config/rag.yaml), and runs via
[`scripts/rag-query.py`](../scripts/rag-query.py) (container profile `rag`, same image as `ingest`). Full
guide: [`docs/setup/04-rag-pipeline.md`](../docs/setup/04-rag-pipeline.md).

- **Retrieve:** query embedded with the same `nomic-embed-text` model; Qdrant `search` with `score_threshold`
  and optional `scope`/`tags` payload filters (`scope` = exact match, `tags` = match-any).
- **Re-rank (optional, off by default):** dependency-free **lexical-overlap** blend
  (`(1−w)·vector + w·lexical`) over a wider `candidate_k` — a cheap CPU-friendly precision nudge; a
  cross-encoder is deferred (Profile B+/Phase 11).
- **Assemble:** numbered `[n]` context blocks within a char budget (`max_context_chars`, per-chunk cap);
  each block carries provenance so the answer can cite `source`.
- **Generate:** Ollama chat (`qwen2.5-coder:7b`, low temperature) with a strict system prompt — answer
  **only** from context, cite `[n]`, and return a fixed **no-answer** phrase when context is insufficient.
- **Guardrails:** empty retrieval short-circuits to the no-answer message **without** calling the model
  (no hallucinated citations); retrieved text is delimited as **data, not instructions** (OWASP LLM01).
- **Offline by construction:** the `rag` container attaches only to the internal `backend` network.

```bash
# grounded question (cites sources)
docker compose --profile rag run --rm rag "How does PAIEP stay usable offline?"
# scope-filtered + JSON
docker compose --profile rag run --rm rag "..." --scope global --json
# retrieval recall@k eval
docker compose --profile rag run --rm --entrypoint python rag /app/benchmarks/m4/eval.py
```

## Safety

Sanitize ingested content; delimit as data (OWASP LLM01). Offline by default; `web.fetch` opt-in only.


## Tuning backlog (M1 / Phase 11)
- Measure recall vs. chunk size/overlap and top-k.
- Fusion weights for hybrid search.
- Cross-encoder re-rank cost/benefit on CPU vs. GPU.
