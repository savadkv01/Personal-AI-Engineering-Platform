#!/usr/bin/env bash
# PAIEP M1 — run the inference benchmark against the default chat model. [M1]
# Loads docker/.env for CHAT_MODEL + ports, then drives benchmarks/m1/bench.py.
#
# Usage:  benchmarks/m1/run-bench.sh [model] [runs]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"

[ -f "${DOCKER_DIR}/.env" ] && { set -a; . <(sed 's/\r$//' "${DOCKER_DIR}/.env"); set +a; }

MODEL="${1:-${CHAT_MODEL:-qwen2.5-coder:7b}}"
RUNS="${2:-3}"
HOST="http://${BIND_HOST:-127.0.0.1}:${OLLAMA_HOST_PORT:-11434}"
CONTAINER="${COMPOSE_PROJECT_NAME:-paiep}_ollama"

exec python3 "${REPO_ROOT}/benchmarks/m1/bench.py" \
  --host "${HOST}" --model "${MODEL}" --runs "${RUNS}" --container "${CONTAINER}"
