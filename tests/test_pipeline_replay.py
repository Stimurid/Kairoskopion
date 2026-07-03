"""Tests for pipeline replay engine (Track 7)."""
from __future__ import annotations

import pytest

from kairoskopion.services.pipeline_replay import (
    PIPELINE_STAGES,
    ReplayPlan,
    RunDiffEntry,
    diff_runs,
    get_downstream_stages,
    get_stage_index,
    plan_rerun_all,
    plan_rerun_from_stage,
    plan_rerun_stage,
    scaffold_replay_run,
)
from kairoskopion.services.pipeline_trace import (
    PipelineNode,
    PipelineRun,
    PipelineTraceStore,
)


class TestStageDefinitions:
    def test_18_stages(self):
        assert len(PIPELINE_STAGES) == 18

    def test_unique_ids(self):
        ids = [s["stage_id"] for s in PIPELINE_STAGES]
        assert len(ids) == len(set(ids))

    def test_known_stages_present(self):
        ids = [s["stage_id"] for s in PIPELINE_STAGES]
        for expected in ("intake", "article_model", "fit_assessment", "evidence_audit"):
            assert expected in ids

    def test_stage_index(self):
        assert get_stage_index("intake") == 0
        assert get_stage_index("evidence_audit") == 17
        assert get_stage_index("nonexistent") is None

    def test_downstream(self):
        ds = get_downstream_stages("fit_gate")
        ds_ids = [s["stage_id"] for s in ds]
        assert "fit_assessment" in ds_ids
        assert "intake" not in ds_ids


class TestReplayPlans:
    def test_rerun_all(self):
        plan = plan_rerun_all()
        assert plan.mode == "rerun_all"
        assert len(plan.stages_to_rerun) == 18
        assert plan.stages_to_copy == []

    def test_rerun_single_stage(self):
        plan = plan_rerun_stage("article_model")
        assert plan.mode == "rerun_stage"
        assert plan.stages_to_rerun == ["article_model"]
        assert len(plan.stages_to_copy) == 17

    def test_rerun_from_stage(self):
        plan = plan_rerun_from_stage("fit_assessment")
        assert plan.mode == "rerun_from_stage"
        assert "fit_assessment" in plan.stages_to_rerun
        assert "evidence_audit" in plan.stages_to_rerun
        assert "intake" in plan.stages_to_copy
        assert "article_model" in plan.stages_to_copy

    def test_rerun_from_invalid_stage(self):
        plan = plan_rerun_from_stage("nonexistent")
        assert plan.stages_to_rerun == []

    def test_overrides_passed_through(self):
        plan = plan_rerun_all(overrides=["ovr-1", "ovr-2"])
        assert plan.prompt_override_ids == ["ovr-1", "ovr-2"]

    def test_base_run_id(self):
        plan = plan_rerun_stage("intake", base_run_id="prun-old")
        assert plan.base_run_id == "prun-old"


class TestDiffRuns:
    def test_diff_identical_runs(self):
        store = PipelineTraceStore()
        r1 = PipelineRun()
        r2 = PipelineRun()
        store.save_run(r1)
        store.save_run(r2)
        n1 = PipelineNode(run_id=r1.run_id, stage_id="intake", status="completed", output_hash="h1")
        n2 = PipelineNode(run_id=r2.run_id, stage_id="intake", status="completed", output_hash="h1")
        store.save_node(n1)
        store.save_node(n2)
        diffs = diff_runs(store, r1.run_id, r2.run_id)
        assert diffs == []

    def test_diff_changed_hash(self):
        store = PipelineTraceStore()
        r1 = PipelineRun()
        r2 = PipelineRun()
        store.save_run(r1)
        store.save_run(r2)
        store.save_node(PipelineNode(run_id=r1.run_id, stage_id="intake", output_hash="h1"))
        store.save_node(PipelineNode(run_id=r2.run_id, stage_id="intake", output_hash="h2"))
        diffs = diff_runs(store, r1.run_id, r2.run_id)
        changed = [d for d in diffs if d.field == "output_hash"]
        assert len(changed) == 1
        assert changed[0].changed is True

    def test_diff_missing_stage(self):
        store = PipelineTraceStore()
        r1 = PipelineRun()
        r2 = PipelineRun()
        store.save_run(r1)
        store.save_run(r2)
        store.save_node(PipelineNode(run_id=r1.run_id, stage_id="intake"))
        diffs = diff_runs(store, r1.run_id, r2.run_id)
        assert any(d.field == "presence" for d in diffs)


class TestScaffoldReplayRun:
    def test_scaffold_rerun_all(self):
        store = PipelineTraceStore()
        plan = plan_rerun_all()
        run = scaffold_replay_run(plan, case_id="c1", trace_store=store)
        assert run.case_id == "c1"
        assert run.trigger == "rerun_all"
        assert len(run.node_ids) == 18
        nodes = store.list_nodes(run.run_id)
        assert len(nodes) == 18
        assert all(n.status == "pending" for n in nodes)

    def test_scaffold_rerun_stage(self):
        store = PipelineTraceStore()
        plan = plan_rerun_stage("article_model")
        run = scaffold_replay_run(plan, trace_store=store)
        nodes = store.list_nodes(run.run_id)
        rerun = [n for n in nodes if n.status == "pending"]
        skipped = [n for n in nodes if n.status == "skipped"]
        assert len(rerun) == 1
        assert rerun[0].stage_id == "article_model"
        assert len(skipped) == 17

    def test_scaffold_copies_base_results(self):
        store = PipelineTraceStore()
        base_run = PipelineRun(case_id="c1")
        store.save_run(base_run)
        store.save_node(PipelineNode(
            run_id=base_run.run_id,
            stage_id="intake",
            order_index=0,
            status="completed",
            output_hash="base_h",
        ))

        plan = plan_rerun_stage("article_model", base_run_id=base_run.run_id)
        new_run = scaffold_replay_run(plan, case_id="c1", trace_store=store)
        new_nodes = store.list_nodes(new_run.run_id)
        intake_node = [n for n in new_nodes if n.stage_id == "intake"][0]
        assert intake_node.status == "completed"
        assert intake_node.output_hash == "base_h"
