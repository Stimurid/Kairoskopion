# Round III-K2 — RiskOfficer Failure Diagnostics

**Date:** 2026-06-24
**Operator:** Claude Code (owner: Timur Shchukin)

---

## Failure Summary

| Field | Value |
|-------|-------|
| Organ | RiskOfficer (`try_llm_risk_officer`) |
| Provider | 302.ai proxy → `claude-sonnet-4-5-20250929` |
| `provider_status` | `called_ok` |
| `parse_status` | `repair_failed` |
| `content_length` | 11,851 chars |
| `content_hash_prefix` | `9836192f5963764b` |
| `risk_items` | 0 |
| `semantic_status` | `needs_llm` |
| `llm_grounded` | false |

## Root Cause Chain

1. `try_llm_call_with_outcome()` calls provider with `strict_schema=False`
   — no `response_format` JSON constraint sent to the 302.ai API.
2. Sonnet returns 11,851 chars of mixed content (prose + JSON or XML-wrapped JSON).
3. `json.loads()` fails on raw content.
4. `repair_and_parse()` attempts: fence stripping, smart quotes, trailing commas,
   balanced {…} extraction, island extraction — ALL fail.
5. Returns `repair_failed` → adapter falls back to `needs_llm` placeholder with 0 items.

## Proof This Is NOT Agentum Scope

| Evidence | Verdict |
|----------|---------|
| `provider_status = called_ok` | Provider works. API envelope is valid. |
| `content_length = 11851` | LLM returned substantial content — not a refusal. |
| FitAssessor/MismatchNarrator/RewritePlanner all succeed through the same provider | Model routing and availability are fine. |
| The 302.ai proxy returns well-formed API envelopes | No malformed provider envelope. |

**Conclusion:** The failure is in the Kairoskopion RiskOfficer prompt/parser/schema contract,
not in Agentum model routing or provider configuration.

## Delta: RiskOfficer vs Working Organs

| Dimension | RiskOfficer (broken) | RewritePlanner (works) | CitationPlanner (works) |
|-----------|---------------------|----------------------|----------------------|
| System prompt anti-prose | "No markdown, no code fences, no explanatory prose" | "No markdown, no code fences, no prose around the JSON" | "No markdown, no code fences" |
| `strict_schema` | `False` | `False` | `False` |
| `required` in OUTPUT_SCHEMA | `[]` (empty) | `[]` (empty) | `[]` (empty) |
| `additionalProperties` | `True` | `True` | `True` |
| User template closing | "Return a JSON object with categorized risk items." (generic) | "Return a JSON object with the ordered adaptation plan." (generic) | "Return a JSON object with citation ecology analysis." (generic) |
| Content volume from LLM | 11,851 chars (long risk analysis) | ~3,000-5,000 chars | ~2,000-4,000 chars |

**Key difference:** RiskOfficer produces the longest LLM output among all organs.
The repair module's balanced-extraction and island-extraction work on shorter
responses but fail on the 11K+ response, likely because the prose wrapping is
more extensive or contains nested JSON-like structures that confuse the parser.

## Fixes Applied (commit `c12476a`)

### 1. Prompt Hardening (`risk_reporting.py`)

- Replaced "Output shape (strict)" with "Output format (MANDATORY — read every word)"
- Added explicit WRONG/CORRECT output examples
- Added anti-pattern list: `<thinking>` tags, code fences, prose preambles
- Strengthened user template closing: "IMPORTANT: respond with ONLY the JSON object. No other text."

### 2. Parser Hardening (`json_repair.py`)

- Added XML tag regex: strips `<thinking>`, `<response>`, `<answer>`, `<output>`,
  `<result>`, `<analysis>`, `<json>` wrappers before extraction.
- XML-stripped content searched for islands in addition to original text.
- New repair step: `xml_tags_stripped`.

### 3. Schema/Adapter Hardening (`llm_semantic_organs.py`)

- Added `_PROMPT_TO_CANONICAL_RISK_TYPE` mapping: bridges prompt-family enum names
  (`desk_rejection`, `method_gap`, `field_core_destruction`, etc.) to canonical
  service types (`desk_reject_risk`, `methodology_mismatch`, `core_transformation_risk`).
- Extended `_RISK_SEVERITY_MAP` with tolerant values: `moderate`, `severe`, `warning`,
  `info`, `minor`, `major`, `blocking`.

### 4. Diagnostics Hardening (`llm_semantic_organs.py`)

- Replaced generic `repair_failed` with specific categories:
  - `no_content_returned` — LLM returned empty
  - `json_repair_exhausted` — all repair strategies failed
  - `no_json_found` — content present but no JSON detected
- Added structured warning log with content_length, hash, top_keys.

## Test Coverage

17 new tests in `tests/test_round3k2_risk_officer_contract.py`:
- Tests 1-4: JSON repair paths (pure, fenced, prose+JSON, `<thinking>`-wrapped)
- Test 5: `risk_type` normalization (prompt enum → canonical)
- Test 6: severity normalization (tolerant values)
- Tests 7-10: full adapter chain (empty items, unparseable, fenced, `<thinking>`)

Full suite: **2221 passed, 0 failed.**
