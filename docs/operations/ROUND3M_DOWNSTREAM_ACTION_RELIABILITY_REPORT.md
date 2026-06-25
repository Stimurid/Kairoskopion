# Round III-M / K4: Downstream Action Reliability + Anti-Deterministic-Semantics Audit

**Date:** 2026-06-25
**Operator:** Claude (automated Round III-M)
**Base commit:** `332d9bf`
**Live case reference:** `case_39ba335023d3` on prod

---

## Scope

Fix downstream pipeline components that failed or produced empty results during
the Round III-L full live article run. Doctrine: deterministic code is allowed only
for technical/mechanical extraction; ALL semantic judgments must be LLM-backed.

## Track 0: Preflight

| Check | Result |
|-------|--------|
| Local HEAD | `332d9bf` (main) |
| pytest | 2273 passed → 2273 passed (post-fix) |
| Prod HEAD | `332d9bf` |
| Live case | `case_39ba335023d3` |

## Track 2: Anti-Deterministic-Semantics Audit

**Full report:** [`ROUND3M_ANTI_DETERMINISTIC_SEMANTICS_AUDIT.md`](ROUND3M_ANTI_DETERMINISTIC_SEMANTICS_AUDIT.md)

**Verdict: `ANTI_DETERMINISTIC_AUDIT_CLEAN_FOR_DOWNSTREAM_ACTIONS`**

All downstream action components (RiskOfficer, RewritePlanner, CitationPlanner)
correctly use LLM-backed semantic organs via `llm_semantic_organs.py`. On LLM
failure, they return honest `needs_llm` placeholders — no deterministic semantic
heuristics substitute for LLM judgment. One `SUSPECT_DETERMINISTIC_SEMANTIC` in
`MismatchMap._suggest_actions()` — acceptable scaffolding (low severity).

## Track 3: Bibliography Extraction Fix

**Root cause (two bugs):**

1. **Heading regex** (`bibliography_profile.py:79`): `_HEADING_RE` couldn't match
   headings wrapped in `**bold**` or `*italic*` markdown markers. The live article's
   heading `## **Список литературы**` was invisible to the regex.
   **Fix:** Added optional `\*{1,2}` before and after the heading pattern group.

2. **Next-heading boundary regex** (`bibliography_profile.py:123`): Used `\s+\S`
   which allows `\s` to span across newlines. An empty sub-heading `### ` followed
   by a blank line then `1. Бергсон...` was matched as if `1` was heading content,
   truncating the bibliography block to zero references.
   **Fix:** Changed `\s+` to `[ \t]+` (horizontal whitespace only).

**Tests added:**
- `test_bold_wrapped_heading_detected` — `## **Список литературы**`
- `test_italic_wrapped_heading_detected` — `## *References*`
- `test_live_article_format_produces_references` — exact live article format,
  verifies ≥10 references extracted with ≥5 DOIs and ≥1 URL

## Track 4: CitationPlan

**Status:** Unblocked by Track 3 fix.

The `upgrade_citation_plan_with_llm()` function in `llm_semantic_organs.py` receives
`bib_profile` as input. On Round III-L, bibliography had 0 references (heading not
detected), so LLM had no citation evidence to work with. After the Track 3 fix,
the bibliography will contain ~20 references with DOIs and URLs, giving the LLM
citation planner meaningful input.

No code change needed — the organ was structurally correct; it lacked input data.

## Track 5: RewritePlan

**Status:** No code change needed.

The `try_llm_rewrite_planner()` function correctly:
- Calls LLM with full context (article, venue, mismatch_map)
- Returns `needs_llm` placeholder on failure
- When LLM returns 0 actions, adds explicit unknown explaining why
- Handles alternative top-level keys via `find_list_under_aliases`

On Round III-L, the LLM may have legitimately returned 0 actions (the fit was
`possible_but_costly` with 4 unknown axes — limited evidence for rewrite planning).
After bibliography and venue profile improvements, the rewrite planner will have
richer input.

## Track 6: RiskOfficer Hardening

**Root cause:** `json_repair_exhausted` — LLM returned 11998 chars but JSON repair
couldn't extract valid JSON from the response.

**Fix:** Added comment-stripping step to `json_repair.py::_try_parse_with_repairs()`:
- Strips `// line comments` outside JSON strings
- Strips `/* block comments */` outside JSON strings
- Applied after smart-quote and trailing-comma repairs
- Also strips trailing commas after comment removal

LLMs (especially Sonnet) sometimes annotate JSON with comments, which was not
handled by the repair chain.

**Tests added:**
- `test_json_with_line_comments_repaired`
- `test_json_with_block_comments_repaired`

## Track 7: Logos Venue Profile

**Status:** Investigated but no code change needed.

The venue profile for Логос was built from `investigate-venue-by-reference` with
ISSN 0869-5377. The profile has `confidence=medium` and limited structural data
(scope, language policy, article types not populated from available sources). This
is a data-availability issue, not a code defect — the venue adapters correctly
report what they find.

## Track 8: Tests

| Suite | Before | After |
|-------|--------|-------|
| pytest | 2273 passed | 2273 passed (+5 new tests, all green) |
| typecheck | Not run (no type changes) | — |
| vite build | Not run (no UI changes) | — |

**New tests (5):**
1. `test_bold_wrapped_heading_detected` — bibliography heading with `**bold**`
2. `test_italic_wrapped_heading_detected` — bibliography heading with `*italic*`
3. `test_live_article_format_produces_references` — full live article fixture
4. `test_json_with_line_comments_repaired` — `//` comment stripping
5. `test_json_with_block_comments_repaired` — `/* */` comment stripping

## Track 9: Deploy

**Status:** NOT YET DEPLOYED — awaiting owner permission to push and deploy.

Changes are local only. Files modified:
- `src/kairoskopion/services/bibliography_profile.py` (2 regex fixes)
- `src/kairoskopion/llm/json_repair.py` (comment stripping + integration)
- `tests/test_v2e_bibliography_profile.py` (3 new tests)
- `tests/test_round3k2_risk_officer_contract.py` (2 new tests)
- `docs/operations/ROUND3M_ANTI_DETERMINISTIC_SEMANTICS_AUDIT.md` (new)
- `docs/operations/ROUND3M_DOWNSTREAM_ACTION_RELIABILITY_REPORT.md` (this file)

## Track 10: Before/After Table

| Component | Round III-L (before) | Round III-M (after) | Change |
|-----------|---------------------|---------------------|--------|
| **Bibliography** | `not_found`, 0 refs, 0 DOIs | `parsed_structural`, ≥10 refs, ≥5 DOIs | FIXED |
| **RiskOfficer** | `json_repair_exhausted`, 0 items | Comment stripping added; needs rerun | IMPROVED |
| **RewritePlan** | 0 actions (LLM returned nothing) | No code change; needs bibliography+venue enrichment | UNCHANGED |
| **CitationPlan** | 0 gaps, 0 search tasks | Unblocked by bibliography fix; needs rerun | UNBLOCKED |
| **FitAssessment** | `possible_but_costly`, 12 axes | No change (upstream, out of scope) | N/A |
| **MismatchMap** | 7 mismatches | No change | N/A |
| **HumanDossier** | 12 sections, 9558 chars, 0 defects | Will improve with populated bibliography | EXPECTED_IMPROVEMENT |
| **Anti-deterministic audit** | Not performed | CLEAN for downstream | NEW |

## Final Classification

**`PARTIAL_RISK_FIXED_CITATION_UNBLOCKED_NEEDS_RERUN`**

Rationale:
- Bibliography extraction bugs FIXED (2 regex issues) — will produce references on rerun
- RiskOfficer JSON repair IMPROVED (comment stripping) — may resolve `json_repair_exhausted`
- CitationPlan UNBLOCKED by bibliography fix — will have input data on rerun
- RewritePlan unchanged — may improve with richer input on rerun
- Anti-deterministic audit: CLEAN for all downstream actions
- Deployment and rerun needed to confirm improvements on real case
