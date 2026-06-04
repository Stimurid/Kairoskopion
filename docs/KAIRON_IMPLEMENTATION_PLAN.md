# Kairoskopion — Implementation Plan

## Completed

### Batch 0 — Project scaffold
- [x] README.md, pyproject.toml, .gitignore, .env.example
- [x] docs/ with spec (12665 lines, 10 waves), origin, this plan, compatibility

### Batch 1 — MVP-0 domain skeleton
- [x] ID generation, 22 domain enums, 18+ dataclass models
- [x] JSONL registry (append/read/list/find)
- [x] Evidence layer, quality gates, operation traces, user decisions
- [x] Markdown card generators (7 entity types)
- [x] Integration stubs: Litops (5 types), WhiteCrow (6 types)
- [x] Pipeline base class
- [x] Tests: schema, registry, evidence, quality, cards, fixtures, invariants

### Audit Pass
- [x] 18 negative-case tests (SubmissionPack gate, CitationPlan invariants,
      FitAssessment evidence prereqs, unknowns/evidence preservation)
- [x] Fixtures with spec §158 acceptance criteria
- [x] Pipeline base class

### Batch 2 — Fixture pipeline
- [x] Synthetic fixtures: manuscript, venue guidelines, submission scenario
- [x] 9 domain services: article modeling, venue profiling, scenario,
      fit assessment, mismatch mapping, rewrite planning, risk reporting,
      compliance, evidence audit
- [x] ManuscriptVenueFitPipeline: 16-step deterministic pipeline
- [x] Markdown artifact generation

### Batch 3 — Persistence + vault + CLI
- [x] JSONL persistence: 13 registry files, append/read/list
- [x] Vault filesystem: 8 subdirs, markdown cards for all key entities
- [x] CLI: status, run-fixture, inspect-storage
- [x] Storage root via --storage-root flag and KAIROSKOPION_STORAGE_ROOT env

### Sprint — Source acquisition + integration
- [x] Source intake adapter: local file registration, evidence creation,
      text input registration, 14 source roles
- [x] URL snapshot placeholder: INACCESSIBLE status, no real fetch
- [x] Additional vault card writers: ComplianceChecklist, MismatchMap
- [x] inspect-storage CLI command
- [x] Documentation update

## Current state

- 215+ tests, all passing
- Full local pipeline: fixtures -> services -> entities -> persistence -> vault
- CLI operational: status, run-fixture, inspect-storage
- No network dependencies, no LLM calls
- Source acquisition contract ready for adapter expansion

## Next batches (not started)

### Batch N+1 — Adapter expansion
- [ ] OpenAlex adapter stub with mock responses
- [ ] Crossref DOI lookup stub with mock responses
- [ ] OpenCitations stub
- [ ] Adapter tests with mocked responses
- [ ] Source acquisition quality gate
- [ ] SourceSnapshot + EvidenceItem creation from adapter results

### Batch N+2 — Pipeline from real files
- [ ] Pipeline accepts arbitrary manuscript + guidelines file paths
- [ ] Pipeline run from CLI with --manuscript and --venue args
- [ ] Source registration wired into pipeline steps
- [ ] Multiple venue comparison (light profiles)

### Batch N+3 — Citation ecology stub
- [ ] CitationPlan service with reference bridge detection
- [ ] Bibliography parsing from manuscript
- [ ] Venue citation expectation profile stub
- [ ] Reference verification stub (Crossref DOI check)

### Batch N+4 — Enhanced vault
- [ ] Vault search/navigation
- [ ] JSON export/import for registries
- [ ] Vault card cross-linking (fit -> article + venue)
- [ ] Timeline/freshness tracking

### Later
- [ ] Telegram intake layer
- [ ] Web UI
- [ ] WhiteCrow patch queue integration
- [ ] Real LLM-assisted article modeling
- [ ] Reviewer risk simulation (controlled, labeled)
- [ ] Venue pool discovery
- [ ] Submission portal profiles
