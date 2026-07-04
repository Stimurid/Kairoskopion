"""P11.3 Live provider replay smoke test.

Proves the article_model replay path can call a real LLM provider
when configured via .env. Skipped when no provider is available.

The test:
1. Loads dotenv from repo root (same as app.py does at uvicorn startup)
2. Constructs LLMConfig + OpenAICompatProvider
3. Creates a PromptOverride (active)
4. Calls execute_replay_run with llm_provider + manuscript_text
5. Asserts: node status=completed, PromptRunRecord has provider_status=success,
   response_excerpt_or_ref is non-empty, diff against a no-provider run is non-empty
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Guard: skip unless live provider is configured
# ---------------------------------------------------------------------------

def _read_dotenv() -> dict[str, str]:
    """Parse .env from repo root WITHOUT mutating os.environ.

    Mutating os.environ at import time poisons every other test collected
    in the same pytest run (they start hitting the live provider), so the
    parsed vars are applied per-test via the ``dotenv_env`` fixture instead.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return {}
    parsed: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and key not in os.environ:
            parsed[key] = val
    return parsed


_DOTENV_VARS = _read_dotenv()


def _provider_available() -> bool:
    """Check availability under the parsed vars, restoring env afterwards."""
    with patch.dict(os.environ, _DOTENV_VARS):
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.from_env()
        return cfg is not None and bool(cfg.api_key)


_PROVIDER_AVAILABLE = _provider_available()

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        not _PROVIDER_AVAILABLE,
        reason="Live LLM provider not configured (no .env or missing keys)",
    ),
]


@pytest.fixture(autouse=True)
def dotenv_env():
    """Apply .env vars for the duration of each test only."""
    with patch.dict(os.environ, _DOTENV_VARS):
        yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MANUSCRIPT = """
# Cognitive Load in AI-Assisted Learning Environments

## Abstract

This study examines the effects of AI-based tutoring systems on student
cognitive load during complex problem-solving tasks. We conducted a
quasi-experimental study with 120 undergraduate students in a Russian
university setting, comparing traditional instruction with AI-assisted
personalized learning paths.

## Introduction

The integration of artificial intelligence into educational settings has
created new opportunities and challenges for instructional design. As
AI tutoring systems become more sophisticated, understanding their impact
on learner cognition becomes critical.

## Methods

We employed a mixed-methods design combining cognitive load measurements
(NASA-TLX) with learning outcome assessments. Participants were randomly
assigned to control (n=60) and experimental (n=60) groups.

## Results

Students in the AI-assisted group showed significantly lower extraneous
cognitive load (M=3.2, SD=1.1) compared to the control group (M=4.8,
SD=1.3), t(118)=7.21, p<.001. However, germane cognitive load was
comparable across groups.

## Discussion

These findings suggest that AI tutoring systems can effectively reduce
extraneous cognitive load without diminishing productive cognitive
engagement. The implications for instructional design in higher education
are discussed.

## References

1. Sweller, J. (2011). Cognitive Load Theory. Springer.
2. Paas, F., & van Merriënboer, J. J. (2020). Cognitive load theory. Cambridge.
3. Holmes, W., Bialik, M., & Fadel, C. (2019). Artificial Intelligence in Education. CITE.
""".strip()


@pytest.fixture
def trace_env(tmp_path):
    """Set up trace store, override store, prompt registry, and provider."""
    from kairoskopion.services.pipeline_trace import PipelineTraceStore
    from kairoskopion.services.prompt_override import PromptOverride, PromptOverrideStore
    from kairoskopion.services.prompt_registry import PromptRegistry
    from kairoskopion.llm.config import LLMConfig
    from kairoskopion.llm.openai_compat import OpenAICompatProvider

    trace_store = PipelineTraceStore(data_dir=tmp_path / "traces")
    override_store = PromptOverrideStore(data_dir=tmp_path / "overrides")
    prompt_registry = PromptRegistry()

    cfg = LLMConfig.from_env()
    assert cfg is not None, "LLMConfig.from_env() returned None despite guard"
    provider = OpenAICompatProvider(cfg)

    return {
        "trace_store": trace_store,
        "override_store": override_store,
        "prompt_registry": prompt_registry,
        "provider": provider,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLiveArticleModelReplay:
    """Prove live LLM replay for article_model stage."""

    def test_live_replay_produces_completed_node(self, trace_env, tmp_path):
        """article_model node reaches status=completed with a live provider."""
        from kairoskopion.services.pipeline_replay import (
            execute_replay_run,
            plan_rerun_stage,
        )

        plan = plan_rerun_stage("article_model")
        outcome = execute_replay_run(
            plan,
            case_id="smoke-live-1",
            trace_store=trace_env["trace_store"],
            override_store=trace_env["override_store"],
            prompt_registry=trace_env["prompt_registry"],
            llm_provider=trace_env["provider"],
            manuscript_text=SAMPLE_MANUSCRIPT,
        )

        assert outcome["status"] == "live_executed"
        nodes = trace_env["trace_store"].list_nodes(outcome["run"].run_id)
        art_nodes = [n for n in nodes if n.stage_id == "article_model"]
        assert len(art_nodes) == 1
        node = art_nodes[0]
        assert node.status == "completed"
        assert node.provider_status == "success"
        assert node.output_hash is not None

    def test_live_replay_creates_prompt_run_record(self, trace_env):
        """PromptRunRecord has provider_status=success and response excerpt."""
        from kairoskopion.services.pipeline_replay import (
            execute_replay_run,
            plan_rerun_stage,
        )

        plan = plan_rerun_stage("article_model")
        outcome = execute_replay_run(
            plan,
            case_id="smoke-live-2",
            trace_store=trace_env["trace_store"],
            override_store=trace_env["override_store"],
            prompt_registry=trace_env["prompt_registry"],
            llm_provider=trace_env["provider"],
            manuscript_text=SAMPLE_MANUSCRIPT,
        )

        nodes = trace_env["trace_store"].list_nodes(outcome["run"].run_id)
        art_node = [n for n in nodes if n.stage_id == "article_model"][0]
        records = trace_env["trace_store"].get_prompt_records_for_node(art_node.node_id)
        assert len(records) >= 1
        rec = records[0]
        assert rec.provider_status == "success"
        assert rec.response_excerpt_or_ref is not None
        assert len(rec.response_excerpt_or_ref) > 50

    def test_live_replay_with_override(self, trace_env):
        """Override is applied and live call still succeeds."""
        from kairoskopion.services.pipeline_replay import (
            execute_replay_run,
            plan_rerun_stage,
        )
        from kairoskopion.services.prompt_override import PromptOverride

        ovr = PromptOverride(
            case_id="smoke-live-3",
            base_prompt_family_id="article_modeling",
            status="active",
            edited_system_prompt="You are an expert academic article analyzer. Extract structured metadata from the manuscript text provided.",
        )
        trace_env["override_store"].save_override(ovr)

        plan = plan_rerun_stage("article_model")
        outcome = execute_replay_run(
            plan,
            case_id="smoke-live-3",
            trace_store=trace_env["trace_store"],
            override_store=trace_env["override_store"],
            prompt_registry=trace_env["prompt_registry"],
            llm_provider=trace_env["provider"],
            manuscript_text=SAMPLE_MANUSCRIPT,
        )

        assert outcome["status"] == "live_executed"
        nodes = trace_env["trace_store"].list_nodes(outcome["run"].run_id)
        art_node = [n for n in nodes if n.stage_id == "article_model"][0]
        assert art_node.status == "completed"
        assert art_node.prompt_override_id == ovr.override_id

    def test_diff_live_vs_no_provider(self, trace_env):
        """Diff between live run and prompt-only run is non-empty."""
        from kairoskopion.services.pipeline_replay import (
            diff_runs,
            execute_replay_run,
            plan_rerun_stage,
        )

        # Run 1: no provider (prompt_rendered only)
        plan_a = plan_rerun_stage("article_model")
        outcome_a = execute_replay_run(
            plan_a,
            case_id="smoke-live-4",
            trace_store=trace_env["trace_store"],
            override_store=trace_env["override_store"],
            prompt_registry=trace_env["prompt_registry"],
            llm_provider=None,
            manuscript_text=None,
        )

        # Run 2: live provider
        plan_b = plan_rerun_stage("article_model")
        outcome_b = execute_replay_run(
            plan_b,
            case_id="smoke-live-4",
            trace_store=trace_env["trace_store"],
            override_store=trace_env["override_store"],
            prompt_registry=trace_env["prompt_registry"],
            llm_provider=trace_env["provider"],
            manuscript_text=SAMPLE_MANUSCRIPT,
        )

        diffs = diff_runs(
            trace_env["trace_store"],
            outcome_a["run"].run_id,
            outcome_b["run"].run_id,
        )
        changed = [d for d in diffs if d.changed]
        assert len(changed) > 0
        stage_ids_changed = {d.stage_id for d in changed}
        assert "article_model" in stage_ids_changed
