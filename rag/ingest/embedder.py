"""Embeddings via the Ollama runtime (M1). Batched HTTP, dimension-checked."""
from __future__ import annotations

import json
import urllib.request

from .config import ServiceConfig


class EmbedError(RuntimeError):
    pass


def embed_texts(texts: list[str], svc: ServiceConfig) -> list[list[float]]:
    """Embed a list of texts, batching per ``svc.batch_size``."""
    out: list[list[float]] = []
    for i in range(0, len(texts), svc.batch_size):
        batch = texts[i:i + svc.batch_size]
        out.extend(_embed_batch(batch, svc))
    return out


def _embed_batch(batch: list[str], svc: ServiceConfig) -> list[list[float]]:
    url = svc.base_url + svc.endpoint
    body = json.dumps({"model": svc.model, "input": batch}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=svc.request_timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001 - surface a clear ingest error
        raise EmbedError(f"embed request failed ({url}): {exc}") from exc

    vectors = data.get("embeddings")
    if not vectors or len(vectors) != len(batch):
        raise EmbedError(f"expected {len(batch)} embeddings, got {len(vectors or [])}")
    for v in vectors:
        if len(v) != svc.dim:
            raise EmbedError(
                f"embedding dim {len(v)} != configured dim {svc.dim} "
                f"(model={svc.model}); check config/index-catalog.yaml")
    return vectors
