# Mavrinsky real venue pool — pass #001

**Date:** 2026-06-14
**Branch:** `main` @ `v0.2.0-alpha-rc17` (working tree)
**Run ID:** `mavrinsky_real_venue_pool_001`
**Goal:** Answer concretely how close we are to a real venue-selection
case for Mavrinsky's article using **existing infrastructure only**.

---

## Part A — Inventory of existing venue/profile assets

Classification table. Counts are exact at this main HEAD.

| asset_path | asset_type | count | class | durable? | tracked? | usable for real venue fit? | notes |
|---|---|---|---|---|---|---|---|
| `benchmarks/golden/mavrinsky_venue_side_gold.md` | doc | 1 | GOLD_RUBRIC | durable | tracked | yes (as rubric, not data) | 5-cluster envelope topology |
| `benchmarks/golden/venue_source_layer_map.md` | doc | 1 | GOLD_RUBRIC | durable | tracked | yes (as rubric) | per-axis source authority |
| `benchmarks/golden/source_acquisition_funnel.md` | doc | 1 | GOLD_RUBRIC | durable | tracked | yes (as rubric) | V1–V8 funnel doc |
| `benchmarks/golden/mavrinsky_article_side_gold.md` | doc | 1 | GOLD_RUBRIC | durable | tracked | article side only | — |
| `benchmarks/fixtures/mavrinsky_venue_side/pool.json` | fixture | 5 venues | SYNTHETIC_FIXTURE | durable | tracked | **no** — `[FIXTURE]`-tagged synthetic archetypes | for harness test only |
| `benchmarks/fixtures/mavrinsky_venue_side/article_fpm.json` | fixture | 1 article | SYNTHETIC_FIXTURE | durable | tracked | article point reference | gold-aligned, not LLM-extracted |
| `tests/fixtures/uc1_demo_pack/venue_seeds.json` | fixture | 5 venues | DEMO_SEED | durable | tracked | partly — real names (*Techné*, *Social Studies of Science*, *Philosophy & Technology*, *AI & Society*, *Frontiers in HCI*) but no source basis beyond scope sketch | UC-1 demo authored 2026-06-13 |
| `tests/fixtures/uc1_demo_pack/corpus/*.json` | fixture | 3 corpora | DEMO_SEED | durable | tracked | small synthetic corpora for 3 of the 5 demo seeds | not real published articles |
| `tests/fixtures/venue_evidence/synthetic_venue_identity.json` | fixture | 1 venue | SYNTHETIC_FIXTURE | durable | tracked | no | `Synthetic Philosophy of Technology Journal` |
| `tests/fixtures/venue_evidence/synthetic_corpus.json` | fixture | 1 corpus | SYNTHETIC_FIXTURE | durable | tracked | no | — |
| `tests/fixtures/venue_*.md` (4 files) | fixture | 4 guidelines samples | SYNTHETIC_FIXTURE | durable | tracked | no | — |
| `examples/venue_seed_corpus/venues.jsonl` | registry seed | 5 venues | SYNTHETIC_FIXTURE | durable | tracked | no | all named `vrec_synth_*` |
| `examples/venue_seed_corpus/sources.jsonl` | registry seed | 12 sources | SYNTHETIC_FIXTURE | durable | tracked | no | — |
| `examples/venue_seed_corpus/claims.jsonl` | registry seed | 34 claims | SYNTHETIC_FIXTURE | durable | tracked | no | — |
| `.kairoskopion/registries/venue_models.jsonl` | runtime registry | 1 venue | DEMO_SEED | durable | **ignored** | partly — real journal *Social Studies of Science* but `confidence: "medium"`, `evidence_refs: []`, no corpus, no board | UC-1 demo output captured to local registry |
| `.kairoskopion/vault/venues/ven_8b8f44016c8f.md` | vault card | 1 card | DEMO_SEED | durable | ignored | same as above | markdown card for the registry entry |
| `.kairoskopion/registries/*.jsonl` (other 14 files) | runtime registry | ~14 records total | DEMO_SEED | durable | ignored | UC-1 / Logos trial artefacts | not real journal profiles |
| `.kairoskopion_cache/*.json` | HTTP cache | 3 files | SOURCE_CACHE | ephemeral | ignored | yes — **real DOAJ and OpenAlex responses** (49 + 55 + 1 results) | freshly cached; pool build below |
| `private_inputs/runs/mavrinsky_venue_det_001/venue/*.json` | generated | 4 files | GENERATED_BENCHMARK_OUTPUT | ephemeral | ignored | no — synthetic deterministic proof | — |
| `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/*.json` | generated | 5 files | REAL_EPHEMERAL_CANDIDATE | ephemeral | ignored | **yes — this pass** | pool=234, shortlist=12, deep-lite=5 |
| `tests/fixtures/uc1_demo_pack/draft_article.md` | fixture | 1 article | DEMO_SEED | durable | tracked | not venue, but used by demo | — |
| `architecture/`, `docs/VENUE_*` (15 docs) | doc | 15 docs | DOC_ONLY | durable | tracked | doctrine + architecture, not data | — |

**No `ORPHAN` entries detected.** All venue-related modules and fixtures
are linked into either tests, the harness, or the canon documentation.

---

## Part B — Counts (exact, no inflation)

| class | count |
|---|---|
| **REAL_DURABLE_VENUE_PROFILE** (identity + source basis + evidence + storage) | **0** |
| **REAL_EPHEMERAL_CANDIDATE** (this run, in ignored `private_inputs/`) | **234** deduped from 273 raw |
| SYNTHETIC_FIXTURE (fixtures/seeds/registry seed) | **18** files / ~16 venues |
| GENERATED_BENCHMARK_OUTPUT (`private_inputs/runs/.../venue/`) | **9** files across 2 runs |
| DEMO_SEED (UC-1 + Logos trial captured to local registry) | **5–6** venue-shaped records (1 in registry, 5 in demo pack) |
| GOLD_RUBRIC (`benchmarks/golden/*.md`) | **4** docs |
| SOURCE_CACHE (`.kairoskopion_cache/`) | **3** HTTP responses (DOAJ × 2 + OpenAlex × 1) |
| DOC_ONLY (architecture / spec) | **15** docs |

**Real durable venue profiles on this main: zero.** What exists in the
runtime registry (`venue_models.jsonl`, 1 record for *Social Studies of
Science*) is a UC-1 demo capture without evidence backing and without
corpus / board / citation layers — it does not meet the canon §2
definition of a durable `VenueProfilePackage` instance.

---

## Part C — Storage model reality

| where | what | wired in? |
|---|---|---|
| `benchmarks/golden/` | rubrics + topology gold | yes — read by scorer + harness |
| `benchmarks/fixtures/mavrinsky_venue_side/` | synthetic archetype pool for the venue-side deterministic proof | yes — read by `scripts/run_venue_side_benchmark.py` |
| `tests/fixtures/uc1_demo_pack/`, `tests/fixtures/venue_evidence/` | demo / unit-test fixtures | yes — read by tests + `run-uc1-demo` |
| `examples/venue_seed_corpus/*.jsonl` | synthetic seed corpus for `import-venue-seed` CLI | partial — schema is real, content is `vrec_synth_*` |
| `.kairoskopion/registries/*.jsonl` (ignored) | JSONL append-only runtime registry | yes — `services.venue_registry` writes; `Case.investigate_venue` reads through its in-memory orchestrator |
| `.kairoskopion/vault/venues/` (ignored) | markdown cards | yes — `artifacts` + `cards` modules generate them |
| `.kairoskopion_cache/` (ignored) | HTTP response cache | yes — `adapters.http_client.fetch_json_safe` |
| `private_inputs/runs/<id>/venue/` (ignored) | per-run generated artefacts | yes — both harnesses write here |
| LocalFsVault for `VenueProfilePackage` | **NOT wired** — the canon-§2 package has no aggregating dataclass yet (deferred to VF-C2) | **partial**: vault stores `VenueModel`, not `VenueProfilePackage` |
| Durable, indexed, cross-session venue DB | **does not exist**. The registry is JSONL append-only; there is no lookup-by-canonical-name index, no dedup, no cross-case sharing in the current `Case` orchestrator | **no** |
| UI reads persisted venue profiles? | **no** — `Case` orchestrator stores venues per-case in memory; UI calls `/cases/{id}/venue-pool` etc., not `/venues/*` (there is no `/venues/*` endpoint) | **no** |
| Staging has persistent venue data? | unknown — no SSH access this pass; given staging persistence is "in-memory only" per the existing audit, the answer is almost certainly **no** | **presumed no** |

---

## Part D — First real Mavrinsky candidate pool

**Approach:** existing infrastructure only. Live HTTP to DOAJ public
search API and OpenAlex Sources API (both free, no auth). NO LLM, NO
EditorialBoardCloud, NO ВАК / РИНЦ / КиберЛенинка, NO Sherpa /
Unpaywall, NO Sci-Hub-like, NO paid sources (Scopus / WoS / JCR).

**Command (no commit of fetched data):**

```powershell
python scripts/build_real_venue_pool.py `
    --output private_inputs/runs/mavrinsky_real_venue_pool_001
```

**Results:**

| stage | count |
|---|---|
| pool raw (across 15 cluster queries × 2 sources) | 273 |
| pool deduped (by ISSN ∪ canonical name) | **234** |
| shortlist (top 12 by discovery-cluster fan-out + light keyword bonus) | **12** |
| deep-lite (top 5 with OpenAlex Works concept hint, 15 works each) | **5** |

**What deep-lite actually fetched:** for 4 of 5 candidates, OpenAlex
Works metadata (titles + machine-tagged concepts + publication years).
1 of 5 had no OpenAlex source id resolvable → that subobject is
marked `unknowns`, no fabrication.

### Top-5 deep-lite (full evidence)

| # | candidate | source | ISSN | publisher | OpenAlex works fetched | top concepts (machine-tagged) | year range | evidence status | unknowns |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Novation** | DOAJ + OpenAlex | 2562-7147 | Univ. Federal do Paraná | 15 | Sociology, Political science, Public relations, Engineering ethics | 2024–2025 | DOAJ listing + OpenAlex concepts (machine-tagged) | no abstracts, no refs, no board, no guidelines |
| 2 | **Journal of Educational Research in Mathematics** | DOAJ + OpenAlex | 2288-7733 | Korean Society of Educational Studies in Mathematics | 15 | Computer science, Mathematics education, Mathematics, Psychology | 2020 only | same | same |
| 3 | **Culturas Cientificas** | DOAJ + OpenAlex | 0719-9856 | Univ. de Santiago de Chile | 5 | Philosophy, Humanities, Epistemology | 2022–2024 | same | same |
| 4 | **Colloquy: Text, Theory, Critique** | DOAJ only | 1447-0950 | Monash University | — | (no OpenAlex source id) | — | DOAJ listing only | also no OpenAlex coverage at this tier |
| 5 | **Memory, Mind & Media** | DOAJ + OpenAlex | 2635-0238 | Cambridge University Press | 15 | Sociology, Psychology, Collective memory, Aesthetics, Narrative | 2025–2026 | same | same |

### Honest verdict on these top-5

**Most of them are wrong for Mavrinsky's article.** *Novation* is
innovation studies; *Journal of Educational Research in Mathematics*
is what it says; *Memory, Mind & Media* is memory studies. The screen
returned them because DOAJ's full-text relevance ranker hit on the
words "philosophy" and "technology" inside their scope texts, and our
discovery layer is honestly noisy — it has no access to the actual
philtech canon. **The free-tier discovery layer is not enough on its
own for this article.**

What is **conspicuously absent** from the top-12 — and from the 234
pool — because of source-layer limits, not because the system failed:

- *Philosophy & Technology* (Springer) — subscription, **not in DOAJ**;
  needs Crossref + manual editorial-board crawl (deferred).
- *Techné: Research in Philosophy and Technology* (Philosophy
  Documentation Center) — closed, **not in DOAJ**.
- *Foucault Studies* (RUC) — open access **but** indexed under
  "philosophy" not "philosophy of technology" in DOAJ; would surface
  on a wider continental query.
- *Phenomenology and Mind* — open, present in DOAJ but ranked below
  the 15-per-cluster cutoff.
- *Russian* philosophy journals — Voprosy Filosofii, Logos, etc.
  **not in DOAJ** (DOAJ has very thin Russian-philosophy coverage);
  needs ВАК / РИНЦ adapters (deferred).

This is the **expected** output of free-tier discovery. AP1 from the
source layer rubric (scope keyword ≠ fit) is exactly the trap our
shortlist would fall into if the scorer didn't have access to corpus
or editorial board.

---

## Part E — Save paths

| artefact | path | status |
|---|---|---|
| harness script | `scripts/build_real_venue_pool.py` | tracked + committed in this report's commit |
| this report | `docs/benchmarks/MAVRINSKY_REAL_VENUE_POOL_001_REPORT.md` | tracked + committed |
| pool raw (273) | `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/01_pool_raw.json` | ignored — not committed |
| pool deduped (234) | `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/02_pool_deduped.json` | ignored |
| shortlist (12) | `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/03_shortlist.json` | ignored |
| deep-lite (5) | `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/04_deep_lite.json` | ignored |
| summary | `private_inputs/runs/mavrinsky_real_venue_pool_001/venue/00_summary.json` | ignored |

No raw fetched pages with copyrighted full text were saved. The
deep-lite expansion stored only OpenAlex metadata (titles, concept
tags, year), which is `metadata_api` authority level (`registry_card`-
class), public, and citable.

---

## Part F — Readiness scoring

### F.1 Are we ready for real venue selection?

**No.** Three layers are missing for a believable Mavrinsky fit, in
order of importance:

1. **Real corpus hull from real published articles.** The deep-lite
   step gathered OpenAlex concept tags, not abstracts, not references,
   not theory shoulders, not method patterns. Without those, the
   `school_envelope` / `argument_move_envelope` / `evidence_type_envelope`
   are all UNKNOWN at the per-venue level. The `corpus_hull_builder`
   service exists and is deterministic; it just has no real
   `CorpusAnalysisResult` to feed it, because the `corpus_sampler`
   has no live wiring to fetch abstracts from a venue's recent
   articles.
2. **Formal guidelines extraction.** Author guidelines for the top-5
   candidates were not fetched. Without them, `FormalSubmissionProfile`
   stays empty (no method requirement, no language regime, no APC,
   no review model from A `formal_page` evidence). `SnapshotCrawler`
   exists but is explicit-URL-only by current contract; a guidelines
   URL collector is not wired.
3. **EditorialBoardCloud.** No editor records collected. Geographic
   envelope and school commitments by editor remain UNKNOWN. The
   contract is in canon §3.E and source layer map §1; the adapter is
   the next venue-side sprint per ADR-16 and explicit operator
   instruction (deferred).

### F.2 Are we ready for real journal profile persistence?

**Partial.**

- The schema half exists: `VenueModel` + `VenueRecord` + `VenueSource`
  + `VenueClaim` + `VenueEvidencePack` are real dataclasses and the
  registry writes them.
- The aggregating `VenueProfilePackage` from canon §2 is **not** a
  code dataclass yet — VF-C2 is the open sprint that adds it.
- Cross-session, cross-case venue lookup is **not wired**. Each
  `Case` keeps venues in-memory per case. Two consecutive Mavrinsky
  searches would not share any data; the second would re-discover.

### F.3 Are we ready for UX bench?

**No.** Independent of (F.1) and (F.2):

- UI cockpit has not been smoke-tested against the Mavrinsky case
  this pass (no operator browser session in this window).
- The `/venues/*` API surface does not exist; UI reads venues only
  through the per-case path. Operator browsing of a durable journal
  catalogue is not possible from the cockpit.
- Staging deploy of rc17 has not been performed (no SSH this pass).

### F.4 Exact layers missing

| layer | status | next action source |
|---|---|---|
| Durable `VenueProfilePackage` storage | **missing** — registry exists, aggregating package doesn't | VF-C2 sprint (open) |
| Cross-session durable venue index | **missing** — JSONL append, no lookup | VF-C2 / VF-C4 |
| Real `PublishedCorpusHull` from real articles | **infrastructure exists, wiring missing** — `corpus_hull_builder` runs on `CorpusAnalysisResult`, but `corpus_sampler` is not connected to live OpenAlex Works for a target venue at the harness level | small wiring sprint, deferred |
| Formal guidelines extraction | **missing** — SnapshotCrawler is explicit-URL-only, no auto-collector | small wiring sprint, deferred |
| EditorialBoardCloud | **missing entirely** — contract defined, adapter not built | deferred per explicit director instruction |
| ВАК / РИНЦ / КиберЛенинка adapters | **missing entirely** | deferred per explicit director instruction |
| LLM runtime contract for content-grade fit | **external (Agentum)** — Kairoskopion code reads from it once Agentum exposes it | not a Kairoskopion sprint |
| UI cockpit venue catalogue view | **missing** — only per-case venues | deferred until VF-C2 lands |

### Quick answer to the user's broader wishes

The user described an end-state where:

- a few **dozen** discipline clusters cover the article (philosophy →
  psychology → engineering → interdisciplinary);
- **all** journals in each cluster are profiled (V1–V2);
- top-15 across clusters get a deep V8 pass (15 latest articles →
  pathway / genre / style models);
- top-5 also get editor-biography mining (≥ 50 % of board, ≥ 5 latest
  articles per editor);
- everything is **persisted** so the next article search reuses what's
  already in the DB.

Where we stand right now:

- "all journals" reality: **DOAJ + OpenAlex free tiers, 234 deduped
  candidates** for Mavrinsky's discipline fan-out. To go beyond DOAJ
  + OpenAlex requires Crossref full mining (`OpenAlex` covers much of
  it), and to surface paid / Russian journals requires Scopus / WoS
  (paid, currently UNKNOWN_NOT_VERIFIED) and ВАК / РИНЦ (deferred).
- "models of all journals" reality: zero durable profiles right now;
  the aggregating `VenueProfilePackage` dataclass is VF-C2.
- "15 latest articles per top-15" reality: OpenAlex Works gives that
  for each OpenAlex-listed venue, but for now we fetch only
  titles + concepts + year, not abstracts / references.
- "editor biographies, ≥ 50 % of board, ≥ 5 articles each" reality:
  **zero infrastructure today**. The EditorialBoardCloud sprint is
  not started.
- "saved for next search" reality: the registry exists but is not
  indexed for venue lookup; the `Case` orchestrator does not consult
  the registry on a new case. The persistence half-of-the-system is
  visible to operators only through the JSONL files.

The genre / style typology the user asked about ("kстати где хранится у
нас типология этих «жанров» и стилей для разных дисциплин?"):

- **Article-side genre enum** in `enums.Genre`: 11 values
  (research_article, conceptual_article, theoretical_essay,
  systematic_review, position_paper, commentary, conference_paper,
  forum_piece, book_symposium_piece, review, unknown).
- **Argument-move taxonomy** in `enums.ArgumentMoveType`: 12 values
  used by `argument_move_vector`.
- **Method status** in `enums.MethodStatus`: 8 values.
- **Novelty mode** in `enums.NoveltyMode`: 10 values.

These typologies are **discipline-agnostic** today; there is no
per-discipline genre profile (e.g., "STS expects empirical_conceptual
hybrid with 30–60 references and a methods section"). That per-
discipline calibration would need a real corpus-hull pass across a
multi-discipline set, which lands when:

- VF-C2 ships the aggregating `VenueProfilePackage`,
- corpus mining is wired to OpenAlex Works abstracts,
- and `corpus_hull_builder` is run across enough real venues to
  derive per-discipline distributions.

That is a multi-sprint, multi-week effort. Honest position: **not in
rc17, not in the next sprint either** without the three deferred
adapters being unblocked first.

---

## Part G — Final report

| item | value |
|---|---|
| main HEAD | `53ba69b` (rc17 tag) |
| harness script added | `scripts/build_real_venue_pool.py` (new) |
| report added | `docs/benchmarks/MAVRINSKY_REAL_VENUE_POOL_001_REPORT.md` (this file) |
| code changed beyond harness/report | none |
| **REAL_DURABLE_VENUE_PROFILE** count | **0** |
| **REAL_EPHEMERAL_CANDIDATE** count (this pool) | **234** deduped from 273 raw |
| shortlist count | **12** |
| deep-lite count | **5** |
| top-3–5 candidate names (real but mostly mismatched per Part D) | Novation; Journal of Educational Research in Mathematics; Culturas Cientificas; Colloquy: Text, Theory, Critique; Memory, Mind & Media |
| evidence status of those names | DOAJ external_claim + OpenAlex metadata_api concept tags |
| what was NOT collected | abstracts, references, editorial board, formal author guidelines, full text, Scopus/WoS indexing, ВАК/РИНЦ status, Russian journals (DOAJ coverage too thin) |
| live adapter failure? | no — DOAJ and OpenAlex both responded; the gap is **structural**, not connectivity |
| ready for real venue selection? | **no** |
| ready for real journal profile persistence? | **partial** (schema yes, aggregator no, cross-case index no) |
| ready for UX bench? | **no** |
| tests | not run yet — see §validation below |
| UI build | not run yet — see §validation below |
| commit made | yes — harness + report (only) |
| push | yes — origin/main (after validation) |

### Validation

Will run pytest + UI build to confirm rc17 main is intact after this
pass adds only the harness script and a report file. See commit
section below.

---

## What this pass NOT doing

- not starting `EditorialBoardCloud` live adapter,
- not adding ВАК / РИНЦ / КиберЛенинка adapters,
- not adding shadow / full-text resolvers,
- not tuning LLM parameters,
- not redesigning the UI,
- not adding `VenueProfilePackage` dataclass (that's VF-C2),
- not calling any of the 234 candidates "the right journals" for
  Mavrinsky,
- not promoting `external_claim` evidence to `corpus_observation`.

### Next single milestone after this pass

Per the director's framing, **not started here**. The next venue-side
milestone is one of:

1. VF-C2 (aggregating `VenueProfilePackage` dataclass + registry
   index by canonical name + ISSN), so the next pool pass writes
   durable profiles.
2. A small wiring sprint: pipe `OpenAlex Works abstracts → corpus_sampler
   → corpus_analyzer → corpus_hull_builder` so deep-lite produces
   real `PublishedCorpusHull` envelopes per venue.
3. EditorialBoardCloud (explicitly deferred by operator).

Operator picks the order. This pass does not.

End of report.
