# Human-readable model review — merge + post-merge smoke report

**Date:** 2026-06-15
**Source branch:** `feature/human-readable-model-review` (commit `3aa1930`)
**Main HEAD after merge:** `3aa1930 Human-readable ArticleModel + VenueModel review in cockpit`
**Merge method:** fast-forward (`git merge --ff-only`)

This pass executed a controlled merge of the
`feature/human-readable-model-review` branch into `main`, ran a real
browser smoke against a cold uvicorn instance with live LLM, and
cleaned up the feature branch.

No new features. No tag. No deploy.

---

## A. Pre-merge audit

- Branch HEAD = `3aa1930`, clean tree.
- 10 changed files vs main, no runtime/secret leak in the diff
  (no `.env`, no `.kairoskopion`, no `private_inputs`, no smoke
  user data, no JSONL test data committed).
- Focused tests on the feature branch: **69 passed** in 2.6 s
  (auth + isolation + cases + human card + human view API).
- Frontend `npx tsc --noEmit`: clean.
- Frontend `npx vite build`: clean (272 KB JS, 63 KB CSS).

## B. Merge

```
git checkout main
git pull --ff-only origin main    # at 38cd150 before merge
git merge --ff-only feature/human-readable-model-review
                                    # → 3aa1930
git push origin main
```

Post-merge sanity on `main`:

- Focused tests: **69 passed** in 2.6 s.
- `npx tsc --noEmit`: clean.
- `npx vite build`: clean (identical bundle to the feature branch
  build).

## C. Cold-uvicorn + live-LLM browser smoke

Spun up backend without `source .env`:

```
KAIROSKOPION_DATA_DIR=.kairoskopion_smoke \
  python -m uvicorn kairoskopion.api.app:app \
  --port 8000 --host 127.0.0.1
```

`GET /health` returned:

```
llm.available=True  model=gpt-4o-mini
```

(verifies `_load_dotenv_if_present` from commit `86dbb7e` still
catches `.env` on a clean process).

Seeded one case via `/auth/signup` + `/cases` + `/intake/text` with
the Cyrillic Guattari-style porcupine fragment. The intake took
~90 s of real 302.ai LLM round-trip and persisted the resulting
ArticleModel through `CaseStore` under
`.kairoskopion_smoke/users/<user_id>/cases/<case_id>.json`.

### Smoke checklist (10 checks)

| # | check | result |
|---|---|---|
| 1 | no token → gate appears | **PASS** (`auth-gate` rendered) |
| 2 | user chip shows display name | **PASS** ("Merge Smoke") |
| 3 | preliminary disclaimer banner visible at top of workspace | **PASS** (`.preliminary-banner` rendered) |
| 4a | HUMAN/TECHNICAL toggle visible on Article view | **PASS** |
| 4b | HUMAN tab is the **default active** state | **PASS** ("Человеческая модель" active) |
| 5a | human view body renders with 11 H2 sections | **PASS** (`h2_count: 11`) |
| 5b | disclaimer blockquote visible | **PASS** ("Это предварительная модель статьи, построенная системой. Она НЕ является рекомендацией по подаче.…") |
| 5c | "Подтвердить модель" CTA visible | **PASS** |
| 5d | `<!-- field: ... -->` anchors do NOT leak into rendered UI | **PASS** (stripped by `HumanModelView`) |
| 6 | toggle Human ↔ Technical works both ways | **PASS** (`ArticleCard` shows under Technical; human view re-renders on Human) |
| 7a | isolation: Bob's `/cases` empty | **PASS** |
| 7b | isolation: Bob's GET on Alice's `/article-model` | **404 PASS** |
| 7c | isolation: Bob's GET on Alice's `/article-model/human-view` | **404 PASS** |
| 8a | logout clears localStorage token | **PASS** (`token === null`) |
| 8b | logout returns to gate | **PASS** |
| 9 | continue with Alice email → same workspace visible | **PASS** (`sameCase === aliceCaseId`) |

10 of 10 checks PASS.

## D. Exact user-facing change

Operators / testers now see, by default, the **«Человеческая
модель»** view on every Article and Venue surface in the cockpit.
The view is a 11-section (Article) / 9-section (Venue) prose
rendering of the same structured model that the registry holds —
with explicit honest unknowns, evidence statuses, and the
spec-mandated *"Это предварительная модель статьи… НЕ является
рекомендацией по подаче"* disclaimer.

The structured **«Техническая модель»** view (existing `ArticleCard`
/ `VenueProfile`) is one click away under the toggle, so debugging
and structured field corrections remain available.

Field-level "это неверно" anchors (HTML comments
`<!-- field: article_model.<key> -->`) are emitted in the markdown
but stripped before display — future correction UIs can map them
back to structured fields without re-parsing prose.

## E. Deferred items

| item | reason |
|---|---|
| LLM JSON repair | Task preamble: Mavrinsky failure was unreadable presentation, not validation fallback. Later hardening pass. |
| FitAssessment human view | Same pattern; next pass. |
| MismatchMap / RewritePlan / CitationPlan / RiskReport / SubmissionPack / VenueMemory human views | Replicable pattern from this pass. |
| Per-candidate inline human cards in `VenuePoolBoard` | Trivial wiring (~5 min): `HumanModelView caseId={...} kind="venue" venueKey={canonical_name}`. |
| PromptPatch / RuleUpdate infra | Canon does not require it. Entity-level correction is enough. |

## F. Cleanup

Per task spec section E, after a successful merge + smoke the feature
branch is safe to remove. Both local and remote refs deleted —
canonical history lives on `main` from `3aa1930` onward.

```
git push origin --delete feature/human-readable-model-review
git branch -D feature/human-readable-model-review
```

No other Journal-Yuga branches were touched.

## G. Acceptance criteria

| F# | criterion | status |
|---|---|---|
| F.1 | main contains human-readable ArticleModel and VenueModel/VPKG views | ✅ `3aa1930` |
| F.2 | cockpit default user-facing model view is human-readable | ✅ "Человеческая модель" active on entry |
| F.3 | technical/debug view remains available | ✅ ArticleCard / VenueProfile under Technical tab |
| F.4 | Mavrinsky + rabbit regressions pass | ✅ 20 + 6 dedicated tests; full pytest 1680 passed pre-merge baseline |
| F.5 | full or focused backend tests pass on main | ✅ focused 69/69 (auth + isolation + cases + human card + human view API) on main |
| F.6 | frontend build passes on main | ✅ tsc + vite clean |
| F.7 | browser smoke confirms human view | ✅ 10/10 checks |
| F.8 | main pushed | ✅ `origin/main` at `3aa1930` |
| F.9 | no secrets/runtime data committed | ✅ smoke storage gitignored; .env never touched |
| F.10 | feature branch cleaned up after success | ✅ deleted local + origin |

End of report.
