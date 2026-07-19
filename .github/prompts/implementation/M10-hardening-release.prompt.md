---
mode: agent
description: "Implementation M10 — Security hardening, backups, and v1 release packaging. Reversible."
---

# Implementation Milestone M10 — Security Hardening & Release

> **Precondition:** M9 complete and approved. Follow repo rules in
> [`../../copilot-instructions.md`](../../copilot-instructions.md).

## Role
You are a **Security Architect / DevOps Engineer** finalizing a v1 baseline release.

## Objective
Harden the platform (secrets, least privilege, network boundaries, backups) and package a
reproducible, documented **v1** local release.

## Prerequisites
- Full stack (M0–M9) running.
- Phase 05 security architecture and Phase 10 release criteria.

## Scope
- **In:** secrets management, container hardening, network segmentation, backup/restore, one-command
  bring-up, versioning, release docs.
- **Out:** new features (future roadmap, Phase 12).

## Tasks
1. Move secrets out of Compose into `.env`/secret files; verify none are committed.
2. Apply least-privilege container settings (non-root, read-only mounts where possible,
   dropped capabilities, resource limits) and segment internal vs exposed networks.
3. Implement **backup/restore** for vector DB, memory, and UI/config volumes.
4. Provide a single-command bring-up and a documented teardown.
5. Tag a **v1** release with `docs/RELEASE.md`, versioned Compose, and a full validation run.
6. Run a lightweight OWASP-style checklist for the local deployment.

## Deliverables
- Hardened `docker/compose.yaml`; backup/restore scripts; `docs/setup/10-hardening-release.md`;
  `docs/RELEASE.md`; ADR `docs/adr/0014-v1-release-baseline.md`.

## Validation Checklist
- [ ] No secrets in git history or Compose; scan passes.
- [ ] Containers run as non-root with resource limits; only intended ports exposed.
- [ ] Backup then restore reproduces working state (data intact).
- [ ] One-command bring-up starts the full stack cleanly; teardown is clean.
- [ ] Security checklist reviewed with findings recorded.

## Expected Outputs
- A reproducible, hardened, documented **v1** local platform.

## Rollback Plan
- Revert to the previous Compose/version tag; restore from the latest known-good backup.

## Troubleshooting
- Permission errors from non-root, restore mismatches, capability drops breaking services, port exposure.

## Documentation to Update
- `docs/setup/10-hardening-release.md`; `docs/RELEASE.md`; `README.md` status → v1.

## Testing
- Full end-to-end validation across a representative hardware profile; backup/restore drill.

## STOP
Output **"Milestone M10 complete"**, list files, confirm validation, then **STOP**. This completes the
v1 implementation; future capabilities follow the Phase 12 roadmap.
