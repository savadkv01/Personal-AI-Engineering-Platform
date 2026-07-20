"""Chunking — split document text into overlapping passages.

Uses LlamaIndex's ``SentenceSplitter`` (proven in the M1 spike) so chunk
boundaries respect sentences. Falls back to a simple character window if
LlamaIndex is unavailable, so the pipeline degrades gracefully.
"""
from __future__ import annotations


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    try:
        from llama_index.core.node_parser import SentenceSplitter

        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return [c for c in splitter.split_text(text) if c.strip()]
    except Exception:
        return _char_window(text, chunk_size * 4, chunk_overlap * 4)


def _char_window(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]
