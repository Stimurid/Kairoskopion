# Environment Invariants

**Last updated:** 2026-07-10

These rules are permanent until explicitly changed by the repository owner.
Chat context is temporary — these files are the source of truth.

---

## SSH is disabled

- SSH access to the production host is **disabled by owner environment policy**.
- SSH retry limit: **zero**.
- No SSH, SCP, SFTP, port-22 probes, or SSH retries are permitted.
- Any deployment workflow that depends on SSH must use an alternative
  contour or return `DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR`.

## Deployment contour

- **Production host:** 81.26.176.248 (kairoskop.mindkampf.ru)
- **Service:** `kairoskopion-api` on port 8088 behind nginx
- **App path:** `/opt/kairoskopion/app`
- **Deploy method:** Non-SSH contour required. If no working non-SSH
  deployment path is available, push main and return
  `DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR` with the exact merge commit.

## Session handoff rules

- All active blockers must be written to repository files before session ends.
- Next steps must be recorded in `docs/operations/CURRENT_WORKING_STATE.md`.
- Do not rely on chat memory for deployment state, commit hashes, or
  test results — persist them in repository files.
- Relative dates in task descriptions must be converted to absolute dates.

## Repository as source of truth

- Chat context is compressed and eventually lost.
- Repository files are the only durable record.
- Any finding, decision, or blocker discovered during a session must be
  persisted to the appropriate `docs/operations/` file before the session
  ends or context is lost.
