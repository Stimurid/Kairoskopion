"""Tests for P11 Prompt Pipeline Workbench API (Track 8)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIROSKOPION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAIROSKOPION_NO_DOTENV", "1")
    # Reset singletons
    import kairoskopion.api.workbench as wb
    wb._prompt_registry = None
    wb._trace_store = None
    wb._override_store = None
    wb._data_dir = tmp_path

    from kairoskopion.api.app import app
    return TestClient(app, raise_server_exceptions=False)


class TestCORSPreflight:
    """CORS must allow every method the UI client actually uses.

    Regression guard for the audit-branch CORS narrowing: the workbench
    prompt-override update uses PATCH (ui/src/api/client.ts) and broke
    when allow_methods omitted it.
    """

    UI_METHODS = ("GET", "POST", "PATCH", "DELETE")

    @pytest.mark.parametrize("method", UI_METHODS)
    def test_preflight_allows_ui_method(self, client, method):
        r = client.options(
            "/api/cases/case_x/prompt-overrides/ovr_x",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        assert r.status_code == 200, f"preflight for {method} rejected"
        allowed = r.headers.get("access-control-allow-methods", "")
        assert method in allowed, (
            f"{method} missing from allow-methods: {allowed}"
        )

    def test_preflight_allows_ui_headers(self, client):
        r = client.options(
            "/cases",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        assert r.status_code == 200
        allowed = r.headers.get("access-control-allow-headers", "").lower()
        assert "content-type" in allowed
        assert "authorization" in allowed


class TestPromptEndpoints:
    def test_list_prompts(self, client):
        r = client.get("/api/prompts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 15
        ids = [p["prompt_family_id"] for p in data]
        assert "article_modeling" in ids

    def test_get_prompt(self, client):
        r = client.get("/api/prompts/article_modeling")
        assert r.status_code == 200
        data = r.json()
        assert data["prompt_family_id"] == "article_modeling"
        assert "version_hash" in data

    def test_get_prompt_404(self, client):
        r = client.get("/api/prompts/nonexistent")
        assert r.status_code == 404


class TestPipelineStages:
    def test_list_stages(self, client):
        r = client.get("/api/pipeline-stages")
        assert r.status_code == 200
        stages = r.json()
        assert len(stages) == 18
        assert stages[0]["stage_id"] == "intake"


class TestPipelineRunEndpoints:
    def test_list_runs_empty(self, client):
        r = client.get("/api/cases/c1/pipeline-runs")
        assert r.status_code == 200
        assert r.json() == []

    def test_rerun_creates_run(self, client):
        r = client.post("/api/cases/c1/rerun", json={})
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == "c1"
        assert data["trigger"] == "rerun_all"
        assert len(data["node_ids"]) == 18

        r2 = client.get("/api/cases/c1/pipeline-runs")
        assert len(r2.json()) == 1

    def test_rerun_stage(self, client):
        r = client.post("/api/cases/c1/rerun-stage", json={"stage_id": "article_model"})
        assert r.status_code == 200
        data = r.json()
        run_id = data["run_id"]
        assert data.get("execution_status") in ("partial_not_replayable", "scaffold_only", "prompt_rendered")

        r2 = client.get(f"/api/cases/c1/pipeline-runs/{run_id}/nodes")
        assert r2.status_code == 200
        nodes = r2.json()
        art_nodes = [n for n in nodes if n["stage_id"] == "article_model"]
        assert len(art_nodes) == 1
        assert art_nodes[0]["status"] in ("pending", "stage_not_yet_replayable", "prompt_rendered_needs_llm")

    def test_rerun_stage_invalid(self, client):
        r = client.post("/api/cases/c1/rerun-stage", json={"stage_id": "bogus"})
        assert r.status_code == 400

    def test_rerun_from_stage(self, client):
        r = client.post("/api/cases/c1/rerun-from-stage", json={"stage_id": "fit_assessment"})
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        r2 = client.get(f"/api/cases/c1/pipeline-runs/{run_id}/nodes")
        nodes = r2.json()
        pending = [n for n in nodes if n["status"] == "pending"]
        assert len(pending) >= 5

    def test_get_run_404(self, client):
        r = client.get("/api/cases/c1/pipeline-runs/nonexistent")
        assert r.status_code == 404

    def test_get_node_prompt_404(self, client):
        r = client.get("/api/cases/c1/pipeline-runs/r1/nodes/n1/prompt")
        assert r.status_code == 404


class TestPromptOverrideEndpoints:
    def test_create_and_list(self, client):
        r = client.post("/api/cases/c1/prompt-overrides", json={
            "base_prompt_family_id": "article_modeling",
            "edited_system_prompt": "Custom prompt",
            "notes": "test override",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == "c1"
        assert data["status"] == "draft"

        r2 = client.get("/api/cases/c1/prompt-overrides")
        assert len(r2.json()) == 1

    def test_create_invalid_family(self, client):
        r = client.post("/api/cases/c1/prompt-overrides", json={
            "base_prompt_family_id": "nonexistent",
        })
        assert r.status_code == 404

    def test_update_override(self, client):
        r = client.post("/api/cases/c1/prompt-overrides", json={
            "base_prompt_family_id": "article_modeling",
        })
        oid = r.json()["override_id"]

        r2 = client.patch(f"/api/cases/c1/prompt-overrides/{oid}", json={
            "status": "active",
        })
        assert r2.status_code == 200
        assert r2.json()["status"] == "active"

    def test_update_override_404(self, client):
        r = client.patch("/api/cases/c1/prompt-overrides/bogus", json={"status": "active"})
        assert r.status_code == 404


class TestPipelineDiff:
    def test_diff_two_runs(self, client):
        r1 = client.post("/api/cases/c1/rerun", json={})
        r2 = client.post("/api/cases/c1/rerun", json={})
        run_a = r1.json()["run_id"]
        run_b = r2.json()["run_id"]

        r = client.get(f"/api/cases/c1/pipeline-diff?run_a={run_a}&run_b={run_b}")
        assert r.status_code == 200

    def test_diff_missing_run(self, client):
        r = client.get("/api/cases/c1/pipeline-diff?run_a=x&run_b=y")
        assert r.status_code == 404


class TestCorrectionEndpoints:
    def test_create_correction(self, client):
        r = client.post("/api/cases/c1/corrections", json={
            "node_id": "pnode-1",
            "correction_type": "wrong_output",
            "user_note": "Title is wrong",
            "affected_prompt_family_id": "article_modeling",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "pending_review"
        assert data["case_id"] == "c1"
