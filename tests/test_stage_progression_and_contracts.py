"""Regression tests for stage progression, _objects_present keys,
venue profiler dict guard, discipline matcher ARCH-SEM-001 enforcement,
and genre/method hypothesis handling.
"""

from __future__ import annotations

import pytest

from kairoskopion.api.cases import Case, CaseStage
from kairoskopion.schema import ArticleModel, VenueModel, SubmissionScenario
from kairoskopion.enums import Genre, MethodStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _case_with_article_and_venue() -> Case:
    """Return a Case wired to ADAPTING stage with article + venue set."""
    case = Case()
    case.article_model = ArticleModel(title_current="Test Article")
    case.selected_venue = VenueModel(canonical_name="Test Journal")
    # Advance stage through the allowed chain to ADAPTING
    case.stage = CaseStage.ADAPTING
    return case


def _case_at_submission_pack() -> Case:
    """Return a Case at SUBMISSION_PACK stage for dossier test."""
    case = _case_with_article_and_venue()
    case.stage = CaseStage.SUBMISSION_PACK
    return case


# ---------------------------------------------------------------------------
# 1. Stage progression
# ---------------------------------------------------------------------------

class TestStageProgression:

    def test_build_submission_pack_transitions_to_submission_pack(self):
        case = _case_with_article_and_venue()
        assert case.stage == CaseStage.ADAPTING

        result = case.build_submission_pack_api()
        assert "status" not in result or result.get("status") != "not_ready"
        assert case.stage == CaseStage.SUBMISSION_PACK

    def test_finalize_dossier_transitions_to_dossier(self):
        case = _case_at_submission_pack()
        assert case.stage == CaseStage.SUBMISSION_PACK

        result = case.finalize_dossier()
        assert isinstance(result, dict)
        assert case.stage == CaseStage.DOSSIER

    def test_build_dossier_does_not_transition(self):
        """GET-safe build_dossier must NOT mutate stage."""
        case = _case_at_submission_pack()
        assert case.stage == CaseStage.SUBMISSION_PACK

        result = case.build_dossier()
        assert isinstance(result, dict)
        assert case.stage == CaseStage.SUBMISSION_PACK

    def test_build_submission_pack_requires_article_and_venue(self):
        case = Case()
        case.stage = CaseStage.ADAPTING
        result = case.build_submission_pack_api()
        assert result.get("status") == "not_ready"
        # Stage should NOT advance
        assert case.stage == CaseStage.ADAPTING


# ---------------------------------------------------------------------------
# 2. _objects_present keys
# ---------------------------------------------------------------------------

class TestObjectsPresentKeys:

    EXPECTED_KEYS = {
        "intake",
        "article_model",
        "scenario",
        "pathways",
        "venue_pool",
        "venue_selected",
        "fit_assessed",
        "adapting",
        "submission_pack",
        "dossier",
    }

    def test_objects_present_has_exact_keys(self):
        case = Case()
        present = case._objects_present()
        assert set(present.keys()) == self.EXPECTED_KEYS

    def test_objects_present_no_adaptation_plan_key(self):
        case = Case()
        present = case._objects_present()
        assert "adaptation_plan" not in present

    def test_objects_present_adapting_key_exists(self):
        case = Case()
        present = case._objects_present()
        assert "adapting" in present

    def test_objects_present_values_are_bool(self):
        case = Case()
        present = case._objects_present()
        for key, val in present.items():
            assert isinstance(val, bool), f"Key {key!r} has non-bool value: {val!r}"


# ---------------------------------------------------------------------------
# 3. Venue profiler dict guard — _build_from_llm handles venue_type as dict
# ---------------------------------------------------------------------------

class TestVenueProfilerDictGuard:

    def test_venue_type_dict_does_not_crash(self):
        from kairoskopion.agents.venue_profiler import _build_from_llm

        parsed = {
            "canonical_name": "Test Journal",
            "venue_type": {"type": "journal", "evidence_status": "fact"},
            "scope_summary": "A test journal.",
            "publisher_or_owner": "Test Publisher",
        }
        venue, regime = _build_from_llm(parsed, "some text", "test-ref")
        assert venue.canonical_name == "Test Journal"
        from kairoskopion.enums import VenueType
        assert venue.venue_type == VenueType.JOURNAL.value

    def test_venue_type_dict_with_conference_type(self):
        from kairoskopion.agents.venue_profiler import _build_from_llm

        parsed = {
            "canonical_name": "Proceedings of X",
            "venue_type": {"type": "conference_proceedings", "evidence_status": "fact"},
        }
        venue, regime = _build_from_llm(parsed, "text", None)
        from kairoskopion.enums import VenueType
        assert venue.venue_type == VenueType.CONFERENCE_PROCEEDINGS.value

    def test_venue_type_plain_string_still_works(self):
        from kairoskopion.agents.venue_profiler import _build_from_llm

        parsed = {
            "canonical_name": "Journal X",
            "venue_type": "journal",
        }
        venue, regime = _build_from_llm(parsed, "text", None)
        from kairoskopion.enums import VenueType
        assert venue.venue_type == VenueType.JOURNAL.value

    def test_venue_type_dict_with_value_key_fallback(self):
        from kairoskopion.agents.venue_profiler import _build_from_llm

        parsed = {
            "canonical_name": "Special Issue Y",
            "venue_type": {"value": "special_issue"},
        }
        venue, regime = _build_from_llm(parsed, "text", None)
        from kairoskopion.enums import VenueType
        assert venue.venue_type == VenueType.SPECIAL_ISSUE.value


# ---------------------------------------------------------------------------
# 4. ARCH-SEM-001: discipline matcher prohibits deterministic semantic output
# ---------------------------------------------------------------------------

class TestDisciplineMatcherArchSem001:

    def test_execute_deterministic_raises_semantic_error(self):
        from kairoskopion.agents.discipline_matcher import DisciplineMatcherAgent
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError

        agent = DisciplineMatcherAgent()
        inp = AgentInput(
            operation_id="test",
            agent_role_id="discipline_matcher",
            raw_text="test article",
            entities={"article_summary": "test", "region": "auto"},
        )
        with pytest.raises(SemanticLLMRequiredError):
            agent.execute_deterministic(inp)

    def test_venue_profiler_execute_deterministic_raises_semantic_error(self):
        from kairoskopion.agents.venue_profiler import VenueProfilerAgent
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError

        agent = VenueProfilerAgent()
        inp = AgentInput(
            operation_id="test",
            agent_role_id="venue_profiler",
            raw_text="test venue text",
        )
        with pytest.raises(SemanticLLMRequiredError):
            agent.execute_deterministic(inp)


# ---------------------------------------------------------------------------
# 5. Genre/method unknown — no enum-list alternatives (ARCH-SEM-001)
# ---------------------------------------------------------------------------

class TestGenreMethodNoEnumListing:

    def test_genre_unknown_has_needs_resolution_but_no_enum_alternatives(self):
        """ARCH-SEM-001: unknown genre must NOT enumerate all Genre values
        as alternatives — that's deterministic semantic content."""
        case = Case()
        case.article_model = ArticleModel(
            genre_current=Genre.UNKNOWN.value,
            method_status=MethodStatus.EMPIRICAL_METHOD.value,
        )
        case.stage = CaseStage.ARTICLE_MODEL
        case._populate_semantic_hypotheses_from_article()

        hyp = case.semantic_hypotheses.get("genre")
        assert hyp is not None, "genre hypothesis must be created"
        primary = hyp.get("primary", {})
        assert primary["confidence"] == "needs_resolution"
        alternatives = hyp.get("alternatives")
        assert not alternatives, "enum-list alternatives are prohibited by ARCH-SEM-001"

    def test_method_unknown_has_needs_resolution_but_no_enum_alternatives(self):
        case = Case()
        case.article_model = ArticleModel(
            genre_current=Genre.RESEARCH_ARTICLE.value,
            method_status=MethodStatus.UNKNOWN.value,
        )
        case.stage = CaseStage.ARTICLE_MODEL
        case._populate_semantic_hypotheses_from_article()

        hyp = case.semantic_hypotheses.get("method")
        assert hyp is not None, "method hypothesis must be created"
        primary = hyp.get("primary", {})
        assert primary["confidence"] == "needs_resolution"
        alternatives = hyp.get("alternatives")
        assert not alternatives, "enum-list alternatives are prohibited by ARCH-SEM-001"

    def test_known_genre_has_no_alternatives(self):
        case = Case()
        case.article_model = ArticleModel(
            genre_current=Genre.RESEARCH_ARTICLE.value,
            method_status=MethodStatus.EMPIRICAL_METHOD.value,
        )
        case.stage = CaseStage.ARTICLE_MODEL
        case._populate_semantic_hypotheses_from_article()

        hyp = case.semantic_hypotheses.get("genre")
        assert hyp is not None
        primary = hyp.get("primary", {})
        assert primary["confidence"] != "needs_resolution"
        alternatives = hyp.get("alternatives")
        assert not alternatives

    def test_known_method_has_no_alternatives(self):
        case = Case()
        case.article_model = ArticleModel(
            genre_current=Genre.RESEARCH_ARTICLE.value,
            method_status=MethodStatus.EMPIRICAL_METHOD.value,
        )
        case.stage = CaseStage.ARTICLE_MODEL
        case._populate_semantic_hypotheses_from_article()

        hyp = case.semantic_hypotheses.get("method")
        assert hyp is not None
        primary = hyp.get("primary", {})
        assert primary["confidence"] != "needs_resolution"
        alternatives = hyp.get("alternatives")
        assert not alternatives
