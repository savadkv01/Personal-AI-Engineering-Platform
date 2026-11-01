"""Model router + chat client (FR-003).

``ModelRouter`` resolves a persona tier to a model for the active hardware profile,
falling back to installed models. ``ChatClient`` calls the OpenAI-compatible gateway
(default) or native Ollama, requesting JSON-schema-constrained output so small local
models stay on-format; responses are parsed and validated by the caller.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


class LLMError(RuntimeError):
    pass


@dataclass
class ChatResult:
    text: str
    data: dict | None
    model: str
    tier: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


@dataclass
class RouterConfig:
    kind: str = "openai"
    base_url: str = "http://gateway/v1"
    token: str | None = None
    request_timeout: float = 600
    default_model: str = "qwen2.5-coder:7b"
    profile: str = "cpu"
    profiles: dict[str, dict[str, str]] = field(default_factory=dict)
    fallback: dict[str, list[str]] = field(default_factory=dict)
    tier_options: dict[str, dict] = field(default_factory=dict)


def load_router_config(path: str | None = None) -> RouterConfig:
    p = Path(path or os.environ.get("ROUTER_CONFIG") or REPO_ROOT / "config" / "router.yaml")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    ep = raw.get("endpoint") or {}
    return RouterConfig(
        kind=os.environ.get("ROUTER_ENDPOINT_KIND", ep.get("kind", "openai")),
        base_url=os.environ.get("ROUTER_BASE_URL", ep.get("base_url", "http://gateway/v1")).rstrip("/"),
        token=os.environ.get(ep.get("token_env", "GATEWAY_TOKEN")),
        request_timeout=float(ep.get("request_timeout", 600)),
        default_model=raw.get("default_model", "qwen2.5-coder:7b"),
        profile=os.environ.get("PAIEP_PROFILE", "cpu"),
        profiles=raw.get("profiles") or {},
        fallback=raw.get("fallback") or {},
        tier_options=raw.get("tier_options") or {},
    )


class ModelRouter:
    def __init__(self, cfg: RouterConfig, available: set[str] | None = None):
        self.cfg = cfg
        self.available = available   # None = unknown (no filtering)

    @staticmethod
    def _present(model: str, available: set[str]) -> bool:
        return model in available or (":" not in model and f"{model}:latest" in available)

    def resolve(self, tier: str) -> str:
        table = self.cfg.profiles.get(self.cfg.profile) or self.cfg.profiles.get("cpu") or {}
        for t in [tier, *self.cfg.fallback.get(tier, [])]:
            model = table.get(t)
            if model and (self.available is None or self._present(model, self.available)):
                return model
        return self.cfg.default_model

    def options(self, tier: str) -> dict:
        return dict(self.cfg.tier_options.get(tier) or {})


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse_json(text: str) -> dict | None:
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except (json.JSONDecodeError, TypeError):
        m = _JSON_BLOCK.search(text or "")
        if m:
            try:
                v = json.loads(m.group(0))
                return v if isinstance(v, dict) else None
            except json.JSONDecodeError:
                return None
    return None


class ChatClient:
    def __init__(self, cfg: RouterConfig, router: ModelRouter | None = None):
        self.cfg = cfg
        self.router = router or ModelRouter(cfg)

    def _post(self, url: str, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.cfg.kind == "openai" and self.cfg.token:
            headers["Authorization"] = f"Bearer {self.cfg.token}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.request_timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise LLMError(f"HTTP {exc.code} from {url}: {exc.read().decode()[:300]}") from exc
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"model call failed ({url}): {exc}") from exc

    def list_models(self) -> set[str]:
        try:
            if self.cfg.kind == "openai":
                req = urllib.request.Request(self.cfg.base_url + "/models",
                                             headers={"Authorization": f"Bearer {self.cfg.token or ''}"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return {m["id"] for m in json.loads(resp.read().decode()).get("data", [])}
            with urllib.request.urlopen(self.cfg.base_url + "/api/tags", timeout=15) as resp:
                return {m["name"] for m in json.loads(resp.read().decode()).get("models", [])}
        except Exception:  # noqa: BLE001 - unknown availability => no filtering
            return set()

    def complete(self, messages: list[dict], *, tier: str, schema: dict | None = None,
                 max_tokens: int | None = None) -> ChatResult:
        model = self.router.resolve(tier)
        opts = self.router.options(tier)
        temperature = float(opts.get("temperature", 0.1))
        n_out = int(max_tokens or opts.get("max_tokens", 700))
        t0 = time.perf_counter()
        if self.cfg.kind == "openai":
            body = {"model": model, "messages": messages, "temperature": temperature,
                    "max_tokens": n_out, "stream": False}
            if schema:
                body["response_format"] = {"type": "json_schema",
                                           "json_schema": {"name": "agent_output", "schema": schema}}
            data = self._post(self.cfg.base_url + "/chat/completions", body)
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            pt, ct = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        else:
            body = {"model": model, "messages": messages, "stream": False,
                    "options": {"temperature": temperature, "num_predict": n_out}}
            if schema:
                body["format"] = schema
            data = self._post(self.cfg.base_url + "/api/chat", body)
            text = (data.get("message") or {}).get("content") or ""
            pt, ct = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
        ms = (time.perf_counter() - t0) * 1000
        return ChatResult(text=text.strip(), data=parse_json(text) if schema else None, model=model,
                          tier=tier, prompt_tokens=int(pt or 0), completion_tokens=int(ct or 0),
                          latency_ms=round(ms, 1))
