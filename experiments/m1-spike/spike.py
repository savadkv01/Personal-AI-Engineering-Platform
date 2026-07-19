#!/usr/bin/env python3
"""PAIEP M1 integration spike — thin Ollama -> LlamaIndex -> Qdrant slice.

Proves the reference stack end to end on a tiny corpus (ADR 0007):
  1. Read a few local docs.
  2. Embed them with Ollama (nomic-embed-text) and index into Qdrant.
  3. Answer a question with the Ollama chat model, grounded in retrieved chunks.
  4. Print a CITATION-BACKED answer (source file + similarity score per chunk).

Deep ingestion / RAG / vector-store features come in M2-M4; this is only a
stack-validation spike. Exit code is non-zero unless the answer is grounded in
at least one retrieved source node.
"""
from __future__ import annotations

import os
import sys
import time

from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5-coder:7b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
CORPUS_DIR = os.environ.get("CORPUS_DIR", "/app/corpus")
COLLECTION = "paiep_m1_spike"
QUESTION = os.environ.get(
    "SPIKE_QUESTION",
    "What is PAIEP's default coding model and which host port is the gateway published on?",
)


def wait_for_qdrant(client: "qdrant_client.QdrantClient", tries: int = 30) -> None:
    for _ in range(tries):
        try:
            client.get_collections()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"Qdrant not reachable at {QDRANT_URL}")


def main() -> int:
    print(f"[spike] chat={CHAT_MODEL} embed={EMBED_MODEL}")
    print(f"[spike] ollama={OLLAMA_BASE_URL} qdrant={QDRANT_URL}")

    Settings.llm = Ollama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=600.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    client = qdrant_client.QdrantClient(url=QDRANT_URL)
    wait_for_qdrant(client)

    # Fresh collection each run so the spike is idempotent/repeatable.
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)

    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print(f"[spike] loading corpus from {CORPUS_DIR} ...")
    documents = SimpleDirectoryReader(CORPUS_DIR).load_data()
    print(f"[spike] {len(documents)} document(s); building index (embed + upsert) ...")
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    query_engine = index.as_query_engine(similarity_top_k=3)
    print(f"[spike] Q: {QUESTION}")
    response = query_engine.query(QUESTION)

    print("\n[spike] === grounded answer ===")
    print(str(response).strip())

    sources = getattr(response, "source_nodes", []) or []
    print("\n[spike] === citations ===")
    for i, node in enumerate(sources, 1):
        fname = node.metadata.get("file_name", "unknown")
        score = f"{node.score:.3f}" if node.score is not None else "n/a"
        print(f"  [{i}] {fname}  (score={score})")

    if not sources:
        print("\n[spike] FAIL: answer had no retrieved source nodes (not grounded).")
        return 1
    print("\n[spike] PASS: citation-backed answer produced end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
