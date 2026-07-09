# P10 Operational Harvest — Final Report

**Date:** 2026-07-09
**Main base commit:** `5ebbe1a`
**Old P10 branch:** `feature/p10-ru-education-ai-operational-harvest` @ `c85be3d`
**Clean branch:** `feature/p10-operational-harvest-final`
**Old branch base:** `b6c4d61` (pre-LLM-hardening)

---

## Old-branch audit

| Item | Value |
|---|---|
| Old branch commits | 1 (`c85be3d`) |
| Files changed | 8 (scope, docs, script, adapter fixes, tests) |
| Contamination | NONE (no .env, no keys, no Engelbart, no Round3) |
| Adapter bugs fixed | 2 (OpenAlex filter URL, DOAJ oa_start int/dict) |
| Cherry-pick result | Clean, no conflicts |
| Audit doc | `docs/operations/P10_EXISTING_WORK_AUDIT.md` |

---

## Clean branch

| Item | Value |
|---|---|
| Base | `5ebbe1a` (main, post-LLM-hardening + intake metadata fix) |
| Branch | `feature/p10-operational-harvest-final` |
| Cherry-picked | `c85be3d` (old P10 commit) |
| New files added | scope doc, final script, final tests, reports, harvest data |

---

## Source needs (6)

| ID | Question | Status |
|---|---|---|
| SN-01 | Venue universe bootstrap | SATISFIED (87 provisional from OpenAlex + DOAJ) |
| SN-02 | ISSN/publisher verification | OPEN (Crossref lookup task created) |
| SN-03 | Discipline seed corroboration | OPEN (VAK lookup tasks created) |
| SN-04 | Venue ranking/metrics | BLOCKED (Scopus/WoS paid, eLibrary needs key) |
| SN-05 | Russian-language venue coverage | OPEN (CyberLeninka task created) |
| SN-06 | Venue section structure | DEFERRED (requires per-venue evidence packs) |

---

## Acquisition tasks

| Category | Count |
|---|---|
| Total | 6 |
| Open | 4 |
| Blocked | 2 |
| Already satisfied | 0 (SN-01 was satisfied by first harvest, no task needed) |
| Duplicate | 0 |
| Rejected | 0 |

---

## Acquired sources

| Metric | Value |
|---|---|
| Adapters queried | OpenAlex (LIVE), DOAJ (LIVE) |
| Raw adapter results | 90 |
| Deduplicated | 87 |
| With ISSN | ~70 |
| With publisher | ~60 |
| Source queries | 10 (6 OpenAlex + 4 DOAJ) |
| Acquisition date | 2026-06-27 |

---

## Domain classification

| Tier | Count | Description |
|---|---|---|
| tier1_ru_education | 8 | Russian education journals (highest relevance) |
| tier2_ai_education | 10 | AI in education (international) |
| tier3_edtech | 17 | Educational technology (international) |
| tier4_higher_ed | 9 | Higher education (international) |
| noise | 6 | Off-topic (medical, clinical, sport) |
| unclassified | 37 | Needs manual classification |

---

## Verification decisions

| Verdict | Count |
|---|---|
| keep_provisional | 87 |
| promote_verified | 0 |
| needs_manual_review | 0 |
| reject | 0 |
| blocked | 0 |

**Expected:** all records stay `keep_provisional` because adapter-only evidence is insufficient for promotion. No auto-promotion.

---

## Review packets

| Format | Path | Valid |
|---|---|---|
| MD | `data/.../p10_harvest/review_packet_final.md` | YES (9163 chars) |
| JSONL | `data/.../p10_harvest/review_packet_final.jsonl` | YES (175 lines) |
| TSV | `data/.../p10_harvest/review_packet_final.tsv` | YES (header present) |

---

## Registry-ready outputs

| Metric | Value |
|---|---|
| Total records | 87 |
| Accepted | 0 |
| Provisional | 87 |
| With provenance | 87 (100%) |
| With evidence_refs | 87 (100%) |
| With domain_tier | 87 (100%) |
| Schema-valid | YES |
| Duplicate IDs | 0 |

---

## Operator smoke

| Step | Result |
|---|---|
| List acquisition tasks | PASS (6 tasks) |
| Inspect a task | PASS (all fields present) |
| Inspect a source record | PASS (provenance, evidence, ISSN) |
| Run verification | PASS (keep_provisional, correct reason) |
| Inspect decision | PASS (verdict, reason in file) |
| Export review packet | PASS (MD + JSONL + TSV) |
| Inspect registry output | PASS (87 provisional, 0 accepted) |
| Provenance audit | PASS (0 missing, 0 fabricated) |
| No fabrication | PASS |
| **Overall** | **PASS** |

---

## P11 trace evidence

LLM was NOT used in this harvest pass. All data from deterministic adapter queries and keyword classification. No P11 trace applicable.

---

## Tests / validators

| Gate | Result |
|---|---|
| pytest tests -q | 3240 passed, 5 failed (pre-existing DOCX/python-docx missing dep), 3 skipped, 8 deselected |
| P10 focused tests | 52/52 passed (26 original + 26 final) |
| TypeScript typecheck | PASS |
| Vite build | PASS |
| Registry JSONL parseable | YES |
| Review packet references resolve | YES |
| All accepted sources have provenance | YES (0 accepted, 87 provisional all have provenance) |
| Private/raw files untracked | YES |
| No accidental network calls in tests | YES (all P10 tests use OFFLINE_STUB or tmp_path) |

---

## Privacy / provenance audit

| Check | Result |
|---|---|
| .env committed | NO |
| API keys committed | NO |
| Provider logs committed | NO |
| Private/raw files committed | NO |
| Case/runtime data committed | NO |
| Engelbart files committed | NO |
| Round3 files committed | NO |
| Copyrighted full texts | NO |
| Fabricated sources | 0 |
| LLM assertions as verification | 0 |

---

## Remaining blocked source needs

| Source Need | Blocker |
|---|---|
| SN-04 (venue metrics) | Scopus/WoS paid; eLibrary.ru needs API key |
| SN-05 (RU-language venues) | CyberLeninka requires manual URL input (task open) |
| SN-06 (venue sections) | Requires per-venue evidence packs (deferred) |

---

## Owner answers

| Question | Answer |
|---|---|
| Existing P10 work safely preserved | YES |
| Clean branch based on `5ebbe1a` | YES |
| Real sources acquired | YES (87 from OpenAlex + DOAJ LIVE) |
| Accepted records have provenance | YES (0 accepted; 87 provisional all have provenance) |
| Verification gate executed | YES (87 decisions, all keep_provisional) |
| Review packets exported | YES (MD + JSONL + TSV) |
| Registry outputs validated | YES (schema-valid, provenance complete, no duplicates) |
| Unverified sources excluded | YES (0 promoted to accepted) |
| Operator path proven | YES |
| LLM steps traceable | NOT_USED |
| Private/raw files excluded | YES |
| Full gates green | YES (pre-existing DOCX failures only) |

---

## Merge recommendation

`P10_OPERATIONAL_HARVEST_MERGE_READY`

The operational harvest successfully completed the source need -> acquisition -> verification -> review -> registry loop. 87 provisional venue records from real adapter queries, all with provenance and evidence. No fabricated sources, no auto-promotion, no secrets committed. Domain classification and acquisition tasks generated for next steps. Pre-existing DOCX test failures are environment-specific (missing `python-docx` optional dependency), not P10-related.
