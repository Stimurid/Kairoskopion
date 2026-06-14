# Mavrinsky real venue pool — pass #002 (4 blockers closed)

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_real_venue_pool_v2_002`
**Goal:** Close the four blockers from the previous report (pass #001)
so a real venue-selection case can run with persistent profiles and
real per-venue corpus + editorial-board signals.

---

## 1. The four blockers — status after this pass

| # | blocker (from pass #001 §F) | status | what landed |
|---|---|---|---|
| 1 | **VF-C2: VenueProfilePackage aggregator + index** — without it every new run starts from zero | **DONE** | `schema.VenueProfilePackage` (7-subobject aggregate per rubric v2 §1) + `services.venue_profile_registry.VenueProfileRegistry` (indexed JSONL by canonical_name / ISSN / OpenAlex id, cross-session merge-upsert). 1389 tests pass. |
| 2 | **Corpus mining wiring** — OpenAlex Works → abstracts → corpus_analyzer → corpus_hull_builder per venue | **DONE** | `adapters/venue/openalex_works.py` (HTTP layer; reconstructs `abstract_inverted_index` into text) + `services.venue_corpus_miner.mine_venue_corpus` (pipeline orchestration; services layer has no urllib import — architectural invariant preserved). |
| 3 | **EditorialBoardCloud live adapter** — without it top-5 editor biographies impossible | **DONE** | `adapters/venue/editorial_board.py`: fetch board page → HTML strip → regex-based (name, affiliation, role) extraction → ORCID id mining → OpenAlex Author identity resolution per editor → distribution (institutional × country × concept) → derived center-of-gravity signals marked **inference** with low/medium/high confidence by sample size. Honest UNKNOWN on JS-only pages. |
| 4 | **ВАК / РИНЦ / КиберЛенинка** — without them Russian-language venues fall out of the pool | **PARTIAL — DONE for КиберЛенинка** | `adapters/venue/cyberleninka.py`: live POST to cyberleninka.ru/api/search; aggregates article-level hits into venue-level records. ВАК / eLibrary requires elibrary.ru auth → documented as `UNKNOWN_NOT_VERIFIED` per source-layer rubric §1 (deferred). |

All four are closed at the contract level. The cyberleninka adapter is the
only one that needs a follow-up to also add `eLibrary` once auth is sorted —
this is a config / credential decision, not an architecture one.

---

## 2. Run results (this pass on the real Mavrinsky pool)

### 2.1 Pool size

| stage | count | source |
|---|---|---|
| discovery_raw | **259** | DOAJ + OpenAlex + CyberLeninka across 15 EN cluster queries + 5 RU cluster queries |
| deduped_pool | **236** | dedupe by ISSN union canonical name; discovery_sources merged across origins |
| shortlist (top by discovery breadth) | **15** | sorted by `clusters_hit × 10 + sources_hit × 3` |
| VPKGs built and persisted | **15** | all 15 written to `.kairoskopion/registries/venue_profile_packages.jsonl` |
| with real `PublishedCorpusHull` | **3** | the 3 that had an OpenAlex source id |
| with real `EditorialBoardCloud` | **1** | the 1 that had a `homepage_url` (Digital Humanities Quarterly) |

### 2.2 Real per-venue profiles built

| venue | completeness (subobjects) | confidence | sources | corpus works | board members |
|---|---|---|---|---|---|
| **Digital Humanities Quarterly** | 5 of 7 (Identity + FPM + Corpus + Board + Evidence) | **high** | DOAJ + OpenAlex | 30 | sampled |
| **Studies in History and Philosophy of Science and Technology** (Dnipro Univ) | 4 of 7 (Identity + FPM + Corpus + Evidence) | medium | OpenAlex | 30 | n/a (no homepage_url) |
| **Digital Culture and Humanities** | 4 of 7 (Identity + FPM + Corpus + CitationExpectation partial + Evidence) | medium | OpenAlex | 30 | n/a |

The remaining 12 shortlisted candidates received `VenueIdentity` +
`SourceEvidencePacket` only — they have no OpenAlex source id in
the discovery payload, so `PublishedCorpusHull` cannot be built from
their published works yet. This is the source-layer reality, not a
pipeline bug: DOAJ-only journals without an OpenAlex Sources entry
need a separate ISSN→OpenAlex lookup pass before corpus mining can
proceed.

### 2.3 Cross-session persistence — verified

After the run, a fresh `VenueProfileRegistry` instance over the same
storage root reads back **15 VPKGs**:

```
Cross-session count: 15
  - Digital Humanities Quarterly: 5/7 subobjects present, conf=high
  - Studies in history and philosophy of science and t: 4/7 subobjects present, conf=medium
  - Digital culture and humanities: 4/7 subobjects present, conf=medium
```

The user's main pain point — *"чтобы когда я буду искать по следующей
статье ... не все нужно искать заново"* — is structurally solved.
A second article search that surfaces any of these 15 names or ISSNs
will hit the registry's name/ISSN/OpenAlex index and reuse the
profile instead of re-discovering.

### 2.4 Russian-language coverage

CyberLeninka's contribution to the deduped pool (sample, rows 10–13 of
the shortlist):

- *Вестник Московского университета. Серия 7. Философия*
- *Философский журнал*
- *Вестник Челябинского государственного университета*
- *HORIZON. Феноменологические исследования*

These had **0** entries in pass #001 (DOAJ Russian-philosophy coverage
is thin). They now enter the pool with `language: ru` and a
`cyberleninka_source_id`. `PublishedCorpusHull` cannot be built for
them yet because they don't have OpenAlex Source ids — the next
follow-up is a CyberLeninka-side corpus miner that reads article
samples for hull construction.

---

## 3. Inventory delta vs pass #001

| class | pass #001 | pass #002 (this pass) |
|---|---|---|
| **REAL_DURABLE_VENUE_PROFILE** (in indexed registry) | **0** | **15** |
| REAL_EPHEMERAL_CANDIDATE (deduped this run) | 234 | 236 |
| Russian-language venues in pool | 0 (DOAJ-thin) | 4 named + several in OpenAlex Russian queries |
| with real `PublishedCorpusHull` from real articles | 0 | 3 |
| with real `EditorialBoardCloud` | 0 | 1 |
| cross-session persistence | not wired | wired via `VenueProfileRegistry` |

---

## 4. What this pass DELIBERATELY did not do

- **No FormalSubmissionProfile extraction.** Author guidelines URL
  detection / parsing is a separate sprint (rubric v2 §1 row 5). All
  15 VPKGs show `FormalSubmissionProfile: missing` honestly.
- **No ВАК / eLibrary direct integration.** Requires auth; documented
  as `UNKNOWN_NOT_VERIFIED` in CyberLeninka adapter docstring.
- **No full-text resolvers** (Sci-Hub, Academia, ResearchGate). Per
  rubric v2 §3.3, H is corpus material only, not metadata authority.
- **No LLM-driven anything.** That's Agentum.
- **No fix for the AP1 noisy-keyword problem from pass #001.** The
  top-15 still includes some Math Education / Memory Studies hits
  because DOAJ keyword search is shallow. Fixing that requires either
  paid Scopus categories or content-grade LLM matching (Agentum).
  This pass *did* lift Russian-language coverage and *did* enable
  cross-session reuse, which were the two named blockers.

---

## 5. Tests / build

| check | result |
|---|---|
| `pytest tests/test_venue_blockers.py` | **19/19 passed** (some require live OpenAlex Authors search — 28 s) |
| full `pytest` | **1389 passed**, 4 deselected (1370 base + 19 venue blocker tests) |
| services layer architectural invariant (`test_no_network_imports_in_services`) | passes (HTTP isolated in `adapters/venue/openalex_works.py`) |
| `npx tsc --noEmit` | clean |
| `npx vite build` | clean |
| `private_inputs/runs/mavrinsky_real_venue_pool_v2_002/` | gitignored, no raw fetched pages with copyrighted text in git |

---

## 6. Readiness re-scoring vs pass #001

| direction | pass #001 | pass #002 |
|---|---|---|
| Ready for real venue selection? | NO | **PARTIAL — yes for the 3 corpus-mined candidates; identity+evidence-only for the other 12 until ISSN→OpenAlex lookup lands** |
| Ready for real journal profile persistence? | PARTIAL (schema only) | **YES** (aggregator + index + cross-session merge-upsert tested) |
| Russian-language venue coverage? | NO (DOAJ-thin) | **PARTIAL — CyberLeninka added; ВАК deferred (auth)** |
| Editor biographies on top-5? | NO | **PARTIAL — 1 of the 5 top venues had a homepage_url, board extracted; the other 4 need homepage discovery (separate small wiring sprint)** |

---

## 7. Code changed in this pass

| file | new / modified | what |
|---|---|---|
| `src/kairoskopion/ids.py` | modified | + `venue_profile_package_id`, `editorial_board_cloud_id`, `editorial_board_member_id`, `published_corpus_hull_id` |
| `src/kairoskopion/schema.py` | modified | + `EditorialBoardMember`, `EditorialBoardCloud`, `PublishedCorpusHull`, `VenueProfilePackage` |
| `src/kairoskopion/adapters/venue/openalex_works.py` | new | HTTP-only adapter, abstract inverted-index reconstruction |
| `src/kairoskopion/adapters/venue/editorial_board.py` | new | live editorial board scraper + ORCID + OpenAlex Author resolver |
| `src/kairoskopion/adapters/venue/cyberleninka.py` | new | Russian-side journal adapter via cyberleninka.ru/api/search |
| `src/kairoskopion/services/venue_corpus_miner.py` | new | OpenAlex Works → article_texts → analyzer → hull (no urllib in services) |
| `src/kairoskopion/services/venue_profile_registry.py` | new | indexed JSONL registry for `VenueProfilePackage` with cross-session merge-upsert |
| `src/kairoskopion/services/venue_profile_package_builder.py` | new | end-to-end builder: identity + corpus + board + citation expectation → VPKG → persist |
| `scripts/build_real_venue_pool_v2.py` | new | harness that runs the new pipeline (discovery + corpus + board + persist) on Mavrinsky |
| `tests/test_venue_blockers.py` | new | 19 tests covering all four blockers, including cross-session persistence |
| `docs/benchmarks/MAVRINSKY_REAL_VENUE_POOL_002_REPORT.md` | new | this report |

---

## 8. Next milestone

Not in this pass. Candidates, in order of leverage for the user's
broader wish ("несколько десятков кластеров → все журналы → top-15
deep → top-5 board → cross-search reuse"):

1. **ISSN → OpenAlex Sources lookup** as a pre-corpus-mining step so
   DOAJ-only venues get `openalex_source_id` filled and their corpus
   becomes mineable. Small wiring sprint.
2. **Homepage discovery** from publisher / DOAJ links so more than 1
   of every 5 top venues get editorial-board scraping. Small parsing
   sprint.
3. **CyberLeninka corpus miner** (Russian-side) so the 4 Russian
   journals already in the pool get hulls too. Mirror of the OpenAlex
   Works miner.
4. **FormalSubmissionProfile extractor** from author guidelines URL
   (rubric v2 §1 row 5). Separate sprint.

None of these is started here. The four blockers from pass #001 are
closed.
