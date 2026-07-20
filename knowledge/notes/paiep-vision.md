---
title: PAIEP Vision
tags: [paiep, vision, offline-first]
scope: global
created: 2026-07-20
updated: 2026-07-20
---

# PAIEP Vision

The Personal AI Engineering Platform (PAIEP) is a design-first, offline-first
personal AI operating system that runs primarily on a local laptop. It grows
through twelve gated phases, each producing professional documentation and
reusable prompts before any implementation code.

## Principles

- **Offline-first.** Everything possible runs locally; cloud is optional. The
  default runtime is CPU-optimized (Ollama / llama.cpp) with 7B–8B quantized
  models on the primary machine.
- **Design before code.** Architecture, comparisons, and decision records come
  first; implementation lands only in approved, reversible milestones.
- **Model-agnostic.** Models are swappable; nothing downstream hard-codes a
  model name. The active hardware profile selects sensible defaults.

## Target machine

The reference machine is an HP EliteBook 840 G7: Intel i7-10610U, 32 GB RAM,
CPU-only inference. It behaves like a hybrid "A+" profile — plenty of RAM but
no GPU — so interactive latency, not memory, is the binding constraint.
