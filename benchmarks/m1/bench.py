#!/usr/bin/env python3
"""PAIEP M1 benchmark harness — measured CPU inference numbers (never invented).

Drives Ollama's native /api/generate endpoint (richer metrics than /v1) and
records, per run:
  * first-token latency (TTFT)  — wall-clock to the first streamed token
  * generation throughput       — eval_count / eval_duration (tokens/s)
  * prompt eval + load time      — from Ollama's response metrics
  * peak container RAM           — sampled from `docker stats` during the run

Stdlib only (urllib/json/threading) so it runs offline with no pip installs.
Results are written as JSON to benchmarks/m1/results/ and summarised as a
Markdown table row for benchmarks/m1/README.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PROMPT = (
    "Write a Python function `is_prime(n)` that returns True if n is prime. "
    "Include a short docstring and handle n < 2. Then show one example call."
)


def sample_peak_ram_mib(container: str, stop: threading.Event) -> list[float]:
    """Poll `docker stats` for a container's RAM; return all samples in MiB."""
    samples: list[float] = []
    while not stop.is_set():
        try:
            out = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container],
                capture_output=True, text=True, timeout=15,
            ).stdout.strip()
            # Format: "1.234GiB / 31.3GiB"  → take the used side.
            used = out.split("/")[0].strip()
            num = float("".join(c for c in used if (c.isdigit() or c == ".")))
            if "GiB" in used:
                num *= 1024
            elif "kB" in used or "KiB" in used:
                num /= 1024
            if num > 0:
                samples.append(num)
        except Exception:
            pass
        time.sleep(1.0)
    return samples


def one_run(host: str, model: str, prompt: str, num_predict: int = 200) -> dict:
    """One streaming generation; return timing + Ollama metrics.

    Output is capped at num_predict tokens so run duration is bounded and
    comparable across models (throughput is still eval_count/eval_duration).
    """
    url = f"{host.rstrip('/')}/api/generate"
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})

    t0 = time.perf_counter()
    ttft = None
    final: dict = {}
    with urllib.request.urlopen(req, timeout=600) as resp:
        for line in resp:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if ttft is None and msg.get("response"):
                ttft = time.perf_counter() - t0
            if msg.get("done"):
                final = msg
    wall = time.perf_counter() - t0

    eval_count = final.get("eval_count", 0)
    eval_dur_s = final.get("eval_duration", 0) / 1e9
    tok_per_s = (eval_count / eval_dur_s) if eval_dur_s > 0 else 0.0
    return {
        "ttft_s": round(ttft or wall, 3),
        "tokens_per_s": round(tok_per_s, 2),
        "eval_count": eval_count,
        "prompt_eval_count": final.get("prompt_eval_count", 0),
        "load_s": round(final.get("load_duration", 0) / 1e9, 3),
        "prompt_eval_s": round(final.get("prompt_eval_duration", 0) / 1e9, 3),
        "total_s": round(final.get("total_duration", 0) / 1e9, 3),
        "wall_s": round(wall, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="PAIEP M1 inference benchmark")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--num-predict", type=int, default=200,
                    help="cap generated tokens per run for bounded timing")
    ap.add_argument("--container", default="paiep_ollama")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent / "results"))
    args = ap.parse_args()

    print(f"[bench] host={args.host} model={args.model} runs={args.runs} warmup={args.warmup}")

    # RAM sampler runs for the whole session (captures load + generation peak).
    stop = threading.Event()
    ram_samples: list[float] = []
    sampler = threading.Thread(
        target=lambda: ram_samples.extend(sample_peak_ram_mib(args.container, stop))
    )
    sampler.start()

    try:
        for i in range(args.warmup):
            print(f"[bench] warmup {i + 1}/{args.warmup} ...", flush=True)
            one_run(args.host, args.model, args.prompt, args.num_predict)

        runs = []
        for i in range(args.runs):
            r = one_run(args.host, args.model, args.prompt, args.num_predict)
            runs.append(r)
            print(f"[bench] run {i + 1}/{args.runs}: "
                  f"TTFT={r['ttft_s']}s  {r['tokens_per_s']} tok/s  "
                  f"({r['eval_count']} tokens)", flush=True)
    finally:
        stop.set()
        sampler.join()

    peak_ram = round(max(ram_samples), 1) if ram_samples else None
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": args.host,
        "model": args.model,
        "runs": runs,
        "median_ttft_s": round(statistics.median(r["ttft_s"] for r in runs), 3),
        "median_tokens_per_s": round(statistics.median(r["tokens_per_s"] for r in runs), 2),
        "peak_ram_mib": peak_ram,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"{args.model.replace(':', '_').replace('/', '_')}_{stamp}.json"
    out_file.write_text(json.dumps(summary, indent=2))

    print("\n[bench] === summary ===")
    print(f"  median TTFT       : {summary['median_ttft_s']} s")
    print(f"  median throughput : {summary['median_tokens_per_s']} tok/s")
    print(f"  peak RAM          : {summary['peak_ram_mib']} MiB")
    print(f"  saved             : {out_file}")
    print("\n[bench] Markdown row:")
    print(f"| {args.model} | {summary['median_tokens_per_s']} | "
          f"{summary['median_ttft_s']} | {summary['peak_ram_mib']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
