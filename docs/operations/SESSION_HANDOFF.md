# Session Handoff

**Date:** 2026-07-11
**Purpose:** Durable record of session state for continuation across context boundaries.

---

## Rules

1. Chat context is temporary and will be compressed or lost.
2. Repository files are the only durable record across sessions.
3. Before ending a session, persist all findings, decisions, and blockers to
   `docs/operations/` files.
4. Read `CURRENT_WORKING_STATE.md` at session start for latest state.
5. Read `ENVIRONMENT_INVARIANTS.md` for deployment and access rules.
6. Do not rely on chat memory for commit hashes, test results, or deployment state.

## Current session state (2026-07-13)

### Active task

`program/baseline-user-journey-reconstruction` — full product pipeline
reconstruction. Scopes A-F code complete. Scope G: `RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT`.

### SSH policy

> **Canonical:** `docs/operations/ACCESS_AND_TRANSPORT_POLICY.md`

- `SSH_POLICY=DISABLED_BY_DEFAULT` · `SSH_AUTOMATIC_RETRY_LIMIT=0`
- **Next session MUST NOT** probe SSH, retry SSH, or treat SSH absence as a blocker.
- SSH unavailability blocks only `PRODUCTION_DEPLOYMENT_EXECUTION`.

### Completed — all code phases

**Phase 1: Infrastructure**
- Unified LLM runtime (AGENT_MAX_TOKENS, max_tokens_for_role, truncation detection)
- All 20 agents wired to centralized config
- SemanticHypothesis model + Case integration + 5 API endpoints
- State machine guards (ALLOWED_STAGE_TRANSITIONS + _transition_to)
- Old case migration (schema_version=2, provenance markers)
- 3 broken endpoint fixes, 5 missing persistence fixes

**Phase 2: Semantic review/rerun**
- Hypothesis rerun endpoint (POST /semantic-hypotheses/{axis}/rerun)
- UI panel in HumanModelView with accept/dispute/rerun per axis
- CSS styling for hypothesis cards with status badges
- API client methods for all 5 hypothesis operations

**Phase 3-4: Venue + Fit pipeline**
- Full pipeline already operational (verified by audit)
- `build_submission_pack_api` fixed to use selected_venue or investigated_venue
- Added decision log entry for submission pack build

**SSH policy canonicalization**
- `docs/operations/ACCESS_AND_TRANSPORT_POLICY.md` created
- CLAUDE.md updated to reference it
- ENVIRONMENT_INVARIANTS.md, SESSION_HANDOFF.md, CURRENT_WORKING_STATE.md updated
- Production runbook SSH sections marked deprecated
- Repository test: `tests/test_access_transport_policy.py`

### Pending

- **E2E browser verification** — full user journey not yet executed
- **Scope G: Production deploy** — `RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT`
- **Production acceptance** — requires deployment of new code

### Gate results

| Gate | Result |
|------|--------|
| pytest | pending rerun after policy test addition |
| TypeScript | clean (noEmit) |
| Vite build | clean |
| SSH attempts | 0 |

### Production facts

- **Host:** 81.26.176.248 (kairoskop.mindkampf.ru)
- **Currently deployed commit:** `1fc7c0a`
- **Service:** kairoskopion-api on port 8088
- **SSH:** DISABLED — zero retry budget, do not probe
- **LLM provider:** OpenAI-compatible (302.ai proxy), model claude-sonnet-4-5-20250929
