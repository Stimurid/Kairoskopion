# Round III-K Track 5: RiskOfficer Enum Normalization Repair

## Objective

Fix the RiskOfficer's `_assess_single_risk()` method to handle non-canonical risk type strings returned by LLM responses — title-case, hyphens, `_risk` suffix, whitespace — preventing silent data loss when LLM output doesn't match exact enum values.

## Problem

The RiskOfficer in `llm_semantic_organs.py` compared raw LLM output directly against 18 canonical risk type strings. LLM responses like `"Scope_Drift"`, `"scope-drift"`, `"scope_drift_risk"`, or `" scope_drift "` would fail to match, defaulting to `"unknown"` and losing the actual risk assessment.

## Fix

**File:** `src/kairoskopion/services/llm_semantic_organs.py`

Added `_normalize_risk_type(raw: str) -> str` function:
1. Strip whitespace
2. Lowercase
3. Replace hyphens with underscores
4. Remove `_risk` suffix if present
5. Return canonical form if it matches, else `"unknown"`

The canonical set is built as `frozenset` for O(1) lookup:
```python
_CANONICAL_RISK_TYPE_SET = frozenset(_CANONICAL_RISK_TYPES)
```

Changed line ~183 from:
```python
rtype = (raw.get("risk_type") or "").strip() or "unknown"
```
to:
```python
rtype = _normalize_risk_type(raw.get("risk_type") or "")
```

## Canonical Risk Types (18)

scope_drift, methodological_weakness, citation_gap, novelty_conflict, audience_mismatch, formal_noncompliance, language_register_clash, genre_mismatch, argument_structure_weakness, disciplinary_boundary_risk, publication_regime_conflict, author_eligibility_concern, ethical_compliance_risk, data_availability_risk, reproducibility_concern, prior_art_overlap, length_constraint_risk, timeline_risk

## Test Coverage

**File:** `tests/test_round3k_risk_officer_enum_normalization.py` — 16 tests

| Test | Input | Expected |
|------|-------|----------|
| exact match | `"scope_drift"` | `"scope_drift"` |
| title case | `"Scope_Drift"` | `"scope_drift"` |
| upper case | `"SCOPE_DRIFT"` | `"scope_drift"` |
| hyphenated | `"scope-drift"` | `"scope_drift"` |
| with _risk suffix | `"scope_drift_risk"` | `"scope_drift"` |
| title + hyphen | `"Scope-Drift"` | `"scope_drift"` |
| whitespace | `" scope_drift "` | `"scope_drift"` |
| unknown input | `"nonexistent_type"` | `"unknown"` |
| empty string | `""` | `"unknown"` |
| all 18 canonical types | each canonical value | itself |

All 16 tests pass.

## Impact

Without this fix, any LLM-backed risk assessment that returned non-exact-match risk type strings would silently produce `"unknown"` risks, making the RiskReport useless for real submissions. The normalizer ensures robust parsing regardless of LLM output formatting.

---

*Report generated: 2026-06-24. Track 5 COMPLETE.*
