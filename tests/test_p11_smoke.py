"""P11 Smoke test — end-to-end workbench scenario with fixture article (Track 10).

Verifies: prompt registry discovery → pipeline run scaffold → node creation →
prompt override → rerun-stage → diff → correction candidate.
"""
from __future__ import annotations

import pytest

from kairoskopion.services.pipeline_replay import (
    PIPELINE_STAGES,
    diff_runs,
    plan_rerun_all,
    plan_rerun_from_stage,
    plan_rerun_stage,
    scaffold_replay_run,
)
from kairoskopion.services.pipeline_trace import (
    PipelineNode,
    PipelineRun,
    PipelineTraceStore,
    PromptRunRecord,
)
from kairoskopion.services.prompt_override import (
    PromptOverride,
    PromptOverrideStore,
    PromptPatchCandidate,
)
from kairoskopion.services.prompt_registry import PromptRegistry


class TestE2EWorkbenchFlow:
    """Full operator workflow: upload → inspect → override → rerun → diff → correct."""

    def test_full_workbench_loop(self, tmp_path):
        # 1. Prompt registry discovers all families
        registry = PromptRegistry()
        assert len(registry.list_ids()) >= 15
        art_info = registry.get("article_modeling")
        assert art_info is not None
        assert art_info.system_prompt or art_info.version_hash

        # 2. Scaffold initial pipeline run
        trace = PipelineTraceStore(data_dir=tmp_path / "traces")
        plan = plan_rerun_all()
        run1 = scaffold_replay_run(plan, case_id="smoke-case", trace_store=trace)
        assert run1.status == "pending"
        assert len(trace.list_nodes(run1.run_id)) == 18

        # 3. Simulate completion of all nodes in run1
        nodes1 = trace.list_nodes(run1.run_id)
        for n in nodes1:
            n.status = "completed"
            n.output_hash = f"hash_{n.stage_id}"
        art_node = [n for n in nodes1 if n.stage_id == "article_model"][0]

        # 4. Record a prompt run for the article_model node
        prr = PromptRunRecord(
            node_id=art_node.node_id,
            prompt_family_id="article_modeling",
            prompt_version_hash=art_info.version_hash,
            rendered_system_prompt="You are Article Modeler...",
            rendered_user_prompt="Analyze: [fixture text]",
            provider_status="success",
            response_status="parsed",
        )
        trace.save_prompt_record(prr)
        records = trace.get_prompt_records_for_node(art_node.node_id)
        assert len(records) == 1
        assert records[0].prompt_family_id == "article_modeling"

        # 5. Create a prompt override
        overrides = PromptOverrideStore(data_dir=tmp_path / "overrides")
        ovr = PromptOverride(
            case_id="smoke-case",
            base_prompt_family_id="article_modeling",
            base_prompt_version_hash=art_info.version_hash,
            edited_system_prompt="You are Article Modeler with EXTRA instructions...",
            status="active",
        )
        overrides.save_override(ovr)
        assert overrides.get_active_override("smoke-case", "article_modeling") is ovr

        # 6. Rerun just the article_model stage with override
        plan2 = plan_rerun_stage(
            "article_model",
            overrides=[ovr.override_id],
            base_run_id=run1.run_id,
        )
        run2 = scaffold_replay_run(plan2, case_id="smoke-case", trace_store=trace)
        assert run2.trigger == "rerun_stage"
        assert run2.prompt_override_ids == [ovr.override_id]
        assert run2.base_run_id == run1.run_id

        # Verify only article_model is pending
        nodes2 = trace.list_nodes(run2.run_id)
        pending = [n for n in nodes2 if n.status == "pending"]
        assert len(pending) == 1
        assert pending[0].stage_id == "article_model"

        # Copied intake should have original status
        intake2 = [n for n in nodes2 if n.stage_id == "intake"][0]
        # (skipped because base run had it as pending — but scaffold copies)
        assert intake2.status in ("pending", "skipped", "completed")

        # 7. Diff runs
        diffs = diff_runs(trace, run1.run_id, run2.run_id)
        # There should be differences since article_model was completed in run1
        # but is pending in run2
        art_diffs = [d for d in diffs if d.stage_id == "article_model"]
        assert len(art_diffs) > 0

        # 8. Create correction candidate
        corr = PromptPatchCandidate(
            case_id="smoke-case",
            node_id=art_node.node_id,
            correction_type="wrong_title",
            user_note="Title was not extracted — should be 'Futures Literacy'",
            affected_prompt_family_id="article_modeling",
            proposed_change="Add explicit instruction: extract title from first heading",
        )
        overrides.save_correction(corr)
        corrections = overrides.list_corrections("smoke-case")
        assert len(corrections) == 1
        assert corrections[0].correction_type == "wrong_title"

        # 9. Rerun from fit_assessment downstream
        plan3 = plan_rerun_from_stage("fit_assessment")
        run3 = scaffold_replay_run(plan3, case_id="smoke-case", trace_store=trace)
        nodes3 = trace.list_nodes(run3.run_id)
        pending3 = [n for n in nodes3 if n.status == "pending"]
        copied3 = [n for n in nodes3 if n.status != "pending"]
        assert len(pending3) >= 5
        assert any(n.stage_id == "fit_assessment" for n in pending3)
        assert any(n.stage_id == "evidence_audit" for n in pending3)

        # 10. Verify persistence survives reload
        trace2 = PipelineTraceStore(data_dir=tmp_path / "traces")
        assert len(trace2.list_runs("smoke-case")) == 3
        overrides2 = PromptOverrideStore(data_dir=tmp_path / "overrides")
        assert len(overrides2.list_overrides("smoke-case")) == 1
        assert len(overrides2.list_corrections("smoke-case")) == 1


class TestE2EWorkbenchAPI:
    """Same flow but through FastAPI endpoints."""

    def test_api_workbench_loop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAIROSKOPION_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("KAIROSKOPION_NO_DOTENV", "1")
        import kairoskopion.api.workbench as wb
        wb._prompt_registry = None
        wb._trace_store = None
        wb._override_store = None
        wb._data_dir = tmp_path

        from fastapi.testclient import TestClient
        from kairoskopion.api.app import app
        client = TestClient(app, raise_server_exceptions=False)

        # List prompts
        r = client.get("/api/prompts")
        assert r.status_code == 200
        prompts = r.json()
        assert any(p["prompt_family_id"] == "article_modeling" for p in prompts)

        # List stages
        r = client.get("/api/pipeline-stages")
        assert r.status_code == 200
        assert len(r.json()) == 18

        # Rerun all → creates run
        r = client.post("/api/cases/smoke/rerun", json={})
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # List nodes
        r = client.get(f"/api/cases/smoke/pipeline-runs/{run_id}/nodes")
        assert r.status_code == 200
        assert len(r.json()) == 18

        # Create override
        r = client.post("/api/cases/smoke/prompt-overrides", json={
            "base_prompt_family_id": "article_modeling",
            "edited_system_prompt": "Custom prompt for smoke test",
        })
        assert r.status_code == 200
        ovr_id = r.json()["override_id"]

        # Activate override
        r = client.patch(f"/api/cases/smoke/prompt-overrides/{ovr_id}", json={"status": "active"})
        assert r.status_code == 200
        assert r.json()["status"] == "active"

        # Rerun stage with override
        r = client.post("/api/cases/smoke/rerun-stage", json={
            "stage_id": "article_model",
            "prompt_override_ids": [ovr_id],
            "base_run_id": run_id,
        })
        assert r.status_code == 200
        run2_id = r.json()["run_id"]

        # Diff
        r = client.get(f"/api/cases/smoke/pipeline-diff?run_a={run_id}&run_b={run2_id}")
        assert r.status_code == 200

        # Correction
        r = client.post("/api/cases/smoke/corrections", json={
            "node_id": "pnode-1",
            "correction_type": "wrong_title",
            "user_note": "Title extraction failed",
            "affected_prompt_family_id": "article_modeling",
        })
        assert r.status_code == 200
