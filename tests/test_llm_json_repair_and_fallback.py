"""LLM JSON repair + visible fallback tests (task spec §F)."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from kairoskopion.llm.attempt_metadata import (
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_REPAIR_FAILED,
    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
    LLMAttemptMetadata,
    user_warning_for,
)
from kairoskopion.llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIR_FAILED,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
    repair_and_parse,
)
from kairoskopion.services.human_readable_card import article_model_human_view


# ---------------------------------------------------------------------------
# Repair utility (task spec §F.1–§F.6)
# ---------------------------------------------------------------------------

class TestJsonRepair(unittest.TestCase):
    def test_plain_json_parses_as_is(self):
        r = repair_and_parse('{"a": 1, "b": [2,3]}')
        self.assertEqual(r.status, PARSE_STATUS_PARSED_OK)
        self.assertEqual(r.parsed, {"a": 1, "b": [2, 3]})
        self.assertEqual(r.repair_steps, ["as_is"])

    def test_fenced_json_repairs(self):
        r = repair_and_parse('```json\n{"a": 1}\n```')
        self.assertEqual(r.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(r.parsed, {"a": 1})
        self.assertIn("fences_stripped", r.repair_steps)

    def test_unfenced_code_block_repairs(self):
        r = repair_and_parse('```\n{"a": 1}\n```')
        self.assertEqual(r.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(r.parsed, {"a": 1})

    def test_prose_around_json_extracts(self):
        s = 'Sure, here is your JSON:\n{"a": 1, "b": "ok"}\nLet me know if you need more.'
        r = repair_and_parse(s)
        self.assertEqual(r.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(r.parsed, {"a": 1, "b": "ok"})
        self.assertIn("extracted_balanced_{", r.repair_steps)

    def test_trailing_comma_repairs(self):
        r = repair_and_parse('{"a": 1, "b": [2,3,],}')
        self.assertEqual(r.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(r.parsed, {"a": 1, "b": [2, 3]})
        self.assertIn("trailing_commas_stripped", r.repair_steps)

    def test_smart_quotes_repair(self):
        # Curly quotes around keys/values
        r = repair_and_parse('{“a”: 1, “b”: “ok”}')
        self.assertEqual(r.status, PARSE_STATUS_REPAIRED_OK)
        self.assertEqual(r.parsed, {"a": 1, "b": "ok"})

    def test_schema_missing_required_field_does_not_invent(self):
        schema = {"type": "object", "required": ["title", "claims"],
                  "properties": {"title": {"type": "string"},
                                  "claims": {"type": "array"}}}
        r = repair_and_parse('{"title": "T"}', schema=schema)
        self.assertEqual(r.status, PARSE_STATUS_SCHEMA_VALIDATION_FAILED)
        self.assertIn("claims", " ".join(r.validation_errors))
        # parsed is preserved so caller can inspect — but status flags fail
        self.assertEqual(r.parsed.get("title"), "T")
        # We did NOT invent claims
        self.assertNotIn("claims", r.parsed)

    def test_optional_fields_get_safe_defaults(self):
        schema = {"type": "object", "required": ["title"],
                  "properties": {"title": {"type": "string"},
                                  "claims": {"type": "array"},
                                  "tags": {"type": "object"},
                                  "note": {"type": "string"}}}
        r = repair_and_parse('{"title": "T"}', schema=schema)
        # Input parsed cleanly as-is; we filled optional defaults
        # (not technically "repair" — input was valid JSON).
        self.assertIn(r.status, (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK))
        self.assertEqual(r.parsed["claims"], [])
        self.assertEqual(r.parsed["tags"], {})
        self.assertEqual(r.parsed["note"], "")

    def test_empty_input_marked_invalid(self):
        r = repair_and_parse("")
        # Empty input is flagged invalid (not silently dropped)
        self.assertIn(r.status, ("invalid_json",))

    def test_unrecoverable_text_marks_repair_failed(self):
        r = repair_and_parse("absolutely no json here at all")
        self.assertEqual(r.status, PARSE_STATUS_REPAIR_FAILED)
        self.assertIsNone(r.parsed)


# ---------------------------------------------------------------------------
# LLMAttemptMetadata
# ---------------------------------------------------------------------------

class TestAttemptMetadata(unittest.TestCase):
    def test_parse_ok_has_no_warning(self):
        m = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible", model="gpt-4o-mini",
            latency_ms=1200.0, content_present=True,
        )
        self.assertFalse(m.fallback_used)
        self.assertIsNone(m.warning_for_user)
        self.assertEqual(m.parse_status, "parsed_ok")

    def test_repaired_ok_marks_repaired(self):
        m = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible", model="m", latency_ms=10.0,
            content_present=True, repaired=True,
            repair_steps=["fences_stripped"],
        )
        self.assertEqual(m.parse_status, "repaired_ok")
        self.assertTrue(m.repair_attempted)
        self.assertEqual(m.repair_status, "repaired_ok")
        self.assertFalse(m.fallback_used)

    def test_fallback_carries_visible_warning(self):
        for reason in (
            FALLBACK_REASON_INVALID_JSON,
            FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
            FALLBACK_REASON_REPAIR_FAILED,
            FALLBACK_REASON_PROVIDER_ERROR,
            FALLBACK_REASON_LLM_UNAVAILABLE,
        ):
            m = LLMAttemptMetadata.fallback(reason=reason)
            self.assertTrue(m.fallback_used, reason)
            self.assertEqual(m.fallback_reason, reason)
            self.assertIsNotNone(m.warning_for_user, reason)
            # No stack-trace leakage
            self.assertNotIn("Traceback", m.warning_for_user)

    def test_to_dict_round_trip(self):
        m = LLMAttemptMetadata.fallback(
            reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
            provider="openai_compatible",
            model="m", latency_ms=1000.0,
            validation_errors=["missing required field: title"],
        )
        d = m.to_dict()
        rt = LLMAttemptMetadata.from_dict(d)
        self.assertEqual(rt.fallback_reason, m.fallback_reason)
        self.assertEqual(rt.parse_status, m.parse_status)
        self.assertEqual(rt.validation_errors_summary, m.validation_errors_summary)

    def test_validation_errors_summary_is_truncated(self):
        m = LLMAttemptMetadata.fallback(
            reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
            validation_errors=["e" * 1000] * 20,
        )
        d = m.to_dict()
        # Max 8 entries, max 240 chars each
        self.assertLessEqual(len(d["validation_errors_summary"]), 8)
        for s in d["validation_errors_summary"]:
            self.assertLessEqual(len(s), 240)

    def test_not_attempted_factory(self):
        m = LLMAttemptMetadata.not_attempted()
        self.assertFalse(m.llm_attempted)
        self.assertTrue(m.fallback_used)
        self.assertEqual(m.fallback_reason, FALLBACK_REASON_LLM_UNAVAILABLE)
        self.assertIsNotNone(m.warning_for_user)

    def test_user_warning_for_unknown_reason_uses_generic(self):
        w = user_warning_for("brand_new_reason_that_does_not_exist")
        self.assertIsNotNone(w)
        # Fallback to the generic "unknown" warning
        self.assertEqual(w, user_warning_for("unknown"))


# ---------------------------------------------------------------------------
# Agent-level fake-LLM tests (task spec §F agent block)
# ---------------------------------------------------------------------------

@dataclass
class _FakeResponse:
    content: str
    parsed: Any = None
    model: str = "fake-model"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 10.0
    finish_reason: str = "stop"


class _FakeProvider:
    """Test double for LLMProvider."""

    def __init__(self, *, content: str | None = None,
                  parsed: Any = None, raise_on_call: Exception | None = None):
        self._content = content or ""
        self._parsed = parsed
        self._raise = raise_on_call

    def complete(self, messages, response_schema=None,
                  temperature=0.2, max_tokens=4096, **kw):
        if self._raise is not None:
            raise self._raise
        return _FakeResponse(content=self._content, parsed=self._parsed)


class TestArticleModelerAttempt(unittest.TestCase):
    def _agent_and_input(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput
        return ArticleModelerAgent(), AgentInput(
            operation_id="op",
            agent_role_id="article_modeler",
            raw_text="Краткий текст про интерфейс как онтологическую форму. "
                     "Аргумент строится в континентальном регистре, без эмпирики.",
        )

    def test_provider_returns_parsed_dict_takes_fast_path_no_fallback(self):
        # The article_modeling schema is strict; the provider may already
        # have parsed the LLM response into a dict via the existing
        # _parse_json_robust pass inside openai_compat. In that case, the
        # agent skips our repair pipeline (fast path).
        parsed = {
            "article_stage": "abstract",
            "object_of_inquiry": "interface",
            "core_claims": ["c1"],
            "genre_current": "theoretical_essay",
            "method_status": "conceptual_method",
            "novelty_mode": "concept_introduction",
            "unknowns": [],
            "confidence": "medium",
        }
        provider = _FakeProvider(content='whatever', parsed=parsed)
        agent, inp = self._agent_and_input()
        out = agent.execute(inp, provider)
        entity = out.output_entity
        attempt = entity.get("extraction_attempt") or {}
        # Fast path → no fallback, no repair
        self.assertFalse(attempt.get("fallback_used"))
        self.assertEqual(attempt.get("parse_status"), "parsed_ok")
        # Claims survived
        self.assertEqual(entity.get("core_claims"), ["c1"])

    def test_provider_parsed_none_with_unparseable_text_triggers_fallback(self):
        # Adversarial: provider returned content but couldn't parse it,
        # AND our repair also can't help.
        provider = _FakeProvider(content="plain English sentences only.", parsed=None)
        agent, inp = self._agent_and_input()
        out = agent.execute(inp, provider)
        attempt = out.output_entity.get("extraction_attempt") or {}
        self.assertTrue(attempt.get("fallback_used"))
        self.assertIn(
            attempt.get("fallback_reason"),
            (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED),
        )

    def test_provider_error_marks_provider_error_fallback(self):
        provider = _FakeProvider(raise_on_call=RuntimeError("boom"))
        agent, inp = self._agent_and_input()
        out = agent.execute(inp, provider)
        attempt = out.output_entity.get("extraction_attempt") or {}
        self.assertTrue(attempt.get("fallback_used"))
        self.assertEqual(attempt.get("fallback_reason"),
                          FALLBACK_REASON_PROVIDER_ERROR)
        self.assertIsNotNone(attempt.get("warning_for_user"))

    def test_invalid_non_json_marks_fallback_with_visible_warning(self):
        provider = _FakeProvider(content="this is just text, not JSON")
        agent, inp = self._agent_and_input()
        out = agent.execute(inp, provider)
        attempt = out.output_entity.get("extraction_attempt") or {}
        self.assertTrue(attempt.get("fallback_used"))
        self.assertIn(attempt.get("fallback_reason"),
                       (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED))
        self.assertIsNotNone(attempt.get("warning_for_user"))

    def test_no_stack_trace_in_user_warning(self):
        # Adversarial: provider raises an Exception with stack-trace-like text
        provider = _FakeProvider(
            raise_on_call=RuntimeError(
                "Traceback (most recent call last):\n  File ...\n  raise X"
            ),
        )
        agent, inp = self._agent_and_input()
        out = agent.execute(inp, provider)
        attempt = out.output_entity.get("extraction_attempt") or {}
        warning = attempt.get("warning_for_user") or ""
        # User-facing warning is a clean Russian sentence, never the raw trace
        self.assertNotIn("Traceback", warning)
        self.assertNotIn("File ", warning)


# ---------------------------------------------------------------------------
# Human view surfacing
# ---------------------------------------------------------------------------

class TestHumanViewSurfacesFallback(unittest.TestCase):
    def test_fallback_warning_rendered_in_human_view(self):
        article = {
            "article_model_id": "x",
            "title_current": "T",
            "extraction_attempt": LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
                provider="openai_compatible", model="m",
                validation_errors=["missing required field: claims"],
            ).to_dict(),
        }
        md = article_model_human_view(article)
        # The Russian warning text appears in markdown
        self.assertIn("LLM-анализ был запущен", md)
        self.assertIn("структурную проверку", md)
        # Status badges (technical hint) appear
        self.assertIn("parse_status", md)
        self.assertIn("fallback_reason", md)
        # No stack-trace
        self.assertNotIn("Traceback", md)

    def test_parse_ok_does_not_show_fallback_warning(self):
        article = {
            "article_model_id": "x",
            "title_current": "T",
            "extraction_attempt": LLMAttemptMetadata.parse_ok(
                provider="openai_compatible", model="m",
                latency_ms=10.0, content_present=True,
            ).to_dict(),
        }
        md = article_model_human_view(article)
        self.assertNotIn("LLM-анализ был запущен", md)


if __name__ == "__main__":
    unittest.main()
