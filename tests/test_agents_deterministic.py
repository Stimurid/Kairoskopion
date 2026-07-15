"""Tests for agent deterministic fallback paths.

ARCH-SEM-001 enforcement:
- VenueProfilerAgent.execute_deterministic raises SemanticLLMRequiredError
- DisciplineMatcherAgent.execute_deterministic raises SemanticLLMRequiredError
- ArticleModelerAgent deterministic mode is still permitted (structural, not semantic)
- FitAssessorAgent deterministic mode is still permitted (structural comparison)
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kairoskopion.agents.article_modeler import ArticleModelerAgent
from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.fit_assessor import FitAssessorAgent
from kairoskopion.agents.venue_profiler import VenueProfilerAgent
from kairoskopion.llm.openai_compat import SemanticLLMRequiredError
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


class TestVenueProfilerArchSem001(unittest.TestCase):
    """ARCH-SEM-001: VenueProfilerAgent must NOT produce semantic output
    without LLM."""

    def test_deterministic_raises_semantic_error(self):
        agent = VenueProfilerAgent()
        text = _load_fixture("venue_guidelines_sample.md")
        inp = AgentInput(
            operation_id="test-3",
            agent_role_id="venue_profiler",
            raw_text=text,
            source_refs=["fixture:venue"],
        )
        with self.assertRaises(SemanticLLMRequiredError):
            agent.run(inp, provider=None)

    def test_empty_text_raises_semantic_error(self):
        agent = VenueProfilerAgent()
        inp = AgentInput(
            operation_id="test-4",
            agent_role_id="venue_profiler",
            raw_text="",
        )
        with self.assertRaises(SemanticLLMRequiredError):
            agent.run(inp, provider=None)


class TestFitAssessorDeterministic(unittest.TestCase):
    def test_produces_fit_assessment(self):
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

        # Build venue model deterministically via service (not agent)
        # since VenueProfilerAgent now requires LLM (ARCH-SEM-001)
        from kairoskopion.services.venue_profiling import build_venue_model
        venue, regime = build_venue_model(vg_text)
        venue_dict = venue.to_dict()

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
        self.assertEqual(fit_out.evidence_status, "none")

        fit = FitAssessment.from_dict(fit_out.output_entity)
        self.assertEqual(fit.overall_label, "not_enough_data")
        self.assertTrue(len(fit.axes) > 0)
        for ax in fit.axes:
            ax_val = ax["value"] if isinstance(ax, dict) else ax.value
            self.assertEqual(ax_val, "unknown")


class TestPipelineDeterministic(unittest.TestCase):
    def test_pipeline_runs_without_llm(self):
        """Full pipeline in deterministic mode (no LLM) still works.
        Note: pipeline uses services directly, not agents, for venue/article,
        so ARCH-SEM-001 agent restrictions do not block this path."""
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
