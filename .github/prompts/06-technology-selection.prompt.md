---
mode: agent
description: "Phase 06 — Technology Selection: compare open-source options per layer and recommend one reference architecture."
---

# Phase 06 — Technology Selection

## Role
You are a **Principal Software Engineer**, **MLOps**, and **DevOps Engineer** selecting the
technology stack. Document only — no implementation code.

## Objective
Compare major open-source technologies for each platform layer and recommend **one complete
reference architecture**.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md) … [`05`](../../docs/phases/05-enterprise-architecture.md)

## Layers to Compare (one table each)
- **LLM runtime / serving** (e.g., Ollama, llama.cpp, vLLM, LocalAI)
- **Agent frameworks** (e.g., LangGraph, CrewAI, AutoGen, Semantic Kernel)
- **RAG orchestration** (e.g., LlamaIndex, LangChain, Haystack)
- **Embeddings** (local embedding models)
- **Vector databases** (e.g., Qdrant, Chroma, Milvus, pgvector, Weaviate)
- **Memory** (short/long-term memory stores & strategies)
- **Workflow orchestration** (e.g., Prefect, Temporal, n8n, Airflow — justify weight)
- **Monitoring** (e.g., Prometheus, Grafana, Langfuse)
- **Logging** (e.g., Loki, OpenTelemetry)
- **Security** (secrets, local auth, sandboxing)
- **UI** (e.g., Open WebUI, AnythingLLM, custom)
- **VS Code integration** (Continue, Cline, Roo Code, MCP)

## Design Discipline
Every option: Why · Benefits · Drawbacks · Alternatives · Complexity · Cost · Hardware
impact · Future scalability. Then pick a **winner per layer** and justify.

## Required Outputs
- `docs/phases/06-technology-selection.md` with per-layer comparison tables, per-layer
  recommendation, and a consolidated **reference architecture** (Mermaid).
- ADR: `docs/adr/0007-reference-stack.md` (the chosen end-to-end stack).
- Assumptions, Risks, Future improvements, References.

## STOP
Output **"Phase 06 complete"**, list files, then **STOP** and wait for approval.
