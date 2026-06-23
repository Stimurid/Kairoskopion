"""Round III-H: human-readable Russian author dossier (presentation layer).

Pins the presentation contract:

  - Russian section titles for all 12 sections.
  - No raw JSON dump or English technical headings in the main text.
  - CitationPlan English template prefixes get rewritten to Russian.
  - RiskReport is rendered HONESTLY when semantic_status != llm_grounded
    (no fabricated risk items; redacted diagnostic block only).
  - No fake DOIs / author-year leaks anywhere in the human text.
  - Doctrine: NO LLM call, NO network, NO mutation of upstream models.
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.services.human_dossier import (
    HumanDossier,
    HumanSection,
    build_human_dossier,
)


# ---------------------------------------------------------------------------
# Synthetic dossier resembling case_7a331f7fe613
# ---------------------------------------------------------------------------

def _case_7a_like_dossier() -> dict:
    return {
        "case_id": "case_7a331f7fe613",
        "title": "Статья Тимура (Вариант 2)",
        "stage": "fit_assessed",
        "generated_at": "2026-06-22T19:47:06+00:00",
        "article_model": {
            "title_current": "",
            "language": "Russian",
            "genre_current": "theoretical_essay",
            "confidence": "medium",
            "protected_core": [
                "Различение цифровизации первого и второго порядка",
                "Тезис о пяти следствиях первого кризиса",
            ],
            "mutable_zones": ["введение", "стиль изложения"],
            "unknowns": ["явный заголовок", "формальный abstract"],
            "problem_statement": (
                "О чем такое реальная цифровизация: кризис первой великой попытки."
            ),
            "core_claims": [
                "Цифровизация прошла первый кризис.",
                "Из этого кризиса следует пять структурных следствий.",
            ],
        },
        "semantic_profile": {
            "primary_discipline": "philosophy of technology",
            "disciplinary_registers": [
                "organizational studies", "STS", "philosophy of AI",
            ],
            "schools_and_traditions": [
                "Тоффлер", "Шумпетер", "STS-программа",
            ],
            "theoretical_shoulders": ["organizational discourse", "STS"],
            "opponents_or_foils": ["технооптимизм", "наивный AI-детерминизм"],
            "citation_bridges_needed": [
                "organizational studies классики",
                "STS-программа (Latour/Callon/Law/Mol)",
                "AI in organizations 2020–2025",
            ],
        },
        "selected_venue": {
            "canonical_name": "Вопросы философии",
            "venue_type": "journal",
            "confidence": "low",
            "aims_scope_summary": None,
        },
        "fit_assessment": {
            "overall_label": "not_enough_data",
            "confidence": "low",
            "axes": [
                {"axis": "topic", "value": "ok",
                 "notes": "тема пересекается с философией техники"},
                {"axis": "discipline", "value": "partial_fit",
                 "notes": "несколько дисциплинарных регистров"},
                {"axis": "genre", "value": "unknown",
                 "notes": "политика журнала по теоретическим эссе неизвестна"},
                {"axis": "citation_ecology", "value": "weak",
                 "notes": "библиография отсутствует"},
                {"axis": "language_register", "value": "unknown"},
                {"axis": "audience", "value": "unknown"},
                {"axis": "formal_compliance", "value": "unknown"},
                {"axis": "author_eligibility", "value": "unknown"},
            ],
        },
        "mismatch_map": {
            "mismatches": [
                {
                    "axis": "topic", "severity": "minor",
                    "article_side": "цифровизация и AI",
                    "venue_side": "философия в широком смысле",
                    "description": "тема пересекается, но не центральная",
                    "possible_actions": ["усилить философскую рамку"],
                    "narrative_status": "llm_filled",
                    "field_core_risk": "no_core_impact",
                },
                {
                    "axis": "citation_ecology", "severity": "major",
                    "article_side": "источники не оформлены отдельно",
                    "venue_side": "",
                    "description": "библиография как раздел отсутствует",
                    "possible_actions": [
                        "добавить раздел «Список литературы»",
                        "оформить ссылки в распознаваемом виде",
                    ],
                    "narrative_status": "unknown_due_to_venue_evidence",
                    "field_core_risk": "no_core_impact",
                },
                {
                    "axis": "genre", "severity": "major",
                    "article_side": "теоретическое эссе",
                    "venue_side": "",
                    "description": "",
                    "possible_actions": [],
                    "narrative_status": "needs_llm",
                    "field_core_risk": "unknown_core_impact",
                },
            ],
        },
        "citation_plan": {
            "status": "search_tasks_ready",
            "semantic_status": "llm_grounded",
            "confidence": "low",
            "citation_gap_categories": [
                "Отсутствуют ссылки на классиков organizational studies",
                "Нет включения STS-программы в обсуждение",
            ],
            "missing_bridge_categories": [
                "Мост к organizational studies",
                "Мост к STS-программе",
            ],
            "recommended_reference_search_tasks": [
                "Search for references that bridge: organizational theory classics",
                "Search for references that bridge: STS Latour Callon",
                "Find references for AI in organizations 2020-2025",
            ],
            "verification_tasks": [
                "Verify cross-citation between AI and STS literature",
            ],
            "dangerous_padding_warnings": [
                "Не добивать библиографию ради видимости полноты",
            ],
            "unknowns": ["реальный профиль цитатной экологии журнала"],
        },
        "risk_report": {
            "semantic_status": "needs_llm",
            "risk_items": [],
            "attempt_diagnostics": {
                "ok": False,
                "content_present": True,
                "content_length": 12829,
                "content_hash_prefix": "466a5f5cc17532eb",
                "provider_status": "called_ok",
                "parse_status": "repair_failed",
                "parse_failure_category": "repair_failed",
                "repair_attempted": True,
                "repair_status": "repair_failed",
                "model_role": "risk_officer",
                "agent_role": "risk_officer",
                "semantic_status": "needs_llm",
            },
        },
        "compliance_checklist": {"checklist_items": []},
        "submission_pack": {
            "next_actions": [
                "Добавить заголовок и abstract",
                "Оформить библиографию",
            ],
        },
        "bibliography_profile": None,
        "decision_log": [],
        "quality_gates": {},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

EXPECTED_TITLES = [
    "1. Паспорт",
    "2. Что система поняла про статью",
    "3. Где находится статья в поле",
    "4. Что известно и неизвестно про площадку",
    "5. FitAssessment: почему вердикт «not_enough_data»",
    "6. Несовпадения и работа по ним",
    "7. Работа с источниками",
    "8. Библиография",
    "9. Формальные проверки",
    "10. Что не удалось системе: риск-анализ",
    "11. SubmissionPack / что делать дальше",
    "12. Итоговый авторский вердикт",
]

# Tokens that, if present in the AUTHOR-FACING text, would signal a
# leaked technical surface and break the spec.
FORBIDDEN_TECH_TOKENS = (
    "field_origins", "semantic_status", "provider_status",
    "parse_status:", "created_from",
    "{", "}", "  ",  # JSON-ish surface
)

# DOI pattern — forbidden in author-facing text (no fabricated refs).
DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+", re.IGNORECASE)


class TestHumanDossierShape(unittest.TestCase):
    def test_returns_human_dossier_with_all_12_sections(self):
        h = build_human_dossier(_case_7a_like_dossier())
        self.assertIsInstance(h, HumanDossier)
        self.assertEqual(len(h.sections), 12)
        for sec, expected in zip(h.sections, EXPECTED_TITLES):
            self.assertEqual(sec.title_ru, expected)

    def test_to_dict_is_serializable_and_section_titles_russian(self):
        h = build_human_dossier(_case_7a_like_dossier())
        d = h.to_dict()
        self.assertIn("sections", d)
        for sec in d["sections"]:
            self.assertIn("title_ru", sec)
            # Russian Cyrillic must dominate the title
            cyr = sum(1 for c in sec["title_ru"] if "Ѐ" <= c <= "ӿ")
            self.assertGreater(cyr, 0, sec["title_ru"])

    def test_works_on_empty_dossier(self):
        # Doctrine: must never crash even on partial / missing dossier
        h = build_human_dossier({})
        self.assertEqual(len(h.sections), 12)
        for sec in h.sections:
            # Each section produces *some* author-facing text
            self.assertTrue(sec.paragraphs or sec.bullets or sec.subsections)


class TestHumanDossierAntiSlop(unittest.TestCase):
    def setUp(self):
        self.h = build_human_dossier(_case_7a_like_dossier())

    def _flat_text(self, secs: list[HumanSection]) -> str:
        chunks: list[str] = []
        for s in secs:
            chunks.append(s.title_ru)
            chunks.extend(s.paragraphs)
            chunks.extend(s.bullets)
            for sub in s.subsections:
                chunks.append(sub.title_ru)
                chunks.extend(sub.paragraphs)
                chunks.extend(sub.bullets)
        return "\n".join(c for c in chunks if c)

    def test_no_raw_tech_tokens_in_author_text(self):
        text = self._flat_text(self.h.sections)
        for tok in ("field_origins", "semantic_status:", "provider_status:",
                    "parse_status:", "created_from:"):
            self.assertNotIn(tok, text,
                             f"forbidden technical token in author text: {tok}")

    def test_no_fake_doi_in_author_text(self):
        text = self._flat_text(self.h.sections)
        self.assertIsNone(DOI_RE.search(text),
                          "no fabricated DOI may appear in human dossier")

    def test_citation_section_translates_english_template_prefixes(self):
        sources = next(s for s in self.h.sections if s.id == "sources")
        text = " ".join(
            b for sub in sources.subsections for b in sub.bullets
        )
        # English template prefixes must NOT survive into author text
        self.assertNotIn("Search for references that bridge:", text)
        # Russian rewrite MUST appear
        self.assertIn("Найти источники", text)

    def test_risk_section_does_not_fake_risk_items(self):
        risk = next(s for s in self.h.sections if s.id == "risk")
        text = " ".join(risk.paragraphs + risk.bullets)
        # Honest framing: section MUST say analysis is NOT ready
        self.assertTrue(
            "не готов" in text or "не выдумывает" in text,
            f"risk section must honestly mark itself as not-ready; got: {text}",
        )
        # Redacted diagnostics: hash + length appear, raw output does not
        self.assertIn("466a5f5cc17532eb", text)
        self.assertIn("12829", text)

    def test_main_text_contains_no_english_section_headings(self):
        text = self._flat_text(self.h.sections)
        # These are English upstream lane headings that must not surface
        for english in (
            "Article Model", "Selected Venue",
            "Fit Assessment", "Mismatch Map",
            "Citation Plan", "Risk Report", "Submission Pack",
            "Compliance Checklist", "Bibliography Profile",
        ):
            self.assertNotIn(english, text,
                             f"English technical heading leaked: {english}")


class TestHumanDossierMismatches(unittest.TestCase):
    def test_each_mismatch_axis_rendered_with_russian_status(self):
        h = build_human_dossier(_case_7a_like_dossier())
        mm_section = next(s for s in h.sections if s.id == "mismatches")
        axes_seen = {sub.title_ru for sub in mm_section.subsections}
        # 3 axes: topic, citation_ecology, genre
        self.assertEqual(len(mm_section.subsections), 3)
        self.assertTrue(any("Тематическая" in t for t in axes_seen))
        self.assertTrue(any("Цитатная" in t for t in axes_seen))
        # The needs_llm axis is rendered honestly, not faked as filled
        genre_sub = next(
            sub for sub in mm_section.subsections if "Жанр" in sub.title_ru
        )
        self.assertEqual(genre_sub.badge, "needs_llm")


class TestHumanDossierBibliographyAndNextActions(unittest.TestCase):
    def test_bibliography_section_explains_what_to_do_when_absent(self):
        h = build_human_dossier(_case_7a_like_dossier())
        bib = next(s for s in h.sections if s.id == "bibliography")
        text = " ".join(bib.paragraphs + bib.bullets)
        self.assertIn("Список литературы", text)

    def test_next_actions_prefers_explicit_submission_pack_actions(self):
        h = build_human_dossier(_case_7a_like_dossier())
        nxt = next(s for s in h.sections if s.id == "next_actions")
        joined = " ".join(nxt.bullets)
        self.assertIn("Добавить заголовок и abstract", joined)


if __name__ == "__main__":
    unittest.main()
