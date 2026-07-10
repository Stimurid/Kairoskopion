# Current Working State

**Last updated:** 2026-07-10
**Branch:** `fix/discipline-output-truncation` (ready to merge to main)

---

## What was done this session

### BLOCKER E — Discipline matcher output truncation

**Root cause:** V3 prompt (10 candidates, 7-10 sentence Russian rationales)
consistently exceeds 4096 output tokens. Production LLM session log shows
`output_tokens=4096` (hard ceiling) with `parse_status=text_only`. The JSON
response is truncated mid-object. `repair_and_parse` cannot fix it. Agent
falls back to keyword-only deterministic results (2-4 candidates, no LLM
scoring).

**Fix:**
- `discipline_matcher.py`: `max_tokens` raised from 4096 to 8192
- Added explicit `finish_reason == "length"` truncation detection
- Truncation classified as `output_truncated` (distinct from `invalid_json`)
- Attempt metadata (model, tokens, finish_reason) persisted on fallback
- 16 regression tests in `tests/test_discipline_truncation.py`

**Evidence from production session log:**
```
agent_role: discipline_matcher
output_tokens: 4096
parse_status: text_only
finish_reason: (implicit length — output = max_tokens)
```

### Prior session: BLOCKERs A-D (already deployed as commit 1fc7c0a)

- A: Discipline LLM wiring (registry-first shortcircuit removed)
- B: Genre/method rerun endpoint + UI
- C: Finalization endpoint
- D: Agent map integrity tests

## What is NOT done

1. **Production deployment of BLOCKER E fix** — needs merge to main and deploy.
   SSH is disabled (see `ENVIRONMENT_INVARIANTS.md`). Non-SSH deployment
   contour needed.

2. **Production acceptance** — the 12-step acceptance protocol from the user
   has not been completed. Steps 3-12 remain after deployment.

3. **Genre/method resolution** — `genre=unknown` and `method=unknown` on the
   production test case. The genre/method rerun endpoint exists but has not
   been tested on production after the discipline fix.

4. **Finalization persistence** — not yet tested on production.

## Gate results (feature branch)

| Gate | Result |
|------|--------|
| pytest | 3299 passed, 8 deselected |
| TypeScript | clean (noEmit) |
| Vite build | clean |

## Next steps

1. Merge `fix/discipline-output-truncation` → main
2. Push origin/main
3. Deploy to production (non-SSH contour)
4. Create fresh disposable production case
5. Verify discipline LLM works with 10 candidates
6. Test genre/method rerun
7. Test finalization persistence
8. Write acceptance report
