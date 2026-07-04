"""P11.3 — Live provider call during article_model replay.

Proves that rerun_stage for article_model actually calls the LLM provider
(not just renders the prompt) when a provider is available.

Tests marked ``network`` require a live LLM provider configured via .env
at the repo root.  They are deselected by default (``pytest tests -q``
does NOT run them).  Run explicitly::

    pytest tests/test_p11_3_live_replay_provider_call.py -q -m network

Tests marked ``unit`` run in the default suite without any provider.
"""
from __future__ import annotations

import os
import pytest

from kairoskopion.services.pipeline_replay import (
    execute_replay_run,
    plan_rerun_stage,
    diff_runs,
)
from kairoskopion.services.pipeline_trace import PipelineTraceStore
from kairoskopion.services.prompt_override import PromptOverride, PromptOverrideStore
from kairoskopion.services.prompt_registry import PromptRegistry

# ---------------------------------------------------------------------------
# Provider availability (does NOT load .env at import time)
# ---------------------------------------------------------------------------

def _try_get_provider():
    """Construct provider from .env if available.  Returns None otherwise."""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None
    # Temporarily load .env vars without polluting os.environ permanently
    saved = {}
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        from kairoskopion.llm.config import LLMConfig
        from kairoskopion.llm.openai_compat import OpenAICompatProvider
        cfg = LLMConfig.from_env()
        if cfg is None or not cfg.api_key:
            return None
        return OpenAICompatProvider(cfg)
    except Exception:
        return None
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


_SAMPLE_TEXT = (
    "This study examines the impact of cognitive load theory on instructional "
    "design in higher education, specifically in the context of AI-assisted "
    "learning platforms. Using a mixed-methods approach combining quantitative "
    "analysis of student performance data with qualitative interviews, we "
    "investigate how adaptive learning algorithms can optimize the presentation "
    "of complex material to reduce extraneous cognitive load while maintaining "
    "intrinsic load at appropriate levels. Our findings suggest that AI-driven "
    "content sequencing can significantly improve learning outcomes when "
    "calibrated to individual learner profiles, though the effect varies "
    "across disciplinary contexts. The implications for educational technology "
    "design and pedagogical practice are discussed, with recommendations for "
    "integrating cognitive load principles into adaptive learning systems. "
    "Keywords: cognitive load, adaptive learning, AI education, instructional design. "
) * 3  # ~200+ words


# ===================================================================
# UNIT TESTS — run in default suite, no provider needed
# ===================================================================

class TestReplayWiringUnit:
    """Verify that execute_replay_run accepts and passes llm_provider/manuscript_text."""

    def test_replay_with_provider_none_still_renders_prompt(self, tmp_path):
        """When llm_provider is None, article_model should render prompt only."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        plan = plan_rerun_stage("article_model")
        result = execute_replay_run(
            plan,
            case_id="test_case",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=None,
            manuscript_text=_SAMPLE_TEXT,
        )
        assert result["status"] == "prompt_rendered"
        nodes = store.list_nodes(result["run"].run_id)
        art = [n for n in nodes if n.stage_id == "article_model"][0]
        assert art.status == "prompt_rendered_needs_llm"
        assert art.provider_status == "not_called"

    def test_replay_with_override_renders_edited_prompt(self, tmp_path):
        """Override should be applied in the rendered prompt."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        ovr = PromptOverride(
            case_id="test_case",
            base_prompt_family_id="article_modeling",
            edited_system_prompt="CUSTOM OVERRIDE PROMPT FOR TESTING",
            status="active",
        )
        override_store.save_override(ovr)

        plan = plan_rerun_stage("article_model")
        result = execute_replay_run(
            plan,
            case_id="test_case",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            manuscript_text=_SAMPLE_TEXT,
        )
        nodes = store.list_nodes(result["run"].run_id)
        art = [n for n in nodes if n.stage_id == "article_model"][0]
        assert art.prompt_override_id == ovr.override_id

        records = store.get_prompt_records_for_node(art.node_id)
        assert len(records) >= 1
        assert "CUSTOM OVERRIDE PROMPT" in records[0].rendered_system_prompt


# ===================================================================
# NETWORK / LIVE TESTS — require provider, deselected by default
# ===================================================================

network = pytest.mark.network


@network
class TestLiveReplayProviderCall:
    """Prove that replay actually calls the LLM provider for article_model."""

    @pytest.fixture(autouse=True)
    def _provider(self):
        prov = _try_get_provider()
        if prov is None:
            pytest.skip("No LLM provider available (missing .env or config)")
        self.provider = prov

    def test_live_replay_calls_provider(self, tmp_path):
        """Rerun article_model with provider → provider_status != not_called."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        plan = plan_rerun_stage("article_model")
        result = execute_replay_run(
            plan,
            case_id="live_test",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=self.provider,
            manuscript_text=_SAMPLE_TEXT,
        )
        assert result["status"] == "live_executed"
        nodes = store.list_nodes(result["run"].run_id)
        art = [n for n in nodes if n.stage_id == "article_model"][0]
        assert art.provider_status != "not_called", "Provider was not actually called"
        assert art.status in ("completed", "parse_failed", "provider_failed")

    def test_live_replay_prompt_record(self, tmp_path):
        """PromptRunRecord should have provider/response metadata."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        plan = plan_rerun_stage("article_model")
        result = execute_replay_run(
            plan,
            case_id="live_test",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=self.provider,
            manuscript_text=_SAMPLE_TEXT,
        )
        nodes = store.list_nodes(result["run"].run_id)
        art = [n for n in nodes if n.stage_id == "article_model"][0]
        records = store.get_prompt_records_for_node(art.node_id)
        assert len(records) >= 1
        rec = records[0]
        assert rec.prompt_family_id == "article_modeling"
        assert rec.prompt_version_hash
        assert rec.provider_status in ("success", "error")
        if rec.provider_status == "success":
            assert rec.response_excerpt_or_ref
            assert len(rec.response_excerpt_or_ref) > 50

    def test_live_replay_with_override(self, tmp_path):
        """Override should be applied AND provider should still be called."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        ovr = PromptOverride(
            case_id="live_test",
            base_prompt_family_id="article_modeling",
            edited_system_prompt="You are an academic article modeler. Extract structured metadata. LIVE TEST OVERRIDE.",
            status="active",
        )
        override_store.save_override(ovr)

        plan = plan_rerun_stage("article_model")
        result = execute_replay_run(
            plan,
            case_id="live_test",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=self.provider,
            manuscript_text=_SAMPLE_TEXT,
        )
        nodes = store.list_nodes(result["run"].run_id)
        art = [n for n in nodes if n.stage_id == "article_model"][0]
        assert art.prompt_override_id == ovr.override_id
        assert art.provider_status != "not_called"

    def test_live_diff_vs_no_provider(self, tmp_path):
        """Diff between live run and no-provider run should be non-empty."""
        store = PipelineTraceStore(data_dir=tmp_path / "traces")
        override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
        registry = PromptRegistry()

        # Run A: with provider
        plan_a = plan_rerun_stage("article_model")
        res_a = execute_replay_run(
            plan_a,
            case_id="diff_test",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=self.provider,
            manuscript_text=_SAMPLE_TEXT,
        )

        # Run B: without provider
        plan_b = plan_rerun_stage("article_model")
        res_b = execute_replay_run(
            plan_b,
            case_id="diff_test",
            trace_store=store,
            override_store=override_store,
            prompt_registry=registry,
            llm_provider=None,
            manuscript_text=_SAMPLE_TEXT,
        )

        diffs = diff_runs(store, res_a["run"].run_id, res_b["run"].run_id)
        changed = [d for d in diffs if d.changed]
        assert len(changed) > 0, "Diff should show differences between live and no-provider runs"
        stage_ids = {d.stage_id for d in changed}
        assert "article_model" in stage_ids


# ===================================================================
# Import safety test — default suite
# ===================================================================

class TestEnvIsolation:
    """Importing this module must NOT mutate os.environ."""

    def test_import_does_not_load_env(self):
        """Verify that importing the test module doesn't set LLM env vars."""
        key_before = os.environ.get("KAIROSKOPION_LLM_API_KEY")
        import importlib
        import tests.test_p11_3_live_replay_provider_call as mod
        importlib.reload(mod)
        key_after = os.environ.get("KAIROSKOPION_LLM_API_KEY")
        assert key_before == key_after, "Import mutated KAIROSKOPION_LLM_API_KEY"
