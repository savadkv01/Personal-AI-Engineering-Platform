---
title: RAG Pipeline Overview
tags: [rag, retrieval, qdrant, llamaindex]
scope: global
created: 2026-07-20
updated: 2026-07-20
---

# RAG Pipeline Overview

PAIEP's retrieval-augmented generation pipeline follows the stages
`ingest → chunk → embed → index → retrieve → re-rank → assemble`. The write
path (ingest through index) is built in milestone M3; the read path (retrieve
through assemble) arrives in M4.

## Stack

- **Embeddings:** `nomic-embed-text` (dimension 768), served by the local
  Ollama runtime and fixed per collection.
- **Vector store:** Qdrant, with collections `kb_docs`, `repo_code`, and
  `memory_semantic`. Payloads carry `scope`, `source`, and `tags` so retrieval
  can filter by project or label.
- **Orchestration:** LlamaIndex provides sentence-aware chunking today and the
  retrieval interfaces later.

## Idempotency

Ingestion is idempotent: each chunk gets a deterministic ID derived from its
source path and chunk index, and every point stores a checksum. Re-running the
ingest skips unchanged files and re-embeds only what changed.
