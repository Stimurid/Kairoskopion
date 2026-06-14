# Operator notes: Mavrinsky venue research (RU)

**Status:** operator working notes. **NOT canon. NOT gold. NOT spec.**
Real research artefact for the Mavrinsky test case (continental
philosophy of interface) used as the worked example for the Venue
Funnel v1 doctrine on the venue-discovery side.

**Why in `benchmarks/_operator_notes/` not in `private_inputs/`:**
the user requested that these notes persist across worktrees /
session resets / machine wipes. `private_inputs/` is gitignored by
project policy. This mirror is the persisted copy.

**Provenance:** every venue entry was verified live via WebFetch /
WebSearch against publisher pages, university faculty profiles, or
aggregator catalogues during 2026-06-14 session. Editor publication
traces verified via Google Scholar profiles + Истина MSU + university
profile pages. Each per-venue section names its source.

**Scope (snapshot):**
- 30-cluster taxonomy covering философия → психология + междисциплинарное
- 56-61 RU venues with verified profiles across 3 tiers
  - Tier A (top-15): full corpus + EB + Mavrinsky-fit verdict
  - Tier B: verified existence + cluster placement + metadata
  - Tier C: mentioned via editor publication trails
- 18 of 30 clusters have ≥1 verified venue (60% coverage)
- Top-5 venues with editor publication trace (≥5 items per editor,
  ≥half of operational board)

**Files in this directory:**

| File | Purpose |
|---|---|
| `mavrinsky_training_priors.md` | Original international-venue seed (training-knowledge inference). Kept for sibling-manuscript / English pathway planning. |
| `ru_cluster_taxonomy.md` | 30-cluster RU discipline skeleton |
| `ru_discovery_log.md` | Per-venue verification log: source URL, verification date, cluster placement, Tier A/B classification |
| `top15_corpus_mining.md` | Top-15 ranking with per-venue ToC samples (Соц.обозр, Praxema, НЛО, AnthroForum) and editor board extraction |
| `FINAL_REPORT_mavrinsky_ru.md` | **Consolidated final report.** 11 sections + 13 editor publication traces + 30-cluster table + VAP findings + submission strategy + cross-venue network analysis |
| `README.md` | This file |

**Relationship to canon (`docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md`):**

These notes are the worked example that the canon's funnel was
designed to support. They are NOT normative for the funnel — the
canon is. If notes and canon disagree, canon wins. Specifically:
- The 30-cluster RU taxonomy is operator-local, not part of the canon
  (which discusses funnel layers in §1, not specific discipline lists)
- The Mavrinsky-fit verdicts are operator analysis, not gold
- The top-15 ranking is operator analysis, not gold

**When VF-C2 (`VenueProfilePackage` dataclass) lands:** these venue
entries become ingestible as `VenueRecord` + `VenueClaim` +
`EditorProfile` records with proper provenance fields. This will be
the first real corpus of `VenueProfilePackage` instances. Until then
the notes live as plain markdown.

**Editor data ethics:** all editor names, affiliations, emails,
publication titles, and Google Scholar metrics were extracted from
publicly-accessible faculty profiles, university directories, journal
about-pages, or open Google Scholar profiles. No private databases
were accessed; no contact emails were used; no email addresses are
displayed except where they appear as the editor's own public
self-published contact (Baiburin EUSP page).

**Coverage gaps (as of this snapshot):**

Clusters NOT yet covered or only overlap-covered:
- cl.4 Философия культуры (overlap via Логос)
- cl.8 Постструктурализм / французская мысль (overlap via Логос/НЛО)
- cl.9 Культурология общая (overlap via Соц.обозр/Артикульт)
- cl.11 История идей / интеллектуальная история
- cl.18 Социология культуры (overlap via Соц.обозр)
- cl.19 Социология знания
- cl.26 STS interdisciplinary umbrella

Venues blocked by infrastructure (403/404/ECONNREFUSED):
- Stasis editorial board beyond Magun
- Praxema editorial board
- Социология власти full editorial board (RANEPA pages down)
- Some Filippov / Bankovskaya / Turchik publication titles
