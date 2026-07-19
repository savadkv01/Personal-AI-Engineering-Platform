#!/usr/bin/env bash
# PAIEP — pull default models into Ollama for the active hardware profile. [M1]
# ---------------------------------------------------------------------------
# Reads config/models.yaml + docker/.env, ensures Ollama is running, then pulls
# each non-null model tier for PAIEP_PROFILE. Idempotent (ollama pull is a
# no-op if already present) and offline-friendly after the first pull.
#
# Usage:  scripts/pull-models.sh [profile] [model ...]
#   profile   override PAIEP_PROFILE (cpu|gpu|server); default: .env value.
#   model...  pull exactly these tags instead of the catalog (advanced).
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
MODELS_YAML="${REPO_ROOT}/config/models.yaml"

log()  { printf '\033[36m[pull-models]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[pull-models] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# --- Load environment (profile, project name) ------------------------------
[ -f "${DOCKER_DIR}/.env" ] || fail "docker/.env not found — run scripts/bootstrap.sh first."
# Tolerate CRLF line endings (files may be edited on Windows).
set -a; . <(sed 's/\r$//' "${DOCKER_DIR}/.env"); set +a
PROFILE="${1:-${PAIEP_PROFILE:-cpu}}"; shift || true

# --- Resolve the model list ------------------------------------------------
if [ "$#" -gt 0 ]; then
  MODELS=("$@")                       # explicit override
else
  [ -f "${MODELS_YAML}" ] || fail "config/models.yaml not found."
  # Minimal, dependency-free YAML read: emit non-null tags for the profile.
  mapfile -t MODELS < <(PROFILE="${PROFILE}" python3 - "${MODELS_YAML}" <<'PY'
import sys, os
profile = os.environ["PROFILE"]
path = sys.argv[1]
in_profiles = False; in_profile = False; base = None
for raw in open(path):
    line = raw.rstrip("\n")
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    indent = len(line) - len(line.lstrip())
    key = line.strip().split(":", 1)[0]
    if indent == 0:
        in_profiles = (key == "profiles"); in_profile = False; continue
    if in_profiles and indent == 2:
        in_profile = (key == profile); base = None; continue
    if in_profile and indent >= 4 and ":" in line:
        _, val = line.strip().split(":", 1)
        val = val.strip().split("#", 1)[0].strip()
        if val and val.lower() != "null":
            print(val)
PY
)
fi

[ "${#MODELS[@]}" -gt 0 ] || fail "No models resolved for profile '${PROFILE}'."
log "Profile '${PROFILE}' → models: ${MODELS[*]}"

# --- Ensure Ollama is up ---------------------------------------------------
cd "${DOCKER_DIR}"
if ! docker compose ps --status running ollama | grep -q ollama; then
  log "Starting Ollama (profile: inference)..."
  docker compose --profile inference up -d ollama
fi
log "Waiting for Ollama to become healthy..."
for _ in $(seq 1 30); do
  if docker compose exec -T ollama ollama list >/dev/null 2>&1; then break; fi
  sleep 2
done
docker compose exec -T ollama ollama list >/dev/null 2>&1 || fail "Ollama not responding."

# --- Pull each model -------------------------------------------------------
for m in "${MODELS[@]}"; do
  log "Pulling ${m} ..."
  docker compose exec -T ollama ollama pull "${m}"
done

log "Installed models:"
docker compose exec -T ollama ollama list
log "Done."
