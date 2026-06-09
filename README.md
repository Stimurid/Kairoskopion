# Kairoskopion

Evidence-first publication-positioning system.

Kairoskopion (formerly Journal-Yuga / Venue-Fit Engine) is a bounded context
within the Litops-WhiteCrow ecosystem.  It matches fields, manuscripts and
articles against academic publication containers — journals, sections, special
issues, conference proceedings — and produces traceable, evidence-backed fit
assessments, mismatch maps, adaptation plans, risk reports and submission packs.

## Core formula

```
Field / Idea / Draft / Manuscript / ArticleModel
x
VenueModel / JournalModel / IssueModel / SectionModel / PublicationRegimeModel
x
SubmissionScenario
->
FitAssessment -> MismatchMap
->
RewritePlan / ReframePlan / CitationPlan / RiskReport
->
SubmissionPack / WhiteCrow Patch Queue / External Document Actions / VenueMemory
```

## What Kairoskopion is NOT

- Not a journal recommender with a single fit score
- Not an academic writing assistant or text rewriter
- Not a replacement for WhiteCrow (field/manuscript layer) or Litops (source/provenance layer)
- Not a peer-review authority or bibliometric arbiter

## Project status

**First usable local product build.**

Working pipeline: manuscript + venue guidelines + submission scenario
-> ArticleModel, VenueModel, FitAssessment (8 axes), MismatchMap, RewritePlan,
RiskReport, ComplianceChecklist, BibliographyProfile, CitationEcologyReport,
OperationTrace, QualityGates, markdown artifacts.

Results persist to JSONL registries and markdown vault cards on disk.

No LLM calls, no external API dependencies, no network access.

## Quick start

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Run fixture pipeline (persists to .kairoskopion/)
kairoskopion run-fixture

# Or with a custom storage root
kairoskopion run-fixture --storage-root /tmp/kairon_test

# Run on your own files
kairoskopion run-local \
  --manuscript my_paper.md \
  --venue-guidelines journal_guidelines.md \
  --scenario scenario.json

# Check environment
kairoskopion status

# Inspect stored results
kairoskopion inspect-storage
```

## CLI commands

| Command | Description |
|---------|-------------|
| `kairoskopion status` | Show version, working directory, storage root, registry/vault existence |
| `kairoskopion run-fixture` | Run fixture pipeline, persist JSONL registries + vault cards, print summary |
| `kairoskopion run-local` | Run pipeline on user-provided manuscript + venue guidelines + scenario files |
| `kairoskopion inspect-storage` | Show all registries (record counts, entity IDs) and vault card files |

Use `--storage-root PATH` or env var `KAIROSKOPION_STORAGE_ROOT` to override default `.kairoskopion/` storage.

## Storage layout

```
.kairoskopion/
  registries/
    article_models.jsonl
    manuscripts.jsonl
    venue_models.jsonl
    publication_regimes.jsonl
    submission_scenarios.jsonl
    fit_assessments.jsonl
    mismatch_maps.jsonl
    rewrite_plans.jsonl
    risk_reports.jsonl
    compliance_checklists.jsonl
    pipeline_runs.jsonl
    operation_traces.jsonl
    quality_gates.jsonl
  vault/
    articles/    {article_model_id}.md
    venues/      {venue_model_id}.md
    fits/        {fit_assessment_id}.md
    risks/       {risk_report_id}.md
    compliance/  {compliance_checklist_id}.md
    mismatches/  {mismatch_map_id}.md
    submissions/
    traces/      {pipeline_run_id}.md
```

## Architecture

```
src/kairoskopion/
  __init__.py          — package, version
  ids.py               — UUID-based entity ID generation
  enums.py             — 22 domain enums (EvidenceStatus, LifecycleStatus, ...)
  schema.py            — 18+ dataclass models with to_dict/from_dict
  registry.py          — JSONL append/read/list/find
  persistence.py       — storage root management, pipeline result persistence
  artifacts.py         — vault markdown card filesystem output
  evidence.py          — evidence layer helpers
  quality.py           — quality gate evaluators (fit gate, submission gate)
  traces.py            — operation trace recording
  decisions.py         — user decision tracking
  cards.py             — markdown card generators (7 entity types)
  cli.py               — CLI: status, run-fixture, inspect-storage

  services/
    article_modeling.py  — ManuscriptModel + ArticleModel from text
    venue_profiling.py   — VenueModel + PublicationRegimeModel from guidelines
    scenario.py          — SubmissionScenario from user input
    fit_assessment.py    — multi-axis fit comparison
    mismatch_mapping.py  — MismatchMap from weak/bad axes
    rewrite_planning.py  — RewritePlan action list
    risk_reporting.py    — RiskReport covering 7+ risk types
    compliance.py        — ComplianceChecklist from guidelines
    evidence_audit.py    — evidence coverage quality gate

  pipelines/
    base.py                  — PipelineBase lifecycle
    manuscript_venue_fit.py  — one manuscript x one venue pipeline

  adapters/
    source_intake.py    — local file/text source registration
    url_snapshot.py     — URL placeholder (no real fetch in MVP)

  integrations/
    litops.py           — Litops compatibility stubs
    whitecrow.py        — WhiteCrow compatibility stubs
```

## Licence

Private — not yet published.
