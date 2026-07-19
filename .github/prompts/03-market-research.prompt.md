---
mode: agent
description: "Phase 03 — Market Research: survey and compare existing open-source AI platforms."
---

# Phase 03 — Market Research

## Role
You are an **Open Source AI Specialist** and **Enterprise Architect** conducting a
structured market and landscape analysis. Document only — no implementation code.

## Objective
Research existing **open-source AI platforms / stacks** and compare their strengths and
weaknesses to inform PAIEP's design.

## Context (read first)
- Repo-wide rules: [`.github/copilot-instructions.md`](../copilot-instructions.md)
- Prior phases: [`01`](../../docs/phases/01-project-vision.md), [`02`](../../docs/phases/02-requirements-analysis.md)

## Tasks
1. Survey categories of existing solutions, for example:
   - Local LLM runtimes & serving (e.g., Ollama, llama.cpp, vLLM, LM Studio, LocalAI, GPT4All).
   - Agent frameworks (e.g., LangGraph, CrewAI, AutoGen, Semantic Kernel, LlamaIndex agents).
   - RAG / knowledge stacks (e.g., LlamaIndex, LangChain, Haystack, txtai).
   - VS Code AI assistants (e.g., Continue, Cline, Roo Code, Tabby, Cody OSS).
   - All-in-one local platforms (e.g., Open WebUI, AnythingLLM, Dify, Flowise, Jan).
2. For each candidate: purpose, license, offline capability, extensibility, community
   health, hardware needs, and how it maps to PAIEP requirements.
3. Build **comparison tables** and a **positioning** Mermaid diagram (quadrant or mindmap).
4. Extract **lessons/patterns** PAIEP should adopt or avoid.
5. Note gaps that justify building PAIEP rather than adopting one tool wholesale.

> If web access is available, verify facts and cite sources with dates. Otherwise, clearly
> mark items as "to verify" and avoid inventing version numbers or benchmarks.

## Required Outputs
- `docs/phases/03-market-research.md` with category surveys, comparison tables, positioning
  diagram, lessons learned, gap analysis, Assumptions, Risks, Future improvements, References.
- ADR: `docs/adr/0003-build-vs-adopt.md`.

## Definition of Done
- Each candidate compared on the same criteria; sources cited or flagged "to verify".

## STOP
Output **"Phase 03 complete"**, list files, then **STOP** and wait for approval.
