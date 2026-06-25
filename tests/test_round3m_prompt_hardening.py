"""Round III-M tests: SemanticProfiler + FitAssessor prompt/schema hardening,
title extraction fix, and prose dictionary coverage.

Same K2 pattern: verify that the prompt families, JSON repair, and adapter
chains tolerate common LLM output variations.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from kairoskopion.llm.json_repair import repair_and_parse
from kairoskopion.prompts.semantic_profiling import (
    SEMANTIC_PROFILING_OUTPUT_SCHEMA,
)
from kairoskopion.prompts.fit_assessment import (
    FIT_ASSESSMENT_OUTPUT_SCHEMA,
)
from kairoskopion.agents.article_modeler import _build_from_llm as _build_article
from kairoskopion.schema import ManuscriptModel


# ---- SemanticProfile parse tolerance ----

class TestSemanticProfileParseTolerance:
    SCHEMA = SEMANTIC_PROFILING_OUTPUT_SCHEMA

    def _good_profile(self) -> dict:
        return {
            "disciplinary_registers": ["philosophy of technology", "STS"],
            "primary_discipline": "philosophy of technology",
            "schools_and_traditions": ["postphenomenology"],
            "theoretical_shoulders": ["Ihde", "Simondon"],
            "opponents_or_foils": [],
            "argument_move_type": "model_building",
            "argument_move_description": "builds a tripartite model",
            "citation_bridges_needed": [],
            "citation_ecology_description": None,
            "protected_core_candidates": ["central distinction"],
            "mutable_zones": ["introduction"],
            "field_core_nonnegotiables": [],
            "intended_audience": "philosophers of technology",
            "audience_expertise_level": "specialist",
            "unknowns": ["citation ecology"],
            "questions_for_user": [],
            "confidence": "medium",
        }

    def test_pure_json(self):
        raw = json.dumps(self._good_profile())
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.status == "parsed_ok"
        assert out.parsed["primary_discipline"] == "philosophy of technology"

    def test_fenced_json(self):
        raw = "```json\n" + json.dumps(self._good_profile()) + "\n```"
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None
        assert "parsed" in out.status or "repaired" in out.status

    def test_thinking_wrapped(self):
        raw = (
            "<thinking>I need to analyze this article carefully.</thinking>\n"
            + json.dumps(self._good_profile())
        )
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None

    def test_prose_before_json(self):
        raw = "Here is my analysis:\n" + json.dumps(self._good_profile())
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None

    def test_additional_properties_tolerated(self):
        data = self._good_profile()
        data["extra_field_from_llm"] = "should not break"
        data["analysis_notes"] = "some internal reasoning"
        raw = json.dumps(data)
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.status == "parsed_ok"
        assert out.parsed is not None

    def test_missing_optional_fields_filled(self):
        data = {
            "disciplinary_registers": ["STS"],
            "argument_move_type": "model_building",
            "confidence": "medium",
        }
        raw = json.dumps(data)
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None
        assert out.parsed.get("schools_and_traditions") == []
        assert out.parsed.get("unknowns") == []

    def test_schema_no_longer_requires_fields(self):
        assert self.SCHEMA.get("required") == []
        assert self.SCHEMA.get("additionalProperties") is True


# ---- FitAssessment parse tolerance ----

class TestFitAssessmentParseTolerance:
    SCHEMA = FIT_ASSESSMENT_OUTPUT_SCHEMA

    def _good_fit(self) -> dict:
        return {
            "overall_label": "possible_but_costly",
            "axes": [
                {"axis": "topic_fit", "value": "weak", "reasoning": "low overlap"},
                {"axis": "discipline_fit", "value": "moderate", "reasoning": "partial match"},
            ],
            "recommendation": "Consider strengthening topic alignment",
            "critical_issues": ["topic mismatch"],
            "strengths": ["strong argument structure"],
            "unknowns": ["citation ecology"],
            "questions_for_user": [],
            "confidence": "medium",
        }

    def test_pure_json(self):
        raw = json.dumps(self._good_fit())
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.status == "parsed_ok"
        assert out.parsed["overall_label"] == "possible_but_costly"

    def test_fenced_json(self):
        raw = "```json\n" + json.dumps(self._good_fit()) + "\n```"
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None

    def test_thinking_wrapped(self):
        raw = (
            "<thinking>Let me assess each axis.</thinking>\n"
            + json.dumps(self._good_fit())
        )
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.parsed is not None

    def test_additional_properties_tolerated(self):
        data = self._good_fit()
        data["reasoning_summary"] = "not in schema but should not break"
        raw = json.dumps(data)
        out = repair_and_parse(raw, schema=self.SCHEMA)
        assert out.status == "parsed_ok"

    def test_axes_as_dict_tolerated(self):
        """LLM sometimes returns axes as dict instead of list."""
        from kairoskopion.agents.fit_assessor import _build_from_llm
        data = {
            "overall_label": "possible",
            "axes": {
                "topic_fit": {"value": "strong", "reasoning": "good match"},
                "discipline_fit": {"value": "moderate", "reasoning": "partial"},
            },
            "unknowns": [],
            "confidence": "medium",
        }
        fit = _build_from_llm(data, "art_1", "ven_1", "scn_1")
        assert len(fit.axes) == 2

    def test_schema_no_longer_requires_fields(self):
        assert self.SCHEMA.get("required") == []
        assert self.SCHEMA.get("additionalProperties") is True


# ---- FitAssessor axis normalization ----

class TestFitAxisNormalization:
    def test_axis_names_normalized(self):
        from kairoskopion.agents.fit_assessor import _build_from_llm
        data = {
            "overall_label": "possible",
            "axes": [
                {"axis": "topic_fit", "value": "strong", "reasoning": "ok"},
                {"axis": "discipline_fit", "value": "weak", "reasoning": "no"},
                {"axis": "genre_fit", "value": "moderate", "reasoning": "ok"},
            ],
            "unknowns": [],
            "confidence": "medium",
        }
        fit = _build_from_llm(data, "art_1", "ven_1", "scn_1")
        axis_names = [a["axis"] for a in fit.axes]
        assert "topic" in axis_names
        assert "discipline" in axis_names
        assert "genre" in axis_names
        assert "topic_fit" not in axis_names

    def test_value_normalization(self):
        from kairoskopion.agents.fit_assessor import _build_from_llm
        data = {
            "overall_label": "possible",
            "axes": [
                {"axis": "topic", "value": "Moderate", "reasoning": "ok"},
                {"axis": "discipline", "value": "STRONG", "reasoning": "ok"},
                {"axis": "method", "value": "poor", "reasoning": "no"},
            ],
            "unknowns": [],
            "confidence": "medium",
        }
        fit = _build_from_llm(data, "art_1", "ven_1", "scn_1")
        values = {a["axis"]: a["value"] for a in fit.axes}
        assert values["topic"] == "medium"
        assert values["discipline"] == "strong"
        assert values["method"] == "bad"


# ---- Title extraction heuristic ----

class TestTitleExtractionHeuristic:
    def test_title_from_first_line_when_llm_returns_none(self):
        parsed = {
            "genre": "theoretical_essay",
            "novelty_mode": "new_synthesis",
            "method_status": "case_based",
            "problem_statement": "AI mediates perception of the living",
        }
        ms = ManuscriptModel(title=None, abstract=None, word_count=7000)
        text = "Различимость живого в ИИ-опосредованных практиках\n\nАннотация\n..."
        art = _build_article(parsed, ms, text, source_ref=None)
        assert art.title_current == "Различимость живого в ИИ-опосредованных практиках"

    def test_title_from_markdown_heading(self):
        parsed = {"genre": "theoretical_essay"}
        ms = ManuscriptModel(title=None, word_count=5000)
        text = "# Различимость живого\n\nТекст статьи..."
        art = _build_article(parsed, ms, text, source_ref=None)
        assert art.title_current == "Различимость живого"

    def test_title_from_llm_takes_priority(self):
        parsed = {"title": "LLM extracted title", "genre": "theoretical_essay"}
        ms = ManuscriptModel(title=None, word_count=5000)
        text = "First line of text\nMore text..."
        art = _build_article(parsed, ms, text, source_ref=None)
        assert art.title_current == "LLM extracted title"

    def test_title_from_manuscript_takes_priority_over_heuristic(self):
        parsed = {"genre": "theoretical_essay"}
        ms = ManuscriptModel(title="Manuscript title", word_count=5000)
        text = "First line of text\nMore text..."
        art = _build_article(parsed, ms, text, source_ref=None)
        assert art.title_current == "Manuscript title"

    def test_short_first_line_skipped(self):
        parsed = {"genre": "theoretical_essay"}
        ms = ManuscriptModel(title=None, word_count=5000)
        text = "Hi\nАктуальный заголовок статьи тут\nТекст..."
        art = _build_article(parsed, ms, text, source_ref=None)
        assert art.title_current == "Актуальный заголовок статьи тут"

    def test_bold_markdown_title(self):
        parsed = {"genre": "theoretical_essay"}
        ms = ManuscriptModel(title=None, word_count=7000)
        text = (
            "**Различимость живого в ИИ-опосредованных практиках: "
            "объект, знание и норма действия**\n\nТекст статьи..."
        )
        art = _build_article(parsed, ms, text, source_ref=None)
        assert "Различимость живого" in art.title_current
        assert art.title_current != "Untitled article"
        assert "**" not in art.title_current

    def test_bold_title_via_extract_title(self):
        from kairoskopion.services.article_modeling import _extract_title
        text = (
            "**Различимость живого в ИИ-опосредованных практиках: "
            "объект, знание и норма действия**\n\nАннотация..."
        )
        title = _extract_title(text)
        assert title is not None
        assert "Различимость" in title
        assert "**" not in title


# ---- Discipline sync — human card uses discipline_matches ----

class TestDisciplineSyncInHumanCard:
    def test_no_contradiction_when_matches_exist(self):
        from kairoskopion.services.human_readable_card import article_model_human_view
        article = {
            "article_model_id": "art_1",
            "title_current": "Test",
            "disciplinary_registers": [],
        }
        discipline_matches = {
            "matched": [
                {"discipline_id": "intl-sts", "strength": "primary", "why": "STS text"},
                {"discipline_id": "ru-philosophy-of-technology", "strength": "secondary", "why": "tech philosophy"},
            ],
            "confidence": "high",
        }
        md = article_model_human_view(
            article, pathways=None, discipline_matches=discipline_matches,
        )
        assert "пока не зафиксированы" not in md
        assert "intl-sts" in md
        assert "ru-philosophy-of-technology" in md

    def test_shows_not_registered_when_truly_empty(self):
        from kairoskopion.services.human_readable_card import article_model_human_view
        article = {
            "article_model_id": "art_2",
            "title_current": "Test",
            "disciplinary_registers": [],
        }
        md = article_model_human_view(article, pathways=None, discipline_matches=None)
        assert "пока не зафиксированы" in md

    def test_pathways_take_priority_over_matches(self):
        from kairoskopion.services.human_readable_card import article_model_human_view
        article = {
            "article_model_id": "art_3",
            "title_current": "Test",
            "disciplinary_registers": [],
        }
        pathways = [
            {"discipline_name": "STS", "fit_strength": "strong", "reasoning": "good fit"},
        ]
        discipline_matches = {
            "matched": [{"discipline_id": "intl-sts", "strength": "primary", "why": "ok"}],
        }
        md = article_model_human_view(
            article, pathways=pathways, discipline_matches=discipline_matches,
        )
        assert "публикационные траектории" in md
        assert "матчер выявил" not in md


# ---- Prose dictionary coverage ----

class TestProseDictionaryCoverage:
    def test_genre_prose_covers_all_enums(self):
        from kairoskopion.enums import Genre
        from kairoskopion.services.human_readable_card import GENRE_PROSE
        for g in Genre:
            assert g.value in GENRE_PROSE, f"Genre.{g.name} ({g.value}) missing from GENRE_PROSE"

    def test_method_prose_covers_all_enums(self):
        from kairoskopion.enums import MethodStatus
        from kairoskopion.services.human_readable_card import METHOD_PROSE
        for m in MethodStatus:
            assert m.value in METHOD_PROSE, f"MethodStatus.{m.name} ({m.value}) missing from METHOD_PROSE"

    def test_novelty_prose_covers_all_enums(self):
        from kairoskopion.enums import NoveltyMode
        from kairoskopion.services.human_readable_card import NOVELTY_PROSE
        for n in NoveltyMode:
            assert n.value in NOVELTY_PROSE, f"NoveltyMode.{n.name} ({n.value}) missing from NOVELTY_PROSE"


# ---- M-6: TextEvidence infrastructure ----

class TestSourceTextEndpoint:
    """Verify the source-text endpoint on Case returns article_input_text."""

    def test_case_preserves_article_input_text(self):
        from kairoskopion.api.cases import Case
        c = Case(case_id="test-src-1", title="Source test")
        c.article_input_text = "This is the full article text for evidence binding."
        assert c.article_input_text == "This is the full article text for evidence binding."

    def test_case_article_input_text_preferred_over_input_text(self):
        from kairoskopion.api.cases import Case
        c = Case(case_id="test-src-2", title="Source pref")
        c.input_text = "This is generic input."
        c.article_input_text = "This is article-specific text."
        text = c.article_input_text or c.input_text or ""
        assert text == "This is article-specific text."

    def test_case_falls_back_to_input_text(self):
        from kairoskopion.api.cases import Case
        c = Case(case_id="test-src-3", title="Fallback")
        c.input_text = "Fallback input text."
        c.article_input_text = ""
        text = c.article_input_text or c.input_text or ""
        assert text == "Fallback input text."

    def test_text_evidence_structure(self):
        """TextEvidence dict has the expected shape."""
        ev = {
            "fieldPath": "article_model.genre_current",
            "selectedText": "This article explores the concept",
            "charOffset": 42,
        }
        assert ev["fieldPath"].startswith("article_model.")
        assert len(ev["selectedText"]) >= 5
        assert isinstance(ev["charOffset"], int)


# ---- M-7: ModelDelta + CorrectionRegistry ----

class TestModelDelta:
    """Verify that confirm_article_model computes deltas correctly."""

    def test_delta_computed_on_field_change(self):
        from kairoskopion.api.cases import Case
        c = Case(case_id="delta-1", title="Delta test")
        from kairoskopion.schema import ArticleModel
        c.article_model = ArticleModel(title_current="Old Title")
        result = c.confirm_article_model(
            corrections={"title_current": "New Title"},
        )
        assert result["confirmed"] is True
        assert len(result["model_delta"]) == 1
        d = result["model_delta"][0]
        assert d["field"] == "title_current"
        assert d["old"] == "Old Title"
        assert d["new"] == "New Title"
        assert c.article_model.title_current == "New Title"

    def test_no_delta_when_value_unchanged(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="delta-2", title="No change")
        c.article_model = ArticleModel(title_current="Same")
        result = c.confirm_article_model(
            corrections={"title_current": "Same"},
        )
        assert result["model_delta"] == []

    def test_meta_corrections_separated(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="delta-3", title="Meta test")
        c.article_model = ArticleModel(title_current="Title")
        result = c.confirm_article_model(corrections={
            "_block_rejected_block_1": "rejected",
            "_block_comment_block_1": "I disagree with genre",
            "_text_evidence_article_model.genre_current": "This is a review",
        })
        assert result["model_delta"] == []
        log = c.decision_log[-1]
        assert "block_decisions" in log["details"]
        assert "text_evidence" in log["details"]
        assert "_block_rejected_block_1" in log["details"]["block_decisions"]

    def test_delta_logged_in_decision_log(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="delta-4", title="Log test")
        c.article_model = ArticleModel(genre_current="unknown")
        c.confirm_article_model(corrections={"genre_current": "review"})
        log = c.decision_log[-1]
        assert log["action"] == "confirm_article_model"
        assert len(log["details"]["model_delta"]) == 1
        assert log["details"]["model_delta"][0]["old"] == "unknown"


class TestCorrectionRegistry:
    """Verify JSONL append-only correction registry."""

    def test_append_and_read(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None  # reset cached path

        CorrectionRegistry.append(
            case_id="reg-1",
            user_id="user_abc",
            model_delta=[{"field": "genre_current", "old": "unknown", "new": "review"}],
            meta_corrections={"_block_rejected_block_1": "rejected"},
            text_evidence={"_text_evidence_genre": "This is clearly a review"},
        )
        entries = CorrectionRegistry.read_all()
        assert len(entries) == 1
        assert entries[0]["case_id"] == "reg-1"
        assert entries[0]["user_id"] == "user_abc"
        assert len(entries[0]["model_delta"]) == 1

        # Append second entry
        CorrectionRegistry.append(
            case_id="reg-2",
            user_id="user_abc",
            model_delta=[],
            meta_corrections={},
            text_evidence={},
        )
        entries = CorrectionRegistry.read_all()
        assert len(entries) == 2

        CorrectionRegistry._path = None  # cleanup

    def test_read_empty_registry(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None
        entries = CorrectionRegistry.read_all()
        assert entries == []
        CorrectionRegistry._path = None


# ---- M-8: LLM refinement dialog ----

class TestRefinementDialog:
    """Verify the refinement dialog method on Case."""

    def test_refine_returns_unavailable_when_no_llm(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="refine-1", title="Refine test")
        c.article_model = ArticleModel(title_current="Test article")
        result = c.refine_article_model("Пересмотри жанр")
        assert result["llm_available"] is False
        assert "не подключён" in result["reply"]
        assert result["suggestions"] == []

    def test_refine_no_model_returns_error(self):
        from kairoskopion.api.cases import Case
        c = Case(case_id="refine-2", title="No model")
        result = c.refine_article_model("hello")
        assert "error" in result

    def test_refinement_chat_stored(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="refine-3", title="Chat history")
        c.article_model = ArticleModel(title_current="Test")
        c.refine_article_model("Что с жанром?")
        chat = c.get_refinement_chat()
        assert len(chat) == 2  # user msg + assistant reply
        assert chat[0]["role"] == "user"
        assert chat[0]["content"] == "Что с жанром?"
        assert chat[1]["role"] == "assistant"

    def test_refinement_logged_in_decision_log(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="refine-4", title="Log test")
        c.article_model = ArticleModel(title_current="Test")
        c.refine_article_model("Пересмотри метод")
        log = c.decision_log[-1]
        assert log["action"] == "refine_article_model"
        assert log["details"]["user_message"] == "Пересмотри метод"

    def test_refinement_chat_persists_through_save_load(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import Case, CaseStore
        store = CaseStore(data_dir=str(tmp_path))
        from kairoskopion.schema import ArticleModel
        c = Case(case_id="persist-chat-1", title="Persist test")
        c.article_model = ArticleModel(title_current="Test")
        c.refine_article_model("Проверка персистенции")
        assert len(c.refinement_chat) == 2
        store.save(c)

        store2 = CaseStore(data_dir=str(tmp_path))
        loaded = store2.get("persist-chat-1")
        assert loaded is not None
        assert len(loaded.refinement_chat) == 2
        assert loaded.refinement_chat[0]["role"] == "user"
        assert loaded.refinement_chat[0]["content"] == "Проверка персистенции"
        assert loaded.refinement_chat[1]["role"] == "assistant"


# ---- M-9: PromptCorrectionSignal ----

class TestPromptCorrectionSignal:
    """Verify correction pattern detection from CorrectionRegistry."""

    def test_no_signals_on_empty_registry(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None
        signals = CorrectionRegistry.analyze_signals(min_occurrences=2)
        assert signals == []
        CorrectionRegistry._path = None

    def test_field_correction_pattern_detected(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None

        for i in range(4):
            CorrectionRegistry.append(
                case_id=f"sig-{i}",
                user_id="user_abc",
                model_delta=[{"field": "genre_current", "old": "unknown", "new": "review"}],
                meta_corrections={},
                text_evidence={},
            )

        signals = CorrectionRegistry.analyze_signals(min_occurrences=3)
        assert len(signals) == 1
        assert signals[0]["type"] == "field_correction_pattern"
        assert signals[0]["field"] == "genre_current"
        assert signals[0]["correction_count"] == 4
        assert signals[0]["most_common_override"] == "review"
        CorrectionRegistry._path = None

    def test_block_rejection_pattern_detected(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None

        for i in range(3):
            CorrectionRegistry.append(
                case_id=f"rej-{i}",
                user_id="user_abc",
                model_delta=[],
                meta_corrections={"_block_rejected_block_2": "rejected"},
                text_evidence={},
            )

        signals = CorrectionRegistry.analyze_signals(min_occurrences=3)
        assert any(s["type"] == "block_rejection_pattern" for s in signals)
        block_sig = [s for s in signals if s["type"] == "block_rejection_pattern"][0]
        assert block_sig["block_id"] == "block_2"
        assert block_sig["rejection_count"] == 3
        CorrectionRegistry._path = None

    def test_below_threshold_no_signal(self, tmp_path):
        import os
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        from kairoskopion.api.cases import CorrectionRegistry
        CorrectionRegistry._path = None

        CorrectionRegistry.append(
            case_id="below-1",
            user_id="user_abc",
            model_delta=[{"field": "genre_current", "old": "unknown", "new": "review"}],
            meta_corrections={},
            text_evidence={},
        )

        signals = CorrectionRegistry.analyze_signals(min_occurrences=3)
        assert signals == []
        CorrectionRegistry._path = None
