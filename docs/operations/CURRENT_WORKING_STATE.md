# Current Working State

**Last updated:** 2026-07-13
**Branch:** `program/baseline-user-journey-reconstruction`
**Branch HEAD:** `0e1dbf0`
**Latest main commit:** `0e1dbf0`
**Currently deployed commit:** `1fc7c0a`
**Active task:** `program/baseline-user-journey-reconstruction`

---

## Deployment status: RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT

SSH disabled (`SSH_POLICY=DISABLED_BY_DEFAULT`, `SSH_AUTOMATIC_RETRY_LIMIT=0`).
Code-phase work complete. Production deploy requires non-SSH contour.
See `docs/operations/ACCESS_AND_TRANSPORT_POLICY.md`.

### Available transports

| Transport | Status |
|-----------|--------|
| Local code & tests | Available |
| Browser / UI | Available |
| HTTP API (prod) | Available (basic auth) |
| GitHub push | Available |
| SSH / SCP / SFTP | Disabled |

## Baseline product reconstruction — status by scope

### A. Canonical persisted case runtime — COMPLETE
- CaseStore JSON persistence with user-scoped paths
- `schema_version=2`, provenance markers for old cases
- State machine guards (`ALLOWED_STAGE_TRANSITIONS`, `_transition_to()`)
- All mutations save to store

### B. Unified semantic hypothesis mechanism — COMPLETE
- `SemanticHypothesis` + `SemanticHypothesisEntry` in schema.py
- 5 Case methods: get/set/accept/dispute/rerun per axis
- Auto-populated from article model (genre, method, novelty_mode, discipline)
- 5 API endpoints: GET list, GET axis, POST accept, POST dispute, POST rerun
- UI panel with accept/dispute/rerun buttons and status badges
- Version history tracking on updates

### C. Unified LLM runtime — COMPLETE
- `AGENT_MAX_TOKENS` with 21 per-agent defaults
- `max_tokens_for_role(role_id)` with env var override
- All 20 agent files wired via centralized config
- Truncation detection in `classify_llm_response`

### D. Real pipeline graph — OPERATIONAL (pre-existing)
- AgentMap component with workflow tabs, layer view, agent details
- `/agents/map` endpoint serving runtime graph
- 31 operational agents visible

### E. Full user journey — OPERATIONAL
Pipeline stages all functional:
1. Intake (text/file/URL) → InputClassifierAgent
2. ArticleModel → ArticleModelerAgent (LLM + deterministic)
3. SemanticProfile → ArticleSemanticProfilerAgent
4. Confirm article → protected core, decisions
5. Scenario → SubmissionScenario
6. Pathways → DisciplinaryPathwayMapper
7. Venue Discovery / Direct Investigation → VenueProfilerAgent
8. Select Venue → auto-chains fit/mismatch/rewrite
9. FitAssessment (12-axis) + FPM fit
10. MismatchMap + MismatchNarrator (batch + per-axis rescue)
11. RewritePlan (LLM + deterministic)
12. RiskReport (LLM risk officer)
13. CitationPlan (structural + LLM upgrade)
14. ComplianceChecklist (with error placeholder guarantee)
15. SubmissionPack
16. Dossier (human + technical views)

### F. Migration — COMPLETE
- schema_version field (current=2)
- Old cases stamped with `migrated_from_schema=1`, `rerun_available=true`
- Provenance exposed in `to_dict()` for UI migration banners

### G. Production deployment — RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT
No non-SSH deployment contour configured.
Code is release-ready; deploy blocked only at `PRODUCTION_DEPLOYMENT_EXECUTION`.

## Bug fixes this session
- 3 broken API endpoints: `set-depth-mode`, `set-budget`, `cost-estimate` (NameError)
- 5 missing `store.save(case)` calls
- `build_submission_pack_api` now uses `selected_venue or investigated_venue`
- Test fixes: 3 decision_log assertions updated for relative counts

## Gate results

| Gate | Result |
|------|--------|
| pytest | 3309 passed, 8 deselected |
| TypeScript | clean (noEmit) |
| Vite build | clean |
| SSH attempts | 0 |

## Files changed (uncommitted)

### Backend
- `src/kairoskopion/llm/config.py` — AGENT_MAX_TOKENS, max_tokens_for_role()
- `src/kairoskopion/llm/attempt_metadata.py` — truncation detection
- `src/kairoskopion/schema.py` — SemanticHypothesis, SemanticHypothesisEntry
- `src/kairoskopion/ids.py` — semantic_hypothesis_id()
- `src/kairoskopion/api/cases.py` — state machine, hypotheses, migration, bug fixes, submission pack fix
- `src/kairoskopion/api/app.py` — 5 hypothesis endpoints, 3 endpoint fixes, persistence
- 20 agent files — max_tokens_for_role() wiring

### Frontend
- `ui/src/api/client.ts` — 5 semantic hypothesis API methods
- `ui/src/components/HumanModelView.tsx` — hypothesis panel UI
- `ui/src/styles/cockpit.css` — hypothesis panel styles

### Tests
- `tests/test_api_cases.py` — 10 new tests (stage, hypothesis, migration, fixes)

### Docs
- `docs/operations/BASELINE_PRODUCT_RECONSTRUCTION_INVENTORY.md`
- `docs/operations/CURRENT_WORKING_STATE.md`
- `docs/operations/SESSION_HANDOFF.md`
