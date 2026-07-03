# P11 Post-Merge Operator Smoke Report

**Date:** 2026-07-03
**Main commit:** `4f6fada` (merge: P11 prompt pipeline workbench)
**Environment:** local dev (localhost:8000 + localhost:5173)
**LLM provider:** NOT configured (deterministic fallback only)
**Verdict:** `P11_POST_MERGE_PARTIAL_NO_LIVE_PROVIDER_AND_REPLAY_NOT_EXECUTED`

---

## 0. Sync

- `git pull` confirmed: main at `4f6fada`, up to date with origin
- No dirty tracked files

## 1. Start Local App

| Service | Port | Status |
|---------|------|--------|
| Backend (uvicorn) | 8000 | **OK** — `/health` → `{"status":"ok"}` |
| Frontend (vite dev) | 5173 | **OK** — HMR active, no build errors |

## 2. Browser / Operator Smoke

### 2.1 Auth & Case Creation (points 1–4)

| # | Check | Result |
|---|-------|--------|
| 1 | Open localhost:5173 | **PASS** — Kairoskopion cockpit loads, dark theme |
| 2 | Soft-auth login (Operator Smoke / smoke@test.local) | **PASS** — single form, name + email, logged in |
| 3 | Create case | **PASS** — `case_8a72b7334c74` created, case sidebar shows it |
| 4 | Paste article text (1135 chars, futures literacy) | **PASS** — text pasted, "Анализировать" clicked, POST `/cases/.../intake/text` → 200 |

### 2.2 Article Model View (points 4–5)

| # | Check | Result |
|---|-------|--------|
| 4a | Article model rendered | **PASS** — title "Futures Literacy as a Civic Capability" visible |
| 4b | Human model view | **PASS** — 9 blocks, accept/contest buttons, "Человеческая модель" tab active |
| 4c | Pipeline stage navigation | **PASS** — 10 stages visible (Ввод → Досье) |
| 4d | Evidence panel | **PASS** — badge legend (FACT, CLAIM, CORPUS, INFERRED, USER, UNKNOWN, STALE, CONFLICT) |
| 4e | Disclaimer banner | **PASS** — "Предварительное позиционирование — это не рекомендация к подаче" |
| 4f | Disciplinary positioning | **PASS** — Region: Auto, confidence: low, honest "no matches" message |

### 2.3 Pipeline Workbench (points 5–15)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 5 | Open Pipeline Workbench | **PASS** | "Pipeline Workbench" heading, button toggles Hide/Show |
| 6a | Pipeline stages listed | **PASS** | 18 stages in table: #, Stage, Producer, Prompt, Actions |
| 6b | Producer types visible | **PASS** | `deterministic` (intake, bibliography, fit_gate, mismatch, rewrite, risk, evidence_audit), `llm_agent` (11 stages) |
| 6c | Prompt family IDs visible | **PASS** | `article_modeling`, `venue_fact_extraction`, `fit_assessment`, etc. — `—` for deterministic stages |
| 6d | Action buttons | **PASS** | "Stage" (rerun single) and "From here" (rerun from stage) per row |
| 7 | Rerun All → creates run | **PASS** | POST `/api/.../rerun` → 200; Runs (0) → Runs (1); `prun_d741a1e2aaeb`, 18 nodes, `pending` status |
| 8 | Runs tab shows run | **PASS** | Run ID, status, trigger (`rerun_all`), node count visible |
| 9 | Prompts tab | **PASS** | Prompts (19) — 19 prompt families discovered at runtime |
| 10 | Overrides tab | **PASS** | Overrides (0) initially, Overrides (1) after API override creation |
| 11 | Compare tab | **PARTIAL** | A/B run selectors render with dropdown options; diff returned empty (no real output differences between scaffold runs) |
| 12 | Data survives reload | **PASS** | After page reload: case, article model, Runs (2), Overrides (1), Prompts (19) all preserved |

### 2.4 API-driven Workbench Verification

| # | Endpoint | Result | Evidence |
|---|----------|--------|----------|
| A1 | `GET /api/pipeline-stages` | **PASS** | 18 stages with metadata |
| A2 | `GET /api/prompts` | **PASS** | 19 prompt families with system_prompt, user_template, version_hash |
| A3 | `GET /api/prompts/article_modeling` | **PASS** | Full prompt text, version_hash `30465d733c486759`, agent_ref `ArticleModelerAgent` |
| A4 | `POST /api/.../rerun` | **PASS** | Created `prun_d741a1e2aaeb` with 18 nodes |
| A5 | `GET /api/.../pipeline-runs` | **PASS** | 2 runs listed (rerun_all + rerun_stage) |
| A6 | `GET /api/.../pipeline-runs/{id}/nodes` | **PASS** | 18 nodes with stage_id, producer_type, prompt_family_id, status, diagnostics |
| A7 | `GET /api/.../nodes/{id}/prompt` | **PARTIAL/NO** | "No prompt records" — replay scaffold nodes do not produce PromptRunRecord |
| A8 | `POST /api/.../prompt-overrides` | **PASS** | Created `povr_99277032c6e0` for `article_modeling` with custom system_prompt |
| A9 | `GET /api/.../prompt-overrides` | **PASS** | 1 override listed with all fields |
| A10 | `POST /api/.../rerun-stage` | **PARTIAL** | Created `prun_da3b1c1c9588` with `base_run_id`, but `execution_status: partial_not_replayable`, `unsupported_stages: [article_model]` — stage was not actually re-executed |
| A11 | `GET /api/.../pipeline-diff` | **PARTIAL** | Returns 200 with empty diff — both scaffold runs have no output differences to compare |

### Node Detail Verification

Sample node `pnode_5b7d00317dd3` (article_model):
- `stage_id`: `article_model`
- `producer_type`: `llm_agent`
- `service_or_agent`: `ArticleModelerAgent`
- `prompt_family_id`: `article_modeling`
- `status`: `stage_not_yet_replayable`
- `rerunnable`: `true`
- `diagnostics`: `["stage 'article_model' requires full pipeline context"]`

Replay creates trace structure (node IDs, stage metadata, status fields), but does not execute the stage or produce PromptRunRecord / output_hash.

## 3. API Smoke

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | **200** `{"status":"ok"}` |
| `/api/pipeline-stages` | GET | **200** — 18 stages |
| `/api/prompts` | GET | **200** — 19 families |
| `/api/prompts/{id}` | GET | **200** — full prompt detail |
| `/api/cases/{id}/pipeline-runs` | GET | **200** — 2 runs |
| `/api/cases/{id}/pipeline-runs/{id}/nodes` | GET | **200** — 18 nodes |
| `/api/cases/{id}/pipeline-runs/{id}/nodes/{id}/prompt` | GET | **404** — no PromptRunRecord for replay nodes |
| `/api/cases/{id}/prompt-overrides` | GET/POST | **200** — CRUD works |
| `/api/cases/{id}/rerun` | POST | **200** — creates run (scaffold) |
| `/api/cases/{id}/rerun-stage` | POST | **200** — creates stage-scoped run (not executed) |
| `/api/cases/{id}/pipeline-diff` | GET | **200** — returns empty diff |
| `/cases/{id}/intake/text` | POST | **200** — intake processes |
| `/cases/{id}/article-model` | GET | **200** — model returned |
| `/cases/{id}/article-model/human-view` | GET | **200** — human view rendered |
| `/cases/{id}/discipline-matches` | GET | **200** — matches returned |
| `/correction-signals` | GET | **200** — signals returned |
| `/auth/signup` | POST | **200** — soft-auth works |

No 500 errors observed.

## 4. Privacy Check

| Check | Result |
|-------|--------|
| `.env` tracked? | **NO** — `.gitignore` blocks it; only `.env.example` tracked |
| `data/input/private/` tracked? | **NO** — not in `git ls-files` |
| `data/private_work/` tracked? | **NO** — gitignored |
| `private_inputs/` tracked? | **NO** — gitignored |
| API keys in code? | **NO** — grep found only `.env.example` |
| Raw manuscript in repo? | **NO** — only synthetic fixtures |

## 5. Blockers

1. **Real replay execution not proven in browser smoke.** `rerun_all` and `rerun_stage` create scaffold/pending nodes but do not execute pipeline stages. All LLM-capable stages return `stage_not_yet_replayable`.
2. **PromptRunRecord for replay node missing.** `GET .../nodes/{id}/prompt` returns 404. PromptRunRecords are only created during real pipeline execution (via `_record_prompt()`), not during replay.
3. **Override injection during actual rerun not proven.** Override was created via API (`povr_99277032c6e0`), but no rerun actually executed a stage to demonstrate the override being applied. Acceptance gate unit tests (`test_override_injection_real`) proved this path works, but browser smoke did not.
4. **Meaningful diff not proven.** `GET .../pipeline-diff` returns empty array. Both runs are scaffold runs with no real `output_hash` or `prompt_override_id` differences. Acceptance gate unit test (`test_diff_real_runs`) proved diff works with real runs, but browser smoke did not.
5. **Live LLM semantic rerun not proven.** No LLM provider is configured locally (`KAIROSKOPION_LLM_PROVIDER` not set). All LLM-capable stages fall back to deterministic path. Live semantic rerun requires a configured provider.

**Note on acceptance gate vs. browser smoke:** The P11 acceptance gate report (`docs/operations/P11_ACCEPTANCE_GATE_REPORT.md`, commit `f741c96`) proved blockers 2–4 work at the unit/integration test level using `ManuscriptVenueFitPipeline.execute()` with real instrumentation. The browser smoke tested the UI shell and API routing but could not reproduce real execution because: (a) no LLM provider is configured, and (b) the replay engine creates scaffold structure, not real execution.

## 6. Verdict

**`P11_POST_MERGE_PARTIAL_NO_LIVE_PROVIDER_AND_REPLAY_NOT_EXECUTED`**

### Verdict Table

| Check | Verdict | Evidence |
|-------|---------|----------|
| local backend/frontend | **PASS** | Both servers start, health OK |
| auth/case/intake | **PASS** | Soft-auth login, case creation, text intake all work |
| workbench opens | **PASS** | Pipeline Workbench renders with all tabs |
| stages visible | **PASS** | 18 stages with producer types and prompt families |
| prompt registry | **PASS** | 19 prompt families discovered with full system/user prompts |
| override CRUD | **PASS** | Create + list overrides via API, reflected in UI |
| node PromptRunRecord from replay | **PARTIAL/NO** | replay nodes had no PromptRunRecord |
| rerun stage | **PARTIAL** | returned `partial_not_replayable` — scaffold created, stage not executed |
| compare UI | **PARTIAL** | selectors render, diff empty |
| live semantic rerun | **NO** | no provider configured |

### Owner Answers

| Question | Answer |
|----------|--------|
| Browser upload/run/workbench works? | **YES** |
| Prompt inspection works? | **PARTIAL** — prompt families visible; PromptRunRecord not available for replay nodes |
| Prompt override works? | **PARTIAL** — CRUD works; injection during actual execution not proven in browser |
| Rerun works without provider? | **PARTIAL** — scaffold run created; actual stage execution requires provider |
| Live LLM semantic rerun proven? | **NO** |

### What PASS Means Here

The UI shell, API routing, prompt registry, override CRUD, and data persistence all work correctly. The system does not crash, does not hide failures, and does not pretend replay nodes are executed. Status fields (`stage_not_yet_replayable`, `partial_not_replayable`) are honest.

### What Would Be Needed for Full PASS

1. Configure a live LLM provider (`KAIROSKOPION_LLM_PROVIDER=openai` or equivalent)
2. Run a real pipeline execution that produces PromptRunRecords with `output_hash`
3. Create an override, rerun with override, confirm override appears in PromptRunRecord
4. Run diff between two real runs and confirm non-empty diff output
5. Verify compare UI displays actual old/new output differences
