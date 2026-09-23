# KAIRON BATCH PILOT 001 — P06/P07/F17 × three publication worlds

Status: qualification evidence only. No production authority or production write.

## Purpose

Exercise the first real multi-article batch state on top of the canonical ARTIKL.KAIRON / Kairoskopion provider split. The pilot is bounded to B0-B3 plus resume/regression acceptance: authoritative Artikl inputs, academic-world routing, local-first audit, frozen TargetWorld construction/reuse, durable scheduler state and restart/resume. Article-specific pressure generation starts after this receipt and must remain per-cell.

## Articles

1. **P06 — Bootstrapping Thinking**
   - manuscript: `gdoc:1AmpW5ZV8m_LlDKUSStWtf64SLJ_LrTQap63ZtXDya8U`
   - state: MANUSCRIPT
   - prior Kairon round-trip exists and is used as regression evidence.

2. **P07 — Position as Infrastructure**
   - manuscript: `gdoc:1RGv3XUErBx77JVIPdfJZTH1MesLcPcrRk-m67n0w-fQ`
   - state: MANUSCRIPT
   - publication object is already qualified through D24/D25.

3. **F17 — Distinguishability of the Living**
   - manuscript: `gdoc:1fSdASFbHfEj8Hj9NSSqnOYbttybHCVSYO4GutGb9fOE`
   - state: ACTIVE MANUSCRIPT
   - family identity and manuscript-bearing status are established.

F16 was intentionally excluded because its CUT/WHOLE author strategy remains explicitly open. A batch venue exercise must not turn target pressure into an implicit publication-object decision.
## Target worlds

Fresh qualification-only TargetWorld snapshots were built in an isolated VM data root. Production data and service were not modified.

### Philosophy & Technology
- path: `Anglophone → Philosophy → Philosophy of Technology → international philtech → Philosophy & Technology`
- Crossref ISSN: `2210-5433`
- corpus records: 15
- snapshot: `targetworld:philosophy_technology_batch_pilot:a5e626938d0a`
- prior local/frozen evidence: `targetworld:philosophy_technology:4a125cd4f313`
- acquisition unknowns: none.

### Techné: Research in Philosophy and Technology
- path: `Anglophone → Philosophy → Philosophy of Technology → international philtech → Techné`
- Crossref ISSN: `2691-5928`
- corpus records: 15
- snapshot: `targetworld:techne_batch_pilot:4d3e0b2a22cc`
- prior local/frozen evidence: `targetworld:techne:0823ccebcc43`
- acquisition unknowns: none.

### Эпистемология и философия науки
- path: `RF/post-Soviet → Philosophy → Epistemology/Philosophy of Science → social/digital epistemology → RU epistemology/philosophy-of-science → venue`
- Crossref ISSN: `1811-833X`
- corpus records: 15
- snapshot: `targetworld:epistemology_philosophy_science_ru_batch_pilot:9b4220736ea5`
- local evidence: repository venue evidence pack + 30-cluster Russian taxonomy
- acquisition unknowns: none.
## Matrix and local-first acceptance

The deterministic planner generated 3 × 3 = **9 BatchCell objects**. Each frozen target snapshot is referenced by exactly three article cells. TargetWorld state is reused rather than rebuilt per article.

Article-specific objects remain separate: pressure pack, transition proposal, target variant, return comparison, evidence debt and author/identity decision state.

For every target the pilot records checks of discipline registry, venue registry/evidence, TargetWorld store/frozen evidence and VenueMemory surface before external corpus refresh. Crossref acquisition happened only after these checks and produced a new frozen qualification snapshot. Prior frozen P06 snapshots were preserved.

## Resume/scheduler acceptance

New runtime layer: `src/kairoskopion/kairon_provider/batch_runtime.py`.

It adds:
- `BatchRunStore`;
- per-cell ordered stage state;
- plan fingerprint protection;
- idempotent stage completion;
- target-level work coalescing;
- article-specific work separation;
- block/failure persistence;
- deterministic restart/resume.

Stage order:
`LOCAL_RESOLUTION → TARGET_READY → PRESSURE_READY → TRANSITION_READY → MATERIALIZED → RETURN_EVALUATED → FORMAL_CHECKED → MEMORY_PERSISTED`.

Observed first run:
- local-resolution work-items: 3, one per target;
- target-ready work-items: 3, one per frozen snapshot;
- persisted batch cells: 9;
- after B0-B3: 9 × `PRESSURE_READY`;
- all nine are article-specific and non-coalesced.

Observed restart:
- `BatchRunStore` reloaded `kairon-batch-pilot-001`;
- local resolution and TargetWorld construction were not replayed;
- scheduler resumed at the same 9 × `PRESSURE_READY` cells.
## Tests

Targeted batch suites:
- `tests/test_kairon_batch.py`
- `tests/test_kairon_batch_runtime.py`
- result: **17 PASS**.

Same-environment full repository differential:
- batch-pilot branch: **3350 PASS / 5 FAIL / 8 deselected / 16 subtests PASS**;
- clean main: **3333 PASS / 5 FAIL / 8 deselected / 16 subtests PASS**.

The exact same five failures occur on clean main:
- 2 existing rubric-loader failures;
- 3 `app.routes` failures caused by the FastAPI/Starlette route-object shape in the isolated temporary environment.

Branch-specific new failures: **0**. The branch adds 17 passing tests. Production was not modified.

## Acceptance state

- B0 INPUT = PASS
- B1 WORLD = PASS for three bounded world paths
- B2 LOCAL_FIRST = PASS
- B3 TARGET = PASS with three frozen dev snapshots
- B10 RESUME = PASS
- B11 REGRESSION = PASS by same-environment differential
- B12 PROD = intentionally not attempted

Open execution front:
- 9 × `PRESSURE_READY`;
- transition proposals;
- bounded materialization where permitted;
- frozen-snapshot return pass;
- formal/package pass;
- reusable memory consolidation.

No target-specific pressure may be copied from one article cell to another.