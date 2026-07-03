# P11 Owner Question Answer Report

## Q1: Does the pipeline produce real PipelineNode traces with output_hash, producer_type, and prompt metadata?

**YES.**

Every executed stage in `ManuscriptVenueFitPipeline.execute()` now creates a
`PipelineNode` via `_make_node()`, populates it with real data via `_finish_node()`:

- `output_hash`: SHA256-prefix (16 chars) of the stage's actual output, computed
  by `_hash_text()` on the serialized output dict.
- `producer_type`: set to `"deterministic"` for service stages,
  `"deterministic_fallback"` or `"llm_agent"` for agent stages depending on
  whether LLM was used.
- `prompt_family_id`, `prompt_version_hash`, `prompt_override_id`,
  `provider_status`: populated for the 3 LLM-capable stages
  (article_model, venue_investigation, fit_assessment).
- 7 not-applicable stages get `status="not_applicable"` nodes.

**Evidence:** `tests/test_p11_smoke.py::TestE2ERealPipelineInstrumentation::test_real_pipeline_emits_trace`
verifies all 18 nodes, checks output_hash length == 16, producer_type correctness,
and prompt metadata presence. Test passes.

## Q2: Are rendered prompts captured as PromptRunRecord with the actual template content?

**YES.**

For each LLM-capable stage, `_record_prompt()` creates a `PromptRunRecord` with:

- `rendered_system_prompt`: the full system prompt text (from the prompt family
  or override).
- `rendered_user_prompt`: the formatted user prompt with actual manuscript/venue
  data interpolated.
- `prompt_version_hash`: SHA256-prefix of the canonical system+user template.
- `prompt_override_id`: set when an override was injected.
- `provider_status`: `"not_called"` / `"deterministic_fallback"` / `"success"`.

**Evidence:** `test_real_pipeline_emits_trace` step 7 verifies PromptRunRecords
exist for all 3 LLM stages, checks rendered prompts are non-empty and > 50 chars.
`test_override_injection_real` verifies custom prompt text appears in the record.

## Q3: Does PromptOverride injection work without mutating canonical prompt sources?

**YES.**

Override injection works through:

1. `ManuscriptVenueFitPipeline._get_override_for(family_id)` queries the
   `PromptOverrideStore` for an active override matching the case+family.
2. The override dict is passed to `agent.run(inp, prompt_family_override=ovr_dict)`.
3. `AgentRole.run()` stores it as `self._prompt_family_override`.
4. Each agent's `execute()` copies the canonical family dict and overlays the
   override: `family = dict(CANONICAL_FAMILY); if _ovr: family["system_prompt"] = ...`.
5. The canonical `ARTICLE_MODELING_FAMILY` / `VENUE_FACT_EXTRACTION_FAMILY` /
   `FIT_ASSESSMENT_FAMILY` dicts are never mutated.

**Evidence:** `test_override_injection_real` creates an override with "CUSTOM
article modeler" text, runs the pipeline, and verifies:
- `art_node.prompt_override_id == ovr.override_id`
- `"CUSTOM article modeler" in records[0].rendered_system_prompt`

## Q4: Does rerun execute real pipeline stages (not just scaffold)?

**PARTIAL.**

- `rerun_all` with manuscript+venue text: runs the full `ManuscriptVenueFitPipeline`
  with real execution. Status: `"executed"`.
- Individual stage rerun for deterministic stages (`mismatch_map`, `rewrite_plan`,
  `risk_report`, `compliance_check`, `evidence_audit`): declared replayable but
  requires upstream artifacts (not yet wired for standalone replay).
- Individual stage rerun for LLM stages: returns `"stage_not_yet_replayable"`.
  These stages need full pipeline context (article model, venue model) that
  individual replay cannot yet provide.

**Evidence:** `test_replay_rerun_stage_unsupported` verifies LLM stage rerun
returns `partial_not_replayable` with the stage listed in `unsupported_stages`.
`test_diff_real_runs` verifies two real full-pipeline runs can be diffed.
