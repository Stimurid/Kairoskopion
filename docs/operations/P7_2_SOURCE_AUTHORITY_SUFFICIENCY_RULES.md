# P7.2 Source Authority Sufficiency Rules (Track 3)

**Date:** 2026-06-27

## Minimum Authority Set

For any venue discovery workflow, the system requires authority sources
covering these 7 types:

| authority type | description | required for |
|----------------|-------------|--------------|
| `discipline_classification` | Official discipline/specialty classification | discipline lookup, venue universe |
| `national_journal_registry` | National/regional journal list or registry | venue universe, venue discovery |
| `metric_source` | Journal metrics/indexing database | shortlist, venue metrics |
| `author_guidelines_source` | Journal author guidelines / aims & scope | deep venue model, fit assessment |
| `editorial_board_source` | Editorial board page | deep venue model, editor background |
| `journal_archive_source` | Journal archive / recent issues | deep venue model, corpus analysis |
| `citation_database` | Citation/reference database | citation ecology, corpus analysis |

## Task-Dependent Requirements

- `venue_discovery` → base + citation_database
- `shortlist` / `venue_metrics` → base + metric_source
- `deep_venue_model` / `fit_assessment` → base + all 7
- `desired_outputs: ["corpus"]` → + journal_archive_source

## Country-Specific Hints

### Russia (RU)

- discipline_classification → VAK nomenclature, ГРНТИ
- national_journal_registry → eLibrary.ru / РИНЦ, VAK journal list
- metric_source → РИНЦ indicators, Scopus/SJR, WoS/ESCI
- journal_archive_source → CyberLeninka, eLibrary archive
- citation_database → OpenAlex, Crossref, OpenCitations

### Generic (fallback)

- discipline_classification → National research classification, OECD FORD
- national_journal_registry → National scholarly journal index
- journal_archive_source → DOAJ, journal official archives
- citation_database → OpenAlex, Crossref

## Sufficiency Verdict

- **Sufficient** (confidence: medium): all required types covered
- **Partial** (confidence: low): 1-2 missing, not discipline_classification
- **Insufficient** (confidence: low): 3+ missing or discipline_classification missing

## Cross-Country Guardrail

If VAK/РИНЦ records are present for a non-Russian target country,
the evaluator emits a warning. This prevents Russia-specific sources
from polluting non-Russian analyses.
