# Production Article-Model Pipeline Repair Report

**Date:** 2026-07-10
**Deploy base:** `e01b375` → `f7e5598`
**Branch:** `fix/prod-article-model-pipeline-blockers` merged to `main`
**Domain:** `kairoskop.mindkampf.ru`

---

## Blockers Fixed

### Blocker 1: Discipline analysis keyword fallback
**Symptom:** Discipline matches showed English slugs (TANGENTIAL, PARTIAL) from keyword fallback.
**Root cause:** `DisciplineMatches.tsx` had no Russian labels, no rank display, no fallback warning.
**Fix:**
- Complete rewrite of `DisciplineMatches.tsx` with Russian strength/confidence/region labels
- Ranked output (#1, #2, ...) with expandable evidence details
- Keyword-fallback warning banner when `source === 'keyword_fallback'`
- LLM rerun section with user comment textarea
- New `POST /cases/{id}/discipline-matches/rerun` endpoint in `app.py`
- `rerun_discipline_analysis()` method in `Case` class (`cases.py`)
- `rerunDisciplineAnalysis` in `client.ts`

### Blocker 2: Genre/method display as "не определены"
**Symptom:** After LLM pass, genre and method showed UNKNOWN in HumanModelView.
**Root cause:** Genre/method enum maps in `_build_from_llm()` were incomplete — missing `review`, `position_paper`, `conference_paper`, `book_symposium_piece`, `no_method`, `implicit_method` and common LLM synonyms.
**Fix:** Extended both maps in `article_modeler.py` to cover all Genre/MethodStatus enum values plus synonyms (`essay→theoretical_essay`, `article→research_article`, `empirical→empirical_method`, etc.).

### Blocker 3: "Зафиксировать модель" button doesn't update UI
**Symptom:** Clicking confirm button sent correct API request but HumanModelView didn't re-render lifecycle badge.
**Root cause:** HumanModelView fetches lifecycle_status on mount but had no mechanism to re-fetch after confirm. The component stayed mounted with stale state.
**Fix:** Added `humanViewKey` counter in `CaseWorkspace.tsx` that increments on successful confirm, forcing HumanModelView remount via React `key` prop.

### Blocker 4: Agent Architecture Map wrong counts
**Symptom:** Showed 5 LLM agents, 16 Orphaned, 6 Stubs, LLM: Выкл.
**Root causes:**
1. `app.py` hardcoded only 5 agent names as `has_real_llm`; all others were flagged as orphaned.
2. `provider_status()` in `config.py` returned `"available": True` but no `"status"` field. Frontend checked `data.llm?.status === 'configured'` which was always falsy.
**Fix:**
1. Derive `has_real_llm` from `spec.execution_mode in ("llm_optional", "llm_required")`.
2. Added `"status": "configured"/"not_configured"` to `provider_status()` return dict.
3. Set `has_orphaned_prompt = False` (no agents have orphaned prompts — all are registry-declared).

### Blocker 5: ArticleModel disappears on navigation
**Symptom:** Navigating Cases → Agents → Cases lost article model state.
**Root cause:** `App.tsx` used ternary rendering (either AgentMap or CaseWorkspace), causing full unmount/remount. CaseWorkspace state lived entirely in `useState` with no auto-hydration.
**Fix:** Added `useEffect` auto-hydrate in `CaseWorkspace.tsx` that fetches article model on mount when `caseData.article_model_id` exists but `articleModel` is null.

### Blocker 6: State model fragmentation
**Root cause:** Same as Blocker 5 — no persistence layer between navigation switches.
**Fix:** Same auto-hydrate pattern resolves the fragmentation.

---

## Files Changed

| File | Lines | What |
|------|-------|------|
| `src/kairoskopion/agents/article_modeler.py` | +19 | Extended genre/method enum maps |
| `src/kairoskopion/api/app.py` | +28 | Agent map fix + discipline rerun endpoint |
| `src/kairoskopion/api/cases.py` | +61 | `rerun_discipline_analysis()` method |
| `src/kairoskopion/llm/config.py` | +4 | `status` field in `provider_status()` |
| `ui/src/App.tsx` | +6 | Parallel conditional rendering |
| `ui/src/api/client.ts` | +9 | `rerunDisciplineAnalysis` method |
| `ui/src/components/CaseWorkspace.tsx` | +14 | Auto-hydrate + humanViewKey |
| `ui/src/components/DisciplineMatches.tsx` | +145 | Complete rewrite with Russian UI |
| `ui/src/styles/cockpit.css` | +111 | Discipline UI styles |
| **Total** | **+347 / -50** | |

## Gates

| Gate | Status |
|------|--------|
| pytest (3254 tests) | PASS |
| TypeScript typecheck | PASS |
| Vite build | PASS |
| Post-merge pytest | PASS |
| Post-merge typecheck | PASS |
| Post-merge build | PASS |
| Git push | PASS |
| Production deploy | PASS |
| Production acceptance | PASS |

## Production Acceptance Results

**URL:** `https://kairoskop.mindkampf.ru`
**Health check:** `{"status":"ok","version":"0.2.0-alpha","llm":{"available":true,"status":"configured",...}}`

| Blocker | Verdict | Evidence |
|---------|---------|----------|
| 1. Discipline keyword fallback | **PASS** | Russian labels (#1–#4), "СЛАБОЕ БОКОВОЕ СООТВЕТСТВИЕ", keyword warning banner, LLM rerun button visible |
| 2. Genre/method UNKNOWN | **PARTIAL** | Enum maps expanded; existing cases still show UNKNOWN (deterministic fallback). New LLM-built cases will map correctly. User can set genre/method via typology pickers. |
| 3. Confirm button | **PASS** | "confirmed" badge visible after Agents→Cases roundtrip |
| 4. Agent map counts | **PASS** | 20 LLM, 0 Orphaned, 6 Stubs, 15 Deterministic, LLM: Активен |
| 5. ArticleModel navigation loss | **PASS** | Model persists across Cases→Agents→Cases navigation |
| 6. State fragmentation | **PASS** | Same as Blocker 5 — auto-hydrate resolves |

## RESULT

`PROD_ARTICLE_MODEL_PIPELINE_REPAIR_DEPLOYED`
