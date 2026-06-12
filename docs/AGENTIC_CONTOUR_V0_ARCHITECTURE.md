# Agentic Contour v0.1 — Architecture

## Overview

The Agentic Contour v0.1 adds an orchestrated agent layer to Kairoskopion,
enabling the UC-1 pipeline (draft → venue pool positioning) to run as a
coordinated workflow of specialized agents.

## Layers

| Layer      | Agents | Status |
|------------|--------|--------|
| control    | 4      | operational_now |
| article    | 3      | operational_now |
| venue      | 5      | operational_now |
| fit        | 4      | operational_now (3 wrap deterministic services) |
| submission | 3      | operational_now |
| review     | 6      | contract_only (future: LLM-required) |
| evidence   | 1      | operational_now |
| **Total**  | **26** | |

## Agent Contract

All agents implement `AgentRole`:
- `execute(inp: AgentInput, provider: LLMProvider) -> AgentOutput` — LLM path
- `execute_deterministic(inp: AgentInput) -> AgentOutput` — deterministic fallback
- `run(inp, provider=None) -> AgentOutput` — auto-dispatch

## Execution Model

```
AgentTask → Executor → AgentRun → AgentResult + AgentTrace
```

The executor (`agents/executor.py`):
1. Creates AgentTask with auto-generated ID
2. Creates AgentRun tracking record
3. Dispatches to deterministic or LLM path
4. Captures result or failure
5. Returns AgentResult with full trace

## Orchestration

```
AgenticWorkflowSpec → Orchestrator → WorkflowRun → WorkflowResult + WorkflowTrace
```

The orchestrator (`agents/orchestrator.py`):
1. Iterates steps sequentially
2. Each step's output_key writes to shared entity pool
3. Steps with skip_if_missing skip gracefully when dependencies absent
4. Failures can stop or continue depending on stop_on_failure flag

## Workflows

| Workflow | Steps | Status |
|----------|-------|--------|
| direct_manuscript_venue_fit | 8 | executable |
| uc1_draft_to_venue_pool_positioning | 12 | executable |
| venue_deep_profile | 3 | executable |
| review_loop | 6 | skeleton |

## Prompt Families

16 prompt families in the catalog:
- 5 existing (article_modeling, semantic_profiling, disciplinary_mapping, fit_assessment, venue_fact_extraction)
- 11 new (scenario_interview, publication_regime, corpus_pattern_mining, citation_ecology, mismatch_mapping, rewrite_planning, risk_reporting, compliance_checklist, submission_pack, review_outcome, evidence_audit)

Each family provides: system prompt, user template, output schema, validator, evidence requirements, forbidden behaviors.

## Registry

`agents/registry.py` — 26 AgentSpec entries with:
- Layer assignment
- Implementation status (operational_now / contract_only)
- Execution mode (deterministic / llm_optional / llm_required)
- Prompt family bindings
- Input/output contracts
- Workflow membership

## CLI Commands

- `list-agents [--layer L]` — list all or filtered agents
- `inspect-agent ROLE_ID` — show agent spec as JSON
- `list-prompt-families` — list all prompt families
- `inspect-prompt-family FAMILY_ID [--full]` — show family details
- `list-workflows` — list all workflow specs
- `inspect-workflow WORKFLOW_ID` — show workflow spec as JSON
- `run-agent-workflow WORKFLOW_ID [--manuscript FILE] [--venue-json FILE] [--output FILE]` — execute workflow

## Key Design Decisions

1. **Dual execution**: Every agent has both execute() and execute_deterministic(). The executor defaults to deterministic unless LLM is explicitly requested.

2. **Service wrapping**: Operational agents wrap existing deterministic services (build_article_model, assess_fit, etc.) rather than reimplementing logic.

3. **Contract-only stubs**: Review-layer agents return explicit "not implemented" outputs with unknowns, never fake results.

4. **No fabrication**: All outputs preserve unknowns, evidence_refs, evidence_status. No synthetic data.

5. **Sequential orchestration**: v0.1 runs steps sequentially. Parallel execution is a future enhancement.

## File Map

```
agents/
├── __init__.py          — re-exports all agent classes
├── contract.py          — AgentInput, AgentOutput, AgentRole (existing)
├── runtime_models.py    — AgentSpec, AgentTask, AgentRun, AgentResult, etc.
├── base_shell.py        — service_output(), contract_only_output(), missing_input_output()
├── registry.py          — 26 AgentSpec entries + lookup functions
├── executor.py          — execute_agent() single-agent runner
├── orchestrator.py      — run_workflow() sequential orchestrator
├── workflows.py         — 4 workflow specs + registry
├── prompt_families/     — 11 new prompt family modules + catalog
├── control/             — 4 control-layer agents
├── article/             — re-exports existing article agents
├── venue/               — 5 venue-layer agents (2 existing + 3 new)
├── fit/                 — 4 fit-layer agents (1 existing + 3 new)
├── submission/          — 3 submission-layer agents
├── review/              — 6 contract-only review stubs
└── evidence/            — 1 evidence auditor agent
```
