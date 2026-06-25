"""Round III-N: CitationPlan anti-fake filter + ecology recovery tests.

Tests:
1. Anti-fake filter keeps article-local gap descriptions (no DOI)
2. Anti-fake filter removes fabricated DOIs
3. Anti-fake filter preserves items mentioning existing author+year
4. Filter diagnostics report pre/post counts
5. CitationPlanner receives bibliography items
6. Prompt includes bibliography-present guidance
7. Anti-deterministic: no deterministic citation gap generation
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass

from kairoskopion.schema import (
    ArticleModel,
    BibliographyProfile,
    CitationPlan,
    FitAssessment,
    VenueModel,
)
from kairoskopion.services.llm_semantic_organs import (
    upgrade_citation_plan_with_llm,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.bibliography_profile import (
    build_minimal_bibliography_profile,
)


def _make_provider(content: str):
    from kairoskopion.llm.provider import LLMProvider
    mock = MagicMock(spec=LLMProvider)
    resp = MagicMock()
    resp.content = content
    resp.parsed = None
    resp.model = "test"
    resp.input_tokens = 100
    resp.output_tokens = 200
    resp.latency_ms = 150
    mock.complete.return_value = resp
    return mock


def _article():
    return ArticleModel(
        article_model_id="art_test",
        title_current="Различимость живого",
        abstract_current="Постфеноменологический анализ ИИ.",
        language="ru",
    )


def _venue():
    return VenueModel(
        venue_model_id="ven_logos",
        canonical_name="Логос",
        scope_summary="Философия, культурология, социальные науки",
    )


def _bib_profile():
    return build_minimal_bibliography_profile(
        "## Список литературы\n\n"
        "1. Бергсон А. Материя и память. М., 1992.\n"
        "2. Ihde D. Technology and the Lifeworld. 1990.\n"
        "3. Verbeek P.-P. What Things Do. 2005.\n"
        "4. Мол — Множественные тела\n"
    )


def _fit():
    return FitAssessment(
        axes=[
            {"axis": "topic", "value": "medium", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
            {"axis": "citation_ecology", "value": "unknown", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
        ],
        overall_label="possible_but_costly",
    )


def _citation_plan(bib_profile=None):
    return build_minimal_citation_plan(
        _article(), _venue(), _fit(), None, None, None,
        bibliography_profile=bib_profile,
    )


class TestAntiFakeFilter(unittest.TestCase):
    """Anti-fake filter must keep article-local gaps, remove fabricated DOIs."""

    def test_article_local_gap_preserved(self):
        """Gap describing incomplete reference (no DOI) must survive filter."""
        llm_output = json.dumps({
            "tradition_gaps": [
                "Ссылка на Мол неполная: отсутствуют выходные данные",
                "Не хватает работ по постфеноменологии технологий",
            ],
            "bridge_references_needed": [
                "Источники case-study требуют уточнения роли",
            ],
            "unknowns": ["Цитатные нормы Логос не профилированы"],
        })
        provider = _make_provider(llm_output)
        plan = _citation_plan(_bib_profile())
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), _bib_profile(), provider,
        )
        self.assertGreaterEqual(len(result.citation_gap_categories), 2)
        self.assertGreaterEqual(len(result.missing_bridge_categories), 1)

    def test_fabricated_doi_removed(self):
        """Item containing fabricated DOI must be filtered out."""
        llm_output = json.dumps({
            "tradition_gaps": [
                "Добавить: Smith J. AI Ethics. 10.1234/fake.2024",
            ],
            "bridge_references_needed": [
                "Safe bridge category without DOI",
            ],
        })
        provider = _make_provider(llm_output)
        plan = _citation_plan(_bib_profile())
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), _bib_profile(), provider,
        )
        self.assertEqual(len(result.citation_gap_categories), 0)
        self.assertEqual(len(result.missing_bridge_categories), 1)

    def test_author_year_in_context_preserved(self):
        """Items mentioning existing authors by name+year must NOT be filtered."""
        llm_output = json.dumps({
            "tradition_gaps": [
                "Bergson 1992 cited but original French edition needed",
                "Ihde 1990 insufficient — add Ihde 2009 Postphenomenology",
                "Verbeek 2005 needs companion piece from 2011",
            ],
            "unknowns": [],
        })
        provider = _make_provider(llm_output)
        plan = _citation_plan(_bib_profile())
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), _bib_profile(), provider,
        )
        self.assertGreaterEqual(
            len(result.citation_gap_categories), 3,
            f"Author-year mentions should survive filter, got: "
            f"{result.citation_gap_categories}",
        )

    def test_filter_diagnostics_in_attempt(self):
        """Diagnostics must include pre/post filter counts."""
        llm_output = json.dumps({
            "tradition_gaps": ["Safe gap"],
            "bridge_references_needed": [
                "Fabricated: 10.9999/does-not-exist"
            ],
        })
        provider = _make_provider(llm_output)
        plan = _citation_plan(_bib_profile())
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), _bib_profile(), provider,
        )
        diag = result.attempt_diagnostics or {}
        af = diag.get("anti_fake_filter", {})
        self.assertIn("pre", af)
        self.assertIn("post", af)
        self.assertIn("removed_count", af)
        self.assertEqual(af["removed_count"], 1)


class TestCitationPlannerInputs(unittest.TestCase):
    """CitationPlanner must receive bibliography data."""

    def test_bibliography_passed_to_prompt(self):
        """When bib_profile exists, its data is passed to LLM prompt."""
        bp = _bib_profile()
        self.assertTrue(bp.bibliography_section_detected)
        self.assertGreaterEqual(bp.reference_count, 3)

        provider = _make_provider(json.dumps({
            "tradition_gaps": ["test gap"],
        }))
        result = upgrade_citation_plan_with_llm(
            _citation_plan(bp), _article(), _venue(), bp, provider,
        )
        # Verify provider.complete was called with bibliography data
        call_args = provider.complete.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1].get("messages", [])
        user_msg = next(
            (m for m in messages if m.get("role") == "user"), None,
        )
        self.assertIsNotNone(user_msg)
        content = user_msg.get("content", "")
        self.assertIn("bibliography", content.lower())

    def test_no_provider_returns_unchanged(self):
        """Without LLM provider, plan stays structural."""
        plan = _citation_plan(_bib_profile())
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), _bib_profile(), None,
        )
        self.assertEqual(result.citation_gap_categories, plan.citation_gap_categories)


class TestPromptGuidance(unittest.TestCase):
    """Prompt must include bibliography-present guidance."""

    def test_prompt_has_bibliography_present_section(self):
        from kairoskopion.agents.prompt_families.citation_ecology import (
            SYSTEM_PROMPT,
        )
        self.assertIn("bibliography IS present", SYSTEM_PROMPT)
        self.assertIn("incomplete references", SYSTEM_PROMPT)
        self.assertIn("placeholder", SYSTEM_PROMPT)

    def test_prompt_forbids_fabricated_dois(self):
        from kairoskopion.agents.prompt_families.citation_ecology import (
            SYSTEM_PROMPT,
        )
        self.assertIn("DOI", SYSTEM_PROMPT)


class TestAntiDeterministicSemantic(unittest.TestCase):
    """No deterministic rule may generate final citation gap prose."""

    def test_structural_plan_has_no_semantic_gaps(self):
        """Minimal (deterministic) citation plan must not contain gap prose."""
        bp = _bib_profile()
        plan = build_minimal_citation_plan(
            _article(), _venue(), _fit(), None, None, None,
            bibliography_profile=bp,
        )
        self.assertEqual(plan.citation_gap_categories, [])
        self.assertEqual(plan.missing_bridge_categories, [])

    def test_semantic_gaps_only_from_llm(self):
        """Only LLM may populate citation_gap_categories."""
        llm_output = json.dumps({
            "tradition_gaps": ["LLM-produced gap"],
        })
        provider = _make_provider(llm_output)
        bp = _bib_profile()
        plan = _citation_plan(bp)
        result = upgrade_citation_plan_with_llm(
            plan, _article(), _venue(), bp, provider,
        )
        self.assertEqual(len(result.citation_gap_categories), 1)
        origins = result.field_origins or {}
        self.assertEqual(origins.get("citation_gap_categories"), "llm")


if __name__ == "__main__":
    unittest.main()
