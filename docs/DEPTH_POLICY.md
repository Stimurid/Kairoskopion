# Venue Depth Policy Reference

## 8-Level Evidence Depth Model

| Level | Name | What it covers | Key sources |
|-------|------|----------------|-------------|
| L0 | IDENTITY | Name, ISSN, URL, publisher | OpenAlex, Crossref |
| L1 | OFFICIAL_FORMAL | Submission guidelines, scope, APC | Homepage snapshot |
| L2 | PUBLICATION_MODEL | Article types, word limits, review model | Aggregation of L0+L1 |
| L3 | CORPUS_SAMPLE | Genre/method/school distributions from articles | Corpus sampler + analyzer |
| L4 | EDITORIAL_INTELLIGENCE | Board composition, disciplinary center | Editorial board analysis |
| L5 | POLICY_AND_INDEXING | OA policy, indexing, Sherpa/Romeo | DOAJ, policy databases |
| L6 | EXTERNAL_GRAPH | Citation ecology, co-citation networks | OpenCitations, citation analysis |
| L7 | USER_MEMORY_AND_OUTCOMES | Past submission outcomes, tacit knowledge | User memory store |

## Analysis Purposes → Default Policies

| Purpose | Target depth | Max API calls | Corpus sample |
|---------|-------------|---------------|---------------|
| `quick_look` | L2 | 10 | 0 |
| `fit_assessment` | L4 | 25 | 30 |
| `venue_deep_profile` | L6 | 50 | 50 |
| `submission_ready` | L7 | 100 | 100 |
| `resubmission_analysis` | L5 | 50 | 50 |
| `comparative_positioning` | L4 | 25 | 30 |

## Policy structure

Each `VenueDepthPolicy` contains:
- `min_depth` / `target_depth` / `max_depth` — depth range
- `required_source_roles` — must succeed for level to be complete
- `optional_source_roles` — best-effort
- `required_agents` / `optional_agents` — which agents to invoke
- `stop_conditions` — when to stop collecting
- `degradation_rules` — fallback behavior when sources unavailable
- `max_api_calls` / `max_articles_to_sample` — resource limits
- `freshness_threshold_days` — staleness cutoff

## Depth coverage tracking

`VenueDepthCoverage` reports per-level status:
- `fresh` — data collected recently within freshness threshold
- `partial` — some but not all sources available
- `stale` — data older than freshness threshold
- `never_run` — no data collected for this level

Missing required sources and unavailable sources are tracked explicitly.

## CLI usage

```bash
# Inspect a depth policy
python -c "from kairoskopion.cli import main; main(['inspect-venue-depth-policy', '--purpose', 'fit_assessment'])"

# Build evidence stack with depth policy
python -c "from kairoskopion.cli import main; main(['build-venue-evidence-stack', '--venue-name', 'Nature', '--purpose', 'quick_look'])"
```

## Code locations

- `src/kairoskopion/venue_depth.py` — depth model, policies, coverage
- `src/kairoskopion/services/venue_evidence_stack.py` — stack builder orchestrator
- `src/kairoskopion/cli.py` lines 1270-1310 — CLI commands
