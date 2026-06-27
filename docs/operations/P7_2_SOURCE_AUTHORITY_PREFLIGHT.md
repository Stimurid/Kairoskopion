# P7.2 Source Authority Discovery — Preflight (Track 0)

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## Pre-Conditions

| check | status | evidence |
|-------|--------|----------|
| Branch correct | PASS | `feature/round3-p7-llm-integration` |
| P7 Bootstrap committed | PASS | `a8fea60` — SeedRegistryWorkflow + 22 tests |
| Tests green | PASS | 2814 passed before P7.2 work |
| Existing `source_authority.py` identified | PASS | Authority ASSESSMENT module (claim validation, conflict reconciliation) — NOT the registry |
| New file namespace planned | PASS | `source_authority_registry.py` for the new registry |
| No paid API calls | PASS | All adapters default to free/disabled |
| No Claude-memory facts | PASS | No ISSNs, quartiles, editor names fabricated |

## Doctrine Constraints

- SourceAuthorityRegistry = WHERE facts come from (source-of-sources)
- Factual registries = the facts themselves (journals, disciplines, metrics)
- Before creating factual acquisition tasks → check authority coverage
- Missing authorities → SourceAuthorityDiscoveryTasks, not factual tasks
- Argentina/fishing-clubs must NOT get VAK/РИНЦ hints
