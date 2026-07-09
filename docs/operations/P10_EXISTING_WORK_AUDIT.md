# P10 Existing Work Audit

**Date:** 2026-07-09
**Old branch:** `feature/p10-ru-education-ai-operational-harvest`
**Old branch HEAD:** `c85be3d`
**Old branch base:** `b6c4d61` (pre-LLM-hardening main)
**Current main:** `5ebbe1a` (post-LLM-hardening, post-intake-metadata-fix)

---

## Unique commits on old branch

| Commit | Message |
|---|---|
| `c85be3d` | feat(P10): first operational harvest — RU education/AI venue discovery via free adapters |

1 commit, 8 files changed, 1087 insertions, 3 deletions.

---

## Artifact classification

### Committed files

| File | Classification | Reason |
|---|---|---|
| `data/seed_registry/education_ai_russia/p10_target_scope.yaml` | **KEEP** | Domain scope definition, clean, no secrets |
| `docs/operations/P10_INPUT_INVENTORY.md` | **KEEP** | Source authority and adapter inventory, accurate |
| `docs/operations/P10_OPERATIONAL_HARVEST_PREFLIGHT.md` | **SUPERSEDED** | References old base `b6c4d61`, old test count; will regenerate |
| `docs/operations/P10_OPERATIONAL_HARVEST_REPORT.md` | **KEEP** | Documents first harvest run results, still valid reference |
| `scripts/run_p10_education_ai_harvest.py` | **KEEP** | Harvest script, adapter usage, pipeline logic |
| `src/kairoskopion/adapters/venue/doaj.py` | **KEEP** | Bug fix: oa_start int/dict handling |
| `src/kairoskopion/adapters/venue/openalex.py` | **KEEP** | Bug fix: filter=type:journal |
| `tests/test_p10_harvest.py` | **KEEP** | 26 tests covering harvest pipeline |

### Untracked files (on old branch)

| File | Classification | Reason |
|---|---|---|
| `data/seed_registry/education_ai_russia/p10_harvest/adapter_raw_results.jsonl` | **KEEP** | Live adapter results from first run |
| `data/seed_registry/education_ai_russia/p10_harvest/harvest_summary.json` | **KEEP** | Summary of first harvest |
| `data/seed_registry/education_ai_russia/p10_harvest/provisional_venue_records.jsonl` | **KEEP** | 87 provisional records |
| `data/seed_registry/education_ai_russia/p10_harvest/review_packet.jsonl` | **KEEP** | Review packet JSONL export |
| `data/seed_registry/education_ai_russia/p10_harvest/review_packet.md` | **KEEP** | Review packet markdown |
| `data/seed_registry/education_ai_russia/p10_harvest/review_packet.tsv` | **KEEP** | Review packet TSV |
| `data/seed_registry/education_ai_russia/p10_harvest/verification_decisions.jsonl` | **KEEP** | 601 verification decisions |
| `data/seed_registry/p73_harvest_output/*` | **UNRELATED_EXCLUDE** | P7.3 outputs, not P10 |
| `docs/ENGELBARTS_VIOLIN.md` | **UNRELATED_EXCLUDE** | Engelbart, not P10 |
| `docs/operations/ROUND3K3_LIVE_ARTICLE_RERUN_REPORT.md` | **UNRELATED_EXCLUDE** | Round3 report |
| `docs/operations/ROUND3L_FULL_LIVE_ARTICLE_RUN_REPORT.md` | **UNRELATED_EXCLUDE** | Round3 report |
| `docs/operations/ROUND3L_LIVE_USER_RUN_REPORT.md` | **UNRELATED_EXCLUDE** | Round3 report |
| `docs/operations/ROUND3O_FULL_BUILD_PLAN.md` | **UNRELATED_EXCLUDE** | Round3 report |
| `docs/operations/ROUND3O_WORKFLOW_SPLIT_AUDIT.md` | **UNRELATED_EXCLUDE** | Round3 report |

---

## Existing harvest state

| Item | Value |
|---|---|
| Source needs defined | 6 open acquisition tasks |
| Adapters used | OpenAlex (LIVE), DOAJ (LIVE) |
| Raw adapter results | 90 |
| Deduplicated results | 87 |
| Provisional records | 87 |
| Loaded to registry | 60 |
| Verification decisions | 601 (441 venue + 160 classification) |
| Promoted records | 0 |
| Review packets exported | MD + JSONL + TSV |

## Provenance assessment

- All records have `evidence_refs` with `source_type=adapter_*`, `evidence_status=FACT_FROM_API_METADATA`
- All records are `provisional` / `pending` — no auto-promotion
- No fabricated ISSNs or metadata
- Adapter bug fixes are legitimate and tested
- Harvest summary matches actual outputs

## Contamination check

| Check | Result |
|---|---|
| .env in diff | NO |
| API keys in diff | NO |
| Provider logs in diff | NO |
| Case/runtime data | NO |
| Engelbart in committed files | NO |
| Round3 in committed files | NO |
| P7.3 outputs in committed files | NO |
| Private/raw sources | NO |

**Old branch is clean for cherry-pick. Only the preflight doc needs regeneration (stale base reference).**

---

## Recommendation

Cherry-pick `c85be3d` onto clean branch from `5ebbe1a`. Then:
- Add P10 harvest data files (untracked on old branch)
- Exclude all UNRELATED_EXCLUDE files
- Regenerate preflight to reference current main
- Continue operational harvest from Step 3 onward
