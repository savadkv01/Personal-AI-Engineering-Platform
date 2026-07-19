# Embedding Models for Local RAG

> CPU-friendly embedding models for the knowledge base / RAG pipeline. Source:
> [Phase 04 feasibility study](../docs/phases/04-feasibility-study.md). Dims/licenses ⚠ verify at Phase 06.

| Model | Dim ⚠ | Size | Strengths | License ⚠ | Notes |
|-------|:-----:|------|-----------|-----------|-------|
| **nomic-embed-text** | 768 | small | Long context, strong general retrieval | Apache-2.0 ⚠ | **Default**; first-class in Ollama |
| bge-small-en / bge-base | 384 / 768 | small | Strong quality/size; multilingual variants | MIT ⚠ | Great CPU choice |
| mxbai-embed-large | 1024 | medium | Higher-quality retrieval | Apache-2.0 ⚠ | Use when quality > speed |
| all-MiniLM-L6-v2 | 384 | tiny | Very fast baseline | Apache-2.0 ⚠ | Lightweight fallback |

## Guidance
- **Default:** `nomic-embed-text` on the primary CPU-only machine — fast, good quality, easy via Ollama.
- **Fix the embedding model per index.** Changing it later requires **re-embedding** the whole corpus.
- Larger dimensions improve recall but increase vector-DB storage and query cost — validate in **M1**.
- The vector database (e.g., Chroma / Qdrant / pgvector) is selected in **Phase 06 / 08**.
