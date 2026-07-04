"""P11.2 — Real replay execution for LLM-capable stages.

When replaying a single LLM-capable stage (e.g. article_model):
- The replay engine must look up the prompt family from PromptRegistry
- Apply any active override from PromptOverrideStore
- Render system_prompt and user_prompt
- Create a PromptRunRecord with the rendered prompts
- Set node status to 'prompt_rendered_needs_llm' (not 'stage_not_yet_replayable')
- Record prompt_version_hash and prompt_override_id on the node
- Make diff between base run and replay run non-empty when override differs
"""
from __future__ import annotations

import pytest

from kairoskopion.services.pipeline_replay import (
    PIPELINE_STAGES,
    diff_runs,
    execute_replay_run,
    plan_rerun_stage,
)
from kairoskopion.services.pipeline_trace import PipelineTraceStore, _hash_text
from kairoskopion.services.prompt_override import PromptOverride, PromptOverrideStore
from kairoskopion.services.prompt_registry import PromptRegistry


CASE_ID = "case_test_p112"


@pytest.fixture
def trace_store(tmp_path):
    return PipelineTraceStore(data_dir=tmp_path / "traces")


@pytest.fixture
def override_store(tmp_path):
    return PromptOverrideStore(data_dir=tmp_path / "overrides")


@pytest.fixture
def prompt_registry():
    return PromptRegistry()


class TestReplayStageRendersPrompt:
    """Rerunning an LLM-capable stage must produce a real PromptRunRecord."""

    def test_rerun_article_model_creates_prompt_run_record(
        self, trace_store, override_store, prompt_registry,
    ):
        plan = plan_rerun_stage("article_model", base_run_id=None)
        outcome = execute_replay_run(
            plan,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )
        run = outcome["run"]
        nodes = trace_store.list_nodes(run.run_id)
        art_node = next(n for n in nodes if n.stage_id == "article_model")

        # Node must have prompt metadata
        assert art_node.prompt_family_id == "article_modeling"
        assert art_node.prompt_version_hash is not None
        assert art_node.status != "stage_not_yet_replayable"
        assert art_node.status == "prompt_rendered_needs_llm"

        # PromptRunRecord must exist for this node
        records = trace_store.get_prompt_records_for_node(art_node.node_id)
        assert len(records) == 1
        rec = records[0]
        assert rec.prompt_family_id == "article_modeling"
        assert rec.prompt_version_hash != ""
        assert rec.rendered_system_prompt != ""
        assert rec.provider_status == "not_called"

    def test_rerun_with_override_applies_override(
        self, trace_store, override_store, prompt_registry,
    ):
        custom_system = "You are a CUSTOM article modeler for testing."
        ovr = PromptOverride(
            case_id=CASE_ID,
            base_prompt_family_id="article_modeling",
            status="active",
            edited_system_prompt=custom_system,
        )
        override_store.save_override(ovr)

        plan = plan_rerun_stage(
            "article_model",
            overrides=[ovr.override_id],
            base_run_id=None,
        )
        outcome = execute_replay_run(
            plan,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )
        run = outcome["run"]
        nodes = trace_store.list_nodes(run.run_id)
        art_node = next(n for n in nodes if n.stage_id == "article_model")

        # Override must be recorded on the node
        assert art_node.prompt_override_id == ovr.override_id

        # PromptRunRecord must contain the overridden system prompt
        records = trace_store.get_prompt_records_for_node(art_node.node_id)
        assert len(records) == 1
        rec = records[0]
        assert rec.prompt_override_id == ovr.override_id
        assert rec.rendered_system_prompt == custom_system

    def test_diff_non_empty_after_override_rerun(
        self, trace_store, override_store, prompt_registry,
    ):
        # Run 1: no override
        plan_a = plan_rerun_stage("article_model", base_run_id=None)
        outcome_a = execute_replay_run(
            plan_a,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )
        run_a = outcome_a["run"]

        # Run 2: with override
        ovr = PromptOverride(
            case_id=CASE_ID,
            base_prompt_family_id="article_modeling",
            status="active",
            edited_system_prompt="OVERRIDE system prompt for diff test",
        )
        override_store.save_override(ovr)

        plan_b = plan_rerun_stage(
            "article_model",
            overrides=[ovr.override_id],
            base_run_id=run_a.run_id,
        )
        outcome_b = execute_replay_run(
            plan_b,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )
        run_b = outcome_b["run"]

        diffs = diff_runs(trace_store, run_a.run_id, run_b.run_id)
        changed = [d for d in diffs if d.changed]
        assert len(changed) > 0

        # At minimum prompt_version_hash or prompt_override_id must differ
        diff_fields = {d.field for d in changed}
        assert "prompt_override_id" in diff_fields or "prompt_version_hash" in diff_fields

    def test_canonical_prompt_unchanged_by_override(
        self, prompt_registry, trace_store, override_store,
    ):
        """Override in the replay must not mutate the canonical prompt registry."""
        info_before = prompt_registry.get("article_modeling")
        assert info_before is not None
        original_hash = info_before.version_hash
        original_system = info_before.system_prompt

        ovr = PromptOverride(
            case_id=CASE_ID,
            base_prompt_family_id="article_modeling",
            status="active",
            edited_system_prompt="MUTANT prompt that must not leak",
        )
        override_store.save_override(ovr)

        plan = plan_rerun_stage(
            "article_model", overrides=[ovr.override_id],
        )
        execute_replay_run(
            plan,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )

        info_after = prompt_registry.get("article_modeling")
        assert info_after.version_hash == original_hash
        assert info_after.system_prompt == original_system

    def test_execution_status_is_prompt_rendered(
        self, trace_store, override_store, prompt_registry,
    ):
        plan = plan_rerun_stage("article_model")
        outcome = execute_replay_run(
            plan,
            case_id=CASE_ID,
            trace_store=trace_store,
            override_store=override_store,
            prompt_registry=prompt_registry,
        )
        assert outcome["status"] == "prompt_rendered"
