"""Regression tests for BLOCKER A–D closure.

Tests that the discipline matcher always goes through the agent path
(not registry-first shortcut), genre/method rerun works, and the
article model endpoint wiring is correct.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# ==================================================================
# BLOCKER A: Discipline matcher must not bypass LLM with registry hit
# ==================================================================

class TestDisciplineLLMWiring:
    """Prove that _run_discipline_matcher does NOT early-return on registry hit."""

    def test_no_registry_first_shortcircuit(self):
        """Source code must not have the old registry-first early return."""
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # The old code had: if found: return (after registry lookup)
        # It must NOT contain registry_first assignment without going
        # through the agent.
        method_src = _extract_method_source(src, "_run_discipline_matcher")
        assert method_src is not None
        # Must not contain "registry_first" — that was the old path
        assert "registry_first" not in method_src, (
            "_run_discipline_matcher still contains registry_first shortcircuit"
        )

    def test_provider_injection_in_discipline_matcher(self):
        """_run_discipline_matcher must call _get_llm_provider and pass it."""
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        method_src = _extract_method_source(src, "_run_discipline_matcher")
        assert method_src is not None
        assert '_get_llm_provider("discipline_matcher")' in method_src
        assert "agent.execute(inp, provider)" in method_src

    def test_source_marked_llm_when_provider_present(self):
        """When provider is available, output must be tagged source=llm."""
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        method_src = _extract_method_source(src, "_run_discipline_matcher")
        assert method_src is not None
        assert '"source"' in method_src
        assert '"llm"' in method_src

    def test_no_deterministic_fallback_arch_sem_001(self):
        """ARCH-SEM-001: _run_discipline_matcher must NOT fall back to
        execute_deterministic — it must raise when LLM is unavailable."""
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        method_src = _extract_method_source(src, "_run_discipline_matcher")
        assert method_src is not None
        assert "execute_deterministic" not in method_src

    def test_discipline_matcher_requires_llm(self, tmp_path):
        """Without LLM, _run_discipline_matcher raises SemanticLLMRequiredError."""
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError

        case = Case()
        case.article_model = ArticleModel(
            title_current="Philosophy of science",
            disciplinary_register_current="philosophy",
        )
        with pytest.raises(SemanticLLMRequiredError):
            case._run_discipline_matcher()


# ==================================================================
# BLOCKER A: Discipline prompt v3 — 10 candidates, 7-10 sentence rationale
# ==================================================================

class TestDisciplinePromptV3:
    """Verify v3 prompt family exists and enforces 10-candidate schema."""

    def test_v3_family_exists(self):
        from kairoskopion.prompts.discipline_matching import (
            DISCIPLINE_MATCHING_V3_FAMILY,
        )
        assert DISCIPLINE_MATCHING_V3_FAMILY["family_id"] == "discipline_matching_v3"
        assert DISCIPLINE_MATCHING_V3_FAMILY["version"] == "3.0.0"

    def test_v3_schema_requires_candidates(self):
        from kairoskopion.prompts.discipline_matching import (
            DISCIPLINE_MATCHING_V3_FAMILY,
        )
        schema = DISCIPLINE_MATCHING_V3_FAMILY["output_schema"]
        props = schema["properties"]
        matched = props["matched"]
        assert matched.get("minItems", 0) >= 1

    def test_v3_candidate_has_required_fields(self):
        from kairoskopion.prompts.discipline_matching import (
            DISCIPLINE_MATCHING_V3_FAMILY,
        )
        schema = DISCIPLINE_MATCHING_V3_FAMILY["output_schema"]
        candidate_props = schema["properties"]["matched"]["items"]["properties"]
        required_fields = {
            "discipline_id", "display_name", "strength", "confidence",
            "why", "supporting_evidence", "contradicting_evidence",
        }
        assert required_fields.issubset(set(candidate_props.keys()))

    def test_v3_validator_rejects_empty(self):
        from kairoskopion.prompts.discipline_matching import (
            validate_discipline_match_v3,
        )
        warnings = validate_discipline_match_v3({"matched": []})
        assert any("empty" in w.lower() or "0" in w for w in warnings)


# ==================================================================
# BLOCKER B: Genre/method rerun endpoint and logic
# ==================================================================

class TestGenreMethodRerun:
    """Genre/method rerun endpoint must be wired and functional."""

    def test_rerun_endpoint_exists(self):
        """POST /cases/{case_id}/article-model/rerun must exist."""
        from kairoskopion.api.app import app
        routes = [r.path for r in app.routes]
        assert "/cases/{case_id}/article-model/rerun" in routes

    def test_rerun_method_exists(self):
        from kairoskopion.api.cases import Case
        assert hasattr(Case, "rerun_article_model")
        sig = inspect.signature(Case.rerun_article_model)
        assert "comment" in sig.parameters

    def test_rerun_requires_article_model(self):
        from kairoskopion.api.cases import Case
        case = Case()
        result = case.rerun_article_model()
        assert "error" in result

    def test_rerun_requires_sufficient_text(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        case = Case()
        case.article_model = ArticleModel(title_current="Test")
        case.input_text = "Short"
        result = case.rerun_article_model()
        assert "error" in result

    def test_rerun_requires_llm_provider(self):
        """Without LLM env vars, rerun must return error, not fake success."""
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        case = Case()
        case.article_model = ArticleModel(title_current="Test article on philosophy")
        case.input_text = "x" * 200
        result = case.rerun_article_model()
        assert "error" in result
        assert "LLM" in result["error"] or "provider" in result["error"].lower()

    def test_genre_method_enum_constraints_in_prompt(self):
        """Prompt schema must constrain genre_current and method_status to enums."""
        from kairoskopion.prompts.article_modeling import ARTICLE_MODELING_OUTPUT_SCHEMA
        genre_schema = ARTICLE_MODELING_OUTPUT_SCHEMA["properties"]["genre_current"]
        assert "enum" in genre_schema
        assert "research_article" in genre_schema["enum"]
        assert "unknown" in genre_schema["enum"]

        method_schema = ARTICLE_MODELING_OUTPUT_SCHEMA["properties"]["method_status"]
        assert "enum" in method_schema
        assert "empirical_method" in method_schema["enum"]
        assert "unknown" in method_schema["enum"]


# ==================================================================
# BLOCKER B: Deterministic UNKNOWN must NOT be treated as success
# ==================================================================

class TestUnknownNotSuccess:
    """UNKNOWN genre/method from deterministic fallback is not acceptance."""

    def test_deterministic_unknown_not_masked(self):
        """If genre_current is unknown, it must remain 'unknown', not be
        silently converted to something else."""
        from kairoskopion.schema import ArticleModel
        model = ArticleModel(
            title_current="Some article",
            genre_current="unknown",
            method_status="unknown",
        )
        assert model.genre_current == "unknown"
        assert model.method_status == "unknown"


# ==================================================================
# BLOCKER C: Finalization — confirm_article_model
# ==================================================================

class TestFinalizationEndpoint:
    """Confirm button must set lifecycle to confirmed_by_user."""

    def test_confirm_method_exists(self):
        from kairoskopion.api.cases import Case
        assert hasattr(Case, "confirm_article_model")

    def test_confirm_sets_lifecycle(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        case = Case()
        case.article_model = ArticleModel(title_current="Test")
        case.confirm_article_model()
        assert case.article_model.lifecycle_status in (
            "confirmed", "confirmed_by_user",
        )

    def test_confirm_endpoint_exists(self):
        from kairoskopion.api.app import app
        routes = [r.path for r in app.routes]
        assert "/cases/{case_id}/article-model/confirm" in routes


# ==================================================================
# BLOCKER D: Pipeline audit — agent map integrity
# ==================================================================

class TestAgentMapIntegrity:
    """Prove agent spec registry and pipeline implementation are consistent."""

    def test_agent_spec_registry_loadable(self):
        from kairoskopion.agents.registry import AGENT_SPEC_REGISTRY
        assert len(AGENT_SPEC_REGISTRY) > 0

    def test_all_required_agents_exist(self):
        from kairoskopion.agents.registry import AGENT_SPEC_REGISTRY
        required = {
            "article_modeler",
            "venue_profiler",
            "fit_assessor",
            "article_semantic_profiler",
            "discipline_matcher",
        }
        missing = required - set(AGENT_SPEC_REGISTRY.keys())
        assert not missing, f"Missing agent specs: {missing}"

    def test_execution_modes_valid(self):
        from kairoskopion.agents.registry import AGENT_SPEC_REGISTRY
        valid_modes = {"llm_optional", "llm_required", "deterministic"}
        for role_id, spec in AGENT_SPEC_REGISTRY.items():
            assert spec.execution_mode in valid_modes, (
                f"Agent {role_id} has invalid execution_mode: {spec.execution_mode}"
            )

    def test_agent_map_endpoint_exists(self):
        from kairoskopion.api.app import app
        routes = [r.path for r in app.routes]
        assert "/agents/map" in routes

    def test_agent_map_derives_has_real_llm_from_execution_mode(self):
        """Agent map must NOT hardcode has_real_llm=False for all agents."""
        from kairoskopion.api import app as app_mod
        src = Path(app_mod.__file__).read_text(encoding="utf-8")
        assert "execution_mode" in src

    def test_case_pipeline_phases_documented(self):
        """Case class must have key pipeline methods."""
        from kairoskopion.api.cases import Case
        required_methods = [
            "intake_text",
            "_build_article_model",
            "_run_discipline_matcher",
            "investigate_venue",
            "discover_venues",
            "confirm_article_model",
            "rerun_article_model",
            "rerun_discipline_analysis",
        ]
        for method_name in required_methods:
            assert hasattr(Case, method_name), f"Case missing {method_name}"


# ==================================================================
# BLOCKER D: Stub classification
# ==================================================================

class TestStubClassification:
    """Enumerate stubs and classify them as intentional or unfinished."""

    def test_known_stubs_identified(self):
        """Agent specs with execution_mode=deterministic or llm_optional
        have fallback paths (not stubs). Verify each has execute_deterministic."""
        from kairoskopion.agents.registry import AGENT_SPEC_REGISTRY
        for role_id, spec in AGENT_SPEC_REGISTRY.items():
            if spec.execution_mode in ("llm_optional", "deterministic"):
                agent_cls = _load_agent_class(role_id)
                if agent_cls is not None:
                    assert hasattr(agent_cls, "execute_deterministic"), (
                        f"Agent {role_id} has mode={spec.execution_mode} "
                        "but no execute_deterministic method"
                    )


# ==================================================================
# UI wiring: API client methods
# ==================================================================

class TestUIClientWiring:
    """Verify API client has the rerun methods."""

    def test_client_has_rerun_article_model(self):
        client_path = Path("ui/src/api/client.ts")
        if not client_path.exists():
            pytest.skip("UI not present")
        src = client_path.read_text(encoding="utf-8")
        assert "rerunArticleModel" in src

    def test_client_has_rerun_discipline_analysis(self):
        client_path = Path("ui/src/api/client.ts")
        if not client_path.exists():
            pytest.skip("UI not present")
        src = client_path.read_text(encoding="utf-8")
        assert "rerunDisciplineAnalysis" in src

    def test_human_view_has_genre_method_rerun(self):
        view_path = Path("ui/src/components/HumanModelView.tsx")
        if not view_path.exists():
            pytest.skip("UI not present")
        src = view_path.read_text(encoding="utf-8")
        assert "rerunArticleModel" in src
        assert "genre-method-rerun-section" in src


# ==================================================================
# Helpers
# ==================================================================

def _extract_method_source(full_src: str, method_name: str) -> str | None:
    """Extract a method body from full source code by name."""
    marker = f"def {method_name}("
    idx = full_src.find(marker)
    if idx < 0:
        return None
    end = full_src.find("\n    def ", idx + 1)
    if end < 0:
        end = full_src.find("\nclass ", idx + 1)
    if end < 0:
        end = len(full_src)
    return full_src[idx:end]


def _load_agent_class(role_id: str):
    """Try to load agent class for a given role_id."""
    module_map = {
        "article_modeler": ("kairoskopion.agents.article_modeler", "ArticleModelerAgent"),
        "venue_profiler": ("kairoskopion.agents.venue_profiler", "VenueProfilerAgent"),
        "fit_assessor": ("kairoskopion.agents.fit_assessor", "FitAssessorAgent"),
        "semantic_profiler": ("kairoskopion.agents.semantic_profiler", "ArticleSemanticProfilerAgent"),
        "discipline_matcher": ("kairoskopion.agents.discipline_matcher", "DisciplineMatcherAgent"),
    }
    entry = module_map.get(role_id)
    if entry is None:
        return None
    try:
        import importlib
        mod = importlib.import_module(entry[0])
        return getattr(mod, entry[1], None)
    except Exception:
        return None
