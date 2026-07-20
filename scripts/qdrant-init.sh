#!/usr/bin/env bash
# PAIEP — bootstrap Qdrant collections + payload indexes from the catalog. [M2]
# ---------------------------------------------------------------------------
# Reads config/index-catalog.yaml and, idempotently, creates each collection
# (vector size = embedding dim, distance metric) plus the shared payload
# indexes (scope/source/tags) that RAG (M3/M4) and memory (M5) filter on.
#
# Dependency-free: uses only python3 stdlib (urllib) against Qdrant's REST API
# and a tiny catalog parser. Offline-friendly — talks only to the local Qdrant.
#
# Usage:  scripts/qdrant-init.sh [--verify]
#   --verify   after creating, run an insert + filtered-search smoke test
#              against a throwaway collection, then delete it.
#
# Env overrides:
#   QDRANT_URL        full REST base url (default: from docker/.env, else
#                     http://127.0.0.1:6333)
#   CATALOG           path to the index catalog (default: config/index-catalog.yaml)
#   SKIP_COMPOSE=1    never try to `docker compose up` Qdrant (assume reachable)
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
CATALOG="${CATALOG:-${REPO_ROOT}/config/index-catalog.yaml}"

log()  { printf '\033[36m[qdrant-init]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[qdrant-init] WARN:\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[31m[qdrant-init] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 is required."
[ -f "${CATALOG}" ] || fail "catalog not found: ${CATALOG}"

# --- Resolve the Qdrant REST URL -------------------------------------------
if [ -z "${QDRANT_URL:-}" ]; then
  if [ -f "${DOCKER_DIR}/.env" ]; then
    # Tolerate CRLF line endings (files may be edited on Windows).
    set -a; . <(sed 's/\r$//' "${DOCKER_DIR}/.env"); set +a
  fi
  QDRANT_URL="http://${BIND_HOST:-127.0.0.1}:${QDRANT_HOST_PORT:-6333}"
fi
log "Qdrant REST: ${QDRANT_URL}"
log "Catalog:     ${CATALOG}"

# --- Small health probe (python stdlib) ------------------------------------
health() {
  QDRANT_URL="${QDRANT_URL}" python3 - <<'PY'
import os, sys, urllib.request
url = os.environ["QDRANT_URL"].rstrip("/") + "/healthz"
try:
    with urllib.request.urlopen(url, timeout=3) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
}

# --- Ensure Qdrant is up (best effort) -------------------------------------
if health; then
  log "Qdrant already healthy."
elif [ "${SKIP_COMPOSE:-0}" = "1" ]; then
  fail "Qdrant unreachable at ${QDRANT_URL} and SKIP_COMPOSE=1."
else
  if command -v docker >/dev/null 2>&1 && [ -f "${DOCKER_DIR}/docker-compose.yml" ]; then
    log "Qdrant not reachable — starting the 'vectordb' profile..."
    ( cd "${DOCKER_DIR}" && docker compose --profile vectordb up -d qdrant )
  else
    warn "docker/compose not available; expecting Qdrant to come up externally."
  fi
  log "Waiting for Qdrant to become healthy..."
  for _ in $(seq 1 30); do health && break; sleep 2; done
  health || fail "Qdrant did not become healthy at ${QDRANT_URL}."
  log "Qdrant is healthy."
fi

# --- Create collections + payload indexes from the catalog -----------------
VERIFY="0"; [ "${1:-}" = "--verify" ] && VERIFY="1"

QDRANT_URL="${QDRANT_URL}" CATALOG="${CATALOG}" VERIFY="${VERIFY}" python3 - <<'PY'
import json, os, sys, urllib.request, urllib.error

BASE = os.environ["QDRANT_URL"].rstrip("/")
CATALOG = os.environ["CATALOG"]
VERIFY = os.environ.get("VERIFY") == "1"

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode() or "{}"
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}

def parse_catalog(path):
    """Tiny tolerant reader for the fixed index-catalog.yaml schema."""
    default_distance = "Cosine"
    payload_indexes, collections = [], {}
    section = None; cur = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n").replace("\t", "  ")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        # Drop trailing inline comments (" # ...") — never appears inside values.
        s = s.split(" #", 1)[0].rstrip()
        if not s:
            continue
        if indent == 0:
            section = s.split(":", 1)[0]
            continue
        if section == "qdrant" and indent == 2 and ":" in s:
            k, v = (x.strip() for x in s.split(":", 1))
            v = v.split(" #", 1)[0].strip()
            if k == "distance" and v:
                default_distance = v
        elif section == "payload_indexes" and s.startswith("-"):
            inner = s.lstrip("-").strip().strip("{}")
            d = {}
            for part in inner.split(","):
                if ":" in part:
                    pk, pv = (x.strip() for x in part.split(":", 1))
                    d[pk] = pv
            if d.get("field"):
                payload_indexes.append((d["field"], d.get("schema", "keyword")))
        elif section == "collections":
            if indent == 2 and s.endswith(":"):
                cur = s[:-1].strip(); collections[cur] = {}
            elif indent >= 4 and cur and ":" in s:
                k, v = (x.strip() for x in s.split(":", 1))
                v = v.split(" #", 1)[0].strip()
                collections[cur][k] = v
    for name, c in collections.items():
        c.setdefault("distance", default_distance)
        c["dim"] = int(c["dim"])
    return default_distance, payload_indexes, collections

default_distance, payload_indexes, collections = parse_catalog(CATALOG)
if not collections:
    print("[qdrant-init] ERROR: no collections found in catalog", file=sys.stderr)
    sys.exit(1)

created, existed = 0, 0
for name, c in collections.items():
    st, _ = req("GET", f"/collections/{name}")
    if st == 200:
        existed += 1
        print(f"  = {name}: exists (dim={c['dim']}, {c['distance']}) — leaving as-is")
    else:
        st, resp = req("PUT", f"/collections/{name}",
                       {"vectors": {"size": c["dim"], "distance": c["distance"]}})
        if st != 200 or not resp.get("result", True):
            print(f"[qdrant-init] ERROR creating {name}: {st} {resp}", file=sys.stderr)
            sys.exit(1)
        created += 1
        print(f"  + {name}: created (dim={c['dim']}, {c['distance']}, "
              f"model={c.get('embed_model','?')})")
    # Payload indexes (idempotent — re-creating an existing index is a no-op/200).
    for field, schema in payload_indexes:
        st, resp = req("PUT", f"/collections/{name}/index?wait=true",
                       {"field_name": field, "field_schema": schema})
        if st not in (200, 409):
            print(f"[qdrant-init] WARN index {name}.{field}: {st} {resp}", file=sys.stderr)

print(f"[qdrant-init] collections: {created} created, {existed} already present; "
      f"payload indexes ensured: {[f for f,_ in payload_indexes]}")

# --- Optional insert + filtered-search smoke test --------------------------
if VERIFY:
    sample = next(iter(collections.values()))
    dim = sample["dim"]; dist = sample["distance"]
    probe = "_paiep_verify"
    req("DELETE", f"/collections/{probe}")
    st, _ = req("PUT", f"/collections/{probe}", {"vectors": {"size": dim, "distance": dist}})
    for field, schema in payload_indexes:
        req("PUT", f"/collections/{probe}/index?wait=true",
            {"field_name": field, "field_schema": schema})
    vec_a = [0.1] * dim
    vec_b = [0.9] * dim
    points = {"points": [
        {"id": 1, "vector": vec_a,
         "payload": {"scope": "global", "source": "verify", "tags": ["alpha"]}},
        {"id": 2, "vector": vec_b,
         "payload": {"scope": "project:demo", "source": "verify", "tags": ["beta"]}},
    ]}
    req("PUT", f"/collections/{probe}/points?wait=true", points)
    # Filtered search: only scope=project:demo should come back.
    st, resp = req("POST", f"/collections/{probe}/points/search", {
        "vector": vec_b, "limit": 5, "with_payload": True,
        "filter": {"must": [{"key": "scope", "match": {"value": "project:demo"}}]},
    })
    hits = resp.get("result", [])
    ids = [h.get("id") for h in hits]
    ok = ids == [2]
    print(f"[qdrant-init] verify: filtered search scope=project:demo -> ids={ids} "
          f"({'PASS' if ok else 'FAIL'})")
    req("DELETE", f"/collections/{probe}")
    if not ok:
        sys.exit(1)
PY

log "Done."
