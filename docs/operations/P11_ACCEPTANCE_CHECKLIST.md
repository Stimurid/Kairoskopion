# P11 Acceptance Checklist

| # | Requirement | Status | Evidence |
|---|------------|--------|----------|
| 1 | Prompt registry discovers all families | PASS | `test_prompt_registry.py::test_scan_real_prompts` — 18+ families found |
| 2 | Version hash computed per family | PASS | `test_prompt_registry.py::test_version_hash_deterministic` |
| 3 | System/user prompts extractable | PASS | `test_prompt_registry.py::test_synthetic_prompt_file` |
| 4 | PipelineRun model with to_dict/from_dict | PASS | `test_pipeline_trace.py::TestPipelineRun::test_roundtrip` |
| 5 | PipelineNode model with all fields | PASS | `test_pipeline_trace.py::TestPipelineNode::test_roundtrip` |
| 6 | PromptRunRecord model | PASS | `test_pipeline_trace.py::TestPromptRunRecord::test_roundtrip` |
| 7 | JSONL persistence for traces | PASS | `test_pipeline_trace.py::TestPipelineTraceStore::test_persistence_roundtrip` |
| 8 | 18 pipeline stages defined | PASS | `test_pipeline_replay.py::TestStageDefinitions::test_18_stages` |
| 9 | plan_rerun_all | PASS | `test_pipeline_replay.py::TestReplayPlans::test_rerun_all` |
| 10 | plan_rerun_stage | PASS | `test_pipeline_replay.py::TestReplayPlans::test_rerun_single_stage` |
| 11 | plan_rerun_from_stage | PASS | `test_pipeline_replay.py::TestReplayPlans::test_rerun_from_stage` |
| 12 | scaffold_replay_run copies base | PASS | `test_pipeline_replay.py::TestScaffoldReplayRun::test_scaffold_copies_base_results` |
| 13 | diff_runs detects changes | PASS | `test_pipeline_replay.py::TestDiffRuns::test_diff_changed_hash` |
| 14 | PromptOverride CRUD | PASS | `test_prompt_override.py::TestPromptOverrideStore` (5 tests) |
| 15 | PromptPatchCandidate CRUD | PASS | `test_prompt_override.py::TestPromptPatchCandidate` |
| 16 | Active override lookup | PASS | `test_prompt_override.py::TestPromptOverrideStore::test_active_override_lookup` |
| 17 | API: GET /api/prompts | PASS | `test_workbench_api.py::TestPromptEndpoints::test_list_prompts` |
| 18 | API: rerun endpoints (3) | PASS | `test_workbench_api.py::TestPipelineRunEndpoints` (7 tests) |
| 19 | API: override endpoints (3) | PASS | `test_workbench_api.py::TestPromptOverrideEndpoints` (4 tests) |
| 20 | API: diff endpoint | PASS | `test_workbench_api.py::TestPipelineDiff` (2 tests) |
| 21 | API: corrections endpoint | PASS | `test_workbench_api.py::TestCorrectionEndpoints` |
| 22 | E2E smoke (service-level) | PASS | `test_p11_smoke.py::TestE2EWorkbenchFlow` |
| 23 | E2E smoke (API-level) | PASS | `test_p11_smoke.py::TestE2EWorkbenchAPI` |
| 24 | UI component created | PASS | `PromptPipelineWorkbench.tsx` — 4 tabs |
| 25 | UI wired into CaseWorkspace | PASS | Toggle button added |
| 26 | TypeScript compiles clean | PASS | `npx tsc --noEmit` — 0 errors |
| 27 | Full test suite passes | PASS | 3094 passed, 0 failed |
| 28 | No private data committed | PASS | Verified |
| 29 | No force push | PASS | Verified |
| 30 | No main merge | PASS | On feature branch |

## Test counts

- `test_pipeline_trace.py`: 19 tests
- `test_prompt_registry.py`: 10 tests
- `test_prompt_override.py`: 8 tests
- `test_pipeline_replay.py`: 12 tests
- `test_workbench_api.py`: 14 tests
- `test_p11_smoke.py`: 2 tests
- **Total P11 tests: 65**
- **Total project tests: 3094+**
