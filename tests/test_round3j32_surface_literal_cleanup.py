"""Round III-J3.2 — Tiny author-surface literal cleanup.

Pin the renderer against two surface defects:
1. Python list-literal strings leaking into author surface
2. "русская переформулировка не построена" in passport/section 2 register line
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.services.human_dossier import build_human_dossier


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


def _base_case(**overrides: object) -> dict:
    case: dict = {
        "case_id": "case_test_j32",
        "title": "test",
        "stage": "fit_assessed",
        "generated_at": "2026-06-23T00:00:00+00:00",
        "russian_surface_cache": {},
        "article_first_paragraph": "ИИ как новое пространство управления",
        "venue_input_text_preview": "Вопросы философии — журнал",
        "venue_input_type": "venue",
        "article_model": {
            "title_current": None,
            "language": "Russian",
            "genre_current": "theoretical_essay",
            "confidence": "medium",
            "problem_statement": "Тестовая проблема.",
            "research_question": "Тестовый вопрос?",
            "core_claims": ["Центральный тезис."],
            "protected_core": ["Защищаемый элемент."],
            "mutable_zones": ["Зона гибкости."],
        },
        "decision_log": [],
        "quality_gates": {},
    }
    am = case["article_model"]
    for k, v in overrides.items():
        if k in am:
            am[k] = v
        else:
            case[k] = v
    return case


# --------------------------------------------------------------------------
# Track A — no list literal repr
# --------------------------------------------------------------------------

class TestNoListLiteralReprInAuthorSurface(unittest.TestCase):
    def test_stringified_list_in_protected_core(self):
        case = _base_case(
            protected_core=["['Защищаемый элемент А', 'Защищаемый элемент Б']"],
        )
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\['")
        self.assertNotRegex(text, r"'\]")
        self.assertNotIn("', '", text)

    def test_stringified_list_in_core_claims(self):
        case = _base_case(
            core_claims=["['Тезис один', 'Тезис два', 'Тезис три']"],
        )
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\['")
        self.assertNotIn("', '", text)

    def test_stringified_list_in_mutable_zones(self):
        case = _base_case(
            mutable_zones=['["Зона А", "Зона Б"]'],
        )
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r'\["')
        self.assertNotIn('", "', text)

    def test_list_literal_repr_metric_zero(self):
        case = _base_case(
            protected_core=["['Элемент А', 'Элемент Б']"],
            core_claims=["['Тезис один', 'Тезис два']"],
        )
        h = build_human_dossier(case).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertEqual(sg["list_literal_repr_count"], 0)

    def test_list_literal_metric_present(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertIn("list_literal_repr_count", sg)


class TestProtectedCoreListStringRendersAsBullets(unittest.TestCase):
    def test_items_render_as_separate_bullets(self):
        case = _base_case(
            protected_core=["['Защищаемый элемент А', 'Защищаемый элемент Б']"],
        )
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertIn("Защищаемый элемент А", text)
        self.assertIn("Защищаемый элемент Б", text)

    def test_normal_list_still_works(self):
        case = _base_case(
            protected_core=["Нормальный элемент один", "Нормальный элемент два"],
        )
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertIn("Нормальный элемент один", text)
        self.assertIn("Нормальный элемент два", text)


# --------------------------------------------------------------------------
# Track B — no "русская переформулировка не построена" in passport
# --------------------------------------------------------------------------

class TestNoUnbuiltRussianSurfacePhraseInPassport(unittest.TestCase):
    def _get_passport_and_section2_text(self, case: dict) -> str:
        h = build_human_dossier(case).to_dict()
        chunks: list[str] = []
        for s in h["sections"][:2]:
            chunks.extend(s["paragraphs"])
            chunks.extend(s["bullets"])
            for sub in s["subsections"]:
                chunks.extend(sub["paragraphs"])
                chunks.extend(sub["bullets"])
        return "\n".join(c for c in chunks if c)

    def test_mapped_register_shows_russian(self):
        case = _base_case()
        case["article_model"]["disciplinary_register_current"] = [
            "management_studies", "organizational_theory",
        ]
        text = self._get_passport_and_section2_text(case)
        self.assertNotIn("русская переформулировка не построена", text)
        self.assertIn("исследования менеджмента", text)
        self.assertIn("теория организаций", text)

    def test_unknown_register_shows_label_not_fallback(self):
        case = _base_case()
        case["article_model"]["disciplinary_register_current"] = [
            "some_unknown_field",
        ]
        text = self._get_passport_and_section2_text(case)
        self.assertNotIn("русская переформулировка не построена", text)
        self.assertIn("some unknown field", text)

    def test_missing_register_shows_not_defined(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotIn("русская переформулировка не построена", text)

    def test_string_register_renders_cleanly(self):
        case = _base_case()
        case["article_model"]["disciplinary_register_current"] = (
            "philosophy_of_technology"
        )
        text = self._get_passport_and_section2_text(case)
        self.assertNotIn("русская переформулировка не построена", text)
        self.assertIn("философия техники", text)


# --------------------------------------------------------------------------
# Regression
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


class TestJ32Regression(unittest.TestCase):
    def test_no_forbidden_placeholders(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        for phrase in _FORBIDDEN_PLACEHOLDERS:
            self.assertNotIn(phrase, text)

    def test_raw_output_not_exposed(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        sg = h["technical_footer"]["safety_gates"]
        self.assertFalse(sg["raw_llm_output_exposed"])
        self.assertEqual(sg["fake_doi_or_ref_count"], 0)

    def test_no_raw_search_for(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\bSearch for\b")

    def test_no_python_dict_repr(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\{'[a-zA-Z_]+'\s*:")

    def test_no_angl_blocks(self):
        case = _base_case()
        h = build_human_dossier(case).to_dict()
        text = _flatten_author_text(h)
        self.assertNotIn("(англ.)", text)


if __name__ == "__main__":
    unittest.main()
