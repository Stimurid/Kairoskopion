# Agentic Contour v0.1 — Implementation Report

**Date**: 2026-06-12
**Branch**: `feature/agentic-contour-uc1-v01`
**Base**: `v0.2.0-alpha-rc7` (commit `bd035d4`)

## Scope

Implement the UC-1 Orchestrated Layer: a complete agentic workflow from
draft input through venue pool positioning to evidence-audited report.

## Deliverables

### Phase 1-3: Runtime Models + Enums + IDs
- 7 new enums in `enums.py` (AgentLayer, AgentExecutionMode, etc.)
- 7 new ID factories in `ids.py`
- 13 runtime dataclasses in `agents/runtime_models.py`
- Full `_DictMixin` serialization for all models

### Phase 4: Prompt Families
- 11 new prompt family modules in `agents/prompt_families/`
- Catalog aggregating all 16 families (5 existing + 11 new)
- Each family: system prompt, user template, output schema, validator

### Phase 5: Agent Registry
- `agents/registry.py` with 26 AgentSpec entries
- Lookup by role_id, layer filtering, class instantiation
- Every spec has matching agent class

### Phase 6: Agent Shells (26 total)
- **Control** (4): IntentClassifier, ScenarioProber, ResearchPlanner, StatusJob
- **Article** (3): existing ArticleModeler, SemanticProfiler, DisciplinaryMapper
- **Venue** (5): existing VenueProfiler + VenueIdentifier, VenueDiscovery, PublicationRegimeClassifier, VenuePublicationProfileBuilder
- **Fit** (4): existing FitAssessor + MismatchMapper, RewritePlanner, CitationPlanner
- **Submission** (3): RiskOfficer, ComplianceAuditor, SubmissionPackBuilder
- **Review** (6): all contract-only stubs
- **Evidence** (1): EvidenceAuditor

### Phase 7: Base Shell Utilities
- `base_shell.py`: service_output(), contract_only_output(), missing_input_output()

### Phase 8: Executor + Orchestrator
- `executor.py`: single-agent execution with task/run/trace tracking
- `orchestrator.py`: sequential workflow execution with entity pool

### Phase 9: Workflow Specs
- 4 workflows: direct_manuscript_venue_fit (8 steps), uc1_draft_to_venue_pool_positioning (12 steps), venue_deep_profile (3 steps), review_loop (6 steps, skeleton)

### Phase 10: CLI Commands
- 7 new commands: list-agents, inspect-agent, list-prompt-families, inspect-prompt-family, list-workflows, inspect-workflow, run-agent-workflow

### Phase 11: Tests
- 6 new test files, 76 new tests
- All 782 tests passing (was 706 before this pass)

### Phase 12: Documentation
- AGENTIC_CONTOUR_V0_ARCHITECTURE.md
- AGENTIC_CONTOUR_V0_REPORT.md (this file)

## What's NOT included (by design)

- No LLM execution paths exercised (deterministic-only in v0.1)
- Review layer is contract-only (6 stubs, all return explicit unknowns)
- No parallel orchestration (sequential only)
- No web crawling or live network calls
- No fabricated venue data or synthetic recommendations

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| test_agentic_runtime_models.py | 17 | PASS |
| test_agent_registry.py | 16 | PASS |
| test_agent_shells.py | 18 | PASS |
| test_agent_executor.py | 5 | PASS |
| test_agent_workflows.py | 10 | PASS |
| test_agentic_cli.py | 10 | PASS |
| **Total new** | **76** | **PASS** |
| **Full suite** | **782** | **PASS** |

## Files Created/Modified

### New files (40+)
- `agents/runtime_models.py`
- `agents/base_shell.py`
- `agents/registry.py`
- `agents/executor.py`
- `agents/orchestrator.py`
- `agents/workflows.py`
- `agents/prompt_families/` — 12 files (11 families + catalog)
- `agents/control/` — 5 files
- `agents/article/__init__.py`
- `agents/venue/` — 5 files
- `agents/fit/` — 4 files
- `agents/submission/` — 4 files
- `agents/review/` — 7 files
- `agents/evidence/` — 2 files
- 6 test files
- 2 doc files

### Modified files
- `enums.py` — 7 new enums
- `ids.py` — 7 new ID factories
- `agents/__init__.py` — re-exports all new agents
- `cli.py` — 7 new commands + subparsers
