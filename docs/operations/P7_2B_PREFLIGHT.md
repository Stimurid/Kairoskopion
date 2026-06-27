# P7.2B Source Authority Recovery — Preflight (Track 0)

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`
**Operator:** Claude (developer pass)

## Constraints Confirmed

| constraint | status |
|-----------|--------|
| No main merge | CONFIRMED |
| No prod deploy | CONFIRMED |
| No force push | CONFIRMED |
| No paid LLM/API calls | CONFIRMED |
| No 302.ai calls | CONFIRMED |
| No model-memory source facts | CONFIRMED — all evidence_refs point to project files |
| No synthetic dogfood if real Luksha exists | CONFIRMED — real article at `data/private_work/...` |
| All tests use tmp_path | CONFIRMED |
| data/private_work gitignored | CONFIRMED |

## Prerequisites Verified

| item | status | evidence |
|------|--------|----------|
| P7.2 code present | YES | source_authority_registry.py, external_source_adapters.py, seed_workflow.py |
| 45 P7.2 tests pass | YES | test_source_authority_registry.py |
| SourceAuthorityStore JSONL persistence | YES | mkdir + append on add() |
| SufficiencyEvaluator evaluate() | YES | target_country, target_domain kwargs |
| ExternalAdapterRegistry | YES | 14 adapters, 9 enabled |
| Real Luksha article available | YES | 08_cited_clean_current_base.md, 75,775 chars |
| Venue evidence packs (5) | YES | data/venue_evidence_packs/ |
| Discipline seeds | YES | data/disciplinary_landscape/seeds/ru_seed.jsonl |
| .gitignore seed exceptions | YES | `!data/seed_registry/` tracked |

## Scope

Owner rejected Track 4 "DEFERRED" in P7.2 acceptance checklist. This recovery session:
1. Audits the project corpus for existing source authorities
2. Creates SourceAuthorityRecord entries from corpus evidence (not model memory)
3. Reruns sufficiency evaluator with recovered authorities
4. Dogfoods on the REAL Luksha article (not synthetic text)
