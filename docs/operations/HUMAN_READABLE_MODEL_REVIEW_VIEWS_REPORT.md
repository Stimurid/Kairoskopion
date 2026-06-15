# Human-readable ArticleModel / VenueModel review — implementation report

**Date:** 2026-06-15
**Branch:** `feature/human-readable-model-review`
**Baseline:** `38cd150 Tester-readiness pass: pathway reasoning + preliminary banner + tester guide`

## A. Why this pass exists

Mavrinsky received a golden ArticleModel + Journal-Yuga venue pass and
could not understand it. The pipeline produced a correct structured
model — the failure was that the structured model was the only
surface a humanities author was offered. JSON / YAML / Obsidian-style
markdown frontmatter is not author-readable.

This is a product failure, not an LLM-extraction failure. The
remedy is **author-facing prose review** of the same structured
model — same axes, same evidence statuses, same unknowns, but in
sentences a humanities author actually reads.

## B. What canon required

(See `HUMAN_READABLE_MODEL_REVIEW_GAP_AUDIT.md` §A for full citations.)

- §10 line 1809–1818 — human-readable Vault cards required for
  ArticleModel, VenueModel, FitAssessment, RewritePlan, CitationPlan,
  RiskReport, SubmissionPack, VenueMemory.
- §16 line 2532 — Vault cards must let a human browse Journal-Yuga
  work without opening raw registry JSON. **This is exactly the
  Mavrinsky use case.**
- §12 line 1866 — vault_card_ref is the human-readable projection;
  registries remain the source of structured truth.

Canon does **not** require prompt-level correction in this layer.
Correction is entity-level via
`Case.confirm_article_model(protected_core, corrections)`.

## C. What existed before

| layer | state at `38cd150` |
|---|---|
| Vault infrastructure | Disk scaffolding + indexes work (`vault.py`). |
| Markdown body | Minimal: title + a few bullet sections (`cards.py::article_model_card`). |
| Cockpit visibility | None — vault markdown not exposed via HTTP. |
| Plain-language explanations of enums (`genre`, `method_status`, `novelty_mode`) | None — raw enum values rendered. |
| Author questions for model verification | None. |
| Honest "missing protected core" warning | Absent. |
| Venue card | Same shape — minimal, not author-readable. |
| Pathway reasoning in cockpit | Just landed in prior pass (38cd150). |

## D. What this pass implements

### Service: `src/kairoskopion/services/human_readable_card.py`

Two pure functions (no LLM, no network, deterministic):

- `article_model_human_view(article_dict, pathways=None) -> str` —
  produces an 11-section Russian-language markdown view per task spec §C:
  1. Коротко — 3–6 sentences summarising what the system thinks
     this article is.
  2. Главный объект статьи.
  3. Главная проблема и напряжение.
  4. Основные утверждения статьи.
  5. Тип статьи (genre + method_status + novelty_mode each
     **explained in prose**, not raw enum). Dictionaries
     `GENRE_PROSE`, `METHOD_PROSE`, `NOVELTY_PROSE` cover all
     project enums.
  6. Дисциплинарные регистры (uses passed pathways with their
     `reasoning` and `fit_strength`).
  7. Теоретические плечи / оппоненты / словарь.
  8. **Неприкосновенное ядро** with explicit honest "Система пока
     не знает, что автор считает неприкосновенным ядром статьи. Без
     этого любые fit/rewrite выводы остаются предварительными."
     when missing (task spec §C.8 verbatim).
  9. Что система не знает — plain-language unknowns + always
     surfaced "what we don't know by default" list
     (target venue, scenario, source base, author goal).
  10. Вопросы автору для проверки модели (7 concrete questions
      from task spec).
  11. Что можно поправить — correction affordances with field
      anchors.

- `venue_human_view(venue_dict) -> str` — produces a 9-section
  Russian-language markdown view per task spec §D for either a
  `VenueModel` or a `VenueProfilePackage`. Distinguishes
  source-fact vs vendor-claim vs corpus-observation vs inference vs
  unknown / inaccessible on every section.

### Field anchors (task spec §E)

Every section header emits an unobtrusive HTML comment
`<!-- field: article_model.<key> -->`. These are invisible to the
author in cockpit rendering (stripped in `HumanModelView`) but
preserved in the raw markdown so a future UI surface can map a
"это неверно" click back to the structured field path without
re-parsing prose.

### API endpoints

Added to `src/kairoskopion/api/app.py`, **all user-scoped via
`_user_case`**:

- `GET /cases/{case_id}/article-model/human-view` →
  `{format: "markdown", lifecycle_status, not_a_submission_recommendation: true, markdown: ...}`.
- `GET /cases/{case_id}/venues/{venue_key}/human-view` →
  resolves `investigated` literal OR canonical_name OR
  venue_candidate_id OR venue_model_id OR
  venue_profile_package_id, returns markdown.

Cross-tenant access returns 404 — no information leak about whether
the case exists for another user.

The existing `POST /cases/{case_id}/article-model/confirm` endpoint
is reused for confirmation. The human view's "Подтвердить модель"
button calls it with `protected_core` from the current ArticleModel.

### Cockpit UI

- `ui/src/components/HumanModelView.tsx` — fetches the markdown,
  renders it via a minimal dependency-free markdown converter,
  shows lifecycle badge, "Подтвердить модель" CTA when relevant.
  Strips machine field anchors. Handles loading + error states.

- `ui/src/components/CaseWorkspace.tsx` — both `article_model` and
  `venue_investigation` views now show a **Human / Technical**
  toggle (Russian labels: «Человеческая модель» / «Техническая
  модель»). **Human view is the default.** The existing
  `ArticleCard` / `VenueProfile` remain available behind the
  Technical tab — debugger and structured-corrections path is
  preserved.

### CSS

`ui/src/styles/cockpit.css` extended with `.model-view-toggle`,
`.human-view`, `.human-view-body` (typography for H1/H2/H3, lists,
blockquotes, strong/em), `.human-view-actions`. Consistent with the
existing dark-theme cockpit palette.

## E. How ArticleModel human view works (operator perspective)

1. Tester signs in, creates a case, pastes text, hits Analyze.
2. Backend builds the ArticleModel (LLM dual-execution; falls back
   to deterministic on failure).
3. Workspace auto-routes to `article_model` view.
4. **Default view is Human.** The cockpit fetches
   `/cases/{id}/article-model/human-view`, gets back markdown, and
   renders it.
5. The author reads 11 sections. Lifecycle banner says
   "preliminary, NOT a submission recommendation".
6. If the model is correct: click «Подтвердить модель» — lifecycle
   flips to `confirmed`.
7. If something is wrong: switch to «Техническая модель», edit the
   structured fields via the existing `ArticleCard` flow, hit
   Confirm. Then back to «Человеческая модель» to read the
   confirmed version.

## F. How VenueModel / VPKG human view works

1. From the investigated-venue view, toggle to «Человеческая модель».
2. Backend fetches the venue dict, renders the 9-section human view.
3. Sections explicitly say what is `source_fact` / `vendor_claim`
   / `corpus_observation` / `inference` / `unknown` / `inaccessible`
   on each axis — no editor-taste speculation.
4. Author questions ("Есть ли у вас опыт с этим журналом?",
   "Нужны ли Scopus/WoS/ВАК?", …) lead naturally into the existing
   scenario builder.

(The `venue_pool` view does not yet show per-candidate human cards
inline — selecting a candidate first routes via the existing
investigation path. Per-candidate inline human cards are a small
follow-up: pass `venueKey={canonical_name}` to `HumanModelView`.)

## G. How corrections / confirmation work

- **Existing entity-level correction path is reused**:
  `Case.confirm_article_model(protected_core, corrections)`. The
  human view's CTA calls `POST /cases/{id}/article-model/confirm`
  with the current `protected_core` array.
- The technical `ArticleCard` view remains the place to do
  fine-grained field corrections. Toggle is one click.
- **No prompt-level patch infrastructure** in this pass — canon
  does not require it; entity corrections are enough.

## H. What this pass explicitly defers

| deferred item | why |
|---|---|
| LLM JSON repair | Task spec preamble: *"Do NOT start with LLM JSON repair in this pass. The Mavrinsky failure was not caused by JSON validation fallback. It was caused by unreadable model presentation. LLM JSON repair is a later hardening pass."* |
| Full PromptPatch / RuleUpdate | Canon does not require it. Entity-level correction is enough. |
| Full FitAssessment human view | Same pattern, smaller priority. Next pass. |
| MismatchMap / RewritePlan / CitationPlan / RiskReport / SubmissionPack / VenueMemory human views | Pattern from this pass is replicable; deferred. |
| Per-candidate inline human cards in `VenuePoolBoard` | Trivial wiring, can ship next pass. |

## I. Tester / author usage instructions

Updated `KAIROSKOPION_STAGING_TESTER_GUIDE.md` with a new
"Before trusting fit/venue output — read your human model" section
(see commit). Short summary:

- **Before** acting on any fit/mismatch/venue output, read the
  human ArticleModel view and either confirm it or correct it.
- The system is **NOT** giving you a submission recommendation —
  it's giving you a **model of your own article** + a **map of
  possible journals**. The submission decision is yours.
- A wrong model → correct the model. Don't trust the recommendation
  built on a wrong model.

## J. Tests

`tests/test_human_readable_card.py` — **20 tests, all pass:**

- 4 article-view shape tests (markdown not JSON; preliminary
  banner; no recommendation leakage; field anchors emitted).
- 2 protected-core tests (missing → exact spec-mandated warning;
  present → listed without the warning).
- 1 enum prose explanation test (genre/method/novelty rendered in
  Russian prose, not raw enum).
- 1 pathways enrichment test.
- 2 **Mavrinsky regression tests** — all required sections render
  with content sanity (desire-as-excess, dispositif,
  Deleuze_Guattari visible), 5–9 author questions present, no
  recommendation leakage.
- 6 **rabbit/early-modern-England fragment fixture tests** —
  topic markers visible (rabbit/breeding/fertility/early modern);
  multiple pathways render; no collapse into sexuality unless text
  evidence supports it; unknowns visible; preliminary warning
  visible; no recommendation leakage.
- 3 venue-view shape tests (all 9 sections render; missing-board
  → honest status without editor-taste speculation; field anchors
  emitted).
- 1 **frozen-top-5-venue regression** (Foucault Studies from v2.3
  golden freeze — identity + corpus + board id visible, inference
  marker on derived signals).

`tests/test_human_view_api.py` — **6 tests, all pass:**

- ArticleModel human-view endpoint returns markdown for owner.
- 404 when article not yet built.
- Cross-tenant access → 404.
- Auth required (401 without Bearer).
- Venue human-view endpoint: 404 with no investigated venue.
- Venue human-view endpoint: cross-tenant → 404.

Focused suite total: **69 passed** including all existing
auth/isolation/cases tests. Frontend `tsc --noEmit` clean,
`vite build` clean (272 KB JS, 63 KB CSS).

Full pytest in progress at commit time — see commit message for
final count.

## K. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no venue discovery changes | OK |
| no extraction-agent changes | OK |
| no broad pipeline rewrite | OK |
| no final submission recommendation | OK — `not_a_submission_recommendation: true` in every response + tests guard the leak |
| no silent protected-core modification | OK — the only protected-core write path is the existing `confirm_article_model` |
| no replacing structured model with prose | OK — Technical view stays, registries unchanged |
| no secrets/runtime data committed | OK |
| no deploy/tag/merge unless explicitly asked | OK — branch only |

End of report.
