# Round III-P6.2 — Remaining Bypass Audit

**Date:** 2026-06-27
**Scope:** All direct agent instantiations in `src/kairoskopion/api/cases.py`

## Direct agent call sites — full classification

| # | Agent | Line | Registry-relevant? | Wired? | Classification |
|---|---|---|---|---|---|
| 1 | InputClassifierAgent | 443 | No | N/A | Safe — intake classification, no registry concern |
| 2 | ArticleModelerAgent | 495 | No | N/A | Safe — article extraction, not registry |
| 3 | ArticleSemanticProfilerAgent | 594 | No | N/A | Safe — semantic profile, not registry |
| 4 | DisciplineMatcherAgent | 698 | **Yes** | **Yes** (P6.1) | Wired — gated by `_registry.discipline_lookup()` |
| 5 | ArticleFieldPositionerAgent | 767 | No | N/A | Safe — field positioning, not registry |
| 6 | VenueProfilerAgent | 872 | **Yes** | **Yes** (P6.1) | Wired — output stored via `_registry.store_venue_extraction()` |
| 7 | VenueFieldPositionerAgent | 1329 | No | N/A | Safe — venue field positioning, not registry |
| 8 | DisciplinaryPathwayMapperAgent | 1593 | No | N/A | Safe — consumes confirmed article model |
| 9 | VenueDiscoveryAgent | 1652 | **Yes** | **Yes** (P6.2) | Wired — candidates stored as provisional via `_registry.store_venue_extraction()` |
| 10 | FitAssessorAgent | 1812 | No | N/A | Safe — consumes confirmed article + venue |
| 11 | MismatchNarratorAgent | 1891 | No | N/A | Safe — narrates confirmed fit assessment |

## Non-API agent paths

| Path | Agent | Classification |
|---|---|---|
| `pipelines/manuscript_venue_fit.py` | VenueProfilerAgent (line 87) | Legacy/CLI-only. Not API-reachable. Documented bypass. |
| `agents/executor.py` | Generic dispatch (lines 69, 72) | Internal agent executor — not a direct bypass |

## Status propagation coverage

| Method | propagate_status? | Evidence |
|---|---|---|
| `investigate_venue()` | Yes | line 942 |
| `get_venue_matrix()` | Yes | line 1246 |
| `discover_venues()` | Yes | line 1714 (P6.2) |

## Structural guard

Test `TestBypassAuditStructural.test_no_new_agent_calls` maintains a known-set of 11 agent
calls. Any new `*Agent()` instantiation in `cases.py` will fail this test, forcing
explicit classification before merge.

## Verdict

**All 11 direct agent calls classified.** 3 registry-relevant calls wired (P6.1 + P6.2).
8 non-registry calls documented safe. 1 legacy pipeline bypass documented.
No remaining un-audited bypasses.
