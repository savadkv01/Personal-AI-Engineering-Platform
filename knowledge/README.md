# Knowledge Base — Seed Design Notes

> Seed notes for the knowledge base, notes, and book library. Full design:
> [`docs/phases/08-knowledge-memory.md`](../docs/phases/08-knowledge-memory.md) §7–§11.

## Structure

```text
knowledge/
  notes/         # personal notes (Markdown + front-matter)
  references/    # curated external refs + summaries
  books/         # your notes/summaries + library index (NOT copyrighted full text)
  domains/       # topical folders (ai/, data-eng/, devops/, ...)
  index.md       # top-level catalog
```

## Front-matter (every item)
`title` · `tags` · `source` · `scope` (`global`/`project:<name>`) · `created` · `updated`.

## Taxonomy
Primary axis = **domain** (folders); secondary axis = **tags** (cross-cutting). Stable kebab-case slugs;
relative + wiki-style `[[links]]`.

## Notes
Markdown, git-friendly, quick-capture; indexed into `kb_docs` for RAG.

## Book library ⚠
- Ingest only books you **own/are licensed** to use (personal, offline).
- **Do not commit copyrighted full text** to the repo. Originals + derived full-text live in the local
  `paiep_kb` volume (git-ignored); the repo holds only **your notes/summaries + an index**.
- Retain source metadata for citation.

## Ingestion
Indexed via LlamaIndex into Qdrant (`kb_docs`, `doc_type` = note/doc/book/web). Fixed embedding model per
collection; incremental re-ingest by `content_hash`. Curated by the Knowledge Manager agent (dedupe, tag,
prune — FR-023/024).
