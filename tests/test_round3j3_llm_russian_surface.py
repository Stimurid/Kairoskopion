"""Round III-J3 — LLM-backed Russian author surface tests.

Pin the renderer's behaviour around the Russian-surface cache without
calling the LLM during the test run:

  - When a cache entry exists for an English field, the renderer uses
    it; the J2 stub is NOT shown.
  - Cache results contain only validated Russian text — never raw LLM
    output / DOIs / invented author-year refs.
  - The narrator validates that translations carry no fabricated
    facts: invented DOIs / new author-year patterns / JSON fences /
    runaway length / Cyrillic-poor outputs are all rejected.
  - Provenance / title / venue logic from Round III-J / J2 is
    preserved.
"""

from __future__ import annotations

import unittest

from kairoskopion.services.human_dossier import build_human_dossier
from kairoskopion.services.russian_surface import (
    PROMPT_VERSION,
    RussianSurfaceResult,
    cache_key, cache_get,
    needs_russian_surface,
    russianize_fields_batch,
    _validate_translation,
    collect_translation_items,
)


# --------------------------------------------------------------------------
# Cache + dossier integration
# --------------------------------------------------------------------------

def _english_case_with_cache() -> dict:
    """A dossier with English semantic fields PLUS a pre-populated
    russian_surface_cache (so the renderer reads Russian without an
    LLM call during the test).
    """
    case_id = "case_test_j3"
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
    }
    cache = {
        cache_key(fp, val): {
            "text_ru": paraphrases[fp],
            "prompt_version": PROMPT_VERSION,
        }
        for fp, val in fields
    }
    return {
        "case_id": case_id,
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
                {
                    "tradition": fields[5][1],
                    "confidence": "medium",
                },
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
        "decision_log": [],
        "quality_gates": {},
    }


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


class TestRendererUsesCache(unittest.TestCase):
    def test_author_surface_uses_cached_translation_not_stub(self):
        h = build_human_dossier(_english_case_with_cache()).to_dict()
        text = _flatten_author_text(h)
        # Cached Russian phrases must appear...
        self.assertIn("Организации сталкиваются с ИИ", text)
        self.assertIn(
            "Рамка ксенопсихологии как концептуальная линза", text,
        )
        self.assertIn(
            "пост-феноменологические исследования техники", text,
        )
        # ...and the J2 stub must NOT appear for those fields.
        self.assertNotIn(
            "формулировка модели — англоязычная; см. вкладку", text,
        )
        # Original English content must NOT appear in author surface
        self.assertNotIn(
            "Organizations are encountering AI not as a tool", text,
        )

    def test_cache_miss_falls_back_to_stub(self):
        d = _english_case_with_cache()
        # Drop one cache entry; renderer must fall back to a stub for it
        # but keep using cache for the others.
        del d["russian_surface_cache"][
            cache_key(
                "article_model.problem_statement",
                d["article_model"]["problem_statement"],
            )
        ]
        h = build_human_dossier(d).to_dict()
        text = _flatten_author_text(h)
        # The problem_statement field — no Russian translation; stub
        # appears (Russian honesty stub from Round III-J2).
        self.assertIn("системная реконструкция этого поля доступна", text)
        # Other cached fields still resolve to Russian:
        self.assertIn("Рамка ксенопсихологии", text)


# --------------------------------------------------------------------------
# Validation contract
# --------------------------------------------------------------------------

class TestValidationContract(unittest.TestCase):
    def test_accepts_valid_russian_translation(self):
        ok, diag = _validate_translation(
            "Organizations are encountering AI not as a tool.",
            "Организации сталкиваются с ИИ не как с инструментом.",
        )
        self.assertTrue(ok, diag)
        self.assertGreater(diag["cyrillic_ratio"], 0.45)

    def test_rejects_empty_translation(self):
        ok, diag = _validate_translation("X", "")
        self.assertFalse(ok)

    def test_rejects_non_russian_translation(self):
        ok, diag = _validate_translation(
            "Organizations are encountering AI.",
            "Organizations are encountering AI.",
        )
        self.assertFalse(ok)
        self.assertEqual(diag.get("reason"), "not_russian_dominant")

    def test_rejects_invented_doi(self):
        ok, diag = _validate_translation(
            "Organizations encountering AI.",
            "Организации сталкиваются с ИИ. См. 10.1234/foo.bar.",
        )
        self.assertFalse(ok)
        self.assertEqual(diag.get("reason"), "invented_doi")

    def test_rejects_json_fence_leak(self):
        ok, diag = _validate_translation(
            "Foo bar baz.",
            "Подробное русское описание поля. ```json\n{\"x\":1}\n```",
        )
        self.assertFalse(ok)
        self.assertEqual(diag.get("reason"), "json_fence_leak")

    def test_rejects_invented_author_year(self):
        ok, diag = _validate_translation(
            "Generic statement about AI.",
            "Конкретное утверждение об ИИ. Smith (2024), Doe (2023), Roe (2022).",
        )
        self.assertFalse(ok)
        self.assertEqual(diag.get("reason"), "invented_author_year")

    def test_accepts_authors_present_in_original(self):
        # Authors named in the original may be preserved
        ok, diag = _validate_translation(
            "Latour (2005) framed the problem.",
            "Латур, Latour (2005), задал рамку проблемы.",
        )
        self.assertTrue(ok, diag)


# --------------------------------------------------------------------------
# Cache helpers + collection
# --------------------------------------------------------------------------

class TestCacheAndCollection(unittest.TestCase):
    def test_cache_key_is_deterministic(self):
        k1 = cache_key("foo", "Organizations are...")
        k2 = cache_key("foo", "Organizations are...")
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 24)

    def test_cache_get_returns_text_for_dict_value(self):
        c = {cache_key("a.b", "v"): {"text_ru": "Русский", "prompt_version": "v1"}}
        self.assertEqual(cache_get(c, "a.b", "v"), "Русский")

    def test_needs_russian_surface_detects_english(self):
        self.assertTrue(needs_russian_surface(
            "Organizations are encountering AI not as a tool.",
        ))
        self.assertFalse(needs_russian_surface(
            "Организации сталкиваются с ИИ.",
        ))
        self.assertFalse(needs_russian_surface(""))
        self.assertFalse(needs_russian_surface("OK"))

    def test_collect_translation_items_walks_dossier(self):
        d = {
            "article_model": {
                "problem_statement": "Organizations are entering an era…",
                "core_claims": [
                    "AI represents a new management space.",
                    "Системы AI требуют нового подхода.",  # already Russian
                ],
            },
            "semantic_profile": {
                "schools_and_traditions": [
                    {
                        "tradition": "post-phenomenological tech studies",
                        "evidence": "Treating AI as mediator.",
                    },
                ],
            },
        }
        items = collect_translation_items(d)
        paths = [it["field"] for it in items]
        self.assertIn("article_model.problem_statement", paths)
        self.assertIn("article_model.core_claims[0]", paths)
        # Russian claim NOT included
        self.assertNotIn("article_model.core_claims[1]", paths)
        # dict-shaped tradition: nested .tradition key collected
        self.assertIn(
            "semantic_profile.schools_and_traditions[0].tradition", paths,
        )
        self.assertIn(
            "semantic_profile.schools_and_traditions[0].evidence", paths,
        )


# --------------------------------------------------------------------------
# Batch helper without LLM (provider=None branch)
# --------------------------------------------------------------------------

class TestBatchSafeFallback(unittest.TestCase):
    def test_provider_none_returns_safe_fallback(self):
        items = [
            {"id": "k1", "field": "x", "value": "Generic English text here."},
        ]
        results = russianize_fields_batch(None, items, cache={})
        self.assertEqual(len(results), 1)
        r = results["k1"]
        self.assertEqual(r.method, "safe_fallback")
        self.assertFalse(r.raw_output_exposed)
        self.assertFalse(r.added_facts_claim)

    def test_already_russian_skips_provider(self):
        items = [
            {"id": "k1", "field": "x",
             "value": "Это уже русская формулировка."},
        ]
        results = russianize_fields_batch(None, items, cache={})
        self.assertEqual(results["k1"].method, "already_russian")
        self.assertIn("уже русская", results["k1"].text_ru)


# --------------------------------------------------------------------------
# Regression — J/J2 contract preserved
# --------------------------------------------------------------------------

class TestJ3Regression(unittest.TestCase):
    def test_no_angl_blocks_with_cache(self):
        h = build_human_dossier(_english_case_with_cache()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotIn("(англ.)", text)
        self.assertNotIn("(англ. реконструкция)", text)

    def test_top_card_still_evidence_based(self):
        h = build_human_dossier(_english_case_with_cache()).to_dict()
        # Operator-supplied venue label still surfaces
        self.assertEqual(h["venue_name_ru"], "Вопросы философии")

    def test_technical_footer_preserved(self):
        h = build_human_dossier(_english_case_with_cache()).to_dict()
        f = h["technical_footer"]
        self.assertFalse(f["safety_gates"]["raw_llm_output_exposed"])
        self.assertEqual(f["safety_gates"]["fake_doi_or_ref_count"], 0)


if __name__ == "__main__":
    unittest.main()
