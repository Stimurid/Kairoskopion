# Round III-M Track 2: Anti-Deterministic-Semantics Audit

**Date:** 2026-06-25
**Auditor:** Claude (automated Round III-M audit)
**Scope:** All downstream pipeline components after FitAssessment

---

## Doctrine

Deterministic code is allowed ONLY for technical/mechanical extraction:
- Headings, DOI regex, JSON parsing, persistence, severity normalization
- Input validation, field mapping, schema enforcement

ALL semantic judgments MUST be LLM-backed:
- Article meaning, fit interpretation, risk assessment
- Rewrite strategy, citation ecology, editorial advice

Classification values:
- `OK_TECHNICAL_DETERMINISM_ONLY` — pure mechanical extraction
- `OK_LLM_SEMANTIC` — semantic judgments via LLM
- `SUSPECT_DETERMINISTIC_SEMANTIC` — borderline; deterministic code makes semantic-ish claims
- `LLM_ORGAN_MISSING` — semantic judgment needed but no LLM organ exists
- `FALLBACK_TOO_SEMANTIC` — deterministic fallback produces full semantic output

---

## Component Audit

### 1. BibliographyProfile builder (`bibliography_profile.py`)

**Classification: `OK_TECHNICAL_DETERMINISM_ONLY`**

- Heading detection: regex scan for known heading patterns — mechanical
- Reference splitting: numbered/bulleted/newline patterns — mechanical
- DOI/URL/year extraction: regex — mechanical
- No semantic claims about reference quality, relevance, or completeness
- Status values (`parsed_structural`, `not_found`, etc.) describe technical outcomes

**Bugs found (Track 3):**
- Heading regex didn't handle `**bold**` markers — FIXED
- Next-heading regex matched across newlines, truncating block — FIXED

### 2. MismatchMap builder (`mismatch_mapping.py`)

**Classification: `SUSPECT_DETERMINISTIC_SEMANTIC` (low severity)**

- `build_mismatch_map()` — builds structure from FitAssessment axes, mechanical
- `_suggest_actions()` (line 94) — returns canned editorial advice per axis:
  e.g. "Reframe introduction to emphasize venue-relevant aspects"
  These are semantic-ish suggestions, but they serve as structural scaffolding
  for the LLM RewritePlanner that follows. They are NOT the final user-facing
  editorial advice.

**Verdict:** Acceptable because:
1. The suggestions are axis-category labels, not article-specific advice
2. The RewritePlanner LLM organ produces the actual editorial plan
3. Removing them would leave the mismatch map without even placeholder actions

### 3. MismatchNarrator (`agents/mismatch_narrator.py`)

**Classification: `OK_LLM_SEMANTIC`**

- Produces per-axis narrative descriptions via LLM
- On LLM failure: leaves `narrative_status=needs_llm` — no fabrication
- Rescue mechanism: retries failed axes individually (cap=3)
- No deterministic semantic fallback

### 4. RiskOfficer (`services/llm_semantic_organs.py::try_llm_risk_officer`)

**Classification: `OK_LLM_SEMANTIC`**

- Production chain uses `try_llm_risk_officer()`, NOT the agent class
- On LLM failure: returns `build_needs_llm_risk_report()` — placeholder with
  `semantic_status=needs_llm`, 0 risk items, no fabricated risks
- Severity normalization (`_RISK_SEVERITY_MAP`) is mechanical mapping
- Risk type normalization (`_normalize_risk_type`) is mechanical string cleanup
- The legacy `build_risk_report()` in `services/risk_reporting.py` produces
  deterministic semantic risks but is **NEVER called** from the production chain

**Bugs found (Track 6):**
- JSON repair chain didn't strip `//` and `/* */` comments — FIXED
  (may have contributed to `json_repair_exhausted` on live case)

### 5. RewritePlanner (`services/llm_semantic_organs.py::try_llm_rewrite_planner`)

**Classification: `OK_LLM_SEMANTIC`**

- Production chain uses `try_llm_rewrite_planner()`, NOT the agent class
- On LLM failure: returns `build_needs_llm_rewrite_plan()` — placeholder with
  `semantic_status=needs_llm`, 0 changes
- Field core impact normalization is mechanical enum mapping
- When LLM returns 0 actions: adds explicit unknown explaining why
- The legacy `build_rewrite_plan()` produces deterministic semantic rewrite
  actions but is **NEVER called** from the production chain

### 6. CitationPlanner (`services/llm_semantic_organs.py::upgrade_citation_plan_with_llm`)

**Classification: `OK_LLM_SEMANTIC`**

- Augments structural CitationPlan with LLM semantic fields
- On LLM failure: returns original plan unchanged (structural-only)
- Anti-fake filter strips DOI and author-year patterns from LLM output — mechanical
- Padding warning is editorial but triggered mechanically by presence of bridges/gaps
- When LLM returns nothing usable: adds explicit unknown

### 7. FitAssessor (`agents/fit_assessor.py`)

**Classification: `FALLBACK_TOO_SEMANTIC` (upstream, not in Track scope)**

- LLM path works (produced 12-axis verdict on live case)
- Deterministic fallback `assess_fit()` produces full semantic judgments
  (axis values: strong/medium/weak/unknown) via rule-based heuristics
- This is upstream of the downstream actions being audited
- Out of Track scope per spec, but documented for completeness

### 8. HumanDossier builder (`services/human_dossier.py`)

**Classification: `OK_TECHNICAL_DETERMINISM_ONLY`**

- Assembles sections from upstream results — mechanical structure
- Translates enum values to Russian prose — mechanical mapping
- No semantic interpretation of article content
- All semantic content comes from upstream LLM organs

---

## Summary Table

| Component | Classification | Severity | Action |
|-----------|---------------|----------|--------|
| BibliographyProfile | OK_TECHNICAL_DETERMINISM_ONLY | — | Regex bugs FIXED |
| MismatchMap._suggest_actions | SUSPECT_DETERMINISTIC_SEMANTIC | Low | Acceptable (scaffolding) |
| MismatchNarrator | OK_LLM_SEMANTIC | — | None needed |
| RiskOfficer (prod) | OK_LLM_SEMANTIC | — | JSON repair improved |
| RewritePlanner (prod) | OK_LLM_SEMANTIC | — | None needed |
| CitationPlanner (prod) | OK_LLM_SEMANTIC | — | None needed |
| FitAssessor | FALLBACK_TOO_SEMANTIC | Medium | Out of scope |
| HumanDossier | OK_TECHNICAL_DETERMINISM_ONLY | — | None needed |

**Overall verdict: `ANTI_DETERMINISTIC_AUDIT_CLEAN_FOR_DOWNSTREAM_ACTIONS`**

All downstream action components (Risk, Rewrite, Citation) correctly use LLM-backed
semantic organs with honest `needs_llm` placeholders on failure. No deterministic
semantic heuristics substitute for LLM judgment in the production chain.
