# PAIEP — Reference Stack Facts (spike corpus)

All components talk to each other through an OpenAI-compatible API exposed by
the gateway. The gateway is a thin nginx reverse proxy that adds a bearer-token
auth check and a concurrency limit in front of Ollama.

The gateway is published on loopback host port **8081**. The vector database
used for retrieval is **Qdrant**, and retrieval orchestration uses LlamaIndex.
