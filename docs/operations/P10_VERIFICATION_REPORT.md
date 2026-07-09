# P10 Verification Report

**Date:** 2026-07-09
**Branch:** `feature/p10-operational-harvest-final`
**Gate version:** 0.1.0

---

## Summary

| Metric | Value |
|---|---|
| Total records verified | 87 |
| ACCEPTED | 0 |
| REJECTED | 0 |
| NEEDS_REVIEW | 0 |
| BLOCKED_MISSING_EVIDENCE | 0 |
| keep_provisional | 87 |

**All 87 records remain `keep_provisional`.** This is correct: adapter-only evidence (FACT_FROM_API_METADATA from OpenAlex/DOAJ) is insufficient for promotion to accepted. Promotion requires corroboration from a second authoritative source (Crossref lookup, VAK list, or manual verification).

---

## Verification logic

The P8 verification gate checks each record for:
1. **Evidence presence** — at least one evidence_ref
2. **Evidence quality** — source_type and evidence_status classify the strength
3. **Contradictions** — conflicting metric values or claims
4. **Corroboration** — multiple independent sources agreeing

Records with only `adapter_*` evidence from a single API stay `keep_provisional`.

---

## Per-tier breakdown

| Tier | Count | Verdict | Reason |
|---|---|---|---|
| tier1_ru_education | 8 | keep_provisional | Single adapter source |
| tier2_ai_education | 10 | keep_provisional | Single adapter source |
| tier3_edtech | 17 | keep_provisional | Single adapter source |
| tier4_higher_ed | 9 | keep_provisional | Single adapter source |
| noise | 6 | keep_provisional | Single adapter source (owner should reject after review) |
| unclassified | 37 | keep_provisional | Single adapter source (owner should classify) |

---

## Unresolved questions

1. ISSN verification via Crossref (SN-02) not yet executed
2. VAK list corroboration for discipline seeds (SN-03) pending
3. Noise records (6) should be rejected by owner in review
4. Unclassified records (37) need manual domain classification
5. No metrics data available — blocked by paid sources

---

## Evidence for selected Tier 1 venues

| Venue | ISSN | Source | Evidence Status | Verdict |
|---|---|---|---|---|
| Vysshee Obrazovanie v Rossii | 0869-3617 | OpenAlex | FACT_FROM_API_METADATA | keep_provisional |
| Pedagogical Education in Russia | 2079-8717 | OpenAlex | FACT_FROM_API_METADATA | keep_provisional |
| Professional Education in Russia and Abroad | 2220-3036 | OpenAlex | FACT_FROM_API_METADATA | keep_provisional |
| RUDN Journal of Informatization in Education | 2312-8631 | OpenAlex | FACT_FROM_API_METADATA | keep_provisional |

These are the highest-relevance venues. They need Crossref ISSN verification and/or VAK list corroboration to advance beyond provisional.
