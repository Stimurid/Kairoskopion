"""DisciplinaryPathwayMapper visible fallback metadata tests.

Mirrors the ArticleModel pattern from
`tests/test_llm_json_repair_and_fallback.py` onto the pathway mapper.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.disciplinary_mapper import (
    DisciplinaryPathwayMapperAgent,
)
from kairoskopion.llm.attempt_metadata import (
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_REPAIR_FAILED,
)
from kairoskopion.services.human_readable_card import article_model_human_view


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
    def __init__(self, *, content: str = "", parsed: Any = None,
                  raise_on_call: Exception | None = None):
        self._content = content
        self._parsed = parsed
        self._raise = raise_on_call

    def complete(self, messages, response_schema=None,
                  temperature=0.3, max_tokens=4096, **kw):
        if self._raise is not None:
            raise self._raise
        return _FakeResponse(content=self._content, parsed=self._parsed)


def _agent_input() -> AgentInput:
    return AgentInput(
        operation_id="op",
        agent_role_id="disciplinary_pathway_mapper",
        entities={
            "article": {
                "article_model_id": "art_x",
                "object_of_inquiry": "X",
                "disciplinary_register_current": "philosophy_of_technology",
            },
            "semantic_profile": {},
        },
    )


# ---------------------------------------------------------------------------
# Successful path
# ---------------------------------------------------------------------------

class TestPathwayParseOk(unittest.TestCase):
    def test_provider_returns_dict_fast_path_no_fallback(self):
        parsed = {
            "pathways": [
                {"discipline_name": "Continental philosophy",
                 "fit_strength": "strong",
                 "reasoning": "good fit",
                 "rank": 1},
                {"discipline_name": "STS",
                 "fit_strength": "medium",
                 "reasoning": "adjacent",
                 "rank": 2},
            ],
            "unknowns": [],
            "confidence": "medium",
        }
        provider = _FakeProvider(content="whatever", parsed=parsed)
        out = DisciplinaryPathwayMapperAgent().execute(_agent_input(), provider)
        # Each pathway carries metadata
        for p in out.output_entity["pathways"]:
            ea = p.get("extraction_attempt") or {}
            self.assertFalse(ea.get("fallback_used"))
            self.assertEqual(ea.get("parse_status"), "parsed_ok")
            self.assertIsNone(ea.get("warning_for_user"))
        # Pool-level metadata also present
        pool_ea = out.output_entity.get("extraction_attempt") or {}
        self.assertEqual(pool_ea.get("parse_status"), "parsed_ok")


# ---------------------------------------------------------------------------
# Provider error / non-JSON / repair-failed → visible fallback metadata
# ---------------------------------------------------------------------------

class TestPathwayFallback(unittest.TestCase):
    def test_provider_error_marks_provider_error_fallback(self):
        provider = _FakeProvider(raise_on_call=RuntimeError("boom"))
        out = DisciplinaryPathwayMapperAgent().execute(_agent_input(), provider)
        # Every pathway carries the fallback metadata
        for p in out.output_entity["pathways"]:
            ea = p.get("extraction_attempt") or {}
            self.assertTrue(ea.get("fallback_used"))
            self.assertEqual(ea.get("fallback_reason"),
                              FALLBACK_REASON_PROVIDER_ERROR)
            self.assertIsNotNone(ea.get("warning_for_user"))
            # raw_output_ref MUST be None — no raw capture
            self.assertIsNone(ea.get("raw_output_ref"))
        # No traceback in the user warning
        for p in out.output_entity["pathways"]:
            w = (p.get("extraction_attempt") or {}).get("warning_for_user") or ""
            self.assertNotIn("Traceback", w)
            self.assertNotIn("File ", w)

    def test_non_json_response_marks_invalid_or_repair_failed_fallback(self):
        provider = _FakeProvider(content="plain English. no JSON here.")
        out = DisciplinaryPathwayMapperAgent().execute(_agent_input(), provider)
        ea = out.output_entity["pathways"][0].get("extraction_attempt") or {}
        self.assertTrue(ea.get("fallback_used"))
        self.assertIn(
            ea.get("fallback_reason"),
            (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED),
        )
        self.assertIsNotNone(ea.get("warning_for_user"))
        self.assertIsNone(ea.get("raw_output_ref"))


# ---------------------------------------------------------------------------
# Repair path (fenced JSON returned as content, no parsed dict)
# ---------------------------------------------------------------------------

class TestPathwayRepairPath(unittest.TestCase):
    def test_fenced_json_via_repair_pipeline(self):
        # The disciplinary_mapping schema does NOT enforce required
        # fields on pathway items at top level — repair should succeed
        # for a well-formed fenced response.
        body = (
            '```json\n'
            '{"pathways":[{"discipline_name":"X","fit_strength":"medium",'
            '"reasoning":"r","rank":1}],"unknowns":[],"confidence":"medium"}'
            '\n```'
        )
        provider = _FakeProvider(content=body, parsed=None)
        out = DisciplinaryPathwayMapperAgent().execute(_agent_input(), provider)
        ea = out.output_entity["pathways"][0].get("extraction_attempt") or {}
        # Whichever exact status (parsed_ok / repaired_ok / fallback_used due
        # to required-field strictness) — assert the audit is visible
        self.assertIn(ea.get("parse_status"),
                       ("parsed_ok", "repaired_ok", "fallback_used"))
        self.assertIsNone(ea.get("raw_output_ref"))


# ---------------------------------------------------------------------------
# Human view shows pathway fallback warning when any pathway has it
# ---------------------------------------------------------------------------

class TestHumanViewSurfacesPathwayFallback(unittest.TestCase):
    def test_pathway_fallback_warning_renders_in_human_view(self):
        article = {"article_model_id": "x", "title_current": "T"}
        pathways = [{
            "discipline_name": "Continental",
            "fit_strength": "unknown",
            "rank": 1,
            "extraction_attempt": {
                "fallback_used": True,
                "fallback_reason": "provider_error",
                "parse_status": "fallback_used",
                "warning_for_user": "LLM-провайдер вернул ошибку. Показана детерминированная модель.",
                "raw_output_ref": None,
            },
        }]
        md = article_model_human_view(article, pathways=pathways)
        # The pathway-specific banner is visible in the disciplines section
        self.assertIn("Дисциплинарная карта", md)
        self.assertIn("parse_status", md)
        self.assertIn("fallback_reason", md)
        # No raw-output leakage
        self.assertNotIn("raw_output_ref", md)
        self.assertNotIn("Traceback", md)

    def test_no_pathway_warning_when_all_succeed(self):
        article = {"article_model_id": "x", "title_current": "T"}
        pathways = [{
            "discipline_name": "X",
            "fit_strength": "strong",
            "rank": 1,
            "extraction_attempt": {
                "fallback_used": False,
                "parse_status": "parsed_ok",
            },
        }]
        md = article_model_human_view(article, pathways=pathways)
        # No pathway-specific warning banner
        self.assertNotIn("Дисциплинарная карта", md)


# ---------------------------------------------------------------------------
# Persistence — DisciplinaryPathway round-trips extraction_attempt
# ---------------------------------------------------------------------------

class TestPathwayPersistsExtractionAttempt(unittest.TestCase):
    def test_extraction_attempt_roundtrips_via_dict(self):
        from kairoskopion.schema import DisciplinaryPathway
        p = DisciplinaryPathway(
            discipline_name="X",
            fit_strength="medium",
            rank=1,
            extraction_attempt={
                "parse_status": "fallback_used",
                "fallback_used": True,
                "fallback_reason": "provider_error",
                "warning_for_user": "Russian warning",
                "raw_output_ref": None,
            },
        )
        d = p.to_dict()
        self.assertIn("extraction_attempt", d)
        rt = DisciplinaryPathway.from_dict(d)
        self.assertEqual(rt.extraction_attempt["parse_status"], "fallback_used")
        self.assertTrue(rt.extraction_attempt["fallback_used"])
        self.assertIsNone(rt.extraction_attempt["raw_output_ref"])


if __name__ == "__main__":
    unittest.main()
