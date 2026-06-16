"""Visible-fallback metadata for SemanticProfiler + FitAssessor.

Mirrors the patterns from tests/test_llm_json_repair_and_fallback.py
and tests/test_pathway_mapper_visible_fallback.py onto the remaining
two LLM-backed agents in the intake chain.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.fit_assessor import FitAssessorAgent
from kairoskopion.agents.semantic_profiler import ArticleSemanticProfilerAgent
from kairoskopion.llm.attempt_metadata import (
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_REPAIR_FAILED,
    classify_llm_response,
)


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


def _semantic_input() -> AgentInput:
    return AgentInput(
        operation_id="op",
        agent_role_id="article_semantic_profiler",
        raw_text="Continental philosophy fragment about interface as form.",
        entities={
            "article": {
                "article_model_id": "art_x",
                "disciplinary_register_current": "philosophy_of_technology",
                "theoretical_shoulders": [],
                "protected_core": [],
                "mutable_zones": [],
            },
        },
    )


def _fit_input() -> AgentInput:
    return AgentInput(
        operation_id="op",
        agent_role_id="fit_assessor",
        entities={
            "article": {"article_model_id": "art_x"},
            "venue": {"venue_model_id": "ven_x"},
            "scenario": {"submission_scenario_id": "ss_x"},
        },
    )


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

class TestClassifyHelper(unittest.TestCase):
    def test_fast_path_dict_returns_parse_ok(self):
        r = _FakeResponse(content="ignored", parsed={"a": 1})
        parsed, meta, steps, errors = classify_llm_response(r, schema=None)
        self.assertEqual(parsed, {"a": 1})
        self.assertEqual(meta.parse_status, "parsed_ok")
        self.assertFalse(meta.fallback_used)
        self.assertEqual(steps, [])

    def test_non_json_returns_fallback_meta(self):
        r = _FakeResponse(content="just prose, no JSON.", parsed=None)
        parsed, meta, steps, errors = classify_llm_response(r, schema=None)
        self.assertIsNone(parsed)
        self.assertTrue(meta.fallback_used)
        self.assertIn(
            meta.fallback_reason,
            (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED),
        )
        self.assertIsNotNone(meta.warning_for_user)
        self.assertIsNone(meta.raw_output_ref)


# ---------------------------------------------------------------------------
# SemanticProfiler
# ---------------------------------------------------------------------------

class TestSemanticProfilerSuccess(unittest.TestCase):
    def test_parsed_ok_attaches_metadata_no_fallback(self):
        parsed = {
            "disciplinary_registers": ["philosophy_of_technology"],
            "primary_discipline": "philosophy_of_technology",
            "schools_and_traditions": ["continental"],
            "argument_move_type": "concept_introduction",
            "argument_move_description": "...",
            "protected_core_candidates": [],
            "mutable_zones": [],
            "unknowns": [],
            "confidence": "medium",
        }
        provider = _FakeProvider(content="ignored", parsed=parsed)
        out = ArticleSemanticProfilerAgent().execute(_semantic_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertFalse(ea.get("fallback_used"))
        self.assertEqual(ea.get("parse_status"), "parsed_ok")
        self.assertIsNone(ea.get("warning_for_user"))
        self.assertIsNone(ea.get("raw_output_ref"))


class TestSemanticProfilerFallback(unittest.TestCase):
    def test_provider_error_marks_provider_error_fallback(self):
        provider = _FakeProvider(raise_on_call=RuntimeError("boom"))
        out = ArticleSemanticProfilerAgent().execute(_semantic_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertTrue(ea.get("fallback_used"))
        self.assertEqual(ea.get("fallback_reason"),
                          FALLBACK_REASON_PROVIDER_ERROR)
        self.assertIsNotNone(ea.get("warning_for_user"))
        # Anti-leak
        self.assertNotIn("Traceback", ea.get("warning_for_user") or "")
        self.assertIsNone(ea.get("raw_output_ref"))

    def test_non_json_marks_invalid_or_repair_failed(self):
        provider = _FakeProvider(content="plain English, no JSON.")
        out = ArticleSemanticProfilerAgent().execute(_semantic_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertTrue(ea.get("fallback_used"))
        self.assertIn(
            ea.get("fallback_reason"),
            (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED),
        )
        self.assertIsNone(ea.get("raw_output_ref"))

    def test_anti_traceback_leak_in_user_warning(self):
        provider = _FakeProvider(
            raise_on_call=RuntimeError(
                "Traceback (most recent call last):\n  File ..."
            ),
        )
        out = ArticleSemanticProfilerAgent().execute(_semantic_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        warning = ea.get("warning_for_user") or ""
        self.assertNotIn("Traceback", warning)
        self.assertNotIn("File ", warning)


# ---------------------------------------------------------------------------
# FitAssessor
# ---------------------------------------------------------------------------

class TestFitAssessorSuccess(unittest.TestCase):
    def test_parsed_ok_attaches_metadata(self):
        parsed = {
            "axes": [],
            "overall_label": "possible",
            "confidence": "medium",
            "unknowns": [],
            "recommendation": "consider",
        }
        provider = _FakeProvider(content="ignored", parsed=parsed)
        out = FitAssessorAgent().execute(_fit_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertFalse(ea.get("fallback_used"))
        self.assertEqual(ea.get("parse_status"), "parsed_ok")
        self.assertIsNone(ea.get("warning_for_user"))
        self.assertIsNone(ea.get("raw_output_ref"))


class TestFitAssessorFallback(unittest.TestCase):
    def test_provider_error_marks_provider_error_fallback(self):
        provider = _FakeProvider(raise_on_call=RuntimeError("boom"))
        out = FitAssessorAgent().execute(_fit_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertTrue(ea.get("fallback_used"))
        self.assertEqual(ea.get("fallback_reason"),
                          FALLBACK_REASON_PROVIDER_ERROR)
        self.assertIsNotNone(ea.get("warning_for_user"))
        self.assertIsNone(ea.get("raw_output_ref"))

    def test_non_json_marks_invalid_or_repair_failed(self):
        provider = _FakeProvider(content="just prose")
        out = FitAssessorAgent().execute(_fit_input(), provider)
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertTrue(ea.get("fallback_used"))
        self.assertIn(
            ea.get("fallback_reason"),
            (FALLBACK_REASON_INVALID_JSON, FALLBACK_REASON_REPAIR_FAILED),
        )
        self.assertIsNone(ea.get("raw_output_ref"))


# ---------------------------------------------------------------------------
# Persistence — schema round-trip on both new fields
# ---------------------------------------------------------------------------

class TestPersistence(unittest.TestCase):
    def test_semantic_profile_roundtrips_extraction_attempt(self):
        from kairoskopion.schema import ArticleSemanticProfile
        p = ArticleSemanticProfile(
            extraction_attempt={
                "parse_status": "fallback_used",
                "fallback_used": True,
                "fallback_reason": "provider_error",
                "warning_for_user": "test warning",
                "raw_output_ref": None,
            },
        )
        rt = ArticleSemanticProfile.from_dict(p.to_dict())
        self.assertEqual(rt.extraction_attempt["parse_status"], "fallback_used")
        self.assertTrue(rt.extraction_attempt["fallback_used"])
        self.assertIsNone(rt.extraction_attempt["raw_output_ref"])

    def test_fit_assessment_roundtrips_extraction_attempt(self):
        from kairoskopion.schema import FitAssessment
        f = FitAssessment(
            extraction_attempt={
                "parse_status": "parsed_ok",
                "fallback_used": False,
                "raw_output_ref": None,
            },
        )
        rt = FitAssessment.from_dict(f.to_dict())
        self.assertEqual(rt.extraction_attempt["parse_status"], "parsed_ok")
        self.assertFalse(rt.extraction_attempt["fallback_used"])


# ---------------------------------------------------------------------------
# Human view surfaces per-layer fallback banners
# ---------------------------------------------------------------------------

class TestHumanViewSurfacesLayerFallbacks(unittest.TestCase):
    def test_semantic_fallback_renders_named_banner(self):
        from kairoskopion.services.human_readable_card import (
            article_model_human_view,
        )
        article = {"article_model_id": "x", "title_current": "T"}
        sem = {
            "extraction_attempt": {
                "fallback_used": True,
                "fallback_reason": "provider_error",
                "parse_status": "fallback_used",
                "warning_for_user": (
                    "LLM-провайдер вернул ошибку. Показана детерминированная "
                    "модель."
                ),
                "raw_output_ref": None,
            }
        }
        md = article_model_human_view(article, semantic_profile=sem)
        # New unified contract: aggregator labels the layer as
        # "Семантический профиль" and renders warning_for_user verbatim.
        self.assertIn("Семантический профиль", md)
        self.assertIn("LLM-провайдер вернул ошибку", md)
        self.assertIn("parse_status", md)
        self.assertIn("fallback_reason", md)
        self.assertNotIn("Traceback", md)
        self.assertNotIn("raw_output_ref", md)

    def test_fit_fallback_renders_named_banner(self):
        from kairoskopion.services.human_readable_card import (
            article_model_human_view,
        )
        article = {"article_model_id": "x", "title_current": "T"}
        fit = {
            "extraction_attempt": {
                "fallback_used": True,
                "fallback_reason": "schema_validation_failed",
                "parse_status": "schema_validation_failed",
                "warning_for_user": (
                    "LLM-анализ был запущен, но его ответ не прошёл "
                    "структурную проверку."
                ),
                "raw_output_ref": None,
            }
        }
        md = article_model_human_view(article, fit_assessment=fit)
        # New unified contract.
        self.assertIn("Оценка соответствия", md)
        self.assertIn("LLM-анализ был запущен", md)
        self.assertNotIn("Traceback", md)
        self.assertNotIn("raw_output_ref", md)

    def test_no_banner_when_layers_succeeded(self):
        from kairoskopion.services.human_readable_card import (
            article_model_human_view,
        )
        article = {"article_model_id": "x", "title_current": "T"}
        sem = {"extraction_attempt": {"fallback_used": False, "parse_status": "parsed_ok"}}
        fit = {"extraction_attempt": {"fallback_used": False, "parse_status": "parsed_ok"}}
        md = article_model_human_view(
            article, semantic_profile=sem, fit_assessment=fit,
        )
        # No fallback warning blockquote of any shape.
        self.assertNotIn("Семантический профиль:", md)
        self.assertNotIn("Оценка соответствия:", md)
        self.assertNotIn("Несколько слоёв", md)

    def test_multi_layer_aggregates_into_single_block(self):
        """When 2+ layers fall back, the unified aggregator renders ONE
        bullet-list block instead of N separate banners."""
        from kairoskopion.services.human_readable_card import (
            article_model_human_view,
        )
        article = {
            "article_model_id": "x",
            "title_current": "T",
            "extraction_attempt": {
                "fallback_used": True,
                "fallback_reason": "invalid_json",
                "parse_status": "invalid_json",
                "warning_for_user": "Invalid JSON warning",
                "raw_output_ref": None,
            },
        }
        sem = {"extraction_attempt": {
            "fallback_used": True,
            "fallback_reason": "provider_error",
            "parse_status": "fallback_used",
            "warning_for_user": "Provider error warning",
            "raw_output_ref": None,
        }}
        md = article_model_human_view(article, semantic_profile=sem)
        self.assertIn("Несколько слоёв", md)
        self.assertIn("Модель статьи", md)
        self.assertIn("Семантический профиль", md)
        self.assertIn("invalid_json", md)
        self.assertIn("provider_error", md)
        # Only ONE aggregated parent heading
        self.assertEqual(md.count("Несколько слоёв"), 1)

    def test_anti_leak_on_aggregated_block(self):
        """Adversarial: raw_output_ref must never appear in rendered md
        even when set on an attempt dict."""
        from kairoskopion.services.human_readable_card import (
            article_model_human_view,
        )
        article = {
            "article_model_id": "x",
            "title_current": "T",
            "extraction_attempt": {
                "fallback_used": True,
                "fallback_reason": "provider_error",
                "parse_status": "fallback_used",
                "warning_for_user": "Provider error",
                "raw_output_ref": "MUST-NOT-RENDER-RAW-PAYLOAD",
            },
        }
        md = article_model_human_view(article)
        self.assertNotIn("raw_output_ref", md)
        self.assertNotIn("MUST-NOT-RENDER-RAW-PAYLOAD", md)


# ---------------------------------------------------------------------------
# Regression: ArticleModel + Pathway agents still work
# (sanity — make sure the shared classify_llm_response helper didn't break
# the article_modeler or disciplinary_mapper paths.)
# ---------------------------------------------------------------------------

class TestRegressionArticleAndPathway(unittest.TestCase):
    def test_article_modeler_fast_path_still_works(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        parsed = {
            "article_stage": "abstract",
            "object_of_inquiry": "x",
            "core_claims": ["c1"],
            "genre_current": "theoretical_essay",
            "method_status": "conceptual_method",
            "novelty_mode": "concept_introduction",
            "unknowns": [],
            "confidence": "medium",
        }
        provider = _FakeProvider(content="ignored", parsed=parsed)
        out = ArticleModelerAgent().execute(
            AgentInput(operation_id="op", agent_role_id="article_modeler",
                        raw_text="test"),
            provider,
        )
        ea = (out.output_entity or {}).get("extraction_attempt") or {}
        self.assertEqual(ea.get("parse_status"), "parsed_ok")
        self.assertFalse(ea.get("fallback_used"))

    def test_pathway_mapper_fast_path_still_works(self):
        from kairoskopion.agents.disciplinary_mapper import (
            DisciplinaryPathwayMapperAgent,
        )
        parsed = {
            "pathways": [
                {"discipline_name": "X", "fit_strength": "strong",
                 "reasoning": "r", "rank": 1}
            ],
            "unknowns": [],
            "confidence": "medium",
        }
        provider = _FakeProvider(content="ignored", parsed=parsed)
        out = DisciplinaryPathwayMapperAgent().execute(
            AgentInput(
                operation_id="op",
                agent_role_id="disciplinary_pathway_mapper",
                entities={
                    "article": {"article_model_id": "art_x"},
                    "semantic_profile": {},
                },
            ),
            provider,
        )
        for p in out.output_entity["pathways"]:
            ea = p.get("extraction_attempt") or {}
            self.assertFalse(ea.get("fallback_used"))


if __name__ == "__main__":
    unittest.main()
