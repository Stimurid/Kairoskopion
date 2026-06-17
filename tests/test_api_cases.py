"""Tests for the cockpit API case management."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, CaseStore, CaseStage


class TestInputClassifierDeterministicFallback(unittest.TestCase):
    """The legacy keyword-based ``_classify_input`` was retired in
    Phase A; routing now goes through ``InputClassifierAgent``. When no
    LLM provider is configured, the agent must return
    ``input_type=unknown`` with ``needs_user_choice=True`` — never a
    silent default to 'manuscript' / 'review_letter'."""

    def setUp(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.input_classifier import InputClassifierAgent
        self.agent = InputClassifierAgent()
        self.AgentInput = AgentInput

    def _run(self, text: str) -> dict:
        out = self.agent.execute_deterministic(
            self.AgentInput(
                operation_id="t",
                agent_role_id="input_classifier",
                raw_text=text,
            )
        )
        return out.output_entity

    def test_short_text_yields_unknown_not_abstract(self):
        result = self._run("Some short text")
        self.assertEqual(result["input_type"], "unknown")
        self.assertTrue(result["needs_user_choice"])

    def test_long_text_yields_unknown_not_manuscript(self):
        # The deterministic fallback never guesses — it asks the user.
        result = self._run("word " * 200)
        self.assertEqual(result["input_type"], "unknown")
        self.assertTrue(result["needs_user_choice"])

    def test_reviewer_word_does_not_route_to_review_letter(self):
        # Regression: prior keyword heuristic flagged any "reviewer"
        # mention as review_letter, silently skipping the whole pipeline.
        result = self._run(
            "The reviewer recommended to reject this paper" * 200,
        )
        self.assertNotEqual(result["input_type"], "review_letter")
        self.assertEqual(result["input_type"], "unknown")
        self.assertTrue(result["needs_user_choice"])

    def test_empty_text_yields_unknown(self):
        result = self._run("")
        self.assertEqual(result["input_type"], "unknown")
        self.assertTrue(result["needs_user_choice"])


class TestCaseStore(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self.store = CaseStore(data_dir=self._tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_create_case(self):
        case = self.store.create(title="Test case")
        self.assertIn("case_", case.case_id)
        self.assertEqual(case.title, "Test case")
        self.assertEqual(case.stage, CaseStage.EMPTY)

    def test_get_case(self):
        case = self.store.create()
        retrieved = self.store.get(case.case_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.case_id, case.case_id)

    def test_get_nonexistent(self):
        self.assertIsNone(self.store.get("nonexistent"))

    def test_all_cases(self):
        self.store.create(title="A")
        self.store.create(title="B")
        self.assertEqual(len(self.store.all()), 2)

    def test_delete_case(self):
        case = self.store.create()
        self.assertTrue(self.store.delete(case.case_id))
        self.assertIsNone(self.store.get(case.case_id))

    def test_delete_nonexistent(self):
        self.assertFalse(self.store.delete("nonexistent"))


class TestCaseIntake(unittest.TestCase):
    def test_intake_abstract(self):
        # Phase A: classifier is now LLM-driven; without a provider
        # the test must pass the type explicitly via the chip
        # equivalent (input_type="article") so the article-modeling
        # pipeline runs deterministically.
        case = Case(title="Test")
        result = case.intake_text(
            "This paper examines individuation in technical objects "
            "through a Simondonian lens, offering a conceptual analysis "
            "of how technical objects acquire identity through their "
            "functioning within associated milieus.",
            input_type="article",
        )
        self.assertEqual(result["input_type"], "article")
        self.assertTrue(result["article_model_built"])
        self.assertEqual(case.stage, CaseStage.ARTICLE_MODEL)
        self.assertIsNotNone(case.article_model)

    def test_intake_venue(self):
        case = Case()
        result = case.intake_text(
            "ISSN 1234-5678 journal scope",
            input_type="venue",
        )
        self.assertEqual(result["input_type"], "venue")
        self.assertFalse(result["article_model_built"])
        self.assertEqual(case.stage, CaseStage.INTAKE)


class TestCaseConfirm(unittest.TestCase):
    def setUp(self):
        self.case = Case()
        self.case.intake_text(
            "This paper offers a conceptual analysis of individuation "
            "in technical objects, drawing on Simondon's philosophy of "
            "technology to argue that technical objects have genuine "
            "individuality through their associated milieu.",
            input_type="article",
        )

    def test_confirm_sets_lifecycle(self):
        result = self.case.confirm_article_model(
            protected_core=["thesis", "object"],
        )
        self.assertTrue(result["confirmed"])
        self.assertEqual(result["lifecycle_status"], "confirmed")
        self.assertEqual(self.case.article_model.protected_core, ["thesis", "object"])

    def test_confirm_logs_decision(self):
        self.case.confirm_article_model(protected_core=["thesis"])
        self.assertEqual(len(self.case.decision_log), 1)
        self.assertEqual(self.case.decision_log[0]["action"], "confirm_article_model")


class TestCaseScenario(unittest.TestCase):
    def test_set_scenario(self):
        case = Case()
        case.intake_text(
            "A conceptual analysis of individuation in technical objects "
            "through Simondon's philosophy of technology.",
            input_type="article",
        )
        result = case.set_scenario({
            "goal": "Q1-Q2 Scopus publication",
            "rewrite_depth_allowed": "medium",
            "language": "en",
        })
        self.assertIn("submission_scenario_id", result)
        self.assertEqual(case.stage, CaseStage.SCENARIO)
        self.assertEqual(len(case.decision_log), 1)


class TestCaseSummary(unittest.TestCase):
    def test_summary_fields(self):
        case = Case(title="My case")
        s = case.summary()
        self.assertIn("case_id", s)
        self.assertEqual(s["title"], "My case")
        self.assertEqual(s["stage"], "empty")
        self.assertIn("objects_present", s)

    def test_to_dict_fields(self):
        case = Case(title="Test")
        d = case.to_dict()
        self.assertIn("case_id", d)
        self.assertIn("objects_present", d)
        self.assertIn("quality_gates", d)


class TestCaseDossier(unittest.TestCase):
    def test_empty_dossier(self):
        case = Case(title="Empty")
        d = case.build_dossier()
        self.assertEqual(d["case_id"], case.case_id)
        self.assertIn("generated_at", d)

    def test_dossier_with_article(self):
        case = Case()
        case.intake_text(
            "A conceptual analysis of individuation in technical objects "
            "through Simondon's philosophy of technology.",
            input_type="article",
        )
        d = case.build_dossier()
        self.assertIn("article_model", d)
        self.assertIn("semantic_profile", d)


class TestCaseVenueInvestigation(unittest.TestCase):
    def test_investigate_venue_text(self):
        case = Case(title="Venue test")
        result = case.investigate_venue(
            "# Venue Seed Profile: Philosophy & Technology\n"
            "- **ISSN:** 1234-5678\n"
            "- **Scope:** Philosophy of technology and engineering\n"
            "- **Review type:** Double-blind peer review\n"
        )
        self.assertIn("venue", result)
        self.assertIsNotNone(case.investigated_venue)
        self.assertEqual(len(case.decision_log), 1)
        self.assertEqual(case.decision_log[0]["action"], "investigate_venue")

    def test_intake_venue_auto_investigates(self):
        case = Case()
        result = case.intake_text(
            "ISSN 1234-5678 author guidelines for this journal",
            input_type="venue",
        )
        self.assertEqual(result["input_type"], "venue")
        self.assertIn("venue_investigated", result)


class TestCaseEvidence(unittest.TestCase):
    def test_evidence_returns_unknown_by_default(self):
        case = Case()
        ev = case.get_evidence("ArticleModel", "genre")
        self.assertEqual(ev["evidence_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
