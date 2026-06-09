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

## Agent operating loop

Before any work, read in this order:
1. This `CLAUDE.md` — rules, boundaries, anti-slop
2. `docs/PROJECT_STATUS.md` — current implementation state
3. `docs/SPEC_COVERAGE_MATRIX.md` — what spec requires vs what exists
4. `docs/BACKLOG.md` — concrete sprint packages with scope/tests/acceptance
5. `docs/MILESTONES.md` — version targets

Then:
- Choose next sprint **only from BACKLOG** unless user overrides
- Implement on a feature branch (`feature/sprint-name`)
- Run `pytest` before and after
- Update: PROJECT_STATUS, ROADMAP, SPEC_COVERAGE_MATRIX, CLAUDE.md (test count, commands)
- Never silently mark stubs as complete
- Commit, push feature branch, report

For deep spec questions, read:
- `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` — master spec (12665 lines, 10 waves)
- `docs/DECISIONS.md` — architectural decisions and rationale

## What is implemented (foundation)

- 18+ dataclass domain models with `to_dict`/`from_dict`
- 23 domain enums (EvidenceStatus, FitAxisValue, FieldCoreImpact, etc.)
- 13 deterministic domain services (no LLM)
- 18-step ManuscriptVenueFitPipeline
- JSONL append-only persistence (17+ registries)
- Vault markdown cards (8 entity types + pipeline trace)
- Source acquisition: local file registration (.md, .txt, .json, .html, .pdf, .docx), text input, URL placeholder
- PDF extraction (pypdf), DOCX extraction (python-docx) — optional deps
- Quality gates: fit gate, submission gate, evidence audit
- Operation traces with timestamps
- Real optional adapters: OpenAlex, Crossref, OpenCitations with HTTP caching and rate limiting (mock default)
- Multi-source venue profiling from local files
- Bibliography multi-style parsing (APA, numbered, Vancouver, Chicago)
- Publication trajectory reports
- Submission pack preparation with readiness assessment
- Litops compatibility bridge (export-litops-pack)
- WhiteCrow patch queue bridge (export-whitecrow-patches)
- CLI: 14 commands (`status`, `run-fixture`, `run-local`, `adapters-smoke`, `vault-index`, `export-bundle`, `import-bundle`, `validate-bundle`, `inspect-storage`, `intake-file`, `build-venue-profile`, `build-submission-pack`, `export-litops-pack`, `export-whitecrow-patches`)
- Integration: Litops bridge (JSONL export), WhiteCrow bridge (patch queue export)

## Non-negotiable rules

### Evidence & domain
1. **Evidence-first.** Every claim must trace to a source or be marked UNKNOWN.
2. **No single fit score.** FitAssessment is always multi-axis (12 axes: topic, discipline, genre, argument_structure, method, citation_ecology, novelty_positioning, language_register, audience, formal_compliance, author_eligibility, publication_regime).
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
| `src/kairoskopion/services/` | 13 domain services |
| `src/kairoskopion/adapters/` | Source intake (PDF/DOCX), URL snapshot, OpenAlex/Crossref/OpenCitations (mock+real), HTTP client, bridge |
| `src/kairoskopion/integrations/` | Litops bridge, WhiteCrow bridge, stubs |
| `src/kairoskopion/vault.py` | Vault indexes, manifest, cross-linking, link validation |
| `src/kairoskopion/exchange.py` | Export/import storage bundles (zip) |
| `src/kairoskopion/freshness.py` | Freshness/staleness tracking |
| `tests/` | 556+ tests |
| `tests/fixtures/` | Synthetic manuscript, venue, scenario |
| `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` | Master spec |
