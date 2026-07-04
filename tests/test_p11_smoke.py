"""P11 Smoke test — end-to-end workbench scenario with REAL pipeline instrumentation.

Track 7 gold standard: runs the actual ManuscriptVenueFitPipeline,
verifies that PipelineRun / PipelineNode / PromptRunRecord are emitted
by the real execution — NOT by scaffold_replay_run.

Tests MUST fail if traces are only scaffolds (no output_hash, no
rendered prompts, no producer_type populated from real execution).
"""
from __future__ import annotations

import pytest

from kairoskopion.pipelines.manuscript_venue_fit import (
    ManuscriptVenueFitPipeline,
    ManuscriptVenueFitResult,
)
from kairoskopion.services.pipeline_replay import (
    PIPELINE_STAGES,
    diff_runs,
    execute_replay_run,
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

# -- Fixture texts (200+ chars, structured format for deterministic venue) --

_MANUSCRIPT = """\
# Futures Literacy as a Civic Capability

## Abstract
This article examines futures literacy as a civic competence that enables
citizens to engage with uncertainty, anticipation, and systemic change.
We draw on UNESCO futures literacy framework and empirical data from
participatory workshops conducted in three European cities.

## Introduction
Futures literacy has emerged as a key concept in anticipation studies.
The concept refers to the ability to imagine, understand, and use the
future in the present moment. This paper contributes a civic lens to
the discussion, arguing that futures literacy is not merely an individual
cognitive skill but a collective civic capability.

## Methods
We conducted twelve futures literacy workshops in Helsinki, Amsterdam,
and Vienna between 2022 and 2023. Each workshop included 15-30
participants from diverse backgrounds.

## Results
Participants demonstrated increased ability to articulate alternative
futures and connect them to present civic action.

## References
1. Miller, R. (2018). Transforming the Future. UNESCO.
2. Poli, R. (2017). Introduction to Anticipation Studies. Springer.
"""

_VENUE = """\
# Journal of Anticipation Studies
Journal: Journal of Anticipation Studies
Publisher: Springer International
ISSN: 1234-5678
Scope: Publishes peer-reviewed articles on futures studies, anticipation,
foresight methodology, and related interdisciplinary work.
Article types: Research articles, theoretical essays, systematic reviews.
Language: English.
Word limit: 8000-12000 words.
Review process: Double-blind peer review.
"""

_SCENARIO = {"goal": "publication", "timeline": "2024-Q2"}


class TestE2ERealPipelineInstrumentation:
    """Track 7: gold standard — real pipeline, real traces, real prompts."""

    def test_real_pipeline_emits_trace(self, tmp_path):
        """10-step verification that traces are NOT scaffold-only."""
        trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")

        # 1. Run the real pipeline (deterministic mode, no LLM)
        pipeline = ManuscriptVenueFitPipeline(
            trace_store=trace_store,
            override_store=override_store,
            case_id="e2e-real",
        )
        result = pipeline.execute(
            manuscript_text=_MANUSCRIPT,
            venue_guidelines_text=_VENUE,
            scenario_data=_SCENARIO,
        )

        # 2. PipelineRun was created by real execution
        assert result.trace_run is not None
        trace_run = result.trace_run
        assert trace_run.case_id == "e2e-real"
        assert trace_run.status == "completed"
        assert trace_run.trigger == "pipeline_execute"
        assert trace_run.run_id.startswith("prun_")

        # Verify it's persisted
        runs = trace_store.list_runs("e2e-real")
        assert len(runs) == 1
        assert runs[0].run_id == trace_run.run_id

        # 3. All 18 nodes were created
        nodes = trace_store.list_nodes(trace_run.run_id)
        assert len(nodes) == 18, f"Expected 18 nodes, got {len(nodes)}"

        # 4. Executed stages have real output_hash (NOT scaffold placeholder)
        executed_stage_ids = {
            "intake", "article_model", "bibliography_parse",
            "venue_investigation", "fit_gate", "fit_assessment",
            "mismatch_map", "rewrite_plan", "risk_report",
            "compliance_check", "evidence_audit",
        }
        for node in nodes:
            if node.stage_id in executed_stage_ids:
                assert node.status == "completed", (
                    f"{node.stage_id}: expected completed, got {node.status}"
                )
                assert node.output_hash is not None, (
                    f"{node.stage_id}: missing output_hash (scaffold-only?)"
                )
                assert len(node.output_hash) == 16, (
                    f"{node.stage_id}: output_hash not a real SHA256 prefix"
                )
                assert node.output_artifact_refs, (
                    f"{node.stage_id}: no output_artifact_refs"
                )

        # 5. Not-applicable stages are clearly marked
        na_stage_ids = {
            "input_classification", "semantic_profile",
            "discipline_mapping", "discipline_matching",
            "venue_discovery", "venue_family_context", "venue_matrix",
        }
        for node in nodes:
            if node.stage_id in na_stage_ids:
                assert node.status == "not_applicable", (
                    f"{node.stage_id}: expected not_applicable, got {node.status}"
                )

        # 6. LLM-capable stages record prompt metadata
        llm_stages = {"article_model", "venue_investigation", "fit_assessment"}
        for node in nodes:
            if node.stage_id in llm_stages:
                assert node.prompt_family_id is not None, (
                    f"{node.stage_id}: no prompt_family_id"
                )
                assert node.prompt_version_hash is not None, (
                    f"{node.stage_id}: no prompt_version_hash"
                )
                assert node.provider_status is not None, (
                    f"{node.stage_id}: no provider_status"
                )
                # In deterministic mode, LLM is not called
                assert node.provider_status in (
                    "not_called", "deterministic_fallback", "success"
                ), f"{node.stage_id}: unexpected provider_status={node.provider_status}"

        # 7. PromptRunRecords were emitted for LLM-capable stages
        for node in nodes:
            if node.stage_id in llm_stages:
                records = trace_store.get_prompt_records_for_node(node.node_id)
                assert len(records) >= 1, (
                    f"{node.stage_id}: no PromptRunRecord (scaffold-only?)"
                )
                rec = records[0]
                assert rec.rendered_system_prompt, (
                    f"{node.stage_id}: empty rendered_system_prompt"
                )
                assert rec.rendered_user_prompt, (
                    f"{node.stage_id}: empty rendered_user_prompt"
                )
                assert rec.prompt_version_hash, (
                    f"{node.stage_id}: no prompt_version_hash in record"
                )
                # Must contain actual prompt content, not placeholder
                assert len(rec.rendered_system_prompt) > 50, (
                    f"{node.stage_id}: system prompt too short to be real"
                )

        # 8. Deterministic stages have correct producer_type
        det_stages = {
            "intake", "bibliography_parse", "fit_gate",
            "mismatch_map", "rewrite_plan", "risk_report",
            "compliance_check", "evidence_audit",
        }
        for node in nodes:
            if node.stage_id in det_stages:
                assert node.producer_type == "deterministic", (
                    f"{node.stage_id}: expected deterministic, got {node.producer_type}"
                )

        # 9. Fallback detection: in det-only mode, LLM agents fall back
        for node in nodes:
            if node.stage_id in llm_stages:
                assert node.producer_type in (
                    "llm_agent", "deterministic_fallback"
                ), f"{node.stage_id}: producer_type={node.producer_type}"

        # 10. Result entities were actually produced
        assert result.article is not None
        assert result.venue is not None
        assert result.fit is not None
        assert result.mismatch_map is not None
        assert result.rewrite_plan is not None
        assert result.risk_report is not None
        assert result.compliance is not None
        assert result.citation_ecology is not None

    def test_override_injection_real(self, tmp_path):
        """Override replaces canonical prompt, visible in trace."""
        trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")

        custom_system = (
            "You are a CUSTOM article modeler with special instructions. "
            "Extract the article model from the manuscript text. Return JSON."
        )
        ovr = PromptOverride(
            case_id="ovr-case",
            base_prompt_family_id="article_modeling",
            edited_system_prompt=custom_system,
            status="active",
        )
        override_store.save_override(ovr)

        pipeline = ManuscriptVenueFitPipeline(
            trace_store=trace_store,
            override_store=override_store,
            case_id="ovr-case",
        )
        result = pipeline.execute(
            manuscript_text=_MANUSCRIPT,
            venue_guidelines_text=_VENUE,
            scenario_data=_SCENARIO,
        )

        nodes = trace_store.list_nodes(result.trace_run.run_id)
        art_node = next(n for n in nodes if n.stage_id == "article_model")

        # Override should be recorded
        assert art_node.prompt_override_id == ovr.override_id

        # PromptRunRecord should show the custom prompt
        records = trace_store.get_prompt_records_for_node(art_node.node_id)
        assert len(records) >= 1
        assert records[0].prompt_override_id == ovr.override_id
        assert "CUSTOM article modeler" in records[0].rendered_system_prompt

    def test_diff_real_runs(self, tmp_path):
        """Diff two real pipeline runs with different overrides."""
        trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")

        # Run 1: no override
        p1 = ManuscriptVenueFitPipeline(
            trace_store=trace_store, override_store=override_store, case_id="diff-case",
        )
        r1 = p1.execute(
            manuscript_text=_MANUSCRIPT, venue_guidelines_text=_VENUE,
            scenario_data=_SCENARIO,
        )

        # Run 2: with article modeling override
        ovr = PromptOverride(
            case_id="diff-case", base_prompt_family_id="article_modeling",
            edited_system_prompt="MODIFIED system prompt for diff test",
            status="active",
        )
        override_store.save_override(ovr)
        p2 = ManuscriptVenueFitPipeline(
            trace_store=trace_store, override_store=override_store, case_id="diff-case",
        )
        r2 = p2.execute(
            manuscript_text=_MANUSCRIPT, venue_guidelines_text=_VENUE,
            scenario_data=_SCENARIO,
        )

        diffs = diff_runs(trace_store, r1.trace_run.run_id, r2.trace_run.run_id)

        # Article model node should differ in prompt_override_id
        art_diffs = [d for d in diffs if d.stage_id == "article_model"]
        override_diff = [d for d in art_diffs if d.field == "prompt_override_id"]
        assert len(override_diff) >= 1
        assert override_diff[0].changed

    def test_replay_rerun_stage_unsupported(self, tmp_path):
        """Rerun-stage for an LLM stage returns stage_not_yet_replayable."""
        trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")

        plan = plan_rerun_stage("article_model")
        outcome = execute_replay_run(plan, case_id="replay-test", trace_store=trace_store)

        assert outcome["status"] == "partial_not_replayable"
        assert "article_model" in outcome.get("unsupported_stages", [])

        nodes = trace_store.list_nodes(outcome["run"].run_id)
        art_node = next(n for n in nodes if n.stage_id == "article_model")
        assert art_node.status == "stage_not_yet_replayable"

    def test_persistence_survives_reload(self, tmp_path):
        """Traces from real pipeline survive store reload."""
        trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")
        pipeline = ManuscriptVenueFitPipeline(
            trace_store=trace_store, case_id="persist-test",
        )
        result = pipeline.execute(
            manuscript_text=_MANUSCRIPT, venue_guidelines_text=_VENUE,
            scenario_data=_SCENARIO,
        )

        # Reload from disk
        trace_store2 = PipelineTraceStore(data_dir=tmp_path / "traces")
        runs = trace_store2.list_runs("persist-test")
        assert len(runs) == 1
        nodes = trace_store2.list_nodes(runs[0].run_id)
        assert len(nodes) == 18

        # Prompt records survived too
        llm_nodes = [n for n in nodes if n.stage_id == "article_model"]
        records = trace_store2.get_prompt_records_for_node(llm_nodes[0].node_id)
        assert len(records) >= 1
        assert records[0].rendered_system_prompt  # non-empty


class TestE2EWorkbenchFlow:
    """Scaffold-level smoke test (kept for regression)."""

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

        # 7. Diff runs
        diffs = diff_runs(trace, run1.run_id, run2.run_id)
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
    """API-level workbench flow."""

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

        # Rerun all → creates run (scaffold since no text provided)
        r = client.post("/api/cases/smoke/rerun", json={})
        assert r.status_code == 200
        data = r.json()
        run_id = data["run_id"]
        assert "execution_status" in data

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

        # Rerun stage (unsupported LLM stage)
        r = client.post("/api/cases/smoke/rerun-stage", json={
            "stage_id": "article_model",
            "prompt_override_ids": [ovr_id],
            "base_run_id": run_id,
        })
        assert r.status_code == 200
        run2_data = r.json()
        run2_id = run2_data["run_id"]
        assert run2_data.get("execution_status") in (
            "partial_not_replayable", "scaffold_only", "prompt_rendered"
        )

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
