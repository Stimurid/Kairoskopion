# Round III-P4: Prompt Quality Self-Audit

**Date:** 2026-06-26
**Reviewer:** Claude (automated self-audit — owner should verify)

## Quality Classification

| # | Organ | Prompt Quality | Living Organ? | Algorithm Disguised as Prompt? | Main Weakness | Verdict |
|---|-------|---------------|:-------------:|:-----------------------------:|---------------|---------|
| 1 | DisciplineIntentParser | `ADEQUATE_CONTRACT_PROMPT` | Partial | No | Parsing-oriented — parses operator text, not article evidence. No article-awareness. No venue-awareness. No protected-core policy (not applicable at this stage). Acceptable for a parser role. | PASS with caveat |
| 2 | VenueFunnelPlanner | `ADEQUATE_CONTRACT_PROMPT` | Partial | No | Relies on LLM training data for representative_venues — no grounding in corpus evidence pack. Anti-fabrication rule present but weak ("use well-known venues you are confident about"). No provenance chain. | PASS with caveat |
| 3 | VenueFamilyContextBuilder | `ADEQUATE_CONTRACT_PROMPT` | Partial | No | Same training-data dependency as #2. "Ground in scope_summary" rule present. No corpus evidence integration — siblings come from LLM memory. | PASS with caveat |
| 4 | VenueMatrixAssessor | `THIN_JSON_EXTRACTOR` | No | No | Only 3 semantic axes (topic_fit, discipline_fit, core_risk). Prompt says "lightweight assessment" — technically correct but thin. No article-awareness beyond "article context". No citation ecology, no genre, no method. Schema has axes but prompt guidance is minimal. | WEAK — needs enrichment |
| 5 | DepthRecommendationAgent | `ADEQUATE_CONTRACT_PROMPT` | Partial | No | Reasonable depth-mode taxonomy. But: no awareness of specific article properties (cross-disciplinary flag, core claims count). "If data insufficient, return current mode" is safe fallback. No protected-core awareness. | PASS |
| 6 | FitAssessmentOrgan | `LIVING_AGENTIC_ORGAN` | Yes | No | Strong 16-axis framework. Clear anti-rules (no single score, no acceptance probability). Evidence-aware. Unknown-preserving. Scenario-aware. Protected-core axis present. Best prompt in the set. | PASS |
| 7 | MismatchNarrativeOrgan | `LIVING_AGENTIC_ORGAN` | Yes | No | Article-grounded actions ("anchored to claims, sections, method, bibliography"). Anti-fabrication for citations. Anti-softening rule. Surgical action requirement. Venue-evidence awareness. Language-aware (Russian/English). | PASS |
| 8 | RewritePlanOrgan | `ADEQUATE_CONTRACT_PROMPT` | Partial | No | Surgical action requirement present. field_core_risk tracking. "Conditional" status for unknown venue expectations — good uncertainty handling. But: no explicit anti-boilerplate rule. Could produce generic restructure advice for any article. | PASS with caveat |
| 9 | CitationEcologyOrgan | `LIVING_AGENTIC_ORGAN` | Yes | No | Strong anti-fabrication ("NO fabricated specific citation references"). Tradition-level suggestions, not fake papers. Gap taxonomy (canon, recency, diversity, bridge, methodological). Validator catches fake years. Bridge references require rationale. | PASS |
| 10 | MavrinskySemantic | `REUSED_EXISTING_PROMPT_OK` | Yes | No | Extends #6 with 4 additional axes (argument_form_fit, rewrite_effort, citation_effort, evidence_confidence). Evidence_source per axis requirement. Corpus-aware via corpus_titles input. Same strong anti-rules as #6. | PASS |
| 11 | VenueRegimeDetector | `REUSED_EXISTING_PROMPT_OK` | Yes | No | "Do NOT default to classic_journal_article when unsure. Use null." — strong anti-assumption rule. Regime enum is well-defined. Embedded in the larger venue fact extraction prompt. | PASS |
| 12 | VenuePolicyExtractor | `REUSED_EXISTING_PROMPT_OK` | Yes | No | "Do NOT infer policies from venue type alone." — strong anti-inference rule. "Negation matters" — captures nuance. Per-policy-field extraction from TEXT. Good provenance discipline. | PASS |
| 13 | ComplianceSemanticOrgan | `LIVING_AGENTIC_ORGAN` | Yes | No | "NEVER upgrade absent to satisfied." Structural/semantic separation clear. severity escalation (blocking/warning/informational). "If venue requirement unknown, use unknown_not_verified — do NOT assume not_required." Validator catches impossible states. | PASS |

## Summary Counts

| Quality Level | Count | Organs |
|--------------|-------|--------|
| `LIVING_AGENTIC_ORGAN` | 4 | #6, #7, #9, #13 |
| `REUSED_EXISTING_PROMPT_OK` | 3 | #10, #11, #12 |
| `ADEQUATE_CONTRACT_PROMPT` | 5 | #1, #2, #3, #5, #8 |
| `THIN_JSON_EXTRACTOR` | 1 | #4 |
| `CHECKLIST_DISGUISED_AS_ORGAN` | 0 | — |
| `ALGORITHM_DISGUISED_AS_PROMPT` | 0 | — |
| `PROMPT_MISSING` | 0 | — |

## Honest Assessment

### Strong organs (4)
- **#6 FitAssessmentOrgan** — best prompt: 16 axes, evidence-aware, scenario-aware, protected-core, anti-rules
- **#7 MismatchNarrativeOrgan** — article-grounded, surgical, anti-fabrication, language-aware
- **#9 CitationEcologyOrgan** — tradition-level suggestions, anti-fabrication validator, gap taxonomy
- **#13 ComplianceSemanticOrgan** — structural/semantic split, impossible-state validator, severity escalation

### Adequate organs (5 + 3 reused)
- **#1, #2, #3, #5, #8** — functional contracts with proper schema, validation, and failure policy. Not deeply article-aware but serve their pipeline role.
- **#10, #11, #12** — extensions of strong existing prompts.

### Weak organ (1)
- **#4 VenueMatrixAssessor** — only 3 semantic axes, minimal prompt guidance, "lightweight" by design but thin for a "semantic organ" claim. It works as a triage filter but should not be presented as deep semantic assessment.

### Blockers
None. All 13 have real prompt text, schema, validation, and failure policy. The weak organ (#4) is functionally correct — it's thin, not broken.

### Suspicious patterns found: NONE
- No prompt is "just fill schema"
- No hardcoded journal families or disciplinary mappings in prompts
- No keyword lists as decision logic in prompts
- All prompts have unknown handling
- No generic advice machines (closest: #8 could trend that way but has surgical action requirement)

### Owner attention items
1. **#4 VenueMatrixAssessor** is thin — 3 axes vs 16 in FitAssessor. Consider whether this is intentional (triage-level) or needs enrichment.
2. **#2 VenueFunnelPlanner** relies on LLM training data for venue names — no grounding in local corpus. Acceptable for suggestions but operator must verify.
3. **#3 VenueFamilyContextBuilder** has same training-data dependency for sibling venues.
