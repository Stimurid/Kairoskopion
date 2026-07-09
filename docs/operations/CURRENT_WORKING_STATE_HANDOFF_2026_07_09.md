# Working State Handoff — 2026-07-09

This document is sufficient to resume work without another agent conversation.

---

## Repository state

| Item | Value |
|---|---|
| Final main commit | `ee684c5` (merge: P10 RU education AI operational harvest) |
| Report commit | `1e1161f` (docs: record final working main and P10 operational state) |
| Clean/dirty | Clean tracked tree; unrelated untracked files present (p73, Engelbart, Round3 — leave untouched) |
| Remote push | main pushed to origin |
| Python | >=3.11 |
| Node.js | >=18 |

### Merge commits in main (most recent first)

| Commit | Description |
|---|---|
| `ee684c5` | merge: P10 RU education AI operational harvest |
| `20b6452` | merge: preserve LLM attempt metadata in article intake |
| `a63ebab` | merge: harden LLM timeouts fallbacks and provider diagnostics |
| `987fd7f` | merge: P11.3 live provider replay for article model |
| `828a983` | merge: audit refactor security and P11 browser regression fixes |
| `51672c8` | merge: P11.2 real prompt replay slice |
| `4f6fada` | merge: P11 prompt pipeline workbench |

### Superseded branches (do not merge)

| Branch | Reason |
|---|---|
| `feature/p10-ru-education-ai-operational-harvest` | Superseded by `feature/p10-operational-harvest-final` (now merged) |
| `feature/llm-timeout-fallback-session-logging` | Already merged via `a63ebab` |
| `fix/intake-attempt-metadata-propagation` | Already merged via `20b6452` |
| `feature/p11-prompt-pipeline-workbench` | Already merged via `4f6fada` |
| `feature/p11-2-real-replay-execution` | Already merged via `51672c8` |
| `feature/p11-3-live-replay-provider-call` | Already merged via `987fd7f` |
| `feature/audit-refactor-optimize` | Already merged via `828a983` |

---

## What currently works

### Article intake
- Text intake via API (`POST /cases/{id}/intake/text`)
- File intake: `.md`, `.txt`, `.json`, `.html`, `.pdf`, `.docx`
- ArticleModel built with full attempt metadata (LLM attempts, effective model, timestamps)
- Deterministic fallback when no LLM provider configured

### P11 Workbench
- Prompt override per stage
- No-provider replay (deterministic fallback)
- Live provider replay (when 302.ai or compatible provider available)
- Stage-by-stage prompt inspection

### LLM infrastructure
- OpenAI-compatible provider (302.ai tested with `gpt-4o-mini`)
- Timeout/retry/fallback hardening
- Provider diagnostic logs (bounded, no secrets)
- Attempt history and effective-model trace
- 16 model-per-role overrides

### Venue discovery (P10)
- 6 source needs defined (SN-01 through SN-06)
- 6 acquisition tasks (4 open, 2 blocked)
- 87 provisional venue records from OpenAlex + DOAJ (LIVE queries)
- Verification gate: all records correctly remain `keep_provisional`
- Review packets: MD + JSONL + TSV
- Provisional candidate export with domain tier classification
- Operator CLI commands for full harvest path

### Other
- 58 API endpoints
- 29 UI components (React + TypeScript)
- Soft auth (display name + email, no password)
- Disk-backed persistence (CaseStore)
- Vault cards, exchange bundles, freshness tracking

---

## Exact startup commands

### Environment setup (first time or after clone)
```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev,extract,api]"
cd ui && npm install && cd ..
```

### Backend
```
uvicorn kairoskopion.api.app:app --reload --port 8000
```

### Frontend
```
cd ui && npm run dev
```
Opens at `http://localhost:5173` (proxies API to port 8000).

### Tests
```
pytest tests -q                          # full suite (3254 tests)
pytest tests/test_p10_harvest.py tests/test_p10_harvest_final.py -v   # P10 focused (58 tests)
```

### Typecheck and build
```
cd ui && npx tsc --noEmit               # typecheck
cd ui && npx vite build                  # production build
```

### CLI
```
kairoskopion --help                      # 39 commands
kairoskopion status                      # system status
kairoskopion run-fixture                 # run with synthetic fixture
```

---

## Required local configuration

Environment variables (names only — never commit values):

| Variable | Purpose |
|---|---|
| `KAIROSKOPION_API_KEY` | LLM provider API key |
| `KAIROSKOPION_BASE_URL` | LLM provider base URL (default: `https://api.302.ai/v1`) |
| `KAIROSKOPION_MODEL` | Default model (default: `gpt-4o-mini`) |
| `KAIROSKOPION_FALLBACK_MODELS` | Comma-separated fallback model list |
| `KAIROSKOPION_DATA_DIR` | Data directory (default: `.kairoskopion/`) |
| `KAIROSKOPION_LLM_TIMEOUT` | LLM call timeout seconds (default: 120) |
| `KAIROSKOPION_LLM_MAX_RETRIES` | LLM retry count (default: 3) |
| `VITE_API_URL` | Frontend API base URL (default: `http://localhost:8000`) |

---

## P10 working paths

| Purpose | Path |
|---|---|
| Target scope | `data/seed_registry/education_ai_russia/p10_target_scope.yaml` |
| Provisional records | `data/seed_registry/education_ai_russia/p10_harvest/provisional_venue_records.jsonl` |
| Candidate export | `data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl` |
| Verification decisions | `data/seed_registry/education_ai_russia/p10_harvest/verification_decisions_final.jsonl` |
| Review packets | `data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.{md,jsonl,tsv}` |
| Acquisition tasks | `data/seed_registry/education_ai_russia/p10_harvest/acquisition_tasks_final.json` |
| Domain classification | `data/seed_registry/education_ai_russia/p10_harvest/domain_classification.json` |
| Harvest summary | `data/seed_registry/education_ai_russia/p10_harvest/harvest_summary_final.json` |
| Harvest script | `scripts/run_p10_harvest_final.py` |
| Original harvest script | `scripts/run_p10_education_ai_harvest.py` |

---

## Current counts

| Metric | Value |
|---|---|
| Source needs | 6 (1 satisfied, 3 open, 1 blocked, 1 deferred) |
| Acquisition tasks | 6 (4 open, 2 blocked) |
| Provisional records | 87 |
| Accepted truth | 0 |
| Review packets | 3 (MD + JSONL + TSV) |
| Tier 1 (RU education) | 8 |
| Tier 2 (AI education) | 10 |
| Tier 3 (EdTech) | 17 |
| Tier 4 (Higher ed) | 9 |
| Noise | 6 |
| Unclassified | 37 |
| Total tests | 3254 |

---

## Known limitations

1. **87 P10 records remain provisional** — require operator review and corroboration from a second authority source before promotion
2. **Real multi-model fallback not configured** — infrastructure exists but no fallback models are set
3. **No production deployment** — staging/operator preview only
4. **LLM intake requires reachable provider** — 302.ai or compatible; deterministic fallback available but produces limited ArticleModel
5. **P10 source needs open**: SN-02 (Crossref ISSN verification), SN-03 (VAK corroboration), SN-05 (CyberLeninka RU venues)
6. **P10 source needs blocked**: SN-04 (Scopus/WoS paid), SN-06 (per-venue evidence packs deferred)
7. **37 unclassified venues** need manual domain assignment
8. **6 noise venues** should be rejected after review
9. **Workbench UI** shows deterministic fallback output when no LLM configured

---

## Safe next actions (prioritized)

1. **Operator review of provisional P10 records** — inspect review packets, reject noise, classify unclassified, prioritize Tier 1 for corroboration
2. **Promote only verified records** — run Crossref ISSN lookup (SN-02) for Tier 1 venues; promote to accepted only with corroboration from a second authority
3. **Configure and test a real fallback model** — set `KAIROSKOPION_FALLBACK_MODELS` in `.env`
4. **Continue venue/source harvest** — execute open acquisition tasks (SN-02, SN-03, SN-05)
5. **Production deployment** — only through the verified deployment contour in `docs/operations/KAIROSKOPION_PRODUCTION_DEPLOY_RUNBOOK.md`

---

## Recovery commands

```powershell
# Verify current state
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git status --short

# Restore dependencies
pip install -e ".[dev,extract,api]"
cd ui && npm install && cd ..

# Rerun full tests
pytest tests -q
cd ui && npx tsc --noEmit && npx vite build

# Locate reports
ls docs/operations/P10_*.md
ls docs/operations/FINAL_DOCX_DEPENDENCY_REPAIR_REPORT.md
ls docs/operations/CURRENT_WORKING_STATE_HANDOFF_2026_07_09.md

# Confirm no secrets tracked
git ls-files | Select-String -Pattern "\.env$|secret|credential|\.key$"
# Expected: no matches
```
