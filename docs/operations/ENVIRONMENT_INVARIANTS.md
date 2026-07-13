# Environment Invariants

**Last updated:** 2026-07-10

These rules are permanent until explicitly changed by the repository owner.
Chat context is temporary — these files are the source of truth.

---

## SSH is disabled

> **Canonical policy:** `docs/operations/ACCESS_AND_TRANSPORT_POLICY.md`

- `SSH_POLICY=DISABLED_BY_DEFAULT`
- `SSH_AUTOMATIC_RETRY_LIMIT=0`
- No SSH, SCP, SFTP, port-22 probes, or SSH retries are permitted.
- SSH unavailability blocks only `PRODUCTION_DEPLOYMENT_EXECUTION`.
- Correct status when deploy is blocked: `RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT`.
- ~~`DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR`~~ — **deprecated**, do not use.

## Deployment contour

- **Production host:** 81.26.176.248 (kairoskop.mindkampf.ru)
- **Service:** `kairoskopion-api` on port 8088 behind Caddy (reverse proxy)
- **App path:** `/opt/kairoskopion/app`
- **Deploy method:** Non-SSH contour required. See `ACCESS_AND_TRANSPORT_POLICY.md`
  fallback ladder. If no working non-SSH deployment path is available, push main
  and report `RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT`.

### Available transports (2026-07-13)

| Transport | Status |
|-----------|--------|
| Local code & tests | Available |
| Browser / UI | Available |
| HTTP API (prod) | Available (basic auth) |
| GitHub push | Available |
| SSH / SCP / SFTP | Disabled |
| Cloud control plane | Not configured |
| Pull-based deploy | Not configured |

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
