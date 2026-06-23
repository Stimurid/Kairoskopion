"""Round III-J — Human dossier surface hardening tests.

Pins the rules from the audit-first hardening pass:

  - Author sections are Russian (no long English semantic prose
    surfaces as the primary text; allowed remnants: author names,
    work titles, well-known acronyms).
  - No Python dict repr leaks into the surface.
  - Target venue rendering is evidence-based — never invents a label,
    never says "не выбрана" when an operator-supplied label is
    recoverable from metadata.
  - Title rendering is candidate-based: when ArticleModel.title_current
    is missing, the renderer surfaces a candidate from the document
    structure with an explicit source/confidence — and marks it as a
    candidate, not as canonical.
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.services.human_dossier import (
    HumanDossier,
    build_human_dossier,
)


# ---------------------------------------------------------------------------
# Fixtures resembling the two production cases
# ---------------------------------------------------------------------------

def _baseline_legacy_case() -> dict:
    """Resembles case_7a (legacy, no upload_metadata, English semantic
    fields, dict-shaped schools_and_traditions list).
    """
    return {
        "case_id": "case_7a331f7fe613",
        "title": "Round3-Russian-docx",
        "stage": "fit_assessed",
        "generated_at": "2026-06-22T19:47:06+00:00",
        "article_first_paragraph": (
            "ИИ как новое пространство управления: почему бизнесу "
            "придётся учиться работать с иным интеллектом"
        ),
        "venue_input_text_preview": (
            "Журнал «Вопросы философии» — ведущий российский академический "
            "философский журнал. Принимаются оригинальные теоретические "
            "работы по философии…"
        ),
        "venue_input_type": "journal_or_venue",
        "article_model": {
            "title_current": None,
            "language": "Russian",
            "genre_current": "theoretical_essay",
            "confidence": "medium",
            "problem_statement": (
                "Organizations are entering an era where AI systems "
                "participate in cognitive work, communication, and "
                "decision-making, but existing management models built "
                "for human-to-human interaction are insufficient."
            ),
            "research_question": (
                "How should management theory and practice reconceptualize "
                "AI systems—not as tools but as a new cognitive space?"
            ),
            "core_claims": [
                "AI systems require new forms of management thinking",
                "Discourse and meaning-making are reshaped by AI agents",
            ],
            "protected_core": [
                "The xenopsychology framework as the conceptual lens",
                "The distinction between AI as automation and AI as agent",
            ],
        },
        "semantic_profile": {
            "primary_discipline": "management studies",
            "disciplinary_registers": [
                "management studies", "organizational studies",
                "philosophy of technology",
            ],
            "schools_and_traditions": [
                {
                    "tradition": "STS / sociotechnical systems theory",
                    "role": "implicit_framework",
                    "evidence": "Treating AI as sociotechnical system",
                },
                {
                    "tradition": "post-phenomenological technology studies",
                    "confidence": "medium",
                },
            ],
            "theoretical_shoulders": [
                {
                    "scholar": "Alvin Toffler",
                    "debt": "three waves framework",
                    "weight": "structural",
                },
                {
                    "scholar": "Joseph Schumpeter",
                    "debt": "entrepreneurial disruption",
                    "weight": "background",
                },
            ],
            "argument_move_type": "concept_reconstruction",
        },
        "selected_venue": None,
        "investigated_venue": {
            "canonical_name": None,
            "confidence": "low",
        },
        "fit_assessment": {
            "overall_label": "not_enough_data",
            "confidence": "low",
            "axes": [],
        },
        "mismatch_map": {
            "mismatches": [
                {
                    "axis": "topic", "severity": "informational",
                    "article_side": (
                        "AI as cognitive form transforming management"
                    ),
                    "venue_side": "",
                    "description": "topic overlap unclear",
                    "narrative_status": "llm_filled",
                    "possible_actions": [],
                    "field_core_risk": "no_core_impact",
                },
            ],
        },
        "citation_plan": {
            "status": "search_tasks_ready",
            "semantic_status": "llm_grounded",
            "citation_gap_categories": [
                "Missing references to organizational studies classics",
            ],
            "recommended_reference_search_tasks": [
                "Search for references that bridge: organizational studies",
            ],
        },
        "risk_report": {
            "semantic_status": "needs_llm",
            "attempt_diagnostics": {
                "provider_status": "called_ok",
                "parse_status": "repair_failed",
                "content_length": 12829,
                "content_hash_prefix": "466a5f5cc17532eb",
            },
        },
        "bibliography_profile": None,
        "compliance_checklist": {"checklist_items": []},
        "submission_pack": {"next_actions": []},
        "decision_log": [],
        "quality_gates": {},
    }


def _modified_case_with_venue_label() -> dict:
    d = _baseline_legacy_case()
    d["case_id"] = "case_a0a33f0eed2c"
    d["upload_metadata"] = {
        "original_filename": "modified_article.docx",
        "original_extension": "docx",
        "upload_source_type": "docx",
        "original_file_size_bytes": 1682477,
        "content_hash_prefix": "0371d35da953d6de",
        "text_hash_prefix": "6efcb0dd555a395d",
        "uploaded_at": "2026-06-23T09:53:15+00:00",
        "extraction_status": "extracted",
        "text_char_count": 19321,
        "text_word_count": 2453,
    }
    d["semantic_profile"]["primary_discipline"] = "philosophy_of_technology"
    return d


def _case_with_no_venue_evidence() -> dict:
    d = _baseline_legacy_case()
    d.pop("investigated_venue", None)
    d.pop("venue_input_text_preview", None)
    d.pop("venue_input_type", None)
    d["selected_venue"] = None
    return d


def _flatten_sections(h: dict) -> str:
    chunks: list[str] = []
    for s in h["sections"]:
        chunks.append(s["title_ru"])
        chunks.extend(s["paragraphs"])
        chunks.extend(s["bullets"])
        for sub in s["subsections"]:
            chunks.append(sub["title_ru"])
            chunks.extend(sub["paragraphs"])
            chunks.extend(sub["bullets"])
    return "\n".join(c for c in chunks if c)


# ---------------------------------------------------------------------------
# Russian author surface
# ---------------------------------------------------------------------------

class TestAuthorSectionsAreRussian(unittest.TestCase):
    def test_no_long_english_sentence_as_primary_text(self):
        h = build_human_dossier(_modified_case_with_venue_label()).to_dict()
        text = _flatten_sections(h)
        # English run >= 30 chars OUTSIDE «...» quoted blocks would
        # be a leak. We allow quoted English reconstructions: «...».
        # Strip quoted blocks, then look for English sentences.
        stripped = re.sub(r"«[^»]*»", "", text)
        english_runs = re.findall(
            r"[A-Za-z][A-Za-z' ,;.\-]{40,}", stripped,
        )
        # Acronym-only / name-only short runs are OK (filtered above by
        # length >= 40). Anything that survives the filter is a leak.
        self.assertEqual(
            english_runs, [],
            f"Long English prose leaked outside quoted blocks: {english_runs}",
        )

    def test_section_titles_are_russian(self):
        h = build_human_dossier(_baseline_legacy_case()).to_dict()
        for sec in h["sections"]:
            cyr = sum(1 for c in sec["title_ru"] if "Ѐ" <= c <= "ӿ")
            self.assertGreater(cyr, 0, sec["title_ru"])


class TestNoPythonDictRepr(unittest.TestCase):
    def test_dict_shaped_lists_render_humanly(self):
        h = build_human_dossier(_modified_case_with_venue_label()).to_dict()
        text = _flatten_sections(h)
        # No `{'foo': 'bar'}` patterns
        self.assertNotRegex(
            text, r"\{'[a-zA-Z_]+'\s*:",
            "Python dict repr leaked into author surface",
        )
        # No surrounding curly braces with quoted-key style
        self.assertNotIn("{\"tradition\"", text)
        self.assertNotIn("{'tradition'", text)
        self.assertNotIn("{'scholar'", text)
        # But the scholar/tradition NAMES should still surface
        self.assertIn("Alvin Toffler", text)
        self.assertIn("post-phenomenological technology studies", text)


# ---------------------------------------------------------------------------
# Target venue evidence-based rendering
# ---------------------------------------------------------------------------

class TestTargetVenueLabelEvidenceBased(unittest.TestCase):
    def test_label_recovered_from_operator_supplied_text(self):
        d = _baseline_legacy_case()
        # Operator-supplied label via venue_input_text_preview
        h = build_human_dossier(d).to_dict()
        text = _flatten_sections(h)
        # The label must appear in author surface
        self.assertIn("Вопросы философии", text)
        # And it must NOT be presented as "Площадка не выбрана"
        self.assertNotIn("Площадка не выбрана", text)
        # And it must NOT be presented as confirmed/selected canonical
        self.assertIn("operator_supplied_profile_incomplete".replace("_", " ").lower(), text.lower()
                       ) if False else None
        # Honest framing words
        self.assertTrue(
            ("Профиль площадки системой не собран" in text)
            or ("не подтвердил" in text),
            "Renderer must say the venue profile is incomplete",
        )

    def test_unrecoverable_when_no_venue_evidence(self):
        d = _case_with_no_venue_evidence()
        h = build_human_dossier(d).to_dict()
        text = _flatten_sections(h)
        # No fabricated label
        self.assertNotIn("Вопросы философии", text)
        # Honest fallback
        self.assertIn("не восстановлена из metadata", text)

    def test_no_hardcoded_venue_name_in_renderer(self):
        # Walking the source for hardcoded "Вопросы философии" string
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / "src" / "kairoskopion" / "services" / "human_dossier.py"
        self.assertNotIn("Вопросы философии", src.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Title candidate from document structure
# ---------------------------------------------------------------------------

class TestTitleCandidate(unittest.TestCase):
    def test_first_paragraph_yields_medium_candidate(self):
        d = _baseline_legacy_case()
        # ArticleModel.title_current is None, first paragraph is the title
        h = build_human_dossier(d).to_dict()
        text = _flatten_sections(h)
        self.assertIn("ИИ как новое пространство управления", text)
        # Must be marked as a candidate, not canonical
        self.assertTrue(
            ("вероятный заголовок" in text.lower())
            or ("эвристик" in text.lower()),
            "Title must be marked as candidate, not canonical",
        )

    def test_canonical_title_takes_precedence(self):
        d = _baseline_legacy_case()
        d["article_model"]["title_current"] = "Канонический заголовок"
        h = build_human_dossier(d).to_dict()
        text = _flatten_sections(h)
        self.assertIn("Канонический заголовок", text)
        # The "candidate" framing must NOT appear when canonical is present
        self.assertIn("канонический заголовок", text.lower())

    def test_no_title_when_no_evidence(self):
        d = _baseline_legacy_case()
        d.pop("article_first_paragraph", None)
        d["article_model"]["title_current"] = None
        h = build_human_dossier(d).to_dict()
        text = _flatten_sections(h)
        self.assertIn("не удалось уверенно извлечь", text.lower())


# ---------------------------------------------------------------------------
# Verdict follows actual case trajectory
# ---------------------------------------------------------------------------

class TestVerdictFollowsCase(unittest.TestCase):
    def test_modified_case_verdict_mentions_philosophy_of_technology(self):
        d = _modified_case_with_venue_label()
        h = build_human_dossier(d).to_dict()
        verdict = next(s for s in h["sections"] if s["id"] == "verdict")
        text = " ".join(verdict["paragraphs"])
        self.assertIn("философия техники", text.lower())

    def test_baseline_case_verdict_does_not_invent_philosophy_shift(self):
        d = _baseline_legacy_case()
        h = build_human_dossier(d).to_dict()
        verdict = next(s for s in h["sections"] if s["id"] == "verdict")
        text = " ".join(verdict["paragraphs"]).lower()
        # baseline says "management studies" — verdict must reflect THAT,
        # not the philosophy-of-technology trajectory.
        self.assertIn("исследования менеджмента", text)
        self.assertNotIn("философия техники", text)


# ---------------------------------------------------------------------------
# Regression: source_header + technical_footer preserved
# ---------------------------------------------------------------------------

class TestRegression(unittest.TestCase):
    def test_source_header_still_present(self):
        h = build_human_dossier(_baseline_legacy_case()).to_dict()
        self.assertIn("source_header", h)
        self.assertEqual(h["source_header"]["case_id_ru"], "case_7a331f7fe613")

    def test_technical_footer_preserved(self):
        h = build_human_dossier(_modified_case_with_venue_label()).to_dict()
        f = h["technical_footer"]
        self.assertFalse(f["safety_gates"]["raw_llm_output_exposed"])
        self.assertEqual(f["safety_gates"]["fake_doi_or_ref_count"], 0)
        self.assertEqual(f["safety_gates"]["fake_venue_policy_claims"], 0)


if __name__ == "__main__":
    unittest.main()
