# Kairoskopion — Implementation Plan

## Batch 0 — Project scaffold

- [x] README.md, pyproject.toml, .gitignore, .env.example
- [x] docs/ with spec, origin, this plan, compatibility notes

## Batch 1 — MVP-0 domain skeleton

- [x] ID generation (`ids.py`)
- [x] Enums: EvidenceStatus, LifecycleStatus, QualityGateStatus, etc. (`enums.py`)
- [x] Domain models as dataclasses (`schema.py`):
  ArticleModel, ManuscriptModel, VenueModel, PublicationRegimeModel,
  SubmissionScenario, EvidenceItem, SourceSnapshot, FitAssessment,
  MismatchMap, RewritePlan, CitationPlan, RiskReport, ComplianceChecklist,
  SubmissionPack, PipelineRun
- [x] JSONL registry: append / read / list (`registry.py`)
- [x] Evidence layer (`evidence.py`)
- [x] Quality gates (`quality.py`)
- [x] Operation traces (`traces.py`)
- [x] User decisions (`decisions.py`)
- [x] Markdown card generation (`cards.py`)
- [x] Integration stubs: Litops (`integrations/litops.py`), WhiteCrow (`integrations/whitecrow.py`)
- [x] Empty packages: services/, pipelines/, adapters/
- [x] Tests: test_schema, test_registry, test_evidence, test_quality, test_cards

## Batch 2 — Registry persistence + CLI smoke (future)

- [ ] Registry directory management (create, list registries, export)
- [ ] CLI entry point: `kairon status`, `kairon registry list`
- [ ] JSON/JSONL import/export round-trip tests
- [ ] Vault card output to filesystem

## Batch 3 — Pipeline skeleton (future)

- [ ] PipelineRun execution envelope
- [ ] Pipeline 1 stub: one manuscript × one venue
- [ ] Quality gate checks wired into pipeline
- [ ] Operation trace recording

## Batch 4 — Adapters MVP (future)

- [ ] Manual URL snapshot adapter (stub)
- [ ] File intake adapter (PDF/DOCX text extraction stub)
- [ ] OpenAlex adapter (stub with interface)
- [ ] Crossref adapter (stub with interface)

## Batch 5 — Fit Assessment logic (future)

- [ ] Multi-axis comparison engine
- [ ] MismatchMap generation
- [ ] RewritePlan generation from mismatches
- [ ] RiskReport generation

## Later batches

- Telegram intake
- Web UI
- WhiteCrow patch queue integration
- Citation ecology service
- Compliance engine
- Review loop service
- Venue pool discovery pipeline
