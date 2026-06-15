# LLM JSON repair + visible fallback — merge + post-merge smoke report

**Date:** 2026-06-15
**Source branch:** `feature/llm-json-repair-visible-fallback` (commit `21cf19e`)
**Main HEAD after merge:** `21cf19e LLM JSON repair + visible fallback metadata`
**Merge method:** fast-forward (`git merge --ff-only`)

## A. Pre-merge audit

- Branch on `21cf19e`, clean tree.
- Diff: 8 files, no runtime/secret leak. No `temperature` / `max_tokens`
  / `model` overrides anywhere. `raw_output_ref` defaults `None`
  (LLM output never captured by default).
- Focused tests: **93 passed** (`json_repair` + `human_readable_card`
  + `human_view_api` + `auth_and_isolation` + `cases`).
- Frontend: `tsc --noEmit` clean; `vite build` clean.

## B. Merge

```
git checkout main
git pull --ff-only origin main      # at c2a5780
git merge --ff-only feature/llm-json-repair-visible-fallback   # → 21cf19e
git push origin main
```

Post-merge focused tests on main: **93 passed**.
Frontend on main: tsc + vite clean.

## C. Post-merge smoke

Cold uvicorn (no manual `source .env`):

```
KAIROSKOPION_DATA_DIR=.kairoskopion_smoke \
  python -m uvicorn kairoskopion.api.app:app --port 8000 --host 127.0.0.1
```

`GET /health` → `llm.available=True model=gpt-4o-mini`. Autoload still works.

### API smoke — both fragments

| fragment | latency | `parse_status` | `fallback_used` | `fallback_reason` | `core_claims_n` | `raw_output_ref` |
|---|---|---|---|---|---|---|
| Porcupine / Guattari | 115 s | `fallback_used` | **True** | `provider_error` | 0 (deterministic) | `None` |
| Rabbit / early-modern England | 105 s | `parsed_ok` | False | `not_applicable` | 3 | `None` |

**Today's porcupine run hit a real 302.ai provider error**, and the
`extraction_attempt` field carried the full audit trail
(`llm_attempted=True`, `fallback_used=True`,
`fallback_reason=provider_error`, `raw_output_ref=None`). This is
exactly the case this pass was built for: the failure is **visible**
instead of silent.

### Browser smoke

| check | result |
|---|---|
| Cold autoload `/health` shows LLM available | ✅ |
| Porcupine case: human view renders | ✅ (11 H2 sections) |
| Porcupine case: Russian fallback warning blockquote visible | ✅ `"⚠ LLM-провайдер вернул ошибку. Показана детерминированная модель."` |
| Porcupine case: technical hint visible | ✅ `(parsestatus: 'fallbackused' · fallbackreason: 'providererror')` |
| Porcupine case: NO `Traceback` text in DOM | ✅ |
| Porcupine case: NO `raw_output_ref` text in DOM | ✅ |
| Rabbit case: human view renders rich content (`translation_between_fields`, `rabbit`/`early modern`) | ✅ |
| Rabbit case: **no** fallback warning blockquote | ✅ (1 blockquote total — just the standard preliminary disclaimer) |
| Human ↔ Technical toggle works | ✅ |
| Isolation: Bob GET on Alice's `/article-model/human-view` | **404** ✅ |

The synthetic test-case coverage from the repair pass (the 2
`TestHumanViewSurfacesFallback` cases) is now reinforced by **live
end-to-end evidence**: a real `provider_error` fallback ran through
the full intake → article-model → human-view path on main, and the
Russian warning rendered exactly as designed without leaking the
raw error message.

## D. Tests + builds on main

- Focused: **93 passed** in 2.84 s on main (auth + isolation + cases
  + human card + human view API + json repair + fallback metadata).
- Full pytest (from the feature-branch baseline): **1704 passed**,
  4 deselected. +24 vs the prior 1680 baseline.
- Frontend: tsc clean, vite build clean.

## E. Cleanup

```
git push origin --delete feature/llm-json-repair-visible-fallback
git branch -D feature/llm-json-repair-visible-fallback
```

## F. Deferred

| item | comment |
|---|---|
| `DisciplinaryPathwayMapper` metadata wiring | Same pattern as `ArticleModelerAgent`. Easy to replicate. Next pass. |
| Technical `ArticleCard` badge for `extraction_attempt` | Now that the data flows end-to-end, rendering a small badge in the Technical tab is ~15 minutes of UI work. |
| Second-LLM repair flag | Only behind explicit operator opt-in; not default per task spec. |
| Strict fast-path schema validation | When `response.parsed` is already a dict from `openai_compat._parse_json_robust`, we trust it. Validating against schema in the fast path is a hardening pass. |

## G. Acceptance

| item | status |
|---|---|
| main contains JSON repair + visible fallback metadata | ✅ `21cf19e` |
| `ArticleModel` carries `extraction_attempt` | ✅ field on schema + persisted via `CaseStore` + surfaced in `/article-model` API |
| Human view can show Russian fallback warning | ✅ **live-verified** on porcupine case |
| Tests/build pass on main | ✅ 93 focused + tsc + vite |
| Live success path still works | ✅ rabbit fragment: `parsed_ok`, 3 claims |
| No secrets/runtime/raw LLM output committed | ✅ smoke storage gitignored; `raw_output_ref` stays None |
| Branch deleted after merge | ✅ (executed in §E) |

End of report.
