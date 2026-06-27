# P7 Bootstrap — Current Algorithm Audit on Luksha Article

**Date:** 2026-06-27

## System Under Test

Article: "Universities After AI: Epistemic Legitimation, Distributed Intellectual Production, and the Second-Tier University"
Version: `08_cited_clean_current_base.md` (~76K chars, English, conceptual/theoretical)
Mode: No LLM provider (deterministic fallback only)

## Step-by-step Audit

| # | expected step | current system behavior | works? | gap |
|---|--------------|------------------------|--------|-----|
| 1 | Article text extracted | `Case.intake_text(text)` stores raw text, caps LLM input | YES | Works for text input |
| 2 | ArticleModel created | `ArticleModelerAgent.execute_deterministic()` — heuristic title/section/abstract extraction | PARTIAL | Confidence=low, many unknowns. No keyword extraction, no disciplinary register detection beyond basic heuristics. Skeletal model for conceptual article. |
| 3 | SemanticProfile created | `ArticleSemanticProfiler.execute_deterministic()` — copies `disciplinary_register_current` from ArticleModel | PARTIAL | Near-empty profile. No schools, traditions, argument moves detected. Returns confidence=low. |
| 4 | Discipline/zone/framework lookup | `DisciplinaryPathwayMapper.execute_deterministic()` — creates single pathway from `disciplinary_register_current` | PARTIAL | Single pathway only, fit_strength=UNKNOWN. Cannot detect multi-disciplinary positioning. |
| 5 | Registry miss creates SourceAcquisitionTask | `RegistryIntegrationService.discipline_lookup(query)` — on miss creates task with target_sources=["vak","oecd_ford","openalex"] | YES | Tasks created but nothing processes them automatically. No task runner exists. |
| 6 | Source packets can be attached | `SourcePacketStore.add()` exists, `SourcePacket.to_evidence_ref()` bridge works | YES (infra) | Nothing auto-populates packets from adapter results in deterministic path. Manual attachment only. |
| 7 | Provisional records created | `venue_extraction_to_provisional()` and registry stores support provisional status | YES (infra) | Only triggered after VenueProfiler output. No orchestrated "create provisional from source packet" flow. |
| 8 | Venue universe built from registry/source tasks | `Case.discover_venues()` requires `self.pathways`. Calls `VenueDiscoveryAgent.execute_deterministic()` | PARTIAL | With single UNKNOWN-strength pathway, discovery produces shallow/empty results. |
| 9 | Q/category metrics modeled per db/year/category | `VenueMetricRecord` and `VenueClassificationRecord` exist as registry types | YES (infra) | Records exist but no adapter populates them in no-LLM path. No metric ingestion workflow. |
| 10 | Shortlist created | No dedicated shortlist service exists | NO | Missing: shortlist generation from venue universe + metrics. |
| 11 | Deep VenueModels created | VenueProfiler can create VenueModel from structured text | PARTIAL | Requires venue guidelines text. No "deep model from source packets" flow. |
| 12 | Review queue surfaces provisional records | `GET /registry/review-queue` + `RegistryReviewPanel` UI | YES | Works as designed in P6.2/P7.2. |

## Summary of Gaps

### Critical (blocks self-seeding workflow)
1. **No orchestration layer** — no service chains article intake → discipline lookup → venue search → shortlist
2. **No task runner** — acquisition tasks accumulate but nothing resolves them
3. **No shortlist service** — no way to rank/filter venue universe
4. **No "source packet → provisional record" automated flow** — manual only

### Moderate (limits quality but not blocking)
5. **Deterministic agents too shallow** — single pathway, no keyword extraction, near-empty semantic profile
6. **No zone registry** — zones only exist as lists inside ArticleModel/SemanticProfile
7. **No metric ingestion** — VenueMetricRecord exists but nothing populates it

### Not Missing (infrastructure works)
8. Registry stores, acquisition tasks, source packets, review queue — all functional
9. VenueMetricRecord, VenueClassificationRecord — data models exist
10. EpistemicFrameworkRecord — first-class registry type exists

## Conclusion

The P6 registry infrastructure is solid but passive. The missing piece is the **orchestration layer** that chains existing primitives into a self-seeding workflow. Individual building blocks (registries, stores, tasks, packets) work. The workflow that connects them does not yet exist.
