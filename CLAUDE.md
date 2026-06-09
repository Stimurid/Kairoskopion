# CLAUDE.md — Kairoskopion (Kairon)

## What is Kairoskopion

Kairoskopion (short handle: **Kairon**) is an evidence-first publication-positioning system.
It is a bounded context within the Litops–WhiteCrow ecosystem.

**Core job:** match manuscripts/articles against academic publication containers
(journals, sections, special issues, conference proceedings) and produce
traceable, evidence-backed fit assessments, mismatch maps, adaptation plans,
risk reports and submission packs.

**Kairoskopion is NOT:**
- a journal recommender with a single fit score
- an academic writing assistant or text rewriter
- a replacement for WhiteCrow (field/manuscript) or Litops (source/provenance)
- a peer-review authority or bibliometric arbiter

## Ecosystem position

```
Litops (sources, provenance, context packs, vault)
    ↓
Kairoskopion (article models, venue models, fit, adaptation, submission)
    ↓
WhiteCrow (field, manuscript, protected core, patch queue)
```

Kairoskopion never stores raw external files (Litops's job).
Kairoskopion never directly overwrites manuscript text (creates patch candidates for WhiteCrow).

## Required reading before any refactor

Before any structural change, read in this order:
1. `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` — master spec (12665 lines, 10 waves)
2. `docs/PROJECT_STATUS.md` — current implementation state
3. `docs/ROADMAP.md` — engineering queue
4. `docs/DECISIONS.md` — architectural decisions and rationale

## What is implemented (foundation)

- 18+ dataclass domain models with `to_dict`/`from_dict`
- 22 domain enums (EvidenceStatus, FitAxisValue, FieldCoreImpact, etc.)
- 9 deterministic domain services (no LLM)
- 16-step ManuscriptVenueFitPipeline
- JSONL append-only persistence (13 registries)
- Vault markdown cards (7 entity types + pipeline trace)
- Source acquisition: local file registration, text input, URL placeholder
- Quality gates: fit gate, submission gate, evidence audit
- Operation traces with timestamps
- CLI: `status`, `run-fixture`, `inspect-storage`
- Integration stubs: Litops (5 types), WhiteCrow (6 types)

## Non-negotiable rules

### Evidence & domain
1. **Evidence-first.** Every claim must trace to a source or be marked UNKNOWN.
2. **No single fit score.** FitAssessment is always multi-axis (8 axes: topic, discipline, genre, method, citation_ecology, language_register, formal_compliance, publication_regime).
3. **Unknowns preserved.** UNKNOWN must not silently become absent. If data is missing, mark it UNKNOWN or INACCESSIBLE.
4. **No fake references.** Never fabricate citation data, DOIs, or source entries.
5. **No external API as required dependency.** The system must work fully offline with local files.
6. **No submission automation.** Kairoskopion does not submit to journals.
7. **Protected core.** Core-touching changes from WhiteCrow require explicit user acceptance.

### Code & architecture
8. **No LLM calls** until the source/evidence/persistence layer is stable and tested.
9. **No Telegram, Web UI, reviewer simulation** until explicitly requested.
10. **Do not reduce the system to one LLM prompt.**
11. **Do not rewrite the project or add new agents** without explicit request.
12. **Do not overwrite existing extraction results.**
13. **Do not delete files** without explicit request.
14. **Do not import prompts or connect LLM API** unless explicitly requested.
15. **Do not change the ДАНО/ВАРИАНТЫ/ДОЛЖНО model** (WhiteCrow concept, respected by Kairon).

### Git policy
16. **No force push.** Ever.
17. **No push to `main`** without explicit user command.
18. **No delete remote branches.**
19. **No rebase/merge remote main** automatically.
20. **No commit `node_modules`, `dist`, `.venv`, `.env` with secrets.**
21. **Do not add real API keys** to the repository.

### Test policy
22. All tests use `tmp_path` — never write to real filesystem.
23. `pytest` must pass clean before any commit.
24. New features require tests. No feature without at least one test.
25. Negative-case tests required for domain invariants.

### Architecture policy
26. Separate repo from Litops — bounded context boundary.
27. JSONL append-only registries — no SQL, no ORM.
28. Vault cards are markdown with YAML frontmatter — human-readable.
29. Pipeline steps are deterministic — same input → same output (except UUIDs/timestamps).
30. Services are stateless functions, not classes with state.

## Anti-slop rules

- Do not produce optimistic summaries. Use PASS/PARTIAL/FAIL verdicts.
- Do not hide failures behind "partially working".
- Reports must cite line numbers, code snippets, or test output as evidence.
- Do not say "implicitly done" — if it's not in the code or tests, it's not done.

## Working style

- User communicates in Russian, gives detailed multi-phase task specs.
- Expects honest verdicts with evidence.
- Values: no hidden jumps, no silent failures, no "it should work".
- Stop on true blockers (auth failure, conflict, missing spec, broken env).
- Do not stop on ordinary engineering decisions within the given frame.

## Tech stack

- Python >=3.11, setuptools
- No external runtime dependencies (dev: pytest, pytest-cov)
- Console script: `kairoskopion`
- No database — JSONL files + markdown vault
- No web framework
- No LLM SDK (yet)

## Key file locations

| File | Purpose |
|------|---------|
| `src/kairoskopion/` | Main package |
| `src/kairoskopion/schema.py` | All domain models |
| `src/kairoskopion/enums.py` | All domain enums |
| `src/kairoskopion/cli.py` | CLI entry point |
| `src/kairoskopion/pipelines/manuscript_venue_fit.py` | Main pipeline |
| `src/kairoskopion/services/` | 11 domain services |
| `src/kairoskopion/adapters/` | Source intake, URL snapshot, OpenAlex/Crossref/OpenCitations mocks, bridge |
| `src/kairoskopion/integrations/` | Litops/WhiteCrow stubs |
| `tests/` | 308+ tests |
| `tests/fixtures/` | Synthetic manuscript, venue, scenario |
| `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` | Master spec |
