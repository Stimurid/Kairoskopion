# Staging soft-auth + workspace persistence

**Date:** 2026-06-14
**Branch:** `feature/staging-soft-auth-persistence`
**Status:** delivered; live-verified end-to-end on real HTTP.

This pass makes the cockpit usable by 3–10 trusted testers self-service:
each tester creates a workspace (display name + optional email), gets a
session token, and works on their own case projects. Data partitioned
by `user_id` on disk so tester A cannot see tester B's data and so
data survives server restart.

**This is NOT production auth.** No password. No email verification.
No SMTP. The honest security boundary is documented below. Future
production auth (magic-link or password) sits on top of the same
User table — see §G.

---

## A. Storage layout

Root: `${KAIROSKOPION_DATA_DIR}` (default `./.kairoskopion`).

```
${KAIROSKOPION_DATA_DIR}/
├── users.jsonl                     append-only User log (id, email, name, created_at)
├── sessions.jsonl                  append-only SessionToken log
├── cases/                          LEGACY: pre-auth / system / demo
│   └── <case_id>.json
└── users/
    └── <user_id>/
        └── cases/
            └── <case_id>.json      user-owned cases live here
```

The two stores are **append-only JSONL**, last-write-wins on the
in-memory index. Robust to crash mid-write. No SQL, no ORM.

Legacy / system / demo cases (no `user_id`) keep working in their old
location for backward compatibility with the existing 22 case tests
and CLI tools that use `CaseStore` directly.

---

## B. Endpoints

### POST `/auth/signup`
Input:
```json
{ "display_name": "Anna Researcher", "email": "anna@example.org" }
```
Behavior:
- `display_name` required, non-blank;
- `email` optional, normalized (trim + lowercase). Invalid emails are
  silently treated as no-email (workspace tied to device);
- **Duplicate email → 409** `email_already_registered`. Client routes
  user to `/auth/continue`. **No silent takeover.**
Output: `{ "user": {...}, "session_token": "..." }`.

### POST `/auth/continue`
Input: `{ "email": "anna@example.org" }`
Behavior:
- `email` required;
- **Known email → 200**, returns a fresh `session_token` for the same
  user. Old tokens still valid until logout/revoke;
- **Unknown email → 404** `email_not_found`. Client routes to signup.
- **No silent user creation.** Behavior is deterministic.

### GET `/auth/me`
Requires `Authorization: Bearer <token>`. Returns `{ "user": {...} }`.
Touches `last_used_at` on the session.

### POST `/auth/logout`
Idempotent. With a valid Bearer header → revokes that token.
Without → no-op (returns `{ "revoked": false }`).

### All `/cases/*` endpoints
Now require `Authorization: Bearer <token>`. Scoped by the resolved
`user_id`:
- `GET /cases` → only that user's cases;
- `GET /cases/{case_id}` → 404 if the case is not owned by the user
  (no information leak about whether it exists for someone else);
- `POST /cases` → creates the case under that user;
- `DELETE /cases/{case_id}` → same scoping;
- `POST /cases/{case_id}/intake/file` → multipart upload also carries
  the Bearer header.

Implementation uses a FastAPI dependency `_user_case(case_id,
current_user)` that resolves both at once and 404s on cross-tenant
access.

`GET /health` and `GET /agents/map` remain **unauthenticated** —
they are server-level introspection.

---

## C. Frontend behavior

`ui/src/components/AuthGate.tsx` — gate component with two tabs:

- **Sign up**: Display name (required) + Email (optional). Hint:
  *"Optional, but useful if you want to continue from another device."*
- **Continue**: Email (required). Used after `localStorage` clears,
  on a new device, or after the operator forgot the URL.

`ui/src/api/client.ts`:
- `getToken / setToken / clearToken` wrap `localStorage` (private-mode
  safe — silently no-op);
- every `request<T>()` injects `Authorization: Bearer <token>` when a
  token is present;
- on `401`, clears the stored token + throws `UnauthorizedError` so
  the App can re-prompt;
- multipart `/intake/file` route also injects the Bearer header.

`ui/src/App.tsx`:
- on boot: pings `/health`, then if a token exists, calls `/auth/me`
  to confirm it is still valid;
- if no valid user → renders `<AuthGate>`;
- if authenticated → renders the existing cockpit. Top bar gets a
  user chip + "Sign out" button.

User-facing disclaimer (verbatim, on the Auth gate):
> "This staging login has **no password** and **no email confirmation**.
> Anyone who knows your email can access your workspace. Use only
> with trusted testers."

---

## D. Isolation guarantees (live-verified)

End-to-end verification on the live server (`uvicorn ...:8000`)
using real HTTP / `curl`, NOT just the TestClient. Run captured:

| # | check | result |
|---|---|---|
| 1 | `/health` (no auth) | **200** |
| 2 | Alice signup with email | **200**, returns `user_f30a93969f6b` + token |
| 3 | Alice creates case `Alice paper` | **200**, returns `case_ec244bb9c615` |
| 4 | Bob signup (different email) | **200**, returns different `user_id` |
| 5 | Bob lists `/cases` | **200** `[]` — does NOT see Alice's case |
| 6 | Bob `GET /cases/<alice_case_id>` | **404** — no info leak |
| 7 | `GET /cases` with no token | **401** |
| 8 | Alice `/continue` by email | **200**, new session token, **same user_id** |
| 9 | Alice's new token reads her case | **200** with `title="Alice paper"` |

Disk layout verification:

```
.kairoskopion/users.jsonl     # contains both Alice + Bob (append-only)
.kairoskopion/users/user_f30a93969f6b/cases/case_ec244bb9c615.json
                              # Alice's case at the right path
.kairoskopion/users/user_abf4326abb91/                                                 
                              # Bob's dir exists; cases/ empty (he made none)
```

Case JSON on disk includes `"user_id": "user_f30a93969f6b"` — the
on-disk record carries the owner explicitly, not just the directory
path.

---

## E. Tests

`tests/test_api_auth_and_isolation.py` — **21 tests, all passing**:

`TestSignup` — display-name-only signup; email normalization
(lower + strip); empty display_name → 400; duplicate email → 409;
invalid email silently dropped.

`TestContinue` — known email returns new token same user;
unknown email → 404; missing email → 400.

`TestMe` — valid token returns user; missing/malformed/unknown
authorization → 401.

`TestLogout` — revoke works; revoked token rejected by subsequent
`/auth/me`; no-header logout is no-op.

`TestWorkspaceIsolation` — Alice's case invisible to Bob (list
+ direct fetch + delete attempt); `/continue` returns new token for
existing user; all `/cases*` endpoints require Bearer; `/health`
does NOT.

`TestPersistenceAcrossRestart` — case survives `importlib.reload`
of the app module (simulating server restart) with same data dir;
`/continue` after restart returns a working new token.

`TestStorageLayout` — user case files appear under
`users/<user_id>/cases/`, NOT in the legacy `cases/` directory.

Existing tests untouched:
- `tests/test_api_cases.py` (22 tests, legacy `CaseStore` direct
  usage) still passes — backward-compat preserved by the
  `user_id=None` legacy mode in `CaseStore`.
- Full pytest: **1654 passed**, 4 deselected (+21 new, no
  regressions vs the 1633 pre-auth baseline).

Frontend:
- `npx tsc --noEmit` clean.
- `npx vite build` clean (267 KB JS, 60 KB CSS).

---

## F. Known security limitations (do not oversell)

This is **trust-based staging identity** for a small known tester
group. The boundary:

1. **No password.** A session token is enough to act as the user.
2. **No email verification.** Anyone who knows a tester's email can
   `/continue` and immediately operate that tester's workspace.
3. **No rate limit on `/continue`.** A determined attacker can
   brute-force email guesses.
4. **No session expiry.** Tokens last until revoked. (Browsers
   typically clear `localStorage` on user action only.)
5. **CORS already permissive** for staging origins. Acceptable
   given (1)–(4) — they are the bigger limits.

**Acceptable use:** the 3–10 known testers the operator chooses to
share the staging URL with.

**NOT acceptable for:** public access; any data the operator would
not paste into a public Pastebin.

---

## G. Upgrade path to production auth

The same User + SessionToken tables are the foundation. Production
adds an identity-verification layer ON TOP — no data migration
required:

1. **Magic-link via email** (Resend free tier, $0): adds a
   `verified_at` column on User; `/auth/continue` becomes
   "send link to email", click sets a session cookie. Replaces (2).
2. **OR password**: adds `password_hash` column; `/auth/login`
   takes (email, password). Replaces (1) and (2).
3. **Rate limiting** on `/auth/continue` and `/auth/signup` (e.g.
   slowapi). Closes (3).
4. **Session expiry** with rolling refresh tokens. Closes (4).
5. **OAuth (Google / GitHub)** as a third optional path on the same
   table, with `oauth_provider` + `oauth_sub` columns.

The staging User records carry forward 1:1. Testers who became real
users keep their cases.

---

## H. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no email sending | OK |
| no password system | OK |
| no OAuth | OK |
| no paid dependency | OK |
| no public-production security claims | OK — disclaimer in UI + this doc |
| no secrets committed | OK |
| no venue-side backlog work | OK |
| no broad refactor | OK — only persistence/auth/cockpit routing |
| no merge / tag / deploy | OK |

---

## I. Files

| artefact | path | tracked |
|---|---|---|
| Auth schemas + stores + dependency | `src/kairoskopion/api/auth.py` | ✅ |
| Case extended with user_id; CaseStore partitions | `src/kairoskopion/api/cases.py` | ✅ |
| App: auth routes + all `/cases/*` scoped | `src/kairoskopion/api/app.py` | ✅ |
| Auth-aware API client (Bearer header + 401 handling) | `ui/src/api/client.ts` | ✅ |
| Welcome/Continue gate component | `ui/src/components/AuthGate.tsx` | ✅ |
| App: gate + logout chip | `ui/src/App.tsx` | ✅ |
| Auth gate CSS | `ui/src/styles/cockpit.css` | ✅ |
| Tests | `tests/test_api_auth_and_isolation.py` | ✅ |
| Report (this file) | `docs/operations/STAGING_SOFT_AUTH_AND_PERSISTENCE_REPORT.md` | ✅ |
| User / session data | `.kairoskopion/users.jsonl`, `.kairoskopion/sessions.jsonl` | gitignored |
| User-scoped case files | `.kairoskopion/users/<user_id>/cases/*.json` | gitignored |

End of report.
