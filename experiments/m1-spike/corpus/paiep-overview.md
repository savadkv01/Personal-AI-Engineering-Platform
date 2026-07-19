# PAIEP — Platform Overview (spike corpus)

The Personal AI Engineering Platform (PAIEP) is an offline-first, local AI
engineering platform. Its primary target machine is CPU-only with 32 GB of RAM,
so the default interactive model is a 7B model quantized to Q4_K_M.

The default coding and chat model is **qwen2.5-coder:7b**, served locally by
Ollama. Embeddings are produced by **nomic-embed-text**.
