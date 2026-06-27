"""Tests for pipeline trace models and store (Track 3)."""
from __future__ import annotations

import json

import pytest

from kairoskopion.services.pipeline_trace import (
    PipelineNode,
    PipelineRun,
    PipelineTraceStore,
    PromptRunRecord,
    _hash_text,
)


class TestPipelineRun:
    def test_create_default(self):
        run = PipelineRun()
        assert run.run_id.startswith("prun_")
        assert run.status == "pending"
        assert run.trigger == "upload"
        assert run.node_ids == []
        assert run.prompt_override_ids == []

    def test_to_dict_omits_none(self):
        run = PipelineRun(case_id=None, base_run_id=None)
        d = run.to_dict()
        assert "case_id" not in d
        assert "base_run_id" not in d
        assert "run_id" in d

    def test_roundtrip(self):
        run = PipelineRun(
            case_id="case-1",
            trigger="rerun_stage",
            status="completed",
            node_ids=["n1", "n2"],
            gates_summary={"fit_gate": "PASS"},
        )
        d = run.to_dict()
        restored = PipelineRun.from_dict(d)
        assert restored.case_id == "case-1"
        assert restored.trigger == "rerun_stage"
        assert restored.node_ids == ["n1", "n2"]
        assert restored.gates_summary == {"fit_gate": "PASS"}

    def test_from_dict_ignores_unknown_keys(self):
        d = {"run_id": "prun-test", "unknown_field": 42, "status": "running"}
        run = PipelineRun.from_dict(d)
        assert run.run_id == "prun-test"
        assert run.status == "running"

    def test_all_triggers_valid(self):
        for t in ("upload", "run_all", "rerun_all", "rerun_stage", "rerun_downstream", "cli", "api", "test"):
            run = PipelineRun(trigger=t)
            assert run.trigger == t


class TestPipelineNode:
    def test_create_default(self):
        node = PipelineNode()
        assert node.node_id.startswith("pnode_")
        assert node.status == "pending"
        assert node.rerunnable is True
        assert node.producer_type == "deterministic"

    def test_roundtrip(self):
        node = PipelineNode(
            run_id="prun-1",
            stage_id="article_model",
            stage_label="Article Modeling",
            order_index=2,
            producer_type="llm_agent",
            service_or_agent="ArticleModelerAgent",
            prompt_family_id="article_modeling",
            status="completed",
            downstream_node_ids=["pnode-3", "pnode-4"],
        )
        d = node.to_dict()
        restored = PipelineNode.from_dict(d)
        assert restored.stage_id == "article_model"
        assert restored.producer_type == "llm_agent"
        assert restored.downstream_node_ids == ["pnode-3", "pnode-4"]

    def test_output_hash_omitted_when_none(self):
        node = PipelineNode(output_hash=None)
        d = node.to_dict()
        assert "output_hash" not in d

    def test_all_statuses(self):
        for s in ("pending", "running", "completed", "partial", "failed", "skipped", "needs_llm", "needs_sources", "needs_user_input"):
            node = PipelineNode(status=s)
            assert node.status == s


class TestPromptRunRecord:
    def test_create_default(self):
        rec = PromptRunRecord()
        assert rec.prompt_run_id.startswith("prr_")
        assert rec.rendered_system_prompt == ""

    def test_roundtrip(self):
        rec = PromptRunRecord(
            node_id="pnode-1",
            prompt_family_id="article_modeling",
            prompt_version_hash="abc123",
            rendered_system_prompt="You are Article Modeler",
            rendered_user_prompt="Analyze: ...",
            provider_status="success",
            response_status="parsed",
        )
        d = rec.to_dict()
        restored = PromptRunRecord.from_dict(d)
        assert restored.prompt_family_id == "article_modeling"
        assert restored.rendered_system_prompt == "You are Article Modeler"


class TestHashText:
    def test_deterministic(self):
        h1 = _hash_text("hello world")
        h2 = _hash_text("hello world")
        assert h1 == h2
        assert len(h1) == 16

    def test_different_inputs(self):
        assert _hash_text("a") != _hash_text("b")


class TestPipelineTraceStore:
    def test_in_memory(self):
        store = PipelineTraceStore()
        run = PipelineRun(case_id="c1")
        store.save_run(run)
        assert store.get_run(run.run_id) is run
        assert store.list_runs("c1") == [run]
        assert store.list_runs("c2") == []

    def test_nodes(self):
        store = PipelineTraceStore()
        n1 = PipelineNode(run_id="r1", order_index=1, stage_id="intake")
        n2 = PipelineNode(run_id="r1", order_index=0, stage_id="classification")
        n3 = PipelineNode(run_id="r2", order_index=0, stage_id="other")
        store.save_node(n1)
        store.save_node(n2)
        store.save_node(n3)
        nodes = store.list_nodes("r1")
        assert len(nodes) == 2
        assert nodes[0].stage_id == "classification"
        assert nodes[1].stage_id == "intake"

    def test_prompt_records(self):
        store = PipelineTraceStore()
        rec = PromptRunRecord(node_id="pnode-1", prompt_family_id="article_modeling")
        store.save_prompt_record(rec)
        assert store.get_prompt_record(rec.prompt_run_id) is rec
        assert len(store.get_prompt_records_for_node("pnode-1")) == 1
        assert len(store.get_prompt_records_for_node("pnode-999")) == 0

    def test_persistence_roundtrip(self, tmp_path):
        store = PipelineTraceStore(data_dir=tmp_path)
        run = PipelineRun(case_id="c1", status="completed")
        node = PipelineNode(run_id=run.run_id, stage_id="intake", order_index=0)
        rec = PromptRunRecord(node_id=node.node_id, prompt_family_id="art")
        store.save_run(run)
        store.save_node(node)
        store.save_prompt_record(rec)

        store2 = PipelineTraceStore(data_dir=tmp_path)
        assert store2.get_run(run.run_id).case_id == "c1"
        assert len(store2.list_nodes(run.run_id)) == 1
        assert len(store2.get_prompt_records_for_node(node.node_id)) == 1

    def test_jsonl_files_created(self, tmp_path):
        store = PipelineTraceStore(data_dir=tmp_path)
        store.save_run(PipelineRun())
        store.save_node(PipelineNode())
        store.save_prompt_record(PromptRunRecord())
        assert (tmp_path / "pipeline_runs.jsonl").exists()
        assert (tmp_path / "pipeline_nodes.jsonl").exists()
        assert (tmp_path / "prompt_run_records.jsonl").exists()

    def test_list_all_runs(self):
        store = PipelineTraceStore()
        r1 = PipelineRun(case_id="c1")
        r2 = PipelineRun(case_id="c2")
        store.save_run(r1)
        store.save_run(r2)
        assert len(store.list_runs()) == 2

    def test_get_nonexistent(self):
        store = PipelineTraceStore()
        assert store.get_run("nope") is None
        assert store.get_node("nope") is None
        assert store.get_prompt_record("nope") is None

    def test_empty_data_dir(self, tmp_path):
        store = PipelineTraceStore(data_dir=tmp_path)
        assert store.list_runs() == []
