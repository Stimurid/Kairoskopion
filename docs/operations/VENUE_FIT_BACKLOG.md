# Venue / fit / risk / rewrite backlog

**Status:** prioritized roadmap — implementation not in this branch.
**Authored:** 2026-06-20 during `feature/real-cockpit-venue-fit-pass`.
**Audited services:** `citation_ecology.py`, `risk_reporting.py`,
`rewrite_planning.py`, `mismatch_mapping.py`,
`venue_candidate_screening.py`, `venue_profiling.py`.

## Branch-scope fixes (shipped in current commit)

These were tiny / high-leverage and were applied:

| # | File:line | Fix | Symptom eliminated |
|---|---|---|---|
| F1 | `services/venue_profiling.py:_detect_regime` | Return ``None`` instead of fake `CLASSIC_JOURNAL_ARTICLE` default; emit explicit unknown | Every venue paste stamped as classic journal regardless of input |
| F2 | `services/venue_profiling.py::build_venue_model` | `confidence="medium"` requires BOTH aims/scope ≥200 chars AND journal name | Fake medium confidence on 30-char scope fragments |
| F3 | `api/cases.py::investigate_venue` | Minimum-text guard (≥200 chars); returns `status=needs_more_venue_text` early | Pasting 50 chars produced a blank VenueModel with fake fields, no hint to operator |
| F4 | `services/venue_profiling.py::build_venue_model` | `venue_type` from regime where possible, not hardcoded JOURNAL | Conference/proceedings text shown as journal |
| F5 | `api/cases.py::investigate_venue` | Expose `venue_field_position` + `used_llm` in response | UI couldn't read FPM unknowns / "deterministic fallback ran" warning |
| D1 | `services/venue_profiling.py::_extract_*_policy` family | Negation guard (`_present_unnegated` / `_NEGATION_RE`) | "we do not provide open access" → open_access (inverted policy claim) |
| D2 | `services/mismatch_mapping.py::build_mismatch_map` | `venue_side=""` + explicit unknown instead of literal "Venue expectation on {axis}" placeholder | Placeholder string rendered as if real datum |
| D3 | `services/venue_candidate_screening.py::_assess_discipline_fit` | Token-equality with min length 4 instead of bidirectional substring | "art" ⊂ "cartography" false matches |
| D4 | `services/venue_candidate_screening.py::_assess_regime_fit` | Return `unknown` unless adapter explicitly says `type=journal`; `works_count>0` removed | Universal "regime: likely" on any indexed venue |
| D5 | `services/citation_ecology.py::_detect_bridge_references` | Require ≥2 discipline tokens AND ≥6-char tokens overlap | Bogus bridge author list from common words ("social") |

## Backlog — LLM-conversion items (deferred)

Highest leverage first. Each requires a new agent class with prompt
family + structured output schema. Implement under separate branch
(`feature/<role>-llm-agent`) with paired tests.

### 1. `MismatchNarrativeAgent` — fix axis-by-axis venue interpretation
- **Replaces:** `services/mismatch_mapping.py::build_mismatch_map`
  (currently emits empty `venue_side` + unknown per axis — D2 fix).
- **Input:** axis name, article evidence (claims, method, genre),
  venue evidence (scope, article types, regime).
- **Output schema:** `{axis, article_side, venue_side, description,
  possible_actions[], evidence_refs[]}`.
- **Why:** today the cockpit shows "venue-side description not
  available" for every mismatch — usable as warning but not actionable.
- **Risk to user:** medium — output goes into rewrite planner and
  risk report.

### 2. `RewritePlanAgent` — replace static action templates
- **Replaces:** `services/rewrite_planning.py::_CHANGE_TYPE_MAP` /
  `_CONDITIONAL_ACTIONS` boilerplate.
- **Input:** article text + mismatch map.
- **Output:** list of `{change_id, target_block, current_state (quote),
  desired_state, reason, evidence_refs[], field_core_risk,
  difficulty}`.
- **Why:** static templates produce identical generic advice for any
  article. Real rewrite planning needs article-grounded suggestions
  with quotes from current text.

### 3. `VenuePolicyExtractorAgent` — structured policy extraction
- **Replaces:** `services/venue_profiling.py::_extract_open_access`,
  `_extract_apc_policy`, `_extract_anonymization`,
  `_extract_ai_policy`, `_extract_data_policy`,
  `_extract_ethics_policy`, `_extract_indexing_claims`.
- **Input:** venue guidelines text.
- **Output:** `{open_access, apc, anonymization, ai_policy,
  data_policy, ethics_policy, indexing_claims[]}` each with `{value,
  confidence, evidence_quote}`.
- **Why:** D1 fix added negation guards but cannot handle "abstracts
  must address data sharing concerns" (no negation, also not a data
  policy claim). LLM disambiguates context.

### 4. `CitationBridgeAgent` — replace token-overlap bridge detection
- **Replaces:** `services/citation_ecology.py::_detect_bridge_references`
  and `_check_venue_expectations`.
- **Input:** parsed references + article discipline + venue scope/guidelines.
- **Output:** `{bridges: [{ref_id, rationale}],
  venue_expectations: {recency, data_refs, citation_style}}`.
- **Why:** D5 fix tightened but bridge detection is still
  word-overlap. A bridge between two disciplines is a semantic
  judgment, not a token-set intersection.

### 5. `DisciplineMatcherForVenuesAgent` — replace screening heuristics
- **Replaces:** `services/venue_candidate_screening.py::_assess_discipline_fit`
  and `_assess_article_type_fit`.
- **Input:** candidate venue topics + article disciplinary registers +
  venue's article_types_supported.
- **Output:** `{discipline_fit: {value, rationale},
  article_type_fit: {value, rationale}}`.
- **Why:** D3 fix removed substring false positives but discipline
  match is still token equality. Real match requires understanding
  that "philosophy of education" venue accepts a "philosophy of
  technology" paper if the technology angle bears on educational
  practice — that's interpretation, not tokens.

## Backlog — smaller tweaks (still need testing)

| # | File | Tweak | Effort |
|---|---|---|---|
| BL1 | `services/risk_reporting.py:179` | Replace fragile "AI disclosure policy" substring with stable enum key | 5 LOC |
| BL2 | `services/risk_reporting.py` per-axis output | Add `confidence:"template"` field so UI can badge as scaffolding | 10 LOC |
| BL3 | `services/rewrite_planning.py` `_CONDITIONAL_ACTIONS` | Add `confidence:"template"` field per change | 5 LOC |
| BL4 | `services/venue_profiling.py:_extract_article_types` | Add Russian keyword set ("статья", "обзор", "рецензия", "сообщение") to `_ARTICLE_TYPE_KEYWORDS` | 5 LOC |
| BL5 | `services/citation_ecology.py:_check_venue_expectations` | Add negation guard to "recent" / "data availability" mention checks (currently false-positive on "no data sharing required") | 10 LOC |

## Cockpit-side follow-ups (UI work)

| # | Item | Reason |
|---|---|---|
| UI1 | Render `needs_more_venue_text` hint as a clear "вставьте больше текста / приложите URL" prompt in CaseWorkspace's venue intake response handler | F3 surfaces a new status, but UI today only knows article_model_built / venue_investigated |
| UI2 | Surface `venue_field_position.unknowns` as a "needs LLM venue positioner" banner | F5 exposes FPM in response but UI doesn't read it yet |
| UI3 | Render `used_llm: false` as a "deterministic fallback ran" badge on venue view | Same as UI2 — backend now exposes flag |
| UI4 | Render `mismatches[].venue_side === ""` as "(требуется LLM-комментарий)" instead of blank | D2 fix surfaces blank where the placeholder used to be |

## Why this list and not larger scope

Every LLM-conversion item above (1–5) requires:
1. A new `prompts/<name>.py` family + schema + validator.
2. A new `agents/<name>.py` with execute + execute_deterministic.
3. Wiring in `api/cases.py` with role_id (using the per-call routing
   seam shipped in `030fda4`).
4. New tests covering the LLM path + deterministic fallback +
   anti-leak.

Each is a 1-2 day branch. They are NOT in this pass because the goal
of `feature/real-cockpit-venue-fit-pass` was to stop the immediate
silent-misroute / fake-confidence bleed, then prioritize next moves.
This document is the roadmap.

## Source-of-truth files

- `docs/operations/PER_CALL_MODEL_ROUTING_SPEC.md` — routing seam used
  by future agents.
- `docs/operations/ARTICLE_MODEL_SCHEMA_INVARIANTS.md` — schema
  loosening criteria for new agents.
- `prompts/__init__.py` — register every new family.
- `agents/registry.py` — register every new agent role + add to
  `_build_agent_class_map`.
