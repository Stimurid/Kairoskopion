# P11.1 Acceptance Checklist

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | Each pipeline stage creates PipelineNode with real metadata | YES | `test_real_pipeline_emits_trace` steps 3-5: 18 nodes, output_hash 16 chars, producer_type set |
| 2 | PromptRunRecord captures rendered prompts for LLM stages | YES | `test_real_pipeline_emits_trace` steps 6-7: records exist with >50 char system prompts |
| 3 | PromptOverride injects into agent prompt without mutating canonical | YES | `test_override_injection_real`: "CUSTOM article modeler" in rendered prompt, canonical unchanged |
| 4 | Rerun executes real pipeline (rerun_all) | YES | `execute_replay_run` with text runs `ManuscriptVenueFitPipeline`, returns status="executed" |
| 5 | Individual stage rerun for LLM stages returns correct status | YES | `test_replay_rerun_stage_unsupported`: status="partial_not_replayable" |
| 6 | Compare UI shows A/B run selector and node-level diff | YES | `PromptPipelineWorkbench.tsx` Compare tab with selectors, diff table, prompt comparison |
| 7 | API endpoints use real execution | YES | `workbench.py` all 3 rerun endpoints call `execute_replay_run` |
| 8 | Gold standard E2E test fails on scaffold-only traces | YES | Test checks output_hash length==16, prompt content >50 chars, producer_type values |
| 9 | Traces persist and survive store reload | YES | `test_persistence_survives_reload`: reload from disk, verify 18 nodes + prompt records |
| 10 | Run diff works across two real runs | YES | `test_diff_real_runs`: diff detects prompt_override_id change |
| 11 | TypeScript compiles clean | YES | `npx tsc --noEmit` — no errors |
| 12 | All tests pass | PENDING | Full pytest run required |
| 13 | No main merge | YES | Branch: feature/p11-prompt-pipeline-workbench |
| 14 | No force push | YES | — |
| 15 | No paid LLM/API called | YES | Deterministic fallback only |
