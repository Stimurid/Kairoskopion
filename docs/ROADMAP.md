# Roadmap — Kairoskopion

Engineering queue. Each item is a concrete deliverable, not an aspiration.

## Foundation (complete)

### MVP-0 Domain skeleton
- [x] 18+ dataclass models, 22 enums, JSONL registry
- [x] Evidence layer, quality gates, operation traces, user decisions
- [x] 7 markdown card generators
- [x] Litops/WhiteCrow integration stubs
- [x] Pipeline base class

### Fixture pipeline
- [x] Synthetic fixtures: manuscript, venue guidelines, submission scenario
- [x] 9 domain services (deterministic, no LLM)
- [x] ManuscriptVenueFitPipeline (16 steps)
- [x] Markdown artifact generation

### Persistence + vault + CLI
- [x] JSONL persistence (13 registries)
- [x] Vault filesystem (8 subdirs, markdown cards)
- [x] CLI: status, run-fixture, inspect-storage
- [x] Storage root via flag/env

### Source acquisition skeleton
- [x] Local file registration with content hash
- [x] Text input registration
- [x] URL snapshot placeholder (no fetch)
- [x] 14 source roles
- [x] Evidence creation from source

### Repository operating layer
- [x] CLAUDE.md with agent instructions
- [x] PROJECT_STATUS.md, ROADMAP.md, DECISIONS.md, OPERATOR_MANUAL.md
- [x] Remote-safe push to GitHub

## Next sprint: real-file pipeline

**Goal:** `kairoskopion run-local --manuscript FILE --venue-guidelines FILE --scenario FILE`

- [ ] CLI command `run-local` accepting local file paths
- [ ] Source registration wired into pipeline steps
- [ ] SourceSnapshot + EvidenceItem created per input file
- [ ] Pipeline runs on arbitrary user-provided files
- [ ] Vault artifacts and JSONL registries from real files
- [ ] Tests: local files, missing file errors, unsupported extensions
- [ ] OPERATOR_MANUAL update

## Then: citation ecology stub

- [ ] Bibliography parsing from manuscript text
- [ ] CitationPlan service with reference bridge detection
- [ ] Venue citation expectation profile stub
- [ ] Reference count / style analysis

## Then: external adapter stubs

- [ ] OpenAlex adapter stub with mock responses
- [ ] Crossref DOI lookup stub with mock responses
- [ ] OpenCitations stub
- [ ] Adapter tests with mocked data
- [ ] SourceSnapshot creation from adapter results

## Then: enhanced vault

- [ ] Vault card cross-linking (fit -> article + venue)
- [ ] JSON export/import for registries
- [ ] Timeline/freshness tracking
- [ ] Staleness detection

## Then: integration bridges

- [ ] Litops compatibility bridge (source registration API, ContextPack, Artifact export)
- [ ] WhiteCrow patch queue bridge (ProtectedCore import, PatchCandidate export)
- [ ] Vault sync with Litops Vault (Obsidian)

## Later (only when explicitly requested)

- [ ] LLM-assisted article modeling
- [ ] LLM-assisted venue profiling
- [ ] Telegram intake layer
- [ ] Web UI
- [ ] Reviewer risk simulation (controlled, labeled)
- [ ] Venue pool discovery
- [ ] Submission portal profiles
- [ ] Multi-venue comparison pipeline
