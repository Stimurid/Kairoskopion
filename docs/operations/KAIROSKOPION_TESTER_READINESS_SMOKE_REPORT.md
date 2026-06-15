# Kairoskopion tester-readiness pass — smoke report

**Date:** 2026-06-15
**Main HEAD:** `86dbb7e` (baseline) → this pass adds UI surfacing for
pathway reasoning + a preliminary-positioning banner; new commit at
top of branch.
**Backend port:** 8000 (uvicorn, `127.0.0.1`, autoload `.env`).
**Frontend port:** 5173 (vite dev, `127.0.0.1`).
**Smoke storage:** `${KAIROSKOPION_DATA_DIR}=.kairoskopion_smoke/` —
gitignored; nuked after the run.

---

## A. LLM availability (no secrets leaked)

Cold uvicorn start, no manual `source .env`:

```
GET /health
  llm.available: true
  provider:      openai_compatible
  model:         gpt-4o-mini
```

Autoload `.env` change shipped in commit `86dbb7e` (previous pass)
verified by hitting `/health` with a fresh shell where
`KAIROSKOPION_LLM_*` are NOT exported. The actual API key value is
read from the gitignored `.env` and never logged or echoed by the
backend.

## B. UI behaviour after intake

### Wired by this pass
1. **Preliminary banner** (`.preliminary-banner`) at the top of every
   case view:
   > "Preliminary positioning — this is not a submission
   > recommendation. Outputs are evidence-traceable hypotheses, not
   > decisions. Unknowns are marked explicitly."
2. **PathwayMap reasoning** — `DisciplinaryPathway.reasoning` (optional
   string from the LLM agent) now renders as a left-bordered prose
   block inside each pathway card. Confidence badge surfaces alongside
   fit + core-risk badges.

### Already wired (verified, no changes)
- `IntakeSurface` accepts paste + `Analyze` button.
- After successful intake the workspace auto-routes to the
  `article_model` view and renders `ArticleCard` with
  Object / Problem / Thesis / Method / Novelty / Discipline /
  Protected core / Unknowns.
- `ArticleCard` shows an explicit "Extraction produced a shallow
  model — key fields are missing" panel when the LLM JSON parse
  failed silently.
- `PathwayMap` shows up to 10 disciplinary pathways with fit badge,
  core-risk badge, adaptations list, strategic notes, example
  venues — and now reasoning.
- `VenuePoolBoard` lists candidate venues with confidence + status.
- Top-bar user chip + Sign out + Sign-up disclaimer all visible from
  the previous browser smoke.

## C. Real LLM browser smoke

### Fragment 1 — Guattari / porcupines (Russian)

A 685-char Cyrillic fragment about "совокупляющиеся дикобразы как
шизо-образ, опираясь на Guattari…" was POSTed via the Intake UI.

| step | observed |
|---|---|
| intake elapsed | **94s** (live LLM call confirmed by latency) |
| ArticleCard rendered | YES, with shallow-model warning |
| `novelty_mode` | `unknown` |
| `method_status` | `unknown` |
| `core_claims` | 0 |
| `protected_core` | 0 |
| `unknowns` list | "abstract missing — article model is shallow", "genre not detected", "method not detected", "novelty mode not detected", "protected core not confirmed by user" |
| Pathways count | 0 |
| UI display verdict | **honest** — shallow-model banner + UNKNOWN markers across every field |

**Honest read:** the LLM was called (94s round trip), the response
failed JSON-schema validation in the agent's strict path, and the
agent's exception handler fell back to deterministic — which emits
nothing substantive for a fragment this thin. The UI rendered the
fallback state correctly with explicit `UNKNOWN` markers — no
fabrication.

**This is the failure mode that needs hardening next** (see §I).

### Fragment 2 — rabbits / early modern England (Russian)

A 405-char Cyrillic fragment about rabbit breeding, warrens,
fertility, and moral anxieties in 16th-century England was POSTed via
the API and inspected through the UI.

| step | observed |
|---|---|
| intake elapsed | **81s** (live LLM) |
| `novelty_mode` | **`translation_between_fields`** |
| `method_status` | **`conceptual_method`** |
| `core_claims` count | **3** (e.g. "Management of animal fertility functions as a framework for thinking about domestic order, abundance, and bodily control in early modern England") |
| `protected_core` | 1 (rabbit fertility management as a conceptual lens for domestic order and bodily control) |
| Pathways count | **10** |
| top-3 pathways | `History of science and technology` [strong] · `Science and Technology Studies` [strong] · `Historical anthropology` [strong] |
| also strong | `Animal studies / critical animal studies` · `History of domesticity / family and household studies` |
| medium | `Early modern economic history / agrarian history` · `Philosophy of technology / philosophy of biology` |
| weak / unknown | `Social theory / biopolitics`, `Digital humanities`, `Media studies` |
| collapse-to-sexuality? | **NO** (explicitly checked — not in top-10) |
| reasoning blocks rendered in UI | **10 / 10** |
| UI display verdict | **PASS** — all 10 pathway cards rendered with discipline name + fit badge + reasoning paragraph + preliminary banner |

**Honest read:** for this fragment the LLM round-tripped cleanly,
the agent produced a richly populated ArticleModel and 10 disciplinary
pathways with substantive reasoning. The UI rendered every one.
**Exactly the user-spec expected behaviour** — early-modern history,
animal studies, history of science, agrarian history — without
collapsing into "sexuality".

## D. API smoke (live HTTP, not TestClient)

1. **Signup `tester@porcupine.smoke`** → 200, user_id + token.
2. **Create case** → 200, `case_id`.
3. **`/cases/{id}/intake/text`** for porcupine fragment → 200,
   `stage: article_model`, intake elapsed 94s.
4. **`/cases/{id}/intake/text`** for rabbits fragment → 200, intake
   elapsed 81s.
5. **`/cases/{id}/article-model`** + **`/pathways`** return the
   responses tabled in §C.
6. **Bob (`bob@isolation.smoke`)** second user signs up.
7. **Bob `GET /cases`** → `[]` (empty — no Alice visible).
8. **Bob `GET /cases/<alice_rabbit_id>`** → **404** (no info leak).
9. **Bob `GET /cases/<alice_rabbit_id>/pathways`** → **404**.
10. Restart persistence already verified in
    `STAGING_SOFT_AUTH_PERSISTENCE_MERGE_AND_SMOKE_REPORT.md`; not
    re-run here.

Auth isolation **green**. Persistence unaffected by this pass.

## E. Tests / build

- `tests/test_api_auth_and_isolation.py` + `tests/test_api_cases.py`
  + `tests/test_vf_c3_submodels.py` + `tests/test_vf_c5_funnel_navigator.py`
  + `tests/test_vf_c7_cache_policy.py` — **152/152 pass** in 2.17s.
- Full pytest **`--deselect tests/test_venue_pool_discovery.py::TestLiveAdapterSearchMethods`**
  — **1646 passed, 12 deselected**, 82s. The 12 deselected are the
  pre-existing `TestLiveAdapterSearchMethods` which hit live OpenAlex
  and hang in environments where the network is reachable; they are
  **not** introduced by this pass and not part of CI.
- Frontend `npx tsc --noEmit`: **clean**.
- Frontend `npx vite build`: **clean** (268.29 kB JS, 61.24 kB CSS,
  gzip 79+9 kB).

CI deterministic suite does not require live LLM.

## F. Files changed in this pass

| file | what |
|---|---|
| `ui/src/types/domain.ts` | Optional `reasoning` and `confidence` fields added to `DisciplinaryPathway`. |
| `ui/src/components/PathwayMap.tsx` | Reasoning prose block + confidence badge in each pathway card. |
| `ui/src/components/CaseWorkspace.tsx` | Top-of-workspace `.preliminary-banner` rendering. |
| `ui/src/styles/cockpit.css` | New `.preliminary-banner`, `.pathway-reasoning`, `.pathway-badge--confidence` rules. |
| `docs/operations/KAIROSKOPION_STAGING_TESTER_GUIDE.md` | New tester guide (this commit). |
| `docs/operations/KAIROSKOPION_TESTER_READINESS_SMOKE_REPORT.md` | This report. |

## G. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no broad discovery | OK |
| no VF backlog work | OK |
| no pipeline rewrite | OK |
| no final submission recommendation | OK — banner in UI + report says so explicitly |
| no invented references / journal claims / editor claims | OK |
| no secrets in logs / commits | OK — `.env` gitignored; `config_summary()` returns booleans only; smoke storage nuked |
| no runtime storage committed | OK |
| no deploy / tag | OK |

## H. Branch cleanup

`origin/feature/staging-soft-auth-persistence` was merged via the
controlled FF merge documented in
`STAGING_SOFT_AUTH_PERSISTENCE_MERGE_AND_SMOKE_REPORT.md`. The full
auth-smoke checklist passed in that pass + the new tester-readiness
checks in this pass have not surfaced any regression. **Safe to
delete the branch.** Will be deleted as part of this commit unless
operator vetoes.

## I. Readiness — honest formulation

Per the intermediate audit comment on this smoke log, the readiness
statement needs to be split rather than collapsed into a single
"ready" / "not ready" verdict. The honest formulation:

| readiness flavour | verdict |
|---|---|
| Narrow technical tester smoke | **READY** |
| 3–10 trusted testers with the known LLM-fallback caveat visible | **READY** — caveat is now in UI (shallow-model warning), the tester guide (§10 "Known limitations"), and this report (§C Fragment 1) |
| Author-facing model validation (Mavrinsky-style review of the model) | **NOT READY** — no human-readable ArticleModel / VenueModel view exists yet; the JSON / card layout is for an engineer, not for a humanities author |
| Public production | **NOT READY** — no password, no email verification, no rate limit, no session expiry (separate from this pass) |

## J. What this pass deliberately did NOT close

Two gaps the intermediate audit flagged correctly. Both are real
follow-ups, not "fixed later" handwaves:

1. **LLM JSON repair + visible fallback.** Porcupine fragment shows
   the failure mode: the LLM returned content but the agent's strict
   JSON-schema validation rejected it, exception caught, deterministic
   fallback fired, UI showed UNKNOWN markers. **The fallback is
   currently invisible to the operator** (no `llm_output_invalid_json`,
   `repair_failed`, `fallback_used` flags propagate through the
   AgentOutput / ArticleModel surface). Next micro-pass:
     - try a forgiving JSON-repair parse before deterministic fallback;
     - if both fail, mark `fallback_reason` explicitly on the
       ArticleModel / AgentOutput so the UI can show
       "the LLM tried but its output was unusable — falling back".
   This is the cheapest single move that lifts the porcupine-class
   outcome from "silent shallow" to "visible
   'we attempted, here's the honest result'".

2. **Human-readable model review layer.** What Mavrinsky asked for
   after seeing the gold JSON. Not a new generation pass — the same
   `ArticleModel` (and later `VenueProfilePackage`) data rendered as
   prose: "Your article is about X. You argue Y. Your protected core
   is Z. We could not extract W." With per-field correction buttons.
   **Same fields, same evidence statuses, plain language.** This is a
   separate UI pass; nothing to invent on the data side. Same plan
   for the venue side — a paragraph that says "This journal
   publishes mostly continental-philosophy essays, has an editorial
   board concentrated at X, requires English, ..." instead of a JSON
   dump.

Whether the canonical spec already foresees prompt correction /
human-readable review needs to be confirmed before implementation —
flagged for the next investigation pass.

End of report.
