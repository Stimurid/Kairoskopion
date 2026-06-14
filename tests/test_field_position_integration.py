"""Integration tests for wiring FieldPositionModel into the Case pipeline.

Covers:
- ArticleFieldPositionerAgent deterministic fallback returns valid FPM
- VenueFieldPositionerAgent deterministic fallback returns valid FPM
- Case.intake_text builds article_field_position automatically
- Case.investigate_venue builds venue_field_position automatically
- Case._run_fit_chain computes field_position_fit when both FPMs present
- Case snapshot round-trip preserves FPMs and field_position_fit
"""

from __future__ import annotations

import os
import tempfile
import unittest

from kairoskopion.agents.article_field_positioner import ArticleFieldPositionerAgent
from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.venue_field_positioner import VenueFieldPositionerAgent
from kairoskopion.api.cases import Case, CaseStore, _case_from_snapshot, _case_to_snapshot
from kairoskopion.schema import FieldPositionModel, VenueModel


def _ensure_no_llm():
    """Force deterministic path: clear any LLM env vars during tests."""
    for k in (
        "KAIROSKOPION_LLM_API_KEY",
        "LITOPS_LLM_API_KEY",
        "OPENAI_API_KEY",
    ):
        os.environ.pop(k, None)


class TestArticleFieldPositionerDeterministic(unittest.TestCase):
    def test_returns_field_position_model(self):
        agent = ArticleFieldPositionerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_field_positioner",
            entities={
                "article": {
                    "article_model_id": "art_test",
                    "disciplinary_register_current": "philosophy_of_technology",
                    "language": "en",
                },
                "semantic_profile": {
                    "disciplinary_registers": ["philosophy_of_technology", "STS"],
                    "schools_and_traditions": ["Simondon", "Stiegler"],
                    "theoretical_shoulders": ["Simondon, 1958"],
                    "argument_move_type": "concept_reconstruction",
                },
            },
        )
        out = agent.execute_deterministic(inp)
        self.assertEqual(out.output_entity_type, "FieldPositionModel")
        fpm = FieldPositionModel.from_dict(out.output_entity)
        self.assertEqual(fpm.entity_type, "article")
        self.assertEqual(fpm.entity_id, "art_test")
        self.assertIn("philosophy_of_technology", fpm.discipline_vector)
        self.assertIn("Simondon", fpm.school_affiliation_vector)

    def test_missing_article(self):
        agent = ArticleFieldPositionerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_field_positioner",
            entities={},
        )
        out = agent.execute_deterministic(inp)
        self.assertEqual(out.confidence, "none")


class TestVenueFieldPositionerDeterministic(unittest.TestCase):
    def test_returns_field_position_model(self):
        agent = VenueFieldPositionerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="venue_field_positioner",
            entities={
                "venue": {
                    "venue_model_id": "ven_test",
                    "canonical_name": "Logos",
                    "scope_summary": "philosophy technology phenomenology",
                    "review_type": "double-blind",
                    "open_access_model": "diamond",
                    "languages": ["ru", "en"],
                },
            },
        )
        out = agent.execute_deterministic(inp)
        self.assertEqual(out.output_entity_type, "FieldPositionModel")
        fpm = FieldPositionModel.from_dict(out.output_entity)
        self.assertEqual(fpm.entity_type, "venue")
        self.assertEqual(fpm.entity_id, "ven_test")
        self.assertEqual(fpm.institutional_signals.get("review_model"), "double-blind")


class TestCaseIntakeBuildsArticleFPM(unittest.TestCase):
    def setUp(self):
        _ensure_no_llm()

    def test_intake_text_populates_article_fpm(self):
        case = Case(title="t")
        text = (
            "Abstract: This paper reconceptualizes Simondon's notion of individuation "
            "in the context of contemporary philosophy of technology and STS. "
            "We argue that the relation between technical objects and milieus "
            "requires a renewed methodological framework."
        ) * 4
        case.intake_text(text, input_type="article", search_depth="none")
        self.assertIsNotNone(case.article_model)
        self.assertIsNotNone(case.semantic_profile)
        self.assertIsNotNone(case.article_field_position)
        self.assertEqual(case.article_field_position.entity_type, "article")

    def test_intake_venue_populates_venue_fpm(self):
        case = Case(title="t")
        text = (
            "Author guidelines for the journal. The scope of the journal: "
            "philosophy, ISSN: 1234-5678. Editorial board: ..."
        )
        case.intake_text(text, input_type="venue", search_depth="none")
        self.assertIsNotNone(case.investigated_venue)
        self.assertIsNotNone(case.venue_field_position)
        self.assertEqual(case.venue_field_position.entity_type, "venue")


class TestFitChainComputesFPMFit(unittest.TestCase):
    def setUp(self):
        _ensure_no_llm()

    def test_field_position_fit_present_when_both_fpms_set(self):
        case = Case(title="t")
        text = (
            "Abstract: We discuss the philosophy of technology in relation to "
            "Simondon and STS frameworks. Methods: textual analysis. "
            "We argue for a reconstruction of the technical individuation concept."
        ) * 5
        case.intake_text(text, input_type="article", search_depth="none")
        # Inject venue FPM directly so we don't need investigate_venue
        case.selected_venue = VenueModel(
            canonical_name="Test Venue",
            scope_summary="philosophy technology STS",
        )
        case.venue_field_position = FieldPositionModel(
            entity_type="venue",
            entity_id=case.selected_venue.venue_model_id,
            discipline_vector={"philosophy_of_technology": 0.6, "STS": 0.4},
            discipline_envelope={
                "philosophy_of_technology": [0.0, 1.0],
                "STS": [0.0, 1.0],
            },
            school_affiliation_vector={"Simondon": 0.5},
            school_envelope={"Simondon": [0.0, 1.0]},
            argument_move_vector={"concept_reconstruction": 0.5},
            argument_move_envelope={"concept_reconstruction": [0.0, 1.0]},
            language_register={"language": "en"},
        )
        # Trigger fit chain
        case._run_fit_chain()
        self.assertIsNotNone(case.fit_assessment)
        self.assertIsNotNone(case.field_position_fit)
        self.assertIn("overall_label", case.field_position_fit)
        self.assertIn("axes", case.field_position_fit)
        # Sanity: get_fit() returns merged structure
        fit_payload = case.get_fit()
        self.assertIn("field_position_fit", fit_payload)


class TestCaseSnapshotRoundTrip(unittest.TestCase):
    def setUp(self):
        _ensure_no_llm()

    def test_round_trip_preserves_fpms(self):
        case = Case(title="round trip")
        case.article_field_position = FieldPositionModel(
            entity_type="article",
            entity_id="art_xx",
            discipline_vector={"phil": 0.8, "STS": 0.2},
        )
        case.venue_field_position = FieldPositionModel(
            entity_type="venue",
            entity_id="ven_xx",
            discipline_vector={"phil": 0.5},
            discipline_envelope={"phil": [0.3, 0.9]},
        )
        case.field_position_fit = {
            "overall_label": "possible",
            "summary": {"contained": 2, "adjacent": 1, "outside": 0, "unknown": 5, "total": 8},
            "axes": [],
        }

        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.article_field_position)
        self.assertEqual(restored.article_field_position.entity_id, "art_xx")
        self.assertIsNotNone(restored.venue_field_position)
        self.assertEqual(restored.venue_field_position.discipline_envelope, {"phil": [0.3, 0.9]})
        self.assertEqual(restored.field_position_fit["overall_label"], "possible")

    def test_case_store_persists_fpms(self):
        _ensure_no_llm()
        with tempfile.TemporaryDirectory() as tmp:
            store = CaseStore(data_dir=tmp)
            case = store.create(title="persist")
            case.article_field_position = FieldPositionModel(
                entity_type="article",
                entity_id=case.case_id,
                discipline_vector={"phil": 1.0},
            )
            store.save(case)

            store2 = CaseStore(data_dir=tmp)
            loaded = store2.get(case.case_id)
            self.assertIsNotNone(loaded)
            self.assertIsNotNone(loaded.article_field_position)
            self.assertEqual(loaded.article_field_position.entity_type, "article")


if __name__ == "__main__":
    unittest.main()
