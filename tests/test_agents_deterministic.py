"""Tests for agent deterministic fallback paths.

No LLM calls — these test that agents produce valid output
in deterministic mode using the existing regex/rule services.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kairoskopion.agents.article_modeler import ArticleModelerAgent
from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.fit_assessor import FitAssessorAgent
from kairoskopion.agents.venue_profiler import VenueProfilerAgent
from kairoskopion.schema import ArticleModel, FitAssessment, VenueModel


def _load_fixture(name: str) -> str:
    fixtures = Path(__file__).parent / "fixtures"
    return (fixtures / name).read_text(encoding="utf-8")


class TestArticleModelerDeterministic(unittest.TestCase):
    def test_produces_article_model(self):
        agent = ArticleModelerAgent()
        text = _load_fixture("manuscript_sample.md")
        inp = AgentInput(
            operation_id="test-1",
            agent_role_id="article_modeler",
            raw_text=text,
            source_refs=["fixture:manuscript"],
        )
        out = agent.run(inp, provider=None)
        self.assertEqual(out.output_entity_type, "ArticleModel")
        self.assertIn("article_model_id", out.output_entity)
        self.assertEqual(out.evidence_status, "heuristic")
        self.assertTrue(any("deterministic" in w.lower() for w in out.warnings))

        article = ArticleModel.from_dict(out.output_entity)
        self.assertIsNotNone(article.article_model_id)
        self.assertIsNotNone(article.word_count)

    def test_handles_empty_text(self):
        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-2",
            agent_role_id="article_modeler",
            raw_text="",
        )
        out = agent.run(inp, provider=None)
        self.assertEqual(out.output_entity_type, "ArticleModel")


class TestVenueProfilerDeterministic(unittest.TestCase):
    def test_produces_venue_model(self):
        agent = VenueProfilerAgent()
        text = _load_fixture("venue_guidelines_sample.md")
        inp = AgentInput(
            operation_id="test-3",
            agent_role_id="venue_profiler",
            raw_text=text,
            source_refs=["fixture:venue"],
        )
        out = agent.run(inp, provider=None)
        self.assertEqual(out.output_entity_type, "VenueModel")
        self.assertIn("venue_model_id", out.output_entity)
        self.assertIn("_regime", out.output_entity)
        self.assertEqual(out.evidence_status, "heuristic")

        venue_dict = dict(out.output_entity)
        regime_dict = venue_dict.pop("_regime")
        venue = VenueModel.from_dict(venue_dict)
        self.assertIsNotNone(venue.venue_model_id)

    def test_handles_empty_text(self):
        agent = VenueProfilerAgent()
        inp = AgentInput(
            operation_id="test-4",
            agent_role_id="venue_profiler",
            raw_text="",
        )
        out = agent.run(inp, provider=None)
        self.assertEqual(out.output_entity_type, "VenueModel")


class TestFitAssessorDeterministic(unittest.TestCase):
    def test_produces_fit_assessment(self):
        # Build article and venue first
        ms_text = _load_fixture("manuscript_sample.md")
        vg_text = _load_fixture("venue_guidelines_sample.md")
        sc_data = json.loads(_load_fixture("submission_scenario_sample.json"))

        article_agent = ArticleModelerAgent()
        article_out = article_agent.run(
            AgentInput(
                operation_id="t-art",
                agent_role_id="article_modeler",
                raw_text=ms_text,
                source_refs=["fix:ms"],
            ),
            provider=None,
        )

        venue_agent = VenueProfilerAgent()
        venue_out = venue_agent.run(
            AgentInput(
                operation_id="t-ven",
                agent_role_id="venue_profiler",
                raw_text=vg_text,
                source_refs=["fix:vg"],
            ),
            provider=None,
        )

        venue_dict = dict(venue_out.output_entity)
        venue_dict.pop("_regime", None)

        from kairoskopion.services.scenario import build_scenario_from_dict
        scenario = build_scenario_from_dict(
            sc_data,
            article_model_id=article_out.output_entity.get("article_model_id"),
            venue_model_id=venue_dict.get("venue_model_id"),
        )

        fit_agent = FitAssessorAgent()
        fit_out = fit_agent.run(
            AgentInput(
                operation_id="t-fit",
                agent_role_id="fit_assessor",
                entities={
                    "article": article_out.output_entity,
                    "venue": venue_dict,
                    "scenario": scenario.to_dict(),
                },
            ),
            provider=None,
        )

        self.assertEqual(fit_out.output_entity_type, "FitAssessment")
        self.assertIn("fit_assessment_id", fit_out.output_entity)
        self.assertEqual(fit_out.evidence_status, "heuristic")

        fit = FitAssessment.from_dict(fit_out.output_entity)
        self.assertIsNotNone(fit.overall_label)
        self.assertTrue(len(fit.axes) > 0)


class TestPipelineDeterministic(unittest.TestCase):
    def test_pipeline_runs_without_llm(self):
        """Full pipeline in deterministic mode (no LLM) still works."""
        from kairoskopion.pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline

        ms_text = _load_fixture("manuscript_sample.md")
        vg_text = _load_fixture("venue_guidelines_sample.md")
        sc_data = json.loads(_load_fixture("submission_scenario_sample.json"))

        pipeline = ManuscriptVenueFitPipeline(llm_provider=None)
        result = pipeline.execute(
            manuscript_text=ms_text,
            venue_guidelines_text=vg_text,
            scenario_data=sc_data,
        )

        self.assertIsNotNone(result.article)
        self.assertIsNotNone(result.venue)
        self.assertIsNotNone(result.fit)
        self.assertIsNotNone(result.mismatch_map)
        self.assertIsNotNone(result.risk_report)
        self.assertIsNotNone(result.compliance)
        self.assertIsNone(result.llm_trace)


if __name__ == "__main__":
    unittest.main()
