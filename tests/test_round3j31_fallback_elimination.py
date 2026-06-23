"""Round III-J3.1 — Fallback elimination + translation audit fix.

Pin the renderer's author-surface against all forbidden placeholder
strings and verify that cache-aware rendering, search-task translation,
and surface metrics work correctly.
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.services.human_dossier import build_human_dossier
from kairoskopion.services.russian_surface import (
    PROMPT_VERSION,
    RussianSurfaceResult,
    cache_key, cache_get,
    needs_russian_surface,
    russianize_fields_batch,
    russianize_field_atomic,
    _validate_translation,
    collect_translation_items,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _flatten_author_text(h: dict) -> str:
    chunks: list[str] = [h.get("title_ru", ""), h.get("venue_name_ru", "")]
    for s in h["sections"]:
        chunks.append(s["title_ru"])
        chunks.extend(s["paragraphs"])
        chunks.extend(s["bullets"])
        for sub in s["subsections"]:
            chunks.append(sub["title_ru"])
            chunks.extend(sub["paragraphs"])
            chunks.extend(sub["bullets"])
    return "\n".join(c for c in chunks if c)


def _english_case_with_full_cache() -> dict:
    """A dossier with English fields AND a fully populated cache so that
    the renderer produces zero fallback placeholders.
    """
    fields = [
        ("article_model.problem_statement",
         "Organizations are encountering AI not as a tool but as a "
         "different cognitive form."),
        ("article_model.research_question",
         "How should management reconceptualize AI beyond instrumental "
         "logic?"),
        ("article_model.core_claims[0]",
         "AI represents a new management space rather than a tool."),
        ("article_model.protected_core[0]",
         "The xenopsychology framework as conceptual lens."),
        ("article_model.mutable_zones[0]",
         "Hotel industry examples and case applications"),
        ("semantic_profile.schools_and_traditions[0].tradition",
         "post-phenomenological technology studies"),
        ("mismatch_map.mismatches[0].article_side",
         "AI as cognitive form transforming management."),
        ("fit_assessment.recommendation",
         "Collect venue profile data before making a submission decision."),
        ("citation_plan.recommended_reference_search_tasks[0]",
         "Search for references that bridge: post-phenomenological "
         "technology studies and organizational management."),
        ("citation_plan.recommended_reference_search_tasks[1]",
         "Address tradition gap: STS-program engagement with "
         "organizational contexts."),
        ("submission_pack.next_actions[0]",
         "Add a recognizable bibliography section with proper references."),
    ]
    paraphrases = {
        "article_model.problem_statement":
            "Организации сталкиваются с ИИ не как с инструментом, а как с "
            "иной когнитивной формой.",
        "article_model.research_question":
            "Как менеджменту переосмыслить ИИ за пределами "
            "инструментальной логики?",
        "article_model.core_claims[0]":
            "ИИ представляет собой новое управленческое пространство, "
            "а не просто инструмент.",
        "article_model.protected_core[0]":
            "Рамка ксенопсихологии как концептуальная линза.",
        "article_model.mutable_zones[0]":
            "Примеры из гостиничной отрасли и их применение.",
        "semantic_profile.schools_and_traditions[0].tradition":
            "пост-феноменологические исследования техники",
        "mismatch_map.mismatches[0].article_side":
            "ИИ как когнитивная форма, преобразующая менеджмент.",
        "fit_assessment.recommendation":
            "Собрать данные о профиле площадки, прежде чем принимать "
            "решение о подаче.",
        "citation_plan.recommended_reference_search_tasks[0]":
            "Найти источники, которые связывают: пост-феноменологические "
            "исследования техники и организационный менеджмент.",
        "citation_plan.recommended_reference_search_tasks[1]":
            "Закрыть лакуну традиции: связь программы STS с "
            "организационными контекстами.",
        "submission_pack.next_actions[0]":
            "Добавить распознаваемый раздел библиографии с корректными "
            "ссылками.",
    }
    cache = {
        cache_key(fp, val): {
            "text_ru": paraphrases[fp],
            "prompt_version": PROMPT_VERSION,
        }
        for fp, val in fields
    }
    return {
        "case_id": "case_test_j31",
        "title": "test",
        "stage": "fit_assessed",
        "generated_at": "2026-06-23T00:00:00+00:00",
        "russian_surface_cache": cache,
        "article_first_paragraph": "ИИ как новое пространство управления",
        "venue_input_text_preview": "Вопросы философии — журнал…",
        "venue_input_type": "venue",
        "article_model": {
            "title_current": None,
            "language": "Russian",
            "genre_current": "theoretical_essay",
            "confidence": "medium",
            "problem_statement": fields[0][1],
            "research_question": fields[1][1],
            "core_claims": [fields[2][1]],
            "protected_core": [fields[3][1]],
            "mutable_zones": [fields[4][1]],
        },
        "semantic_profile": {
            "primary_discipline": "philosophy_of_technology",
            "schools_and_traditions": [
                {"tradition": fields[5][1], "confidence": "medium"},
            ],
        },
        "mismatch_map": {
            "mismatches": [
                {
                    "axis": "topic", "severity": "informational",
                    "article_side": fields[6][1],
                    "venue_side": "",
                    "description": "topic overlap unclear",
                    "narrative_status": "llm_filled",
                    "possible_actions": [],
                    "field_core_risk": "no_core_impact",
                },
            ],
        },
        "fit_assessment": {
            "overall_label": "not_enough_data",
            "confidence": "low",
            "recommendation": fields[7][1],
            "axes": [],
        },
        "citation_plan": {
            "semantic_status": "llm_grounded",
            "confidence": "medium",
            "recommended_reference_search_tasks": [
                fields[8][1], fields[9][1],
            ],
        },
        "submission_pack": {
            "next_actions": [fields[10][1]],
        },
        "decision_log": [],
        "quality_gates": {},
    }


# --------------------------------------------------------------------------
# Track A — no forbidden placeholders in author surface
# --------------------------------------------------------------------------

_FORBIDDEN_PLACEHOLDERS = (
    "формулировка модели — англоязычная",
    "см. вкладку «Технические данные»",
    "[англоязычный фрагмент — см. технические данные]",
    "см. технические данные",
    "доступна во вкладке «Технические данные»",
    "сохранены в технических данных",
    "системная реконструкция этого поля доступна",
)


class TestNoAuthorSurfaceTranslationPlaceholders(unittest.TestCase):
    def test_no_forbidden_placeholders_with_full_cache(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        for phrase in _FORBIDDEN_PLACEHOLDERS:
            self.assertNotIn(
                phrase, text,
                f"forbidden placeholder leaked: {phrase!r}",
            )

    def test_no_forbidden_placeholders_even_without_cache(self):
        d = _english_case_with_full_cache()
        d["russian_surface_cache"] = {}
        h = build_human_dossier(d).to_dict()
        text = _flatten_author_text(h)
        for phrase in _FORBIDDEN_PLACEHOLDERS:
            self.assertNotIn(
                phrase, text,
                f"forbidden placeholder leaked without cache: {phrase!r}",
            )

    def test_gentle_fallback_on_cache_miss(self):
        d = _english_case_with_full_cache()
        d["russian_surface_cache"] = {}
        h = build_human_dossier(d).to_dict()
        text = _flatten_author_text(h)
        self.assertIn("русская переформулировка не построена", text)


# --------------------------------------------------------------------------
# Track B — no raw search task prefixes
# --------------------------------------------------------------------------

class TestNoRawSearchTaskPrefixes(unittest.TestCase):
    def test_no_raw_search_for(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(
            text, r"\bSearch for\b",
            "raw 'Search for' leaked into author surface",
        )

    def test_no_raw_address_tradition_gap(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(
            text, r"\bAddress\s+(?:the\s+)?tradition\s+gap\b",
            "raw 'Address tradition gap' leaked into author surface",
        )

    def test_search_task_translated_from_cache(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertIn(
            "Найти источники, которые связывают", text,
        )
        self.assertIn(
            "Закрыть лакуну традиции", text,
        )

    def test_search_task_prefix_translation_without_cache(self):
        d = _english_case_with_full_cache()
        d["russian_surface_cache"] = {}
        h = build_human_dossier(d).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\bSearch for\b")
        self.assertNotRegex(
            text, r"\bAddress\s+(?:the\s+)?tradition\s+gap\b",
        )


# --------------------------------------------------------------------------
# Track C — surface metrics
# --------------------------------------------------------------------------

class TestSurfaceMetrics(unittest.TestCase):
    def test_metrics_present_in_safety_gates(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertIn("fallback_placeholder_count", sg)
        self.assertIn("technical_data_redirect_count", sg)
        self.assertIn("search_for_raw_count", sg)
        self.assertIn("address_tradition_gap_raw_count", sg)
        self.assertIn("unresolved_surface_fallback_count", sg)
        self.assertIn("long_english_semantic_prose_count", sg)

    def test_all_metrics_zero_with_full_cache(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertEqual(sg["fallback_placeholder_count"], 0)
        self.assertEqual(sg["technical_data_redirect_count"], 0)
        self.assertEqual(sg["search_for_raw_count"], 0)
        self.assertEqual(sg["address_tradition_gap_raw_count"], 0)
        self.assertEqual(sg["long_english_semantic_prose_count"], 0)


# --------------------------------------------------------------------------
# Track F — atomic retry simulation
# --------------------------------------------------------------------------

class TestAtomicRetrySimulation(unittest.TestCase):
    def test_batch_failure_then_atomic_success(self):
        """Simulate: batch gives safe_fallback, then atomic retry
        succeeds and populates the cache.
        """
        items = [
            {"id": "k1", "field": "article_model.problem_statement",
             "value": "Generic English text about organizational AI."},
        ]
        cache: dict = {}
        results = russianize_fields_batch(None, items, cache=cache)
        self.assertEqual(results["k1"].method, "safe_fallback")
        self.assertEqual(len(cache), 0)

        # Now simulate atomic success by manually populating cache
        from kairoskopion.services.russian_surface import cache_key as ck
        cache[ck("article_model.problem_statement",
                 "Generic English text about organizational AI.")] = {
            "text_ru": "Общий текст об организационном ИИ.",
            "prompt_version": PROMPT_VERSION,
        }
        # Verify cache is now used
        self.assertEqual(
            cache_get(
                cache, "article_model.problem_statement",
                "Generic English text about organizational AI.",
            ),
            "Общий текст об организационном ИИ.",
        )


# --------------------------------------------------------------------------
# Track D — structured translation audit context
# --------------------------------------------------------------------------

class TestStructuredTranslationAuditContext(unittest.TestCase):
    def test_collect_includes_dict_subfields(self):
        d = {
            "semantic_profile": {
                "theoretical_shoulders": [
                    {
                        "scholar": "Joseph Schumpeter",
                        "debt": "Entrepreneurial disruption logic",
                        "weight": "background",
                    },
                ],
            },
        }
        items = collect_translation_items(d)
        paths = [it["field"] for it in items]
        self.assertIn(
            "semantic_profile.theoretical_shoulders[0].debt", paths,
        )

    def test_collect_preserves_original_value(self):
        d = {
            "semantic_profile": {
                "schools_and_traditions": [
                    {"tradition": "actor network theory",
                     "evidence": "ANT framework applied to organizations"},
                ],
            },
        }
        items = collect_translation_items(d)
        tradition_items = [
            it for it in items
            if "tradition" in it["field"]
        ]
        self.assertTrue(len(tradition_items) > 0)
        self.assertEqual(
            tradition_items[0]["value"], "actor network theory",
        )


# --------------------------------------------------------------------------
# Regression
# --------------------------------------------------------------------------

class TestJ31Regression(unittest.TestCase):
    def test_no_angl_blocks(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotIn("(англ.)", text)

    def test_raw_output_not_exposed(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertFalse(sg["raw_llm_output_exposed"])
        self.assertEqual(sg["fake_doi_or_ref_count"], 0)

    def test_title_venue_evidence_preserved(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        self.assertEqual(h["venue_name_ru"], "Вопросы философии")
        self.assertIn("ИИ как новое пространство", h["title_ru"])

    def test_no_python_dict_repr(self):
        h = build_human_dossier(_english_case_with_full_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\{'[a-zA-Z_]+'\s*:")


if __name__ == "__main__":
    unittest.main()
