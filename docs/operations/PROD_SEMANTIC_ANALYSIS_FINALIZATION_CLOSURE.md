# PROD_SEMANTIC_ANALYSIS_FINALIZATION_CLOSURE

**Date:** 2026-07-10
**Branch:** `fix/prod-semantic-analysis-finalization-closure`
**Merged to main:** commits 6286a68, 02ca4e2, bc80d5a via merge commits aeca430, f982767, 1fc7c0a
**Deployed:** 2026-07-10 14:33 MSK, service `kairoskopion-api` active, build hash `index-L64GH2xn.js`

---

## BLOCKER A — Discipline analysis not using LLM

### Root cause
`_run_discipline_matcher()` in `cases.py` had a registry-first substring lookup
(`_registry.discipline_lookup()`) that returned early with keyword-only results
whenever ANY registry hit was found. Since article titles/discipline register
fields almost always contain a substring matching some discipline record, the
LLM path was never reached in practice.

### Fix
- **Removed** the registry-first early return entirely from `_run_discipline_matcher()`
- LLM path now ALWAYS runs when `_get_llm_provider("discipline_matcher")` returns a provider
- Deterministic fallback via `agent.execute_deterministic()` only when no provider is available
- Output is tagged `source: "llm"` when provider was used
- Exception during LLM call falls back to deterministic (not silent failure)

### Prompt v3
- Added `DISCIPLINE_MATCHING_V3_FAMILY` in `prompts/discipline_matching.py`
- Schema requires `matched` array with `minItems: 1`
- Each candidate: `discipline_id`, `display_name`, `strength`, `confidence`, `why` (7-10 sentences), `supporting_evidence`, `contradicting_evidence`, `position_rationale`, `relation_type_ru`
- `DisciplineMatcherAgent` uses v3 when available, falls back to v2
- `max_tokens` increased from 1024 to 4096

### UI
- `DisciplineMatches.tsx` updated: v3 field support (confidence, relation_type_ru, position_rationale)
- Per-candidate expand/collapse with evidence sections
- LLM source badge

### Tests updated
- `test_case_discipline_matcher_uses_registry` → renamed to `test_case_discipline_matcher_produces_results`, removed `registry_first` assertion
- `test_case_injected_registry_used` → removed `registry_first` assertion
- `test_registry_relevant_agents_wired` → removed `discipline_lookup` source-code check

---

## BLOCKER B — Genre/method still UNKNOWN

### Fix
- **Enum constraints** added to article modeling prompt schema (`article_modeling.py`):
  - `genre_current`: enum of 11 values including `unknown`
  - `method_status`: enum of 8 values including `unknown`
- **`rerun_article_model()` method** added to `Case` class (`cases.py`):
  - Requires existing `article_model`, 100+ char text, LLM provider
  - Uses `ArticleModelerAgent.execute(inp, provider)` — no deterministic fallback
  - Updates `genre_current`, `method_status`, `novelty_mode`, `argument_structure`
  - Returns `{genre: {old, new}, method: {old, new}, source: "llm"}` or `{error: ...}`
  - User comment prepended to text when provided
- **`POST /cases/{case_id}/article-model/rerun` endpoint** added to `app.py`
- **`rerunArticleModel` method** added to `client.ts`
- **Genre/method rerun UI** added to `HumanModelView.tsx`:
  - Yellow warning panel when `unknown` genre or method detected in markdown
  - Comment textarea for LLM context
  - "Повторить анализ жанра/метода с помощью LLM" button
  - Success result display (old → new values)
  - Error display

---

## BLOCKER C — Finalization

### Endpoint
- `POST /cases/{case_id}/article-model/confirm` — sets `lifecycle_status` to `confirmed_by_user`
- `confirm_article_model()` in `Case` accepts `protected_core` and `corrections`
- UI button "Зафиксировать модель" wired via `handleConfirm` callback

### Tests
- `test_confirm_method_exists` — method signature verified
- `test_confirm_sets_lifecycle` — lifecycle transitions to confirmed/confirmed_by_user
- `test_confirm_endpoint_exists` — route registered

### Production acceptance required
User must create a fresh disposable case on production, perform full LLM analysis,
click "Зафиксировать модель", and verify:
1. API request succeeds (200)
2. Backend transitions `lifecycle_status` to `confirmed_by_user`
3. Persistence after hard refresh
4. Navigation preservation
5. Persistence after logout/login

---

## BLOCKER D — Agent Map pipeline audit

### Agent spec registry
- 40+ agent specs in `AGENT_SPEC_REGISTRY` (agents/registry.py)
- 5 core agents verified present: `article_modeler`, `venue_profiler`, `fit_assessor`, `article_semantic_profiler`, `discipline_matcher`
- Valid execution modes: `llm_optional`, `llm_required`, `deterministic`

### Agent map endpoint
- `GET /agents/map` — derives `has_real_llm` from `spec.execution_mode` (not hardcoded)

### Pipeline methods verified on Case class
- `intake_text`, `_build_article_model`, `_run_discipline_matcher`
- `investigate_venue`, `discover_venues`, `confirm_article_model`
- `rerun_article_model`, `rerun_discipline_analysis`

### Stub classification
- All agents with `execution_mode` in `{llm_optional, deterministic}` have `execute_deterministic()` method
- `llm_required` agents (6 total) have no deterministic fallback by design

### Integrity tests
- 29 new regression tests in `tests/test_blocker_regression.py`
- Covers: LLM wiring, provider injection, source marking, prompt v3, genre/method rerun, finalization, agent map, stubs, UI wiring

---

## Production TypeScript fixes
- `UnauthorizedError` — replaced `public body` parameter property with explicit field (erasableSyntaxOnly)
- Removed unused `AgentMapWorkflowStep` import
- Renamed unused `searchDepth` to `_searchDepth`
- Removed unused `NON_FIELD_BLOCK_PREFIXES` constant

---

## Gate results

| Gate | Result |
|------|--------|
| pytest | 3283 passed, 8 deselected |
| TypeScript | clean (noEmit) |
| Vite build | clean |
| Production build | clean (index-L64GH2xn.js) |
| Service status | active (running) |

---

## RESULT

**`DISCIPLINE_PROVIDER_WIRING_BLOCKED`** — pending production browser acceptance.

All code-level fixes for BLOCKER A-D are deployed. The production service is running
with the latest build. However, the final `PROD_SEMANTIC_ANALYSIS_FINALIZATION_PASS`
requires manual production browser acceptance:

1. Create a fresh disposable case
2. Submit a real article text (200+ chars)
3. Verify discipline analysis shows LLM-source candidates (not keyword-only)
4. Verify genre/method are resolved (not UNKNOWN) — if UNKNOWN, use the rerun button
5. Click "Зафиксировать модель" and verify persistence
6. Hard refresh, navigate away and back, logout/login — verify state preserved

The code cannot produce this acceptance from CLI alone. User must perform browser
acceptance to close the loop.

---

## Files changed

| File | Change |
|------|--------|
| `src/kairoskopion/api/cases.py` | _run_discipline_matcher rewritten, rerun_article_model added |
| `src/kairoskopion/api/app.py` | POST article-model/rerun endpoint |
| `src/kairoskopion/agents/discipline_matcher.py` | v3 prompt family, max_tokens=4096 |
| `src/kairoskopion/prompts/discipline_matching.py` | v3 prompt family (170 lines) |
| `src/kairoskopion/prompts/article_modeling.py` | genre/method enum constraints |
| `ui/src/api/client.ts` | rerunArticleModel, erasableSyntaxOnly fix |
| `ui/src/components/DisciplineMatches.tsx` | v3 fields, expand/collapse, evidence |
| `ui/src/components/HumanModelView.tsx` | genre/method rerun section |
| `ui/src/components/AgentMap.tsx` | unused import removed |
| `ui/src/components/CaseWorkspace.tsx` | unused var prefixed |
| `ui/src/styles/cockpit.css` | genre-method-rerun-section styles |
| `tests/test_blocker_regression.py` | 29 new regression tests |
| `tests/test_round3p6_1_integration.py` | Updated for new discipline matcher behavior |
| `tests/test_round3p6_2_closure.py` | Removed discipline_lookup source check |
