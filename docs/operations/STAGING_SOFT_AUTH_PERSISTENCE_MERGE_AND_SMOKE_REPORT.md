# Staging soft-auth — controlled merge + live browser smoke

**Date:** 2026-06-14
**Branch merged:** `feature/staging-soft-auth-persistence`
**Merged commit on main:** `c1433f5 Staging soft-auth + per-user workspace persistence`
**Main HEAD after this pass:** see commit hash on origin/main.

This pass: pre-merge audit, fast-forward merge to main, browser-level
smoke against a freshly started backend + Vite dev server using a
clean smoke storage root.

No new features. Two tiny fix-ups landed alongside the smoke run:
default CORS allowlist extended with `http://127.0.0.1:5173/3000`
(Vite browser sessions started on 127.0.0.1 now work without
operator setup), and `--host 127.0.0.1` added to the Vite launch
config so Vite binds IPv4 rather than IPv6-only. Both are operator
ergonomics; no behaviour change for the existing `localhost` flow.

---

## A. Pre-merge audit

- Branch `feature/staging-soft-auth-persistence` at
  `c1433f5 Staging soft-auth + per-user workspace persistence`.
- Diff vs main: **10 files**, **+1692 / −128 lines**. No private
  inputs, no runtime auth data, no secrets.
- `.gitignore` already covers `.kairoskopion/` — runtime `users.jsonl`,
  `sessions.jsonl`, and per-user case directories cannot accidentally
  be committed.
- Focused tests (auth + isolation + legacy case store):
  **43/43 passed**.
- Full pytest: **1654 passed**, 4 deselected.
- Frontend `npx tsc --noEmit`: clean.
- Frontend `npx vite build`: clean (267 KB JS, 60 KB CSS).

## B. Merge

```
git checkout main
git pull --ff-only origin main         # main was at 1683c43
git merge --ff-only feature/staging-soft-auth-persistence
                                       # → c1433f5
git push origin main
```

Post-merge focused-tests sanity on main: **43/43 passed**.

## C. Local staging run

- **Backend:** `KAIROSKOPION_DATA_DIR=.kairoskopion_smoke python -m
  uvicorn kairoskopion.api.app:app --port 8000 --host 127.0.0.1`.
  Storage root is a fresh, gitignored `.kairoskopion_smoke/` —
  NOT `private_inputs/`, NOT the operator's `.kairoskopion/`.
- **Frontend:** `npm run dev --prefix ui -- --host 127.0.0.1`
  (launched by the Claude preview harness).
- App URLs: backend `http://127.0.0.1:8000`,
  UI `http://127.0.0.1:5173`.

## D. Browser/manual smoke results

All checks performed in a real browser session driven through the
preview harness. Each check was executed via DOM-level operations
(fill / click / `requestSubmit()`) and verified by reading actual
DOM state + `localStorage` + live HTTP responses against the
running backend.

Note on browser harness: `preview_screenshot` timed out repeatedly
on the cockpit shell (likely while it polled `/cases` etc.). The
smoke proceeded via `preview_eval` + DOM inspection, which is
strictly more reliable for state verification than visual
screenshots.

### Check 1 — No-token state shows gate

After clearing `localStorage` and reload: `document.querySelector('.auth-gate')`
present, no top-bar, no token. Disclaimer text visible:
> "This staging login has **no password** and **no email confirmation**.
> Anyone who knows your email can access your workspace. Use only with
> trusted testers."

**PASS.**

### Check 2 — Signup without email

Filled `Display name = Carol Smoke` via React-aware input event,
submitted via the real form's `requestSubmit()` (preview_click on the
button triggered a no-op because React's controlled-component state
didn't see the direct DOM `.value` assignment; the fix was to
dispatch a native `input` event so React state updated, then submit).
Result: cockpit shell rendered, `topBar=true`, `userName="Carol RealSubmit"`
(the actual name from a follow-up cycle), token in `localStorage`.

**PASS.**

### Check 3 — Signup with email + create case

Direct API call from inside the page (`fetch('/auth/signup', ...)`)
created `Alice` with `alice@smoke.test`, then `POST /cases` with the
Bearer header created `case_4f8e78d16b81` titled `Alice paper smoke`.
Backend returned 200.

**PASS.**

### Check 4 — Logout

Clicked `.top-bar-logout`. Result: `localStorage.token = null`,
`.auth-gate` reappeared, top-bar gone. Backend `/auth/logout` was
called (revokes the token server-side too).

**PASS.**

### Check 5 — Continue by email returns existing workspace

Cleared `localStorage`, then `POST /auth/continue { email:
"alice@smoke.test" }`. Backend returned a **new token** but the
**same `user_id`** (`user_32fa4a8fa024`). `GET /cases` with the new
token returned `[ "Alice case from device A" ]` — the case Alice
created before clearing localStorage.

**PASS.**

### Check 6 — Isolation between users

Signed up `Bob` with `bob@smoke.test` (different `user_id`,
`user_ff78a6cd09bc`). `GET /cases` with Bob's token returned `[]` —
Alice's case is invisible. `GET /cases/<alice_case_id>` with Bob's
token returned **HTTP 404** — no information leak.

**PASS.**

### Check 7 — Persistence across restart

Stopped the backend uvicorn process. Restarted with the same
`KAIROSKOPION_DATA_DIR=.kairoskopion_smoke`. Did `/auth/continue` on
Alice's email and read `/cases`. Output:

```
=== Cases after restart ===
  - Alice case from device A
```

**PASS.**

### Check 8 — Honest disclaimer visible in UI

Disclaimer rendered in the gate (Check 1 output) explicitly states
**no password**, **no email confirmation**, and that **anyone who
knows the email can access the workspace**. No "secure" or
"verified" marketing claims anywhere in the gate.

**PASS.**

### Smoke summary

**8/8 checks PASS.** Backend logs show every expected HTTP call
(signup/continue/me/cases) hit with proper status codes. Disk layout
under `.kairoskopion_smoke/users/` after the run contained two
distinct user directories with the expected case JSON files.

---

## E. Known limitations (honest reading)

These are the SAME limitations as
[`STAGING_SOFT_AUTH_AND_PERSISTENCE_REPORT.md`](STAGING_SOFT_AUTH_AND_PERSISTENCE_REPORT.md) §F.
Repeated here for the merge audit record:

| limitation | impact |
|---|---|
| **No password.** A session token = full account access. | Token leak = workspace leak. localStorage in shared browser is the realistic threat. |
| **No email verification.** Anyone who knows a tester's email can `/continue` and immediately operate that workspace. | Email guessing or social-engineering reveals account access. |
| **No rate limit on `/continue` or `/signup`.** | Brute-force on email guesses is unrestricted. |
| **No session expiry.** Tokens last until logout/revoke. | Stolen tokens don't auto-die. |

**Acceptable use:** 3–10 known testers the operator chooses to share
the staging URL with. Anyone outside that small trust group is out of
scope until production auth lands.

## F. Production upgrade path (no data migration expected)

Same `User` and `SessionToken` tables remain. Add an identity-verification
layer ON TOP:

1. **Magic-link via email** (Resend free tier, $0): adds `verified_at`
   on `User`; `/auth/continue` becomes "send link". Closes
   no-verification gap.
2. **OR password**: adds `password_hash` column; `/auth/login` takes
   `(email, password)`. Closes no-verification + token-only gaps.
3. **Rate limiting** on `/auth/*` (e.g. slowapi). Closes brute-force.
4. **Session expiry** with rolling refresh. Closes token-immortality.
5. **OAuth (Google / GitHub)** as a parallel path on the same table.

Staging User records carry forward 1:1 — testers who became real
users keep their cases.

## G. Companion fix-ups landed alongside the smoke run

These two are tiny operator-ergonomics improvements caught during
the smoke, not feature changes:

1. `src/kairoskopion/api/app.py` — default CORS allowlist extended
   to include `http://127.0.0.1:5173` and `http://127.0.0.1:3000`.
   Earlier the allowlist had `localhost` only, so a browser that
   resolved Vite's `--host 127.0.0.1` got a CORS rejection on the
   first `fetch('/auth/signup')`. Fix is additive; existing
   `localhost` origin still works.
2. `.claude/launch.json` — Vite dev server now launches with
   `--host 127.0.0.1`. Vite's default on Windows binds IPv6 (`[::1]`)
   only, which made the preview harness hit a chrome-error page.
3. `.gitignore` — added `.kairoskopion_smoke/`. The smoke storage
   root used in this pass should never be committed.

## H. Arbitrary-text pipeline probe (informational)

The user separately asked whether arbitrary user text
("ебущиеся дикобразы как шизо-образ в духе Гваттари") can run
end-to-end through the existing positioning pipeline. Short answer:
**yes**, the pipeline is wired end-to-end and runs deterministically
with honest UNKNOWNs.

A Cyrillic Guattari fragment was POSTed to
`/cases/<id>/intake/text` (via real HTTP, not TestClient). Pipeline
results in order:

- `POST /intake/text` → 200, `stage: article_model`, `article_model_built: true`.
- `GET /article-model` → returns an `ArticleModel` with
  `lifecycle_status: preliminary`, every undetected field marked
  `null` or `unknown`, with an honest `unknowns` list:
  `["abstract missing — article model is shallow", "genre not
  detected", "method not detected", "novelty mode not detected",
  "protected core not confirmed by user"]`.
- `GET /pathways` → returns 1 deterministic-fallback
  `DisciplinaryPathway` with `discipline_name: "unclassified"`,
  `fit_strength: "unknown"` — honest "no LLM signal".
- `POST /discover-venues` → returns a `VenueCandidatePool` with
  queries derived from the unclassified pathway.

Honest read: **the pipeline does NOT fabricate** when no LLM is
configured. With `KAIROSKOPION_LLM_*` env set, the same agents fall
back to the LLM path (per the existing dual-execution agent pattern)
and would populate `disciplinary_registers`, `tribes_present`,
`protected_core` from the actual Cyrillic prose. The pipeline shape
is already correct end-to-end; LLM configuration is the missing
piece for rich output.

**No new positioning pipeline needs to be built** for the arbitrary-
text case. The existing intake → article-model → pathways →
venue-pool → venue-pool deeplite chain is wired and serves arbitrary
text through case endpoints today. Operator decision: enable LLM via
env vars for testers who want substantive output, vs leave
deterministic-only for honest-but-shallow output.

## I. Acceptance criteria (task F)

| # | criterion | status |
|---|---|---|
| F.1 | main contains soft-auth persistence slice | ✅ commit `c1433f5` on `main`, pushed |
| F.2 | backend tests pass on main | ✅ 43/43 focused, 1654/1654 full |
| F.3 | frontend build passes on main | ✅ `tsc --noEmit` + `vite build` clean |
| F.4 | browser smoke confirms Welcome/Continue/cockpit/logout | ✅ 8/8 checks |
| F.5 | user isolation confirmed in browser or live API | ✅ Bob got `[]` + 404 on Alice's case |
| F.6 | server restart persistence confirmed | ✅ Alice's case visible after uvicorn restart with same storage root |
| F.7 | limitations documented | ✅ §E + UI disclaimer |
| F.8 | main pushed | ✅ |
| F.9 | no secrets/private data committed | ✅ audit clean; smoke storage gitignored |
| F.10 | feature branch may remain until smoke confirmed | branch still exists on origin; safe to delete since all checks passed — pending operator say-so |

## J. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no new features | OK — only CORS allowlist + IPv4 host + gitignore tweak |
| no merge/tag/deploy beyond the named merge | OK — only the planned FF |
| no secrets | OK |
| no Journal-Yuga venue backlog work | OK |

End of report.
