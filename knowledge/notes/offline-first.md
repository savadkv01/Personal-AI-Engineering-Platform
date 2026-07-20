---
title: Offline-First Operation
tags: [offline, privacy, docker, networking]
scope: global
created: 2026-07-20
updated: 2026-07-20
---

# Offline-First Operation

PAIEP is designed to work with the network disabled. Local models are pulled
once and then run entirely offline; the knowledge base and vector store hold
all retrieval data locally.

## Container topology

Services are split across two Docker networks. The `edge` network hosts the
loopback-only published seam (the API gateway), while the `backend` network is
marked internal and has no route to the internet. Data and compute services —
Ollama and Qdrant — live on the backend network, so ingestion and retrieval
succeed even when outbound egress is blocked.

## Privacy

Because nothing leaves the machine by default, personal notes, code, and books
stay private. Any web fetching is strictly opt-in and disabled by default.
