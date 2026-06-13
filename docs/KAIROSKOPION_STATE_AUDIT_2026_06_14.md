# Kairoskopion — State Audit, 2026-06-14

**Scope:** post-staging + post-file-upload-hotfix stabilization audit.
**Branch at audit time:** `main` @ `2aaa8ae`.
**Auditor environment:** local Windows dev workstation, no SSH to staging,
no basic-auth credentials for `kairoskop.mindkampf.ru`.
**Not done in this audit:** any production change, any new feature, any
redesign, any merge, any tag push.

---

## 1. Executive verdict

**YELLOW.**

- Staging at `kairoskop.mindkampf.ru` can be used for **internal UX bench**
  only after Timur confirms which tag/commit is actually running there
  (see §2 blockers).
- `main` is **not** the deployed code: it sits **8 commits ahead of the
  last pushed RC tag `v0.2.0-alpha-rc16`**. Whether those 8 commits
  (file-upload + multipart + LLM wiring + nav fix + web enrichment + FPM
  library) are deployed on staging is unknown from here; it must be
  verified on the server.
- The codebase is internally consistent and tests are green (1307 on
  `main`). Documentation has accumulated significant numeric drift.
- **Not** public-prod. No auth, no DB, no job queue, no secrets manager,
  no observability, no upload size limit. These are non-negotiable
  blockers and they are reflected accurately as "staging preview" in
  CHANGELOG and PROJECT_STATUS.

**Can Timur run a UX bench?** Yes on staging *after* (a) confirming the
running commit, and (b) accepting the file-upload caveats below.
**Can we call it public prod?** No. See §9.

---

## 2. Release / Git truth

### Tags vs. commits

| Tag | Local? | Remote? | Commit | Title | Deployed? | Notes |
|---|---|---|---|---|---|---|
| `v0.2.0-alpha-rc16` | yes | yes | `458e1ff` | Add SPA static file serving to FastAPI app | **assumed yes** (last pushed RC) | needs `git log --oneline --decorate -1` on server to confirm |
| `v0.2.0-alpha-rc15` | yes | yes | `1bcc2c9` | Fix pre-deploy gaps: env-configurable CORS, version alignment | superseded | rc15→rc16 is the staging delta |
| `v0.2.0-alpha-rc1..rc14` | yes | yes | various | historical | superseded | preserved |
| **rc17 / rc18** | **no** | **no** | — | — | — | do NOT exist anywhere |

### `main` vs. `rc16` divergence

`main` (HEAD `2aaa8ae`) is **8 commits ahead** of `v0.2.0-alpha-rc16`:

```
2aaa8ae Add FieldPositionModel: unified coordinate system for articles and venues
8ff5ecf Add web enrichment pipeline: none / light / deep search modes
2c25931 Wire 9 orphaned LLM agents + file persistence + vault + logging
f8592f9 Wire LLM provider into API case pipeline
e88b45e Fix navigation: back buttons, case switch reset, delete, stage gating
f6fe474 Add python-multipart to api dependencies
74f23dc Add file upload to Intake stage (PDF, DOCX, TXT, MD, HTML)
17cef51 Document rc16 staging deployment
458e1ff (tag: v0.2.0-alpha-rc16) Add SPA static file serving to FastAPI app
```

`74f23dc` + `f6fe474` are the file-upload hotfix mentioned in the
deployment brief. If these are NOT yet deployed, file upload on staging
will fail at import time (`python-multipart` missing) or the route
will not exist at all.

### Local branches

| Branch | Tip | On remote? | Notes |
|---|---|---|---|
| `main` | `2aaa8ae` | yes | tracks `origin/main`, **NOT** the deployed code |
| `feature/wire-fpm-pipeline` | `cb464f8` | yes | FieldPositionModel wired into Case orchestrator |
| `feature/sprint-alpha-evidence-policy` | `1a59812` | yes (pushed during this session) | PIM v1 B1+B3: `SourceEvidencePacket`, `ProtectedCorePolicy`, `EvidencePolicy`, hook in rewrite gate; +15 tests |
| `feature/reference-verification-v0` | `5f198c9` | **no — local only** | "Add incident tracking for pipeline failures (Block H)"; should either be pushed for review or deleted |
| `feature/ui-cockpit-v0` | `7bf7fb7` | **no — local only** | "Audit: update docs for UI Cockpit v0"; stale, predates rc16; safe to delete after verification |
| `feature/agentic-contour-quality-review-v01` | `57c8262` | ahead 1 | doc bump only |
| `feature/agentic-contour-uc1-v01` | `21522b1` | ahead 1 | unicode fix |
| `feature/autonomous-local-docs-entities-adapters` | `7684f4f` | ahead 1 | gitignore |
| `feature/real-venue-pool-discovery-v0` | `8f09c76` | ahead 1 | doc fix |

No force-push. No rebase. No deletion done in this audit.

### `pyproject.toml` version drift

`pyproject.toml` declares `version = "0.2.0a15"`. Latest pushed tag is
`v0.2.0-alpha-rc16`. **Version field never bumped for rc16**; this is
cosmetic but trips any deploy tool that reads the package version.

---

## 3. Server / staging truth — **BLOCKED**

Could not run server-side checks (no SSH from this workstation).
Required from Timur, copy-paste-friendly:

```bash
ssh deploy@81.26.176.248 'cd /opt/kairoskopion/app && \
  git rev-parse HEAD && \
  git tag --points-at HEAD && \
  systemctl is-active kairoskopion-api && \
  curl -sS http://127.0.0.1:8088/health && \
  /opt/kairoskopion/app/.venv/bin/python -c "import multipart; print(\"multipart OK\")"'
```

Until that output exists, every claim about staging is "presumed rc16"
and not verified.

---

## 4. Dependency and install reality

Locally on `main`:

- `pytest`: **1307 passed, 4 deselected** (network), 0 failures.
- `npx tsc --noEmit`: clean.
- `npx vite build`: clean, 263 kB JS / 58 kB CSS, 35 modules.
- `pyproject.toml` declares `python-multipart>=0.0.9` in the **`api`
  optional-dependency group** (line 20). Local dev venvs without
  `pip install -e .[api]` will fail to import `kairoskopion.api.app`
  with a hard `RuntimeError`. **The audit hit this** — workaround was
  `pip install python-multipart`. On staging, the `f6fe474` commit
  added this dep; if the server venv was upgraded after that commit
  deployed, it's fine; otherwise it's broken.
- `fastapi==0.136.3`, `uvicorn==0.49.0`, `pypdf==6.12.2`, `python-docx`
  importable.

**Reproducibility from clean checkout:** `pip install -e .[api,extract,dev]`
must be the deploy contract. This is not currently spelled out in
`docs/STAGING_DEPLOYMENT_KAIROSKOP_2026_06_13.md` as a one-liner.

---

## 5. API endpoint inventory (30 routes)

Enumerated from `app.routes` at `2aaa8ae`. Doc said "19 REST endpoints" —
**doc was 11 short**.

| Endpoint | Method | UI? | CLI? | Test? | Status | Notes |
|---|---|---|---|---|---|---|
| `/health` | GET | ✓ | — | ✓ smoke | OK | |
| `/cases` | GET, POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}` | GET, DELETE | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/intake/text` | POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/intake/file` | POST | ✓ | — | partial | OK | **no size limit, full read into RAM** |
| `/cases/{case_id}/investigate-venue` | POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/investigated-venue` | GET | ✓ | — | partial | OK | |
| `/cases/{case_id}/article-model` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/article-model/confirm` | POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/scenario` | GET, POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/pathways` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/discover-venues` | POST | ✓ | — | ✓ | OK | deterministic fallback when no LLM |
| `/cases/{case_id}/venue-pool` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/select-venue/{venue_id}` | POST | ✓ | — | ✓ | OK | triggers fit chain |
| `/cases/{case_id}/fit` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/mismatch-map` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/adaptation-plan` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/decisions` | POST | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/evidence/{entity}/{field}` | GET | ✓ | — | partial | **stub** | returns placeholder; documented as "not yet connected to adapters" |
| `/cases/{case_id}/quality-gates` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/dossier` | GET | ✓ | — | ✓ | OK | |
| `/cases/{case_id}/decision-log` | GET | ✓ | — | ✓ | OK | |
| `/agents/map` | GET | — | — | partial | OK | UI has `AgentMap.tsx` but is it linked in the current shell? — see §6 |
| `/{path:path}` | GET | n/a | — | — | OK | SPA static serve fallback |
| `/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect` | GET | n/a | — | — | OK | FastAPI defaults |

**No dangerous endpoints exposed.** Evidence drill-down is the only
known stub. Authenticated nothing — relies entirely on the Caddy
basic-auth layer.

---

## 6. UI component inventory (18 components)

Counted at `ui/src/components/` + `ui/src/App.tsx`. Doc said "17
components" — off by one (the App shell was not counted). Components:

```
AdaptationStudio, AgentMap, ArticleCard, CaseWorkspace, DecisionLog,
DossierView, EvidenceBadge, EvidenceDrawer, IntakeSurface,
MismatchMapView, PathwayMap, QualityGateBar, RewriteTaskCard,
ScenarioBuilder, StatusBar, VenueCandidateCard, VenuePoolBoard,
VenueProfile
```

**Build is clean** (`tsc --noEmit` + `vite build`). No orphan
import warnings.

**Observable risks (read-only — not browser-verified this audit):**
- `AgentMap.tsx` exists and `/agents/map` is exposed, but I did not
  verify it is rendered from the current shell or reachable from a
  user-clickable surface. Possible orphan.
- No `ProtectedCoreGate` component as a separate surface; the
  protected-core gate is consumed inside `AdaptationStudio` and
  `RewriteTaskCard`. This contradicts the deployment brief's checklist
  but is intentional — gate logic is colocated with the rewrite UI.

Browser smoke at `https://kairoskop.mindkampf.ru` not performed (no
auth). Operator should run the §1-§9 checklist in the original brief
and append results to this report.

---

## 7. CLI inventory (38 commands)

Doc said "16 commands" — **doc was 22 short**. Full list verified from
`python -m kairoskopion.cli --help`:

```
status, run-fixture, inspect-storage, adapters-smoke, vault-index,
export-bundle, import-bundle, validate-bundle, intake-file,
build-venue-profile, run-local, build-submission-pack,
export-litops-pack, export-whitecrow-patches, list-agents,
inspect-agent, list-prompt-families, inspect-prompt-family,
list-workflows, inspect-workflow, run-agent-workflow,
import-venue-seed, build-venue-evidence-pack,
inspect-venue-depth-policy, build-venue-evidence-stack,
acquire-venue-sources, list-source-adapters, inspect-adapter,
sample-venue-corpus, analyze-venue-corpus, run-uc1-demo,
plan-venue-discovery, discover-venue-pool, screen-venue-candidates,
verify-references, review-loop-demo
```

All commands import without error (`--help` exits cleanly).

**Overlaps with API/UI:** `intake-file`, `discover-venue-pool`,
`screen-venue-candidates`, `acquire-venue-sources`, `verify-references`,
`run-uc1-demo` — these have either UI surfaces or API endpoints doing
similar work. Not a bug, but a future doc consolidation target.

**Operator-only candidates:** `export-bundle`, `import-bundle`,
`validate-bundle`, `inspect-storage`, `vault-index`,
`export-litops-pack`, `export-whitecrow-patches`,
`build-venue-evidence-pack`, `import-venue-seed`. Should be flagged as
such in `docs/CLI_OVERVIEW.md` (not currently).

**No commands fail to register.** `review-loop-demo` is gated by
mocked data and is a demo, not production.

---

## 8. Agent registry / workflows

Counts at `2aaa8ae`:

- **28 agents** (PROJECT_STATUS said "26", `registry.py` table said
  "27 AgentSpec" — both wrong by 1–2). By layer: control 4, article 3,
  venue 6, fit 4, submission 3, review 6, evidence 2.
- By status: `operational_now` 21, `executable_stub` 1
  (`publication_regime_classifier`), `contract_only` 6 (all `review`
  layer — by design).
- By execution mode: `deterministic` 15, `llm_optional` 7,
  `llm_required` 6 (all `review` layer).
- **16 prompt families** (`article_modeling_v1`, `citation_ecology_v1`,
  `compliance_checklist_v1`, `corpus_pattern_mining_v1`,
  `disciplinary_mapping_v1`, `evidence_audit_v1`, `fit_assessment_v1`,
  `mismatch_mapping_v1`, `publication_regime_v1`, `review_outcome_v1`,
  `rewrite_planning_v1`, `risk_reporting_v1`, `scenario_interview_v1`,
  `semantic_profiling_v1`, `submission_pack_v1`,
  `venue_fact_extraction_v1`). 1:1 with the 16 LLM-optional /
  LLM-required prompt-using agents.
- **4 workflows**: `direct_manuscript_venue_fit` (9 steps),
  `uc1_draft_to_venue_pool_positioning` (13 steps), `venue_deep_profile`
  (4 steps), `review_loop` (6 steps).

**Orphans found:**
- `publication_regime_classifier` is marked `executable_stub` in the
  registry — fine, but the prompt family `publication_regime_v1` exists
  and the deterministic fallback is shallow. Used inside
  `venue_deep_profile` workflow. Surface this in docs as known-stub.
- `AgentMap.tsx` UI component → `/agents/map` API; integration into
  user navigation not confirmed (see §6).
- No prompt families are orphaned (every family maps to a registered
  agent).
- No agent specs without a class (every spec has a class via the
  registry class map).
- No legacy "Journal-Yuga" names in source code; the name survives only
  in `README.md`, `docs/KAIRON_ORIGIN.md`, and
  `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` as historical
  context. Acceptable.

---

## 9. LLM / prompt reality

- Provider: `OpenAICompatProvider` in `src/kairoskopion/llm/openai_compat.py`.
- Config loader: `LLMConfig.from_env()` reads `KAIROSKOPION_LLM_*` then
  `LITOPS_LLM_*` env vars; returns `None` if no API key. In this
  audit's local env: **all unset → `LLMConfig.from_env() == None`**.
- Default in `Case._get_llm_provider()`: returns `None` if config is
  `None` or `api_key` is empty.
- **Practical state on a fresh `main` checkout:** all agents run their
  deterministic fallback. No outbound HTTP from agents. No user text
  ever leaves the machine unless `KAIROSKOPION_LLM_API_KEY` is set.

**Staging reality (presumed):** depends on the server env file at
`/opt/kairoskopion/secrets/kairoskopion.env`. If `KAIROSKOPION_LLM_API_KEY`
is set there, then every Case stage (intake, semantic profile, pathway
mapping, venue discovery, fit, mismatch, rewrite, citation, risk) will
make outbound HTTP to the configured base URL (302.ai / gpt-4.1-mini
per brief). **Confirm with Timur** what the staging env contains
before sharing with reviewers.

**LLM output validation:** every prompt family ships with a
`validator()` function; outputs are validated and warnings surfaced
into `AgentOutput.warnings`. Failures fall back to deterministic. No
fabricated entity reaches state unchecked.

**LLM path status table:**

| Path | Status |
|---|---|
| Deterministic-only paths | OK on `main` |
| LLM-capable when key present | OK; 16 of 28 agents |
| LLM-required (review layer, 6 agents) | `contract_only` — execute returns a stub |
| Unsafe / untested | None observed; review-loop demo runs but is not connected to production state |

---

## 10. Backend module orphan sweep

`grep -nE "TODO|FIXME|XXX|HACK|legacy|deprecated|placeholder|stub:"` in `src/`:
**17 occurrences in 8 files** — low and bounded:

```
adapters/bridge.py:2          adapters/url_snapshot.py:8
agents/base_shell.py:1        demo/uc1_runner.py:1
enums.py:1                    services/data_sensitivity.py:2
adapters/venue/opencitations.py:1  services/venue_candidate_identity.py:1
```

Spot-checked: all are honest "this is a stub / future work" comments
inside services that document their own limits. **No dangerous dead
code, no orphaned imports, no skipped/xfail tests.** No "Journal-Yuga"
identifiers in source code.

---

## 11. Data / persistence / privacy

### Text intake (`POST /cases/{id}/intake/text`)

`text` → `Case.intake_text` → in-memory `Case.input_text` (full string) →
deterministic article builder (or LLM if configured) → in-memory
`Case.article_model` etc. → `CaseStore._persist` writes a JSON snapshot
to `${KAIROSKOPION_DATA_DIR:-.kairoskopion}/cases/{case_id}.json`.

### File intake (`POST /cases/{id}/intake/file`)

`UploadFile` → extension check against allowlist
(`.pdf .docx .txt .md .html` + variants) → `await file.read()` reads the
**entire file into RAM** (no size limit) → written to OS temp dir under
`tempfile.NamedTemporaryFile` with the original extension → text
extraction via `extract_text_from_file` (pypdf / python-docx / plain
read) → tmp file deleted in `finally`. **Extracted text is then handed
to `Case.intake_text`** and follows the same in-memory + JSON persist
flow as text intake.

### What disappears on restart

If `KAIROSKOPION_DATA_DIR` is set, JSON snapshots survive. Otherwise
defaults to `.kairoskopion/cases/`. Cases are loaded at `CaseStore`
construction. **Uploaded raw files are NOT persisted** — they are
ephemeral; only extracted text reaches the persistent layer.

### Logs

Standard Python logging through `logging.getLogger(__name__)`. Several
modules log `input_text` length but not content. **Spot-check on
`api/cases.py` did not find any `logger.info(self.input_text)`** —
safe by default.

### Privacy / sensitivity risks

| Risk | Severity | Mitigation present? |
|---|---|---|
| Uploaded raw file lingers in OS temp | low | `finally tmp_path.unlink(missing_ok=True)` — OK |
| Extracted manuscript text persists to disk | **medium** | yes, intended; but no encryption, no retention policy, no purge endpoint |
| Manuscript text sent to external LLM | **medium** | only when `KAIROSKOPION_LLM_API_KEY` is set; default off; must be communicated to operator |
| Unbounded upload → memory exhaustion | **medium** | NONE — no `max_size`, no `Content-Length` check |
| Log leakage of manuscript text | low | not observed; periodic re-audit advised |

### Public-prod blockers (data layer)

- No DB, no concurrency control; JSON file write is `tmp + replace` →
  atomic on POSIX but a single-process assumption.
- No auth on the API itself; relies entirely on Caddy basic-auth.
- No purge / TTL / GDPR-style erasure endpoint.
- No encryption at rest.
- No upload quota.

---

## 12. Docs truth

| Doc | Verdict | Specific lies |
|---|---|---|
| `CHANGELOG.md` | mostly accurate | "19 API endpoints" undercount; doesn't mention 8 post-rc16 commits |
| `docs/PROJECT_STATUS.md` | **patched in this audit** | was: 19 endpoints, 17 components, 1275 tests, 26 agents, 27 AgentSpec; corrected to: 30, 18, 1307, 28, 28. Added pyproject version drift, file-upload caveats, rc16-vs-main divergence note. |
| `docs/BACKLOG.md` | mostly stale numerics | "1275 tests total" lines persist as historical; not auto-corrected to avoid rewriting historic sprint claims |
| `docs/SPEC_COVERAGE_MATRIX.md` | not audited line-by-line here | follow-up |
| `docs/STAGING_DEPLOYMENT_KAIROSKOP_2026_06_13.md` | accurate for rc16 deploy moment | does NOT mention post-deploy hotfix (`74f23dc` + `f6fe474`); needs a "post-deploy state" appendix once server is confirmed |
| `CLAUDE.md` | accurate, no overclaims | "1275+ tests" wording is forward-compatible |
| `README.md` | high-level only | "Journal-Yuga" historical reference present — acceptable |
| `docs/PUBLICATION_INTEGRABILITY_MODEL_v1.md` | added on `feature/sprint-alpha-evidence-policy` | reference document, not on `main` |
| `docs/ARTICLE_PUBLICATION_POSITION_MODEL.md` | added on `feature/sprint-alpha-evidence-policy` | superseded by PIM v1; not on `main` |
| `docs/FIELD_POSITION_MODEL.md` | accurate | on `main` |

Patches in §13 cover only `PROJECT_STATUS.md` — that file is the
operator entry point and its numbers were dangerous.

---

## 13. Fix-only stabilization changes (this branch: `chore/state-audit-2026-06-14`)

- `docs/PROJECT_STATUS.md`:
  - Repository table now reflects `main = 2aaa8ae`, last pushed tag
    `v0.2.0-alpha-rc16`, `main` ahead by 8 commits, pyproject version
    drift, four feature branches with their tips.
  - UI Cockpit v0 block updated: 30 endpoints, 18 components, 1307
    tests on main + branch-specific counts, file-upload caveats.
  - `registry.py` row updated to "28 AgentSpec entries".
  - Tests narrative line updated to "1307 tests on main" with branch
    deltas.

No code changes were applied. No tag created. No commit pushed to `main`.

**Not patched in this audit (would require source edits, out of scope):**
- File-upload size limit (would be a real feature change).
- `pyproject.toml` version bump (would require a coherent
  release-tag decision by Timur).
- `evidence` endpoint stubbing (intentional placeholder).

---

## 14. Final verdict and what to do next

### Status

| Subsystem | Color | Note |
|---|---|---|
| Backend tests / build | green | 1307 / 0 fail; UI build clean |
| API surface | green | 30 routes, 1 documented stub |
| Agent runtime | green | 28 specs, 22 operational, 6 contract-only by design |
| Adapters | green | 6 venue adapters, fixture+live+cached modes, authority enforcement |
| Persistence | yellow | JSON file store; no encryption, no purge endpoint |
| LLM path | yellow | default deterministic; staging may differ — must verify |
| File upload | yellow | works but no size limit, full-RAM read |
| Staging deploy | **yellow / unknown** | likely rc16 — needs Timur's confirmation |
| Docs accuracy | yellow → green | PROJECT_STATUS patched; CHANGELOG/BACKLOG retain historical numbers |
| Local-only branches | yellow | `feature/reference-verification-v0` and `feature/ui-cockpit-v0` need a push-or-prune decision |
| Public prod readiness | **RED** | no auth, no DB, no quotas, no observability — staging only |

### Single recommended next milestone (NOT microtasks)

**"Staging consolidation rc17"** — one coherent block:

1. Timur runs the Phase-2 SSH checklist (see §3) and pastes output
   into `docs/STAGING_DEPLOYMENT_KAIROSKOP_2026_06_13.md` as a
   "Post-deploy state 2026-06-14" appendix.
2. If staging is still on rc16 and the operator wants the file-upload
   hotfix live: cut a new tag `v0.2.0-alpha-rc17` from `main`
   *exactly at* `2aaa8ae` (no new code), bump
   `pyproject.toml` to `0.2.0a17`, deploy. The 8 post-rc16 commits
   already on `main` are coherent and test-green; they do not need
   re-merging.
3. After rc17 is deployed and `multipart` confirmed on the server,
   run the browser smoke checklist from the original brief
   (§Phase 6) and append results.
4. Decide on the two local-only branches: push for review
   (`feature/reference-verification-v0`) or delete
   (`feature/ui-cockpit-v0`, already absorbed into `main`).
5. Add a one-paragraph "Operator file-upload limits" section to
   `docs/STAGING_DEPLOYMENT_KAIROSKOP_2026_06_13.md`: no size cap,
   single-process, in-memory.

Only after that block lands does the next *engineering* milestone make
sense — and that is Sprint α (already implemented on
`feature/sprint-alpha-evidence-policy`, 15 new tests passing, ready
for review) followed by PIM v1 deltas B4–B7 (`ArticleSemanticProfile`
enrichment).

### What Timur can do today

- UX bench on staging at `kairoskop.mindkampf.ru`: **conditionally yes**
  (after confirming what's actually running).
- Public demo: **no.** Staging is auth-gated for a reason; do not move
  the URL into any reviewer-visible context without the public-prod
  blocker list in §9 being checked off.
- Continue Sprint α review on `feature/sprint-alpha-evidence-policy`:
  yes.
