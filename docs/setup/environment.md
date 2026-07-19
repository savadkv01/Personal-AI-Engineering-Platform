# Detected Development Environment (Primary Target Machine)

> Auto-detected on **2026-07-19**. This is the concrete machine PAIEP must run on today and is
> the **primary target** for all phase and milestone prompts. Keep this file updated if the
> hardware or tooling changes; prompts reference it as the single source of truth.

## 1. Hardware & OS

| Item | Value |
|------|-------|
| Machine | HP EliteBook 840 G7 Notebook PC |
| OS | Windows 11 Pro (build 26200) |
| CPU | Intel Core i7-10610U — 4 cores / 8 threads @ 1.80 GHz (Comet Lake-U, mobile) |
| RAM | 32 GB (31.78 GB usable) |
| GPU | Intel UHD Graphics (integrated, ~1 GB shared) — **no discrete GPU, no CUDA/ROCm** |
| Storage | C: 952 GB total, ~485 GB free |

## 2. Virtualization & Containers

| Item | Value |
|------|-------|
| WSL | WSL2 enabled; default distro **Ubuntu-22.04** (also Ubuntu-24.04 present) |
| Docker | Docker Desktop — Engine **29.1.3** |
| Compose | Compose **v2** (bundled `v5.0.0-desktop.1`) — use `docker compose` (space, not hyphen) |
| Docker backend | `docker-desktop` WSL2 distro running |

## 3. Effective Hardware Profile

This machine is a **hybrid "Profile A+"**: it has **Profile B's memory (32 GB)** but
**Profile A's compute (CPU-only, no dedicated GPU)**.

| Aspect | Reality | Consequence |
|--------|---------|-------------|
| Inference device | **CPU only** | Prefer CPU-optimized runtimes (Ollama / llama.cpp). Avoid CUDA-only stacks (e.g., default vLLM) as primary. |
| Memory | 32 GB | Can hold larger quantized models than a 16 GB laptop, but throughput is CPU-bound. |
| GPU accel | None usable | No GPU passthrough; drop GPU sections of prompts for this machine. |
| Disk | ~485 GB free | Ample for multiple quantized models + vector data. |

## 4. Realistic Local Model Tiers (CPU-only, 32 GB)

> Guidance for CPU inference with GGUF quantization (validated numbers to be confirmed in Phase 04/M1).

| Tier | Example size / quant | Expected experience |
|------|----------------------|---------------------|
| Snappy | 1B–4B @ Q4_K_M | Fast, good for autocomplete/simple agents |
| **Sweet spot** | 7B–8B @ Q4_K_M / Q5_K_M | Best balance of quality vs speed for interactive use |
| Quality | 13B–14B @ Q4_K_M | Higher quality, noticeably slower first-token/throughput |
| Stretch | >14B | Fits in RAM but likely too slow for interactive work |

Embedding models (small, e.g., `nomic-embed-text`, `bge-small`) run comfortably on CPU.

## 5. Recommended Resource Configuration

- **WSL2 memory cap** (`%UserProfile%\.wslconfig`): allocate ~24 GB to WSL, leave ~8 GB for Windows.
  ```ini
  [wsl2]
  memory=24GB
  processors=8
  swap=8GB
  ```
- **Docker Desktop**: use the WSL2 backend; set resource limits consistent with `.wslconfig`.
- Keep model weights on the fast internal SSD (C:), inside a Docker named volume.

## 6. Constraints & Notes for Prompts

- Treat **CPU-only** as the default execution assumption; mark GPU features as "future / Profile B–D only".
- Interactive latency is the main constraint, not memory. Optimize for smaller/quantized models
  and concurrency limits.
- All services must remain **offline-capable** on this machine.

## 7. Re-detect

To refresh these values, re-run system checks (PowerShell `Get-CimInstance` for OS/CPU/RAM/GPU/disk,
`wsl -l -v`, `docker version`, `docker compose version`) and update this file.

## 8. GPU Acceleration Options (this machine)

This laptop **cannot take an internal discrete GPU** (integrated graphics, soldered; no MXM/PCIe
slot). Acceleration paths, in order of recommendation:

| Option | What it is | VRAM target | Approx. cost* | Notes |
|--------|-----------|-------------|---------------|-------|
| **Stay CPU-only** | Use laptop for dev/orchestration; run 7B–8B Q4/Q5 models | n/a | $0 | Default today. Time/electricity is the "cost", not tokens. |
| **Home AI server (recommended upgrade)** | Cheap used desktop/mini-PC with a GPU on the LAN (Profile D) | 12–24 GB | ~$500–$1200 | Best value & scalability; laptop stays thin client. Feeds Phase 12. |
| **eGPU over Thunderbolt 3** | External GPU enclosure + card via USB-C/TB3 | 12–24 GB | ~$400–$800 | **Verify the 840 G7 unit has Thunderbolt 3** (config-dependent). PCIe bandwidth is fine for inference once weights are in VRAM. |

\* Approximate, verify current market. Enclosure ~$150–$350; used **RTX 3060 12 GB** ~$200–$300
(budget sweet spot); **RTX 4060 Ti 16 GB / RTX 3090 24 GB** ~$400–$800 (higher quality / larger models).

**Guidance:** VRAM ≥ **12 GB** is the key threshold (runs 7B–13B fully on GPU with large speedups);
**24 GB** enables ~30B-class quantized models. For most users a **home AI server** beats an eGPU on
value and future scalability, and aligns with the Profile D roadmap.

## 9. Multi-Workspace Reuse

The platform is designed to serve **all workspaces on this machine**:

- **Backend services** (LLM runtime, vector DB, RAG, memory, agents) run **once** as shared Docker
  containers; every workspace connects to the same local endpoints.
- **Per-workspace config** (`.github/prompts/`, `copilot-instructions.md`, `.vscode/`, MCP hookups)
  is copied into each repo — ideally via a **template repo / cookiecutter**.
- Long-term memory scope (global vs per-project) is decided in Phase 08 / milestone M5.
- Formalized in milestone **M7 (VS Code integration)**.

