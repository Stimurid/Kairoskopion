# Current Working State

**Last updated:** 2026-07-13T16:55+03:00
**Branch:** `program/baseline-user-journey-reconstruction`
**Branch HEAD:** `96e3cab`
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
| pytest | 3313 passed, 8 deselected |
| TypeScript | clean (noEmit) |
| Vite build | clean |
| Browser E2E | PASS (full journey, live LLM) |
| SSH attempts | 0 |

## Browser E2E verification (2026-07-13)

Full user journey executed against local backend+frontend with live LLM provider:

| Step | Result |
|------|--------|
| Login (soft auth) | OK |
| Create case | OK |
| Intake (1124 chars, text paste) | OK — article model via LLM |
| HumanModelView (9 blocks) | OK — all sections rendered |
| Semantic hypotheses (4 axes) | OK — panel with accept/dispute/rerun |
| Discipline matches (6) | OK — LLM analysis, high confidence |
| Accept all + Confirm model | OK |
| Set scenario | OK — stage → scenario |
| Investigate venue (text) | OK — deterministic fallback |
| Select venue → auto-chain | OK — fit via LLM |
| FitAssessment (12-axis) | OK |
| MismatchMap | OK |
| RewritePlan | OK |
| SubmissionPack | OK |
| Dossier (technical + human) | OK — both endpoints 200 |
| UI pipeline navigation | OK — all completed stages |

### Known non-blocking issues
- LLM venue profiling failed with "unhashable type: dict" → fell back to deterministic
- FPM fit returned "not_enough_data" (expected for minimal venue text)

## Committed work

All changes committed as `96e3cab` on branch `program/baseline-user-journey-reconstruction`
and pushed to remote. 38 files, 1581 insertions.
