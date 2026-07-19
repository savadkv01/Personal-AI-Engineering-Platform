# M10 — Security Hardening & Release

> **Milestone:** M10 · **Layer:** Ops · **Anchor:** O8, NFR-021,
> [Phase 05 §5](../docs/phases/05-enterprise-architecture.md), [ADR 0006](../docs/adr/0006-security-model.md) ·
> **Prompt:** [`.github/prompts/implementation/M10-hardening-release.prompt.md`](../.github/prompts/implementation/M10-hardening-release.prompt.md) ·
> **Roadmap:** [`docs/phases/10-implementation-roadmap.md`](../docs/phases/10-implementation-roadmap.md) ·
> **Status:** Planned (not started) · **Author role:** Security Architect + DevOps/MLOps

> ⚠️ **Plan-only.** Do not implement until the roadmap is approved and M10 is explicitly requested.

---

## Objectives & Scope

Harden the platform and package a reproducible, documented **v1** local release
([Phase 05 §5](../docs/phases/05-enterprise-architecture.md), [ADR 0006](../docs/adr/0006-security-model.md)).

**In scope**
- **Secrets management:** move secrets from Compose into `.env`/secret files; verify none committed (NFR-022).
- **Container hardening:** non-root, read-only mounts where possible, dropped capabilities, **resource limits**
  (protect the 32 GB budget), and **network segmentation** (internal vs. exposed; loopback-only,
  [ADR 0005](../docs/adr/0005-container-topology.md)).
- **Backup/restore** for vector DB, memory, and UI/config volumes (models re-pullable).
- **One-command bring-up** + documented teardown; **v1** versioning + release docs.
- **OWASP-style checklist** for the local deployment; full end-to-end regression (M0–M9), incl. offline.

**Out of scope:** new features (future roadmap, Phase 12).

## Prerequisites

- Full stack **M0–M9** running.

## Deliverables

| Artifact | Path (planned) |
|----------|----------------|
| Hardened Compose (limits, non-root, segmentation) | `docker/docker-compose.yml` |
| Backup/restore scripts | `scripts/backup.sh`, `scripts/restore.sh` |
| Bring-up/teardown + version | `scripts/bootstrap.sh`, `VERSION` |
| Setup + release docs | `docs/setup/10-hardening-release.md`, `docs/RELEASE.md` |
| ADR | `docs/adr/0014-v1-release-baseline.md` |

## Validation Checklist

- [ ] No secrets committed; secrets loaded from `.env`/secret files only.
- [ ] Containers run non-root with dropped capabilities + resource limits; no OOM under a stress scenario.
- [ ] No service listens outside `127.0.0.1`; internal vs. exposed networks segmented.
- [ ] Backup → **restore** on a clean environment reproduces working state.
- [ ] Single-command bring-up works on a fresh machine matching [`environment.md`](../docs/setup/environment.md).
- [ ] OWASP-style checklist passes (or documented, accepted risks).
- [ ] **Full regression:** M0–M9 checklists re-run green, including offline.

## Rollback Strategy

- Hardening/limits are config — relax an individual limit via `git restore` if a service is starved.
- Backups enable **restore to a prior known-good state** before any risky change.
- Bring-up scripts are additive; the manual M0–M9 flow remains available.

## Documentation to Produce

- Security review + accepted-risk register + backup/restore + release runbook in
  `docs/setup/10-hardening-release.md` and `docs/RELEASE.md`.
- ADR `docs/adr/0014-v1-release-baseline.md`; confirm [ADR 0006](../docs/adr/0006-security-model.md).

## Testing Approach & Expected Outputs

| Test | Method | Expected |
|------|--------|----------|
| Security | port + secret + image scan; OWASP checklist | loopback-only, no leaked secrets, no critical CVEs |
| Resilience | stress within limits | no OOM; graceful behavior |
| DR | backup then restore on clean env | working state reproduced |
| Release | fresh-machine bring-up | full stack healthy |
| Regression | re-run M0–M9 (offline) | all green |

## Troubleshooting Notes

- **Service starved by limits:** raise the specific `mem_limit`/`cpus`; re-test.
- **Restore fails:** verify volume names + backup integrity (checksums) before trusting DR.
- **CVE in a pinned image:** bump to a patched tag; re-verify license + re-run regression.
- **Bring-up non-idempotent:** ensure scripts detect existing state and skip safely.

## Hardware Profiles

- **A:** tighter limits; obs/UI off; minimal footprint validated.
- **A+:** full stack within 32 GB; the reference hardened target.
- **B/C:** higher limits; GPU services included in scans.
- **D:** add **network hardening** (LAN exposure), always-on backups, central observability
  ([ADR 0100](../docs/adr/0100-gpu-and-reuse-strategy.md), Phase 12).
