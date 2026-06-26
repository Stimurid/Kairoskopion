"""Round III-P4 Track 7: Integration smoke tests on real article.

4 scenarios:
  1. Pipeline deterministic (no LLM) on real article — all organs fallback
  2. DisciplineIntentParser on real article text (deterministic)
  3. FitAssessor deterministic on pipeline output — all axes unknown
  4. ComplianceAssessor deterministic — structural items preserved

Uses private_inputs/article_razlichimost_zhivogo.md if available,
falls back to fixture manuscript_sample.md.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ARTICLE_PATH = Path(__file__).parent.parent / "private_inputs" / "article_razlichimost_zhivogo.md"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "manuscript_sample.md"


def _load_article() -> str:
    if ARTICLE_PATH.exists():
        return ARTICLE_PATH.read_text(encoding="utf-8")
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _load_fixture(name: str) -> str:
    return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


class TestScenario1_PipelineDeterministic(unittest.TestCase):
    def test_full_pipeline_no_llm(self):
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )

        article_text = _load_article()
        venue_text = _load_fixture("venue_guidelines_sample.md")
        scenario_data = json.loads(
            _load_fixture("submission_scenario_sample.json"),
        )

        pipeline = ManuscriptVenueFitPipeline(llm_provider=None)
        result = pipeline.execute(
            manuscript_text=article_text,
            venue_guidelines_text=venue_text,
            scenario_data=scenario_data,
        )

        self.assertIsNotNone(result.article)
        self.assertIsNotNone(result.venue)
        self.assertIsNotNone(result.fit)
        self.assertEqual(result.fit.overall_label, "not_enough_data")
        for ax in result.fit.axes:
            val = ax["value"] if isinstance(ax, dict) else ax.value
            self.assertEqual(val, "unknown")


class TestScenario2_DisciplineIntentOnRealArticle(unittest.TestCase):
    def test_deterministic_fallback(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.discipline_intent_parser import (
            DisciplineIntentParserAgent,
        )

        article_text = _load_article()
        first_500 = article_text[:500]

        agent = DisciplineIntentParserAgent()
        inp = AgentInput(
            operation_id="smoke-2",
            agent_role_id="discipline_intent_parser",
            raw_text=first_500,
        )
        out = agent.execute_deterministic(inp)

        self.assertEqual(out.output_entity["intent_parse_status"], "needs_llm")
        self.assertIsNone(out.output_entity["parse_result"])
        self.assertEqual(out.confidence, "none")


class TestScenario3_FitAssessorOnPipelineOutput(unittest.TestCase):
    def test_all_axes_unknown(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.fit_assessor import FitAssessorAgent

        agent = FitAssessorAgent()
        inp = AgentInput(
            operation_id="smoke-3",
            agent_role_id="fit_assessor",
            entities={
                "article": {"article_model_id": "smoke-art-1",
                            "title_current": "Test"},
                "venue": {"venue_model_id": "smoke-ven-1",
                          "canonical_name": "Test Journal"},
                "scenario": {"submission_scenario_id": "smoke-sc-1"},
            },
        )
        out = agent.execute_deterministic(inp)

        self.assertEqual(out.output_entity["overall_label"], "not_enough_data")
        for ax in out.output_entity["axes"]:
            self.assertEqual(ax["value"], "unknown")
        self.assertEqual(out.confidence, "none")
        self.assertEqual(out.quality_gate_status, "blocked")


class TestScenario4_ComplianceStructuralPreserved(unittest.TestCase):
    def test_structural_items_survive_fallback(self):
        from kairoskopion.agents.compliance_assessor import (
            ComplianceAssessorAgent,
        )
        from kairoskopion.agents.contract import AgentInput

        agent = ComplianceAssessorAgent()
        inp = AgentInput(
            operation_id="smoke-4",
            agent_role_id="compliance_assessor",
            entities={
                "article": {"title_current": "Различимость живого"},
                "venue": {"canonical_name": "Вопросы философии"},
                "structural_checklist": {
                    "items": [
                        {"item_id": "c1", "field": "abstract",
                         "structural_status": "present"},
                        {"item_id": "c2", "field": "keywords",
                         "structural_status": "present"},
                        {"item_id": "c3", "field": "references",
                         "structural_status": "present"},
                        {"item_id": "c4", "field": "ai_disclosure",
                         "structural_status": "absent"},
                    ],
                },
            },
        )
        out = agent.execute_deterministic(inp)

        self.assertFalse(out.output_entity["semantic_pass"])
        items = out.output_entity["items"]
        self.assertEqual(len(items), 4)
        statuses = {i["item_id"]: i["structural_status"] for i in items}
        self.assertEqual(statuses["c1"], "present")
        self.assertEqual(statuses["c4"], "absent")


if __name__ == "__main__":
    unittest.main()
