# Round III-K Track 7: Live User-Run Protocol

## Purpose

Step-by-step protocol for running the Mavrinsky baseline scenario against the Top 5 Russian philosophy journals using the Kairoskopion staging environment. This protocol is designed for the operator (user) to execute independently.

## Prerequisites

- [ ] Python 3.11+ with Kairoskopion installed (`pip install -e .`)
- [ ] Node.js 18+ for UI cockpit
- [ ] Evidence packs present in `data/venue_evidence_packs/` (5 files)
- [ ] Mavrinsky article at `private_inputs/mavrinsky_article.txt`
- [ ] (Optional) OpenAI-compatible API key in environment for LLM mode

## Step 1: Start Backend

```bash
cd Kairoskopion
uvicorn kairoskopion.api.app:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` should return `{"status": "ok"}`.

## Step 2: Start Frontend (Optional)

```bash
cd ui
npm install   # first time only
npm run dev   # starts on port 5173
```

Open `http://localhost:5173` in browser.

## Step 3: Create User Session

Via UI: Enter display name on login screen.
Via API:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Operator", "email": "operator@test.local"}'
```

Save the returned `token` for subsequent requests.

## Step 4: Create Case

Via UI: Click "New Case" button.
Via API:
```bash
curl -X POST http://localhost:8000/cases \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Mavrinsky Baseline Run"}'
```

Save the returned `case_id`.

## Step 5: Intake Article

Via UI: Use article intake panel, paste or upload `private_inputs/mavrinsky_article.txt`.
Via API:
```bash
curl -X POST http://localhost:8000/cases/CASE_ID/intake \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "ARTICLE_TEXT_HERE", "input_type": "manuscript"}'
```

This triggers automatic ArticleModel construction. Check case status to confirm `article_model` stage reached.

## Step 6: Investigate Venues (Top 5)

For each journal, call the venue-by-reference endpoint:

```bash
# 1. Логос
curl -X POST http://localhost:8000/cases/CASE_ID/investigate-venue-by-reference \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issn": "0869-5377"}'

# 2. Вопросы философии
curl -X POST http://localhost:8000/cases/CASE_ID/investigate-venue-by-reference \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issn": "0042-8744"}'

# 3. Эпистемология и философия науки
curl -X POST http://localhost:8000/cases/CASE_ID/investigate-venue-by-reference \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issn": "1811-833X"}'

# 4. Философский журнал
curl -X POST http://localhost:8000/cases/CASE_ID/investigate-venue-by-reference \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issn": "2072-0726"}'

# 5. Цифровой ученый
curl -X POST http://localhost:8000/cases/CASE_ID/investigate-venue-by-reference \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issn": "2618-9267"}'
```

**Note:** The current case model investigates one venue at a time. Each call overwrites the previous venue investigation. To compare all 5, either:
- Run 5 separate cases (one per journal), or
- Run sequentially and save each response before the next call

## Step 7: Review Outputs

After venue investigation, the case contains:
- **Article model** (step 1–3 outputs)
- **Venue model** (from evidence pack)
- **Fit assessment** (12-axis vector)
- **Mismatch map** (per-axis gap analysis)
- **Risk report** (normalized risk types)
- **Adaptation plan** (rewrite candidates)

Via UI: Navigate to case detail view, review each tab.
Via API:
```bash
curl http://localhost:8000/cases/CASE_ID \
  -H "Authorization: Bearer TOKEN"
```

## Step 8: Score and Evaluate

Check which of the 10 quality checks pass:

| Check | What it validates |
|-------|-------------------|
| 1 native_extraction | Title, abstract, language, references extracted |
| 2 academic_move | Argument move type identified |
| 3 field_coordinates | Disciplinary/subdisciplinary vectors populated |
| 4 tribe_recognition | Key thinkers recognized without false positives |
| 5 citation_ecology | Must-cite, absent, pathway-keyed citations |
| 6 venue_logic | Venue pathways and candidates generated |
| 7 core_risk | Protected core concepts identified |
| 8 evidence_discipline | Source evidence with provenance |
| 9 fit_vector | 12-axis fit assessment produced |
| 10 adaptation | Rewrite plan with per-axis recommendations |

**Expected baseline (deterministic):** 3–5 PASS, 1–2 PARTIAL, 3–6 FAIL.
**Expected with LLM:** 7–9 PASS, 1–2 PARTIAL, 0–1 FAIL.

## Step 9: Compare Across Journals

For a meaningful comparison, record per-journal:
- Overall fit verdict (PASS/PARTIAL/FAIL)
- Per-axis fit values (12 axes)
- Risk count and types
- Adaptation plan length and rewrite depth
- Submission readiness (gate pass/fail)

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `evidence_pack_not_found` | ISSN typo or evidence pack file missing | Check `data/venue_evidence_packs/` for the file |
| Empty venue model | Evidence pack text too short or malformed | Check markdown format of evidence pack |
| All fit axes UNKNOWN | No venue investigation performed | Run step 6 first |
| `401 Unauthorized` | Token missing or expired | Re-register (step 3) |
| Port 8000 in use | Another uvicorn instance running | Kill existing process or use different port |

## LLM Mode (Optional)

To enable LLM-backed agents for richer extraction:

```bash
export OPENAI_API_KEY=your-key-here
export KAIROSKOPION_LLM_MODEL=gpt-4o-mini  # or any compatible model
uvicorn kairoskopion.api.app:app --reload --port 8000
```

LLM mode improves: title/abstract extraction, academic move detection, tribe recognition, protected core identification, and fit assessment granularity.

---

*Protocol created: 2026-06-24. Track 7 COMPLETE.*
