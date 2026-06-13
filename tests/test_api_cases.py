"""Tests for the cockpit API case management."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, CaseStore, CaseStage, _classify_input


class TestClassifyInput(unittest.TestCase):
    def test_short_text_is_abstract(self):
        self.assertEqual(_classify_input("Some short text"), "abstract")

    def test_journal_mention_is_venue(self):
        self.assertEqual(_classify_input("ISSN 1234-5678 for this journal"), "venue")

    def test_reviewer_mention_is_review(self):
        self.assertEqual(
            _classify_input("The reviewer recommended to reject this paper"),
            "review_letter",
        )

    def test_long_text_is_manuscript(self):
        text = "word " * 200
        self.assertEqual(_classify_input(text), "manuscript")


class TestCaseStore(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore()

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
        case = Case(title="Test")
        result = case.intake_text(
            "This paper examines individuation in technical objects "
            "through a Simondonian lens, offering a conceptual analysis "
            "of how technical objects acquire identity through their "
            "functioning within associated milieus.",
        )
        self.assertEqual(result["input_type"], "abstract")
        self.assertTrue(result["article_model_built"])
        self.assertEqual(case.stage, CaseStage.ARTICLE_MODEL)
        self.assertIsNotNone(case.article_model)

    def test_intake_venue(self):
        case = Case()
        result = case.intake_text("ISSN 1234-5678 journal scope")
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
            "individuality through their associated milieu."
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
            "through Simondon's philosophy of technology."
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
            "through Simondon's philosophy of technology."
        )
        d = case.build_dossier()
        self.assertIn("article_model", d)
        self.assertIn("semantic_profile", d)


class TestCaseEvidence(unittest.TestCase):
    def test_evidence_returns_unknown_by_default(self):
        case = Case()
        ev = case.get_evidence("ArticleModel", "genre")
        self.assertEqual(ev["evidence_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
