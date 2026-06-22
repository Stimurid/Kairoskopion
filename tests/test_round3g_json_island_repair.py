"""Round III-G JSON-island repair tests + rubric raw-article gate.

Pins:
  - repair_and_parse finds JSON in prose-before, prose-after,
    fenced-json, multi-block, array-root cases.
  - Garbage-only stays repair_failed with diagnostics.
  - raw_article_text plumbing → rubric_applies via Cyrillic ratio.
  - Existing CitationPlan / Risk / Rewrite paths still hold.
"""

from __future__ import annotations


def _ok_outcome(parsed_dict):
    from kairoskopion.agents.base_shell import LLMAttemptOutcome
    return LLMAttemptOutcome(
        ok=True, parsed=parsed_dict, content_present=True,
        parse_status="parsed_ok",
    )


import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_REPAIR_FAILED,
    repair_and_parse,
)
from kairoskopion.schema import ArticleModel
from kairoskopion.services.writing_rubric import (
    rubric_applies_to_article,
)


# ---------------- JSON-island repair ----------------

class TestJSONIslandRepair(unittest.TestCase):
    def test_prose_before_json_is_recovered(self):
        raw = (
            "Sure, here is my analysis of the article:\n\n"
            '{"risk_items": [{"risk_type": "scope_mismatch", '
            '"severity": "high", "description": "X", "evidence": "Y"}]}'
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        self.assertEqual(len(out.parsed["risk_items"]), 1)

    def test_prose_after_json(self):
        raw = (
            '{"actions": [{"action_id": 1, "target_mismatch": "topic", '
            '"description": "reframe"}]}\n\n'
            "I hope this helps."
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        self.assertEqual(len(out.parsed["actions"]), 1)

    def test_fenced_json(self):
        raw = (
            "Analysis follows:\n"
            "```json\n"
            '{"tradition_gaps": ["postphenomenology"], "unknowns": []}\n'
            "```\n"
            "Done."
        )
        out = repair_and_parse(raw)
        self.assertEqual(out.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(out.parsed["tradition_gaps"], ["postphenomenology"])

    def test_multiple_blocks_first_invalid_second_valid(self):
        """Two JSON-like blocks; first is malformed, second is valid.
        Island repair must select the second."""
        raw = (
            "First attempt:\n"
            "{invalid: notjson, broken}\n"
            "\nSecond attempt:\n"
            '{"risk_items": [{"risk_type": "method_gap", "severity": "medium", '
            '"description": "X", "evidence": "Y"}], "unknowns": []}'
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        self.assertIn("risk_items", out.parsed)
        self.assertEqual(len(out.parsed["risk_items"]), 1)

    def test_thinking_envelope_then_json(self):
        """Sonnet sometimes emits <thinking>...</thinking>{json}."""
        raw = (
            "<thinking>\n"
            "Let me consider the risks for this article...\n"
            "</thinking>\n\n"
            '{"risk_items": [{"risk_type": "scope_mismatch", '
            '"severity": "high", "description": "X", "evidence": "Y"}]}'
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))

    def test_array_root_recovered(self):
        raw = (
            "Here are the actions:\n"
            '[{"action_id": 1, "target_mismatch": "topic", "description": "X"}]'
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        self.assertIsInstance(out.parsed, list)

    def test_garbage_only_fails_safely(self):
        raw = "I cannot produce JSON for this analysis."
        out = repair_and_parse(raw)
        self.assertEqual(out.status, PARSE_STATUS_REPAIR_FAILED)
        self.assertIsNone(out.parsed)

    def test_picks_largest_valid_candidate(self):
        """When multiple valid candidates exist, prefer the largest
        (most-complete-looking)."""
        raw = (
            '{"a": 1}\n\n'
            'Here is the real analysis:\n'
            '{"risk_items": [{"risk_type": "scope_mismatch", "severity": "high", '
            '"description": "X with more content here", "evidence": "evidence_long"}], '
            '"unknowns": ["u1"], "confidence": "medium"}'
        )
        out = repair_and_parse(raw)
        self.assertIn(out.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        # The larger candidate should win
        self.assertIn("risk_items", out.parsed)


# ---------------- Rubric raw-article gate ----------------

class TestRubricRawArticleGate(unittest.TestCase):
    def test_russian_raw_text_triggers_rubric_even_with_sparse_article_model(self):
        a = ArticleModel(
            title_current=None,
            abstract_current=None,
            language=None,
            genre_current="theoretical_essay",
        )
        # Article fields are sparse, but raw text is clearly Russian
        raw = (
            "О чем такое реальная цифровизация: первый кризис первой великой "
            "попытки и пять следствий. В последнее время появилось не "
            "пренебрежимое количество публикаций..."
        ) * 10
        self.assertTrue(rubric_applies_to_article(a, raw_article_text=raw))

    def test_english_raw_text_does_not_trigger_rubric(self):
        a = ArticleModel(
            title_current=None, language=None,
            genre_current="theoretical_essay",
        )
        raw = (
            "This is an English-language article about postphenomenology "
            "and philosophy of technology."
        ) * 10
        self.assertFalse(rubric_applies_to_article(a, raw_article_text=raw))

    def test_empty_raw_text_falls_back_to_article_fields(self):
        a = ArticleModel(
            title_current="Постфеноменологический подход",
            language=None,
            genre_current="unknown",
        )
        # No raw text — gate uses ArticleModel fields
        self.assertTrue(rubric_applies_to_article(a, raw_article_text=""))


# ---------------- Helper signature integration ----------------

class TestRawArticleTextPlumbing(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_risk_officer_accepts_raw_article_text_kwarg(self, mock):
        from kairoskopion.schema import (
            ArticleModel, VenueModel, FitAssessment, MismatchMap,
        )
        from kairoskopion.services.llm_semantic_organs import try_llm_risk_officer
        mock.return_value = _ok_outcome({"risk_items": []})
        a = ArticleModel(title_current="X", language=None,
                         genre_current="theoretical_essay")
        v = VenueModel(canonical_name="V", venue_type="journal")
        f = FitAssessment(axes=[], overall_label="possible")
        mm = MismatchMap(mismatches=[])
        # Must accept raw_article_text kwarg without error
        result = try_llm_risk_officer(
            a, v, None, f, mm, MagicMock(),
            raw_article_text="Это русский текст " * 100,
        )
        self.assertIsNotNone(result)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_rewrite_planner_accepts_raw_article_text_kwarg(self, mock):
        from kairoskopion.schema import (
            ArticleModel, VenueModel, FitAssessment, MismatchMap,
        )
        from kairoskopion.services.llm_semantic_organs import try_llm_rewrite_planner
        mock.return_value = _ok_outcome({"actions": []})
        a = ArticleModel(title_current="X", language=None,
                         genre_current="theoretical_essay")
        v = VenueModel(canonical_name="V", venue_type="journal")
        f = FitAssessment(axes=[], overall_label="possible")
        mm = MismatchMap(mismatches=[
            {"axis": "topic", "severity": "major", "article_side": "X",
             "venue_side": "", "description": "", "possible_actions": [],
             "field_core_risk": "unknown_core_impact"},
        ])
        result = try_llm_rewrite_planner(
            a, v, f, mm, None, MagicMock(),
            raw_article_text="Это русский текст " * 100,
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
