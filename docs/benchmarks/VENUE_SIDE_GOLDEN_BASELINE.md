# Venue-side golden baseline — first pass

**Date:** 2026-06-14
**Branch:** `feature/venue-side-golden-baseline` (stacked on
`feature/venue-funnel-v1-canon` doctrine baseline).
**Scope:** structural rubric + deterministic hull builder + harness
skeleton. **No live editorial board adapter, no Russian-regime
adapters, no full-text resolvers, no 50–80 venue live crawl.**

## What this baseline is

The venue side of the Mavrinsky-style fit analysis, made symmetric
to the article-side golden run. The article-side baseline lives on
`fix/llm-agent-tolerance-mavrinsky` and was reported in
`MAVRINSKY_GOLDEN_RUN_REPORT.md` (1355 tests / 4 PASS / 3 PARTIAL /
3 FAIL on the 10-check rubric).

Venue side now starts from envelope **topology**, not from a journal
recommendation: a journal is a region in the same FieldPositionModel
space the article is a point in, and fit is containment + distance
along that region's axes.

## What this baseline says

- The venue-side `VenueProfilePackage` is materialised here as
  **7 minimal subobjects** (VenueIdentity, VenueFieldPosition,
  PublishedCorpusHull, EditorialBoardCloud, FormalSubmissionProfile,
  CitationExpectationProfile, SourceEvidencePacket). The canon's
  remaining 17 subobjects are valid for future depth; they are not
  required for the first deterministic `FitAssessment` to run.
- Each FPM envelope axis is computed from one **primary computation
  layer** out of the source allowlist A–J, with corroborating layers
  raising confidence. See
  `benchmarks/golden/venue_source_layer_map.md` §2 for the matrix.
- Six fundamental caveats apply at every layer:
  official scope ≠ corpus fact, indexing ≠ fit, full text ≠ metadata
  authority, editorial board ≠ psychology, unknown ≠ absent,
  incomplete graph ≠ absence of tradition. See same file §3.
- For Mavrinsky specifically, the funnel must surface five envelope
  clusters: continental/media philosophy (near-native),
  philosophy of technology (citation-bridge), STS/platform
  (sibling/high-rewrite), HCI/design (destructive/sibling-only),
  Russian philosophy (language-and-regime, not automatically field
  fit). See `benchmarks/golden/mavrinsky_venue_side_gold.md`.

## What this baseline ships

| artefact | what it is | LLM? | network? |
|---|---|---|---|
| `benchmarks/golden/venue_source_layer_map.md` | operational rubric, 7 subobjects, primary computation layer per axis, six caveats, forbidden source uses, Mavrinsky per-axis expectations | no | no |
| `benchmarks/golden/mavrinsky_venue_side_gold.md` | five-cluster envelope topology with per-axis expected shapes, core-risk under adaptation per cluster, VAP1–VAP7 anti-patterns, acceptance criteria | no | no |
| `benchmarks/golden/source_acquisition_funnel.md` | pool / shortlist / deep stages mapped to V1–V8 depth, source category activation per stage, deferred adapters explicitly listed | no | no |
| `services/corpus_hull_builder.py` | deterministic `CorpusAnalysisResult → FieldPositionModel(entity_type="venue")` envelope construction over discipline/school/argument_move/evidence_type/method/genre axes. Wider envelope and lower confidence for smaller corpora. Unknown is honest. | no | no |
| `tests/test_corpus_hull_builder.py` | 15 tests covering aggregation, unknown ≠ absent, official-scope-not-corpus-fact, full-text-not-metadata, indexing-not-fit, editorial-board-is-inference, FPM-shape-compatibility | no | no |
| `scripts/run_venue_side_benchmark.py` | harness skeleton implementing pool / shortlist / deep stages against fixture pool + synthetic per-venue corpus, scores against the 5-cluster gold, writes to `private_inputs/runs/<id>/venue/`. `--require-llm`-style honesty: fails loudly without fixture when live discovery is not implemented | no | no by default |

## What this baseline does NOT ship

- `EditorialBoardAdapter` live HTTP scraping. The contract is fixed
  (rubric §3.4 and source layer map §1, §3); the adapter sprint is
  the next venue-side work.
- ВАК / РИНЦ / КиберЛенинка adapters. Cluster 5 (Russian philosophy)
  produces `UNKNOWN_NOT_VERIFIED` for now.
- Full-text resolvers (OA repos, Sci-Hub-likes, ResearchGate,
  Academia, personal library, user ZIP). H layer is corpus material
  only, never metadata authority.
- A 50–80 venue live crawl. Pool stage is fixture-only in this
  baseline.
- The other 17 `VenueProfilePackage` subobjects (sections, SI,
  trust_compliance separate object, tacit signals, etc.). Canon-
  valid, deferred.

## How this relates to the Mavrinsky article-side gold

Article side outputs a `FieldPositionModel(entity_type="article")`
(a point in FPM space). Venue side outputs a
`FieldPositionModel(entity_type="venue")` with envelopes (a region).
`logic.field_position_fit.compute_field_position_fit` already
consumes both and yields a multi-axis fit verdict with no single
score. The venue-side harness invokes that same function on each
deep dossier; the verdict label is one of the 6 canonical labels
from `enums.FitLabel`.

The two golds are not redundant. Article side measures whether the
ArticleModel actually understands the manuscript. Venue side measures
whether the VenueProfilePackage actually understands the publication
container. They join at `FitAssessment`.

## Tests / build

- `pytest tests/test_corpus_hull_builder.py`: **15 passed**.
- Full `pytest`: see end-of-pass report.
- `ui/`: no changes, build clean.

## Next step recommendation

Three options on the table for the next venue-side milestone:

- **A. Merge venue-side baseline into main after review.**
  Doctrine + rubric + hull builder + harness skeleton + tests. No new
  product feature exposed externally. Low blast radius.
- **B. Run first deterministic venue-side benchmark.**
  Author a synthetic fixture pool for the 5 Mavrinsky clusters,
  invoke `scripts/run_venue_side_benchmark.py`, capture scorecard,
  iterate on the gold until topology stabilises. Still no live HTTP.
- **C. Build EditorialBoardCloud live adapter.**
  Highest blast radius. Requires SnapshotCrawler upgrades, ORCID
  lookup chain, OpenAlex Author resolver, and operator-curated fixture
  fallback. The contract is already defined; what remains is the
  adapter itself plus its own unit tests.

**Recommendation: B before A, A before C.**

Rationale. B is one fixture + one harness invocation; it surfaces
whether the rubric is internally consistent before the merge train
locks it in. A is the merge after B confirms shape. C is the next
significant code sprint and benefits from B's empirical findings.

End of report.
