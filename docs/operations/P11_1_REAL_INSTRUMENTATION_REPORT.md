# P11.1 Real Pipeline Instrumentation Report

**Date:** 2026-06-27
**Branch:** `feature/p11-prompt-pipeline-workbench`
**Base:** scaffold checkpoint `e2ac5f0`

## Summary

P11.1 replaces the P11.0 scaffold instrumentation with real pipeline
integration. Every stage of `ManuscriptVenueFitPipeline` now emits
`PipelineNode` and `PromptRunRecord` traces during actual execution,
not via post-hoc scaffold generation.

## What changed

### Track 1: Pipeline instrumentation (`pipelines/manuscript_venue_fit.py`)

- Constructor accepts `trace_store`, `override_store`, `case_id`.
- `execute()` creates a `TraceRun` at start, emits 18 `PipelineNode`s
  (11 executed + 7 not_applicable), and sets `result.trace_run`.
- Helper methods: `_make_node`, `_finish_node`, `_skip_node`,
  `_get_override_for`, `_record_prompt`.
- Each node gets real `output_hash` (SHA256 prefix of serialized output),
  `output_artifact_refs`, `producer_type`, and timing.

### Track 2: Prompt capture (`_record_prompt`)

- Creates `PromptRunRecord` for 3 LLM-capable stages with rendered
  system/user prompts, version hash, override ID, provider/response status.
- In deterministic-fallback mode: `provider_status="deterministic_fallback"`,
  `response_status="deterministic_output"`.

### Track 3: Override injection (`agents/contract.py`, `agents/*.py`)

- `AgentRole.run()` accepts `prompt_family_override` keyword arg, stores
  as `self._prompt_family_override`.
- `ArticleModelerAgent`, `VenueProfilerAgent`, `FitAssessorAgent` each
  copy their canonical family dict and overlay the override.
- Canonical family dicts are never mutated.

### Track 4: Rerun execution (`services/pipeline_replay.py`)

- `execute_replay_run()` for `rerun_all` with text: runs full pipeline.
- Individual stage rerun: deterministic stages declared replayable;
  LLM stages return `stage_not_yet_replayable`.

### Track 5: Compare UI (`ui/src/components/PromptPipelineWorkbench.tsx`)

- New "Compare" tab with A/B run selectors.
- Node-level diff table showing status and changed fields per stage.
- Expandable field-level diff details.
- Side-by-side prompt comparison (system + user) for LLM stages.

### Track 6: API tightening (`api/workbench.py`)

- All 3 rerun endpoints use `execute_replay_run` instead of
  `scaffold_replay_run`.
- Response includes `execution_status` and `unsupported_stages`.

### Track 7: Gold standard E2E test (`tests/test_p11_smoke.py`)

- `TestE2ERealPipelineInstrumentation` (5 tests):
  - `test_real_pipeline_emits_trace`: 10-step verification of real traces.
  - `test_override_injection_real`: override visible in trace.
  - `test_diff_real_runs`: two runs with different overrides, diff works.
  - `test_replay_rerun_stage_unsupported`: LLM stage rerun returns correct status.
  - `test_persistence_survives_reload`: traces survive store reload.
- Tests FAIL if traces are scaffold-only (checks output_hash length,
  rendered prompt content length, producer_type values).

## Files modified

| File | Change |
|------|--------|
| `src/kairoskopion/pipelines/manuscript_venue_fit.py` | Major: trace instrumentation |
| `src/kairoskopion/agents/contract.py` | `run()` accepts prompt_family_override |
| `src/kairoskopion/agents/article_modeler.py` | Override injection in execute() |
| `src/kairoskopion/agents/venue_profiler.py` | Override injection in execute() |
| `src/kairoskopion/agents/fit_assessor.py` | Override injection in execute() |
| `src/kairoskopion/services/pipeline_replay.py` | execute_replay_run() |
| `src/kairoskopion/api/workbench.py` | Real execution in rerun endpoints |
| `ui/src/components/PromptPipelineWorkbench.tsx` | Compare tab |
| `tests/test_p11_smoke.py` | Gold standard E2E (7 tests) |

## Limitations

1. Individual stage rerun for LLM stages is not yet supported (needs full
   pipeline context).
2. Compare UI does not yet highlight text-level diffs within prompts
   (shows side-by-side only).
3. No LLM execution tested (deterministic fallback only) — LLM path
   instrumented but not exercised without configured provider.
