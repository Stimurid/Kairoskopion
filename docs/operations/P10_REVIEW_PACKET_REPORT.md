# P10 Review Packet Report

**Date:** 2026-07-09
**Branch:** `feature/p10-operational-harvest-final`

---

## Packets exported

| Format | Path | Status |
|---|---|---|
| Markdown | `data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.md` | Valid |
| JSONL | `data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.jsonl` | Valid, parseable |
| TSV | `data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.tsv` | Valid, has header |

---

## Packet contents

- **87 venue records** — all provisional, all pending review
- **6 acquisition tasks** — 4 open, 2 blocked
- **87 verification decisions** — all keep_provisional
- **6 documented gaps** in source coverage

---

## Records requiring owner action

### Noise (recommend REJECT)
6 records from adapter queries that are clearly outside education/AI scope (medical, clinical, sport pedagogy, kavkazology).

### Unclassified (recommend CLASSIFY)
37 records where keyword-based classification could not determine tier. Owner should manually classify as Tier 1-4 or Noise.

### High-impact (recommend VERIFY)
8 Tier 1 Russian education venues — these are the primary targets for the harvest and should be prioritized for Crossref/VAK corroboration.

---

## Validation

| Check | Result |
|---|---|
| JSONL parseable (every line) | PASS |
| TSV has header row | PASS |
| MD contains "Review Packet" | PASS |
| All records have venue_id | PASS |
| All records have provenance | PASS |
| No accepted records in packet | PASS |
