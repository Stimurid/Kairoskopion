"""Round III-K2: RiskOfficer JSON contract hardening tests.

10 focused tests per the Track 4 acceptance criteria:
1. Pure JSON → parsed_ok
2. ```json fenced → repaired_ok
3. Prose-before-JSON → island extracted
4. <thinking> wrapped → xml stripped + parsed
5. risk_type normalization (prompt enum → canonical)
6. severity normalization (tolerant values)
7. Empty risk_items → llm_grounded_partial
8. None/missing parsed → specific failure category
9. Malformed JSON with balanced extraction
10. Full adapter chain with mock outcome
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from kairoskopion.llm.json_repair import repair_and_parse
from kairoskopion.services.llm_semantic_organs import (
    _normalize_risk_type,
    _RISK_SEVERITY_MAP,
    try_llm_risk_officer,
)


# ---- Fixtures ----

VALID_RISK_JSON = json.dumps({
    "risk_items": [
        {
            "risk_type": "desk_rejection",
            "severity": "high",
            "description": "Тема не соответствует профилю журнала",
            "evidence": "Журнал фокусируется на X, статья про Y",
            "mitigation": "Переформулировать введение",
        },
        {
            "risk_type": "citation_gap",
            "severity": "medium",
            "description": "Недостаточно ссылок на традицию журнала",
            "evidence": "0 из 10 ключевых авторов процитированы",
            "mitigation": "Добавить ссылки на работы Z",
        },
    ],
    "overall_risk_level": "high",
    "unknowns": ["Не удалось проверить требования к оформлению"],
    "confidence": "medium",
}, ensure_ascii=False)

FENCED_RISK_JSON = f"```json\n{VALID_RISK_JSON}\n```"

PROSE_BEFORE_JSON = (
    "Вот мой анализ рисков для данной пары статья-журнал. "
    "Я выявил следующие основные риски:\n\n"
    + VALID_RISK_JSON
)

THINKING_WRAPPED_JSON = (
    "<thinking>\nLet me analyze the risks for this article-venue pair.\n"
    "The article discusses digital epistemology...\n"
    "The venue focuses on philosophy of science...\n"
    "</thinking>\n"
    + VALID_RISK_JSON
)

MALFORMED_JSON_WITH_TRAILING_COMMA = (
    '{"risk_items": ['
    '{"risk_type": "scope_mismatch", "severity": "high", '
    '"description": "Out of scope", "evidence": "data", "mitigation": null},'
    '], "unknowns": []}'
)

XML_RESPONSE_WRAPPED = (
    "<response>\n" + VALID_RISK_JSON + "\n</response>"
)


class TestJsonRepairRiskOfficer(unittest.TestCase):
    """Tests 1-4: JSON repair for RiskOfficer-shaped responses."""

    def test_01_pure_json_parsed_ok(self):
        """Pure valid JSON → parsed_ok, no repair needed."""
        r = repair_and_parse(VALID_RISK_JSON)
        self.assertEqual(r.status, "parsed_ok")
        self.assertIsInstance(r.parsed, dict)
        self.assertIn("risk_items", r.parsed)
        self.assertEqual(len(r.parsed["risk_items"]), 2)

    def test_02_fenced_json_repaired_ok(self):
        """```json ... ``` fenced → repaired_ok."""
        r = repair_and_parse(FENCED_RISK_JSON)
        self.assertIn(r.status, ("parsed_ok", "repaired_ok"))
        self.assertIsInstance(r.parsed, dict)
        self.assertEqual(len(r.parsed["risk_items"]), 2)

    def test_03_prose_before_json_island_extracted(self):
        """Prose + JSON → island extraction succeeds."""
        r = repair_and_parse(PROSE_BEFORE_JSON)
        self.assertIn(r.status, ("repaired_ok",))
        self.assertIsInstance(r.parsed, dict)
        self.assertIn("risk_items", r.parsed)
        self.assertEqual(len(r.parsed["risk_items"]), 2)

    def test_04_thinking_tags_stripped(self):
        """<thinking>...</thinking> + JSON → xml stripped, parsed."""
        r = repair_and_parse(THINKING_WRAPPED_JSON)
        self.assertIn(r.status, ("parsed_ok", "repaired_ok"))
        self.assertIsInstance(r.parsed, dict)
        self.assertIn("risk_items", r.parsed)
        self.assertEqual(len(r.parsed["risk_items"]), 2)
        has_xml_step = any("xml" in s for s in r.repair_steps)
        has_island_step = any("island" in s or "balanced" in s for s in r.repair_steps)
        self.assertTrue(
            has_xml_step or has_island_step,
            f"Expected xml_tags_stripped or island step, got: {r.repair_steps}",
        )

    def test_04b_response_tags_stripped(self):
        """<response>...</response> wrapper → xml stripped, parsed."""
        r = repair_and_parse(XML_RESPONSE_WRAPPED)
        self.assertIn(r.status, ("parsed_ok", "repaired_ok"))
        self.assertIsInstance(r.parsed, dict)

    def test_trailing_comma_repaired(self):
        """Trailing comma in array → repaired_ok."""
        r = repair_and_parse(MALFORMED_JSON_WITH_TRAILING_COMMA)
        self.assertIn(r.status, ("repaired_ok",))
        self.assertIsInstance(r.parsed, dict)
        self.assertEqual(len(r.parsed["risk_items"]), 1)

    def test_json_with_line_comments_repaired(self):
        """JSON with // comments → comments stripped, parsed."""
        raw = '{"risk_items": [\n  // desk rejection risk\n  {"risk_type": "desk_rejection", "severity": "high", "description": "topic mismatch"}\n]}'
        r = repair_and_parse(raw)
        self.assertIn(r.status, ("repaired_ok",))
        self.assertEqual(len(r.parsed["risk_items"]), 1)
        self.assertIn("json_comments_stripped", r.repair_steps)

    def test_json_with_block_comments_repaired(self):
        """JSON with /* block comments */ → stripped, parsed."""
        raw = '{"risk_items": [/* this is a risk */ {"risk_type": "scope_mismatch", "severity": "medium", "description": "test"}]}'
        r = repair_and_parse(raw)
        self.assertIn(r.status, ("repaired_ok",))
        self.assertEqual(len(r.parsed["risk_items"]), 1)


class TestRiskTypeNormalization(unittest.TestCase):
    """Test 5: risk_type normalization from prompt enum to canonical."""

    def test_05_prompt_enum_to_canonical(self):
        """Prompt-family enum values normalize to canonical RISK_TYPES."""
        cases = {
            "desk_rejection": "desk_reject_risk",
            "method_gap": "methodology_mismatch",
            "field_core_destruction": "core_transformation_risk",
            "compliance_gap": "formatting_violation",
            "language_barrier": "language_quality",
        }
        for prompt_val, expected in cases.items():
            with self.subTest(prompt_val=prompt_val):
                result = _normalize_risk_type(prompt_val)
                self.assertEqual(result, expected)

    def test_canonical_values_unchanged(self):
        """Values already canonical pass through."""
        for v in ("scope_mismatch", "citation_gap", "ethical_concern",
                  "cost_risk", "timeline_risk", "ai_policy_risk"):
            self.assertEqual(_normalize_risk_type(v), v)

    def test_title_case_normalized(self):
        """Title-case and space variants normalize."""
        self.assertEqual(
            _normalize_risk_type("Scope Mismatch"), "scope_mismatch"
        )
        self.assertEqual(
            _normalize_risk_type("CITATION-GAP"), "citation_gap"
        )

    def test_unknown_passthrough(self):
        """Unknown risk types pass through, not silently dropped."""
        self.assertEqual(
            _normalize_risk_type("completely_novel_risk"),
            "completely_novel_risk",
        )

    def test_empty_returns_unknown(self):
        self.assertEqual(_normalize_risk_type(""), "unknown")


class TestSeverityNormalization(unittest.TestCase):
    """Test 6: severity normalization tolerates variant values."""

    def test_06_standard_severities(self):
        """Standard severity values map correctly."""
        self.assertEqual(_RISK_SEVERITY_MAP["critical"], "blocking")
        self.assertEqual(_RISK_SEVERITY_MAP["high"], "major")
        self.assertEqual(_RISK_SEVERITY_MAP["medium"], "major")
        self.assertEqual(_RISK_SEVERITY_MAP["low"], "minor")
        self.assertEqual(_RISK_SEVERITY_MAP["informational"], "informational")

    def test_06_tolerant_severities(self):
        """Non-standard severity values also accepted."""
        self.assertEqual(_RISK_SEVERITY_MAP["moderate"], "major")
        self.assertEqual(_RISK_SEVERITY_MAP["severe"], "blocking")
        self.assertEqual(_RISK_SEVERITY_MAP["warning"], "minor")
        self.assertEqual(_RISK_SEVERITY_MAP["info"], "informational")


class TestRiskOfficerAdapterChain(unittest.TestCase):
    """Tests 7-10: full adapter chain with mock LLM outcomes."""

    def _make_mock_provider(self):
        from kairoskopion.llm.provider import LLMProvider
        mock = MagicMock(spec=LLMProvider)
        return mock

    def _make_article(self):
        from kairoskopion.schema import ArticleModel
        return ArticleModel(
            article_model_id="art_test",
            title_current="Test Article",
            abstract_current="Test abstract for risk assessment.",
        )

    def _make_venue(self):
        from kairoskopion.schema import VenueModel
        return VenueModel(
            venue_model_id="ven_test",
            canonical_name="Test Journal",
        )

    def test_07_empty_risk_items_partial_grounded(self):
        """LLM returns valid JSON with empty risk_items → llm_grounded_partial."""
        provider = self._make_mock_provider()
        resp = MagicMock()
        resp.content = json.dumps({"risk_items": [], "unknowns": ["all clear"]})
        resp.parsed = None
        resp.model = "test"
        resp.input_tokens = 100
        resp.output_tokens = 50
        resp.latency_ms = 200
        provider.complete.return_value = resp

        result = try_llm_risk_officer(
            self._make_article(), self._make_venue(),
            None, None, None, provider,
        )
        self.assertEqual(result.semantic_status, "llm_grounded_partial")
        self.assertEqual(len(result.risk_items), 0)
        diag = result.attempt_diagnostics or {}
        self.assertEqual(diag.get("provider_status"), "called_ok")

    def test_08_none_parsed_specific_failure_category(self):
        """LLM returns unparseable content → specific failure category."""
        provider = self._make_mock_provider()
        resp = MagicMock()
        resp.content = "This is completely unparseable prose with no JSON at all. " * 50
        resp.parsed = None
        resp.model = "test"
        resp.input_tokens = 100
        resp.output_tokens = 500
        resp.latency_ms = 300
        provider.complete.return_value = resp

        result = try_llm_risk_officer(
            self._make_article(), self._make_venue(),
            None, None, None, provider,
        )
        self.assertEqual(result.semantic_status, "needs_llm")
        self.assertEqual(len(result.risk_items), 0)
        diag = result.attempt_diagnostics or {}
        self.assertIn(
            diag.get("parse_failure_category"),
            ("json_repair_exhausted", "no_json_found", "repair_failed"),
        )

    def test_09_fenced_json_through_adapter(self):
        """LLM returns fenced JSON → adapter extracts and normalizes."""
        risk_data = {
            "risk_items": [
                {
                    "risk_type": "desk_rejection",
                    "severity": "high",
                    "description": "Topic mismatch",
                    "evidence": "Article is about X, journal about Y",
                    "mitigation": "Reframe introduction",
                },
            ],
            "confidence": "medium",
        }
        provider = self._make_mock_provider()
        resp = MagicMock()
        resp.content = f"```json\n{json.dumps(risk_data)}\n```"
        resp.parsed = None
        resp.model = "test"
        resp.input_tokens = 100
        resp.output_tokens = 200
        resp.latency_ms = 150
        provider.complete.return_value = resp

        result = try_llm_risk_officer(
            self._make_article(), self._make_venue(),
            None, None, None, provider,
        )
        self.assertIn(result.semantic_status, ("llm_grounded", "llm_grounded_partial"))
        self.assertGreaterEqual(len(result.risk_items), 1)
        self.assertEqual(
            result.risk_items[0]["risk_type"], "desk_reject_risk",
        )

    def test_10_thinking_tags_through_adapter(self):
        """LLM returns <thinking> + JSON → adapter strips and parses."""
        risk_data = {
            "risk_items": [
                {
                    "risk_type": "scope_mismatch",
                    "severity": "medium",
                    "description": "Scope divergence",
                    "evidence": "Venue scope is X",
                    "mitigation": None,
                },
            ],
        }
        wrapped = (
            "<thinking>\nAnalyzing the article-venue fit...\n</thinking>\n"
            + json.dumps(risk_data)
        )
        provider = self._make_mock_provider()
        resp = MagicMock()
        resp.content = wrapped
        resp.parsed = None
        resp.model = "test"
        resp.input_tokens = 100
        resp.output_tokens = 200
        resp.latency_ms = 150
        provider.complete.return_value = resp

        result = try_llm_risk_officer(
            self._make_article(), self._make_venue(),
            None, None, None, provider,
        )
        self.assertIn(result.semantic_status, ("llm_grounded", "llm_grounded_partial"))
        self.assertGreaterEqual(len(result.risk_items), 1)


if __name__ == "__main__":
    unittest.main()
