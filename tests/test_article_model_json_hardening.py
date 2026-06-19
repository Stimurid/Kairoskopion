"""Tests for ArticleModeler JSON parsing/repair/validation hardening.

Root cause investigated and fixed:
- ``_schema_required_present`` flagged ``"foo": null`` as missing even
  when the schema declared ``"type": ["string", "null"]`` and the
  prompt explicitly instructed the LLM to use null for unknown fields.
  Effect: most valid LLM outputs were rejected as
  ``schema_validation_failed`` and silently fell to the deterministic
  path.
- Provider-call exceptions (timeout, network, empty response) were
  mislabelled as ``parse_status="invalid_json"`` even though no JSON
  parse had been attempted. Fixed to ``"not_attempted"`` so the UI
  can distinguish "LLM never returned" from "LLM returned bad JSON".

Additional hardening:
- Enum normalization: ``"Theoretical Essay"`` / ``"Theoretical_Essay"``
  → ``"theoretical_essay"`` before schema check.
- UTF-8 BOM and non-breaking space stripping before parse.

These tests verify behaviour on representative inputs; they do not
exercise the live LLM provider.
"""

from __future__ import annotations

import json
import unittest

from kairoskopion.llm.json_repair import (
    PARSE_STATUS_INVALID_JSON,
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIR_FAILED,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
    repair_and_parse,
)
from kairoskopion.prompts.article_modeling import (
    ARTICLE_MODELING_OUTPUT_SCHEMA,
)


def _valid_output() -> dict:
    """Canonical valid-shape ArticleModelExtraction with explicit nulls
    for null-allowed required fields, mirroring the prompt's
    instruction to the LLM."""
    return {
        "title": None,
        "abstract_summary": None,
        "language": "ru",
        "article_stage": "unknown",
        "problem_statement": None,
        "research_question": None,
        "object_of_inquiry": None,
        "core_claims": [],
        "secondary_claims": [],
        "argument_structure": None,
        "method_status": "unknown",
        "method_description": None,
        "genre_current": "unknown",
        "disciplinary_register_current": None,
        "novelty_mode": "unknown",
        "theoretical_shoulders": [],
        "opponents_or_contrasts": [],
        "key_terms": [],
        "citation_ecology_description": None,
        "protected_core_candidate": [],
        "mutable_zones": [],
        "high_risk_zones": [],
        "unknowns": ["everything"],
        "assumptions": [],
        "confidence": "low",
        "questions_for_user": ["What is this?"],
    }


SCHEMA = ARTICLE_MODELING_OUTPUT_SCHEMA


class TestNullsForNullAllowedRequiredFields(unittest.TestCase):
    """The bug that drove production into the deterministic fallback."""

    def test_valid_output_with_explicit_nulls_parses_ok(self):
        out = repair_and_parse(json.dumps(_valid_output()), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(out.validation_errors, [])
        self.assertIsInstance(out.parsed, dict)

    def test_missing_key_still_flags_schema_validation_failed(self):
        d = _valid_output()
        del d["title"]
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_SCHEMA_VALIDATION_FAILED)
        self.assertTrue(any("title" in e for e in out.validation_errors))

    def test_non_null_required_field_with_null_still_flags(self):
        # core_claims has type "array" (not nullable) but is required.
        d = _valid_output()
        d["core_claims"] = None
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_SCHEMA_VALIDATION_FAILED)
        self.assertTrue(any("core_claims" in e for e in out.validation_errors))


class TestFencesAndProse(unittest.TestCase):
    def test_fenced_json_parses(self):
        raw = "Here is the JSON:\n```json\n" + json.dumps(_valid_output()) + "\n```"
        out = repair_and_parse(raw, schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_REPAIRED_OK)
        self.assertIn("fences_stripped", out.repair_steps)

    def test_fenced_plain_backticks_parses(self):
        raw = "```\n" + json.dumps(_valid_output()) + "\n```"
        out = repair_and_parse(raw, schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_REPAIRED_OK)

    def test_trailing_prose_repairs(self):
        raw = json.dumps(_valid_output()) + "\n\nLet me know if you need more details!"
        out = repair_and_parse(raw, schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_REPAIRED_OK)
        self.assertIn("extracted_balanced_{", out.repair_steps)

    def test_leading_prose_repairs(self):
        raw = "Sure, here is the analysis:\n" + json.dumps(_valid_output())
        out = repair_and_parse(raw, schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_REPAIRED_OK)


class TestEnumNormalization(unittest.TestCase):
    def test_uppercased_underscore_enum_normalized(self):
        d = _valid_output()
        d["genre_current"] = "Theoretical_Essay"
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(out.parsed["genre_current"], "theoretical_essay")

    def test_spaced_enum_normalized(self):
        d = _valid_output()
        d["genre_current"] = "theoretical essay"
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(out.parsed["genre_current"], "theoretical_essay")

    def test_hyphen_enum_normalized(self):
        d = _valid_output()
        d["genre_current"] = "theoretical-essay"
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(out.parsed["genre_current"], "theoretical_essay")

    def test_unknown_enum_value_left_alone(self):
        # No canonical match → value preserved so family-level validator
        # can warn on it. We don't invent a substitute.
        d = _valid_output()
        d["genre_current"] = "manifesto"
        out = repair_and_parse(json.dumps(d), schema=SCHEMA)
        # required fields all present → parsed_ok; the bogus enum is
        # caught by validate_article_extraction at the agent level
        # (warnings list), not by repair-time schema check.
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(out.parsed["genre_current"], "manifesto")


class TestBOMAndWhitespace(unittest.TestCase):
    def test_bom_prefix_handled(self):
        raw = "﻿" + json.dumps(_valid_output())
        out = repair_and_parse(raw, schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_PARSED_OK)
        self.assertIn("bom_stripped", out.repair_steps)


class TestPureGarbageStillFails(unittest.TestCase):
    def test_garbage_returns_repair_failed(self):
        out = repair_and_parse("totally not json", schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_REPAIR_FAILED)
        self.assertIsNone(out.parsed)

    def test_empty_returns_invalid_json(self):
        out = repair_and_parse("", schema=SCHEMA)
        self.assertEqual(out.status, PARSE_STATUS_INVALID_JSON)
        self.assertIn("empty_input", out.repair_steps)


class TestAntiLeak(unittest.TestCase):
    """Hardening must not expose raw provider output anywhere."""

    def test_no_raw_output_in_repair_outcome(self):
        bogus_with_secret = (
            "BEGIN_SECRET_PAYLOAD totally garbage END_SECRET_PAYLOAD"
        )
        out = repair_and_parse(bogus_with_secret, schema=SCHEMA)
        d = out.to_dict()
        flat = json.dumps(d, ensure_ascii=False)
        self.assertNotIn("BEGIN_SECRET_PAYLOAD", flat)
        self.assertNotIn("END_SECRET_PAYLOAD", flat)
        # repair_outcome.to_dict() exposes only metadata (status, steps,
        # error summaries), never the raw input string.

    def test_no_traceback_introduced(self):
        out = repair_and_parse("{ broken", schema=SCHEMA)
        flat = json.dumps(out.to_dict(), ensure_ascii=False)
        self.assertNotIn("Traceback", flat)


class TestArticleModelerExceptionLabel(unittest.TestCase):
    """Provider exception must not be labelled as invalid_json."""

    def _failing_provider(self):
        class _Boom:
            def complete(self, *_a, **_kw):
                raise RuntimeError("simulated network/timeout/empty-response")
        return _Boom()

    def test_provider_exception_labelled_as_not_attempted(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_modeler",
            raw_text="Краткий конспект текста статьи о философии техники.",
        )
        out = agent.execute(inp, self._failing_provider())
        ea = out.output_entity.get("extraction_attempt")
        self.assertIsNotNone(ea)
        # The provider never produced JSON to attempt parsing; honest
        # label is "not_attempted" (not "invalid_json").
        self.assertEqual(ea["parse_status"], "not_attempted")
        # Fallback metadata still surfaces correctly
        self.assertTrue(ea["fallback_used"])
        self.assertEqual(ea["fallback_reason"], "provider_error")

    def test_provider_exception_does_not_leak_internals(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput

        agent = ArticleModelerAgent()
        out = agent.execute(
            AgentInput(operation_id="t", agent_role_id="article_modeler", raw_text="x"),
            self._failing_provider(),
        )
        flat = json.dumps(out.output_entity, ensure_ascii=False)
        self.assertNotIn("Traceback", flat)
        # raw_output_ref must be null/absent everywhere in metadata.
        ea = out.output_entity.get("extraction_attempt") or {}
        self.assertIn(ea.get("raw_output_ref"), (None, ""))


if __name__ == "__main__":
    unittest.main()
