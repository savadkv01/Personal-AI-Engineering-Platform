#!/usr/bin/env bash
# PAIEP — M0 bootstrap.
# Verifies prerequisites and brings up the baseline skeleton.
# Idempotent, offline-first, reversible. Run inside WSL2/Ubuntu from any dir.
#
# Usage:  scripts/bootstrap.sh [profile]   (default profile: core)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
PROFILE="${1:-core}"

log()  { printf '\033[36m[bootstrap]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[bootstrap] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Prerequisites --------------------------------------------------------
command -v docker >/dev/null 2>&1 || fail "docker not found. Install Docker Desktop (WSL2 backend)."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 not found ('docker compose')."
docker info >/dev/null 2>&1 || fail "Docker daemon not reachable. Is Docker Desktop running?"
log "Docker:  $(docker --version)"
log "Compose: $(docker compose version --short)"

# 2. Environment file (never overwrite an existing .env) ------------------
if [ ! -f "${DOCKER_DIR}/.env" ]; then
  cp "${DOCKER_DIR}/.env.example" "${DOCKER_DIR}/.env"
  log "Created docker/.env from .env.example"
else
  log "docker/.env already present — leaving untouched"
fi
set -a; . "${DOCKER_DIR}/.env"; set +a

# 3. Validate + bring up --------------------------------------------------
cd "${DOCKER_DIR}"
log "Validating compose file..."
docker compose config -q
log "Starting profile '${PROFILE}'..."
docker compose --profile "${PROFILE}" up -d

# 4. Report ---------------------------------------------------------------
docker compose --profile "*" ps
if [ "${PROFILE}" = "core" ]; then
  log "Health probe: http://${BIND_HOST:-127.0.0.1}:${PING_HOST_PORT:-8080}/"
fi
log "Done."
