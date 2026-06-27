# P7.2B Sufficiency Rerun Report (Track 5)

**Date:** 2026-06-27

## Setup

- Authority store: 17 recovered records (6 RU, 11 INTERNATIONAL)
- Evaluator: SourceAuthoritySufficiencyEvaluator

## Case A: RU / education

| metric | before (P7.2) | after (P7.2B) |
|--------|--------------|---------------|
| Sufficient | NO | **YES** |
| Confidence | low | **medium** |
| Missing types | 7/7 | **0/7** |
| Usable authorities | 0 | **17** |
| Tasks to create | 7 | **0** |

**Verdict: PASS** — all 7 required authority types covered for Russian education domain.

## Case B: AR / fishing-clubs

| metric | before (P7.2) | after (P7.2B) |
|--------|--------------|---------------|
| Sufficient | NO | NO |
| Confidence | low | low |
| Missing types | 7/7 | **1** (discipline_classification) |
| Usable authorities | 0 | **11** (international only) |
| Tasks to create | 7 | **1** |

**Verdict: CORRECT** — Argentina has no discipline_classification in corpus.
RU-specific authorities (VAK, РИНЦ, CyberLeninka, ISTINA) correctly excluded.
The Argentina cross-check guardrail works as designed.

## Case C: GENERIC / philosophy

| metric | value |
|--------|-------|
| Sufficient | NO |
| Confidence | low |
| Missing types | 1 (discipline_classification) |
| Usable authorities | 11 |
| Tasks to create | 1 |

**Verdict: CORRECT** — no generic discipline_classification exists in corpus.

## Before/After Comparison

| scenario | P7.2 (empty store) | P7.2B (17 records) | delta |
|----------|-------------------|-------------------|-------|
| RU/education missing | 7 | 0 | **-7** |
| AR/fishing missing | 7 | 1 | **-6** |
| GENERIC/philosophy missing | 7 | 1 | **-6** |

The recovery reduced missing authority types from 21 (across 3 cases) to 2.
