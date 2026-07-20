"""PAIEP RAG query path (M4) — the read path.

embed query -> retrieve top-k (scope/tags filters) -> optional re-rank ->
assemble budgeted, cited context -> grounded generation. Public entry point:
``engine.answer``, wrapped by the ``scripts/rag-query.py`` CLI.
"""
