# Round III-N Track 1: CitationPlan Diagnostics

**Date:** 2026-06-25
**Case:** `case_c79309110148`
**Article:** "Различимость живого в ИИ-опосредованных практиках"
**Venue:** Логос / Logos (ISSN 0869-5377)

---

## Bibliography Profile (from Round III-M rerun)

| Field | Value |
|-------|-------|
| status | `parsed_structural` |
| reference_count | 18 |
| doi_count | 7 |
| url_count | 1 |
| section_detected | true |
| verification_status | `identifiers_detected` |

## CitationPlan Input Packet (Track 2)

| Input | Present? | Quality | Source |
|-------|----------|---------|--------|
| ArticleModel | yes | title, abstract, language, genre | intake |
| bibliography items | yes | 18 refs, 7 DOIs | bibliography_profile |
| DOI/URL flags | yes | mechanical regex | bibliography_profile |
| incomplete refs | yes (partial) | only items with missing fields | bibliography_profile |
| placeholders | not flagged | "Мол — Множественные тела" stub not tagged | bibliography_profile |
| fit result | yes | 12 axes, `possible_but_costly` | fit_assessor (LLM) |
| mismatch map | yes | 7 mismatches | mismatch_mapping |
| Logos VenueModel | yes | `canonical_name`, `scope_summary` populated; citation norms absent | venue_profiler |
| venue citation expectations | **no** | VenueModel has no citation norm fields | N/A |

## Root Cause: Anti-Fake Filter Over-Removal

The `_AY_RE = re.compile(r"\b[A-Z][a-z]+\s+\d{4}\b")` filter in
`upgrade_citation_plan_with_llm()` removes ANY item containing an
author-year pattern like "Bergson 1992" or "Ihde 1990".

For an article with 18 bibliography references (all containing
author names and years), virtually any legitimate citation ecology
analysis that references existing bibliography items by name will
be filtered out.

**The filter was designed to prevent fabricated citations**, but it
also prevents:
- "The Bergson reference needs completion (missing publisher/edition)"
- "Ihde 1990 insufficient — need Ihde 2009 for postphenomenology"
- "Мол reference is a placeholder stub"

**No diagnostics were recorded:** the filter silently dropped items
with no pre/post counts or removal reasons in `attempt_diagnostics`.

## Classification

**`ANTI_FAKE_FILTER_OVER_REMOVAL`**

The LLM CitationPlanner was called, received input, and likely
produced actionable items. The anti-fake filter removed them because
they contained author-year patterns from the article's own
bibliography — which is exactly what legitimate citation ecology
analysis references.

## Fix (Track 4)

1. Removed `_AY_RE` author-year filter (over-aggressive)
2. Kept `_DOI_RE` filter (fabricated DOIs are mechanically detectable)
3. Added pre/post filter diagnostics to `attempt_diagnostics`
4. Updated prompt to guide LLM when bibliography IS present
5. Added 10 new tests for the corrected filter behavior
