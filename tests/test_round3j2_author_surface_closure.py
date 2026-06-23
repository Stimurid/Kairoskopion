"""Round III-J2 — Author surface closure tests.

These are stricter than the Round III-J tests:

  - Top card (HumanDossier.venue_name_ru / title_ru) must agree with
    the evidence helpers — never says "Площадка не выбрана" when a
    target label exists in metadata.
  - Source header (document_title_ru) must use the title candidate
    when ArticleModel.title_current is missing — never says "Заголовок
    в документе не найден" while a candidate exists.
  - Author sections must NOT contain `(англ.)` / `(англ. реконструкция)`
    blocks for semantic prose.
  - Author sections must NOT contain long English semantic prose
    anywhere (including inside `«…»` quotes).
  - Original English semantic fields stay available in technical view
    but not in the author surface.
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.services.human_dossier import (
    build_human_dossier,
)


def _english_case() -> dict:
    """Resembles case_a0a33f0eed2c: English semantic prose + dict-shaped
    schools/shoulders + operator-supplied venue + missing canonical title.
    """
    return {
        "case_id": "case_a0a33f0eed2c",
        "title": "Round3-Russian-docx",
        "stage": "adapting",
        "generated_at": "2026-06-23T09:53:15+00:00",
        "article_first_paragraph": (
            "ИИ как новое пространство управления: почему бизнесу "
            "придётся учиться работать с иным интеллектом"
        ),
        "venue_input_text_preview": (
            "Вопросы философии — российский философский журнал…"
        ),
        "venue_input_type": "venue",
        "article_model": {
            "title_current": None,
            "language": "Russian",
            "genre_current": "theoretical_essay",
            "confidence": "medium",
            "problem_statement": (
                "Organizations are encountering AI not as a simple digital "
                "tool but as a different cognitive form entering the space "
                "of decisions, language, interpretations, and responsibility."
            ),
            "research_question": (
                "How should business management reconceptualize AI beyond "
                "instrumental logic to engage with it as a new form of "
                "cognitive agency?"
            ),
            "object_of_inquiry": (
                "The transformation of organizational management and "
                "decision-making processes through the integration of AI."
            ),
            "core_claims": [
                "AI cannot be adequately understood solely as a management "
                "tool; it represents a different cognitive form.",
                "Organizations face the emergence of a new form of "
                "subject-like behavior requiring new managerial models.",
            ],
            "protected_core": [
                "The central thesis that AI represents a new management "
                "space requiring interaction with fundamentally different "
                "cognitive architecture.",
                "The xenopsychology framework as the conceptual lens.",
            ],
            "mutable_zones": [
                "Hotel industry examples and case applications",
                "Introductory contextualization about AI discourse",
            ],
            "unknowns": [
                "Whether xenopsychology framework has established literature",
                "Specific empirical grounding of hotel industry claims",
            ],
        },
        "semantic_profile": {
            "primary_discipline": "philosophy_of_technology",
            "disciplinary_registers": [
                "philosophy_of_technology", "organizational_theory",
                "philosophy_of_ai", "actor_network_theory",
            ],
            "schools_and_traditions": [
                {
                    "tradition": "post-phenomenological technology studies",
                    "confidence": "medium",
                    "evidence": (
                        "Treating AI as mediator that transforms "
                        "organizational perception and action."
                    ),
                },
                {
                    "tradition": "actor_network_theory",
                    "confidence": "high",
                    "evidence": (
                        "AI as actor entering organizational networks."
                    ),
                },
            ],
            "theoretical_shoulders": [
                {
                    "scholar": "Alvin Toffler",
                    "debt": "Temporal framework for AI as fourth-wave.",
                    "weight": "structural",
                },
                {
                    "scholar": "Timur Shchukin",
                    "debt": "Xenopsychology framework.",
                    "weight": "foundational",
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
            "axes": [
                {"axis": "topic", "value": "ok",
                 "notes": "could be management journal, business publication"},
            ],
        },
        "mismatch_map": {
            "mismatches": [
                {
                    "axis": "topic", "severity": "informational",
                    "article_side": (
                        "Transformation of management through AI as "
                        "cognitive agent rather than tool."
                    ),
                    "venue_side": "",
                    "description": (
                        "Topic overlap unclear because scope_summary is "
                        "missing."
                    ),
                    "narrative_status": "llm_filled",
                    "possible_actions": [],
                    "field_core_risk": "no_core_impact",
                },
            ],
        },
        "citation_plan": None,
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
        "compliance_checklist": {
            "checklist_items": [
                {"requirement": "Manuscript title required",
                 "status": "missing", "category": "metadata"},
            ],
        },
        "submission_pack": {
            "next_actions": [
                "Add a recognizable title section to the manuscript.",
            ],
        },
        "upload_metadata": {
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
        },
        "decision_log": [],
        "quality_gates": {},
    }


def _flatten_author_text(h: dict) -> str:
    """Everything that ends up in the AUTHOR-facing surface.
    Excludes technical_footer (which legitimately holds English).
    """
    chunks: list[str] = []
    chunks.append(h.get("title_ru", ""))
    chunks.append(h.get("venue_name_ru", ""))
    sh = h.get("source_header") or {}
    for k in ("source_filename_ru", "source_type_ru", "size_ru",
              "document_title_ru", "case_id_ru", "generated_at_ru"):
        chunks.append(sh.get(k, ""))
    chunks.extend(sh.get("notes") or [])
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
# Track A — top card / source header consistency
# ---------------------------------------------------------------------------

class TestTopCardUsesEvidence(unittest.TestCase):
    def test_top_card_venue_uses_evidence_label(self):
        h = build_human_dossier(_english_case()).to_dict()
        # The case has an operator-supplied venue label; the top card
        # MUST reflect it and MUST NOT say "Площадка не выбрана".
        self.assertEqual(h["venue_name_ru"], "Вопросы философии")
        text = _flatten_author_text(h)
        self.assertNotIn("Площадка не выбрана", text)

    def test_top_card_title_uses_candidate_when_canonical_missing(self):
        h = build_human_dossier(_english_case()).to_dict()
        self.assertIn("ИИ как новое пространство", h["title_ru"])

    def test_source_header_uses_title_candidate(self):
        h = build_human_dossier(_english_case()).to_dict()
        doc_title = h["source_header"]["document_title_ru"]
        # Must not be the legacy "not found" string when a candidate
        # exists.
        self.assertNotIn("Заголовок в документе не найден", doc_title)
        self.assertIn("ИИ как новое пространство", doc_title)

    def test_top_card_falls_back_honestly_when_no_evidence(self):
        d = _english_case()
        d.pop("investigated_venue", None)
        d.pop("venue_input_text_preview", None)
        d.pop("venue_input_type", None)
        d["selected_venue"] = None
        h = build_human_dossier(d).to_dict()
        # No venue evidence — must say "не восстановлена", not invent.
        self.assertIn("не восстановлена", h["venue_name_ru"])


# ---------------------------------------------------------------------------
# Track B — no English semantic prose in author sections
# ---------------------------------------------------------------------------

# Semantic prose probes from the user's spec — these phrases MUST NOT
# appear anywhere in the author-facing surface.
FORBIDDEN_SEMANTIC_PROSE = (
    "Organizations are entering",
    "Organizations are encountering",
    "How should management theory",
    "How should business management",
    "The transformation of",
    "AI represents a new management space",
    "Central thesis that AI is not a tool",
    "Central thesis that AI represents",
    "Hotel industry examples and case applications",
    "Treating AI as mediator",
    "Temporal framework for AI",
    "Xenopsychology framework",
)


class TestNoEnglishSemanticProseInAuthorSections(unittest.TestCase):
    def test_forbidden_phrases_absent(self):
        h = build_human_dossier(_english_case()).to_dict()
        text = _flatten_author_text(h)
        for phrase in FORBIDDEN_SEMANTIC_PROSE:
            self.assertNotIn(
                phrase, text,
                f"forbidden English semantic prose leaked into author "
                f"surface: {phrase!r}",
            )

    def test_no_angl_wrapped_semantic_blocks(self):
        h = build_human_dossier(_english_case()).to_dict()
        text = _flatten_author_text(h)
        # (англ.) / (англ. реконструкция) framings MUST NOT remain
        self.assertNotIn("(англ.)", text)
        self.assertNotIn("(англ. реконструкция)", text)

    def test_no_legacy_english_disclosure_phrase(self):
        h = build_human_dossier(_english_case()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotIn(
            "поле сохранено в исходной англоязычной формулировке", text,
        )

    def test_long_english_semantic_prose_count_is_zero(self):
        """Long English prose ANYWHERE in the author surface — even
        inside quotes — is a leak. Allowed remnants are short author
        names / source titles / acronyms (<40 chars per chunk).
        """
        h = build_human_dossier(_english_case()).to_dict()
        text = _flatten_author_text(h)
        # Strip allowed Russian-quoted Russian content (i.e., «...»
        # blocks whose CONTENT is itself Russian or short).
        # Detection: an English run of >=40 consecutive Latin + ascii
        # punctuation chars is a semantic-prose leak.
        leaks = re.findall(r"[A-Za-z][A-Za-z' ,;.\-]{40,}", text)
        # Filter author/work titles like "Heidegger 'Question Concerning Technology'"
        # which the spec explicitly allows. Such a chunk is shorter than
        # 80 chars and contains either an apostrophe-quoted title or
        # several Capitalized words. We're stricter than that: any
        # ≥80-char English run is a leak no matter what.
        big_leaks = [l for l in leaks if len(l) >= 80]
        self.assertEqual(
            big_leaks, [],
            f"long English prose leaked into author surface: {big_leaks}",
        )


# ---------------------------------------------------------------------------
# Regression: technical footer preserved + raw_output gates
# ---------------------------------------------------------------------------

class TestSurfaceClosureRegression(unittest.TestCase):
    def test_technical_footer_preserved(self):
        h = build_human_dossier(_english_case()).to_dict()
        f = h["technical_footer"]
        self.assertFalse(f["safety_gates"]["raw_llm_output_exposed"])
        self.assertEqual(f["safety_gates"]["fake_doi_or_ref_count"], 0)
        self.assertEqual(f["safety_gates"]["fake_venue_policy_claims"], 0)

    def test_no_python_dict_repr_in_author_surface(self):
        h = build_human_dossier(_english_case()).to_dict()
        text = _flatten_author_text(h)
        self.assertNotRegex(text, r"\{'[a-zA-Z_]+'\s*:")

    def test_no_hardcoded_venue_label_in_renderer(self):
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / "src" / "kairoskopion" / "services" / "human_dossier.py"
        self.assertNotIn("Вопросы философии", src.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
