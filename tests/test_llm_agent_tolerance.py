"""Regression tests for the nine 302.ai/LLM-tolerance bugs found
during the Mavrinsky golden-run baseline (2026-06-14).

Each bug has a named test so a future refactor cannot silently undo
any of them.

NO live LLM calls. All fixtures hand-author the parsed-response shape
that the LLM produced in the wild.
"""

from __future__ import annotations

import json
import unittest
from typing import Any

from kairoskopion.agents.article_modeler import _build_from_llm as _build_article
from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.disciplinary_mapper import (
    _STRENGTH_MAP,
    _build_pathways,
)
from kairoskopion.agents.fit_assessor import _build_from_llm as _build_fit
from kairoskopion.enums import DisciplinaryFitStrength
from kairoskopion.llm.openai_compat import _parse_json_robust
from kairoskopion.llm.provider import LLMProvider
from kairoskopion.logic.field_position_fit import (
    _vector_distance_to_envelope,
    compute_field_position_fit,
)
from kairoskopion.services.article_modeling import build_manuscript_model


# ---------------------------------------------------------------------------
# Bug 1 — Protocol must be runtime_checkable so isinstance() works.
# ---------------------------------------------------------------------------

class TestBug1ProviderProtocolRuntimeCheckable(unittest.TestCase):
    def test_protocol_is_runtime_checkable(self):
        # isinstance against a Protocol only works when @runtime_checkable
        # is set; otherwise Python 3.13 raises TypeError.
        class FakeProvider:
            def complete(self, messages, *, response_schema=None,
                         temperature=0.2, max_tokens=4096):
                raise NotImplementedError

        self.assertTrue(isinstance(FakeProvider(), LLMProvider))

    def test_non_provider_object_is_not_provider(self):
        self.assertFalse(isinstance("not a provider", LLMProvider))


# ---------------------------------------------------------------------------
# Bug 2 — _parse_json_robust handles ```json ... ``` fences.
# ---------------------------------------------------------------------------

class TestBug2JsonFenceParsing(unittest.TestCase):
    def test_bare_json(self):
        self.assertEqual(_parse_json_robust('{"a": 1}'), {"a": 1})

    def test_json_code_fence(self):
        self.assertEqual(
            _parse_json_robust('```json\n{"a": 1, "b": [2,3]}\n```'),
            {"a": 1, "b": [2, 3]},
        )

    def test_plain_code_fence(self):
        self.assertEqual(
            _parse_json_robust("```\n{\"x\":42}\n```"),
            {"x": 42},
        )

    def test_empty_input(self):
        self.assertIsNone(_parse_json_robust(""))
        self.assertIsNone(_parse_json_robust(None))


# ---------------------------------------------------------------------------
# Bug 3 — _parse_json_robust falls back to extracting balanced {...}.
# ---------------------------------------------------------------------------

class TestBug3JsonObjectExtraction(unittest.TestCase):
    def test_prose_then_json(self):
        s = 'Here is the analysis you asked for: {"label": "ok", "score": 7}. Hope this helps.'
        out = _parse_json_robust(s)
        self.assertEqual(out, {"label": "ok", "score": 7})

    def test_returns_none_when_no_json(self):
        self.assertIsNone(_parse_json_robust("nothing here"))


# ---------------------------------------------------------------------------
# Bug 4 — disciplinary_mapper accepts `ranked_pathways` and friends.
# ---------------------------------------------------------------------------

class TestBug4PathwaysAlias(unittest.TestCase):
    def test_ranked_pathways_accepted(self):
        parsed = {
            "ranked_pathways": [
                {"discipline_name": "philosophy_of_technology",
                 "fit_strength": "strong",
                 "reasoning": "x", "rank": 1},
                {"discipline_name": "STS",
                 "fit_strength": "medium",
                 "reasoning": "y", "rank": 2},
            ]
        }
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].discipline_name, "philosophy_of_technology")

    def test_disciplinary_pathways_accepted(self):
        parsed = {"disciplinary_pathways": [
            {"discipline_name": "media", "fit_strength": "medium", "reasoning": "z", "rank": 1},
        ]}
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].discipline_name, "media")


# ---------------------------------------------------------------------------
# Bug 5 — discipline_name alias (`discipline` / `pathway_name` / `name`).
# ---------------------------------------------------------------------------

class TestBug5DisciplineNameAliases(unittest.TestCase):
    def test_discipline_alias(self):
        parsed = {"pathways": [
            {"discipline": "philosophy_of_technology",
             "fit_strength": "strong", "rank": 1},
        ]}
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(out[0].discipline_name, "philosophy_of_technology")

    def test_pathway_name_alias(self):
        parsed = {"pathways": [
            {"pathway_name": "STS", "fit_strength": "weak", "rank": 1},
        ]}
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(out[0].discipline_name, "STS")

    def test_name_alias(self):
        parsed = {"pathways": [
            {"name": "HCI", "fit_strength": "weak", "rank": 1},
        ]}
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(out[0].discipline_name, "HCI")


# ---------------------------------------------------------------------------
# Bug 6 — out-of-enum fit_strength like `very_high`.
# ---------------------------------------------------------------------------

class TestBug6StrengthAliases(unittest.TestCase):
    def test_strength_map_handles_observed_aliases(self):
        # All the values gpt-4o-mini produced in actual runs.
        for raw, expected in [
            ("very_high", DisciplinaryFitStrength.STRONG.value),
            ("high", DisciplinaryFitStrength.STRONG.value),
            ("medium_strong", DisciplinaryFitStrength.STRONG.value),
            ("medium", DisciplinaryFitStrength.MEDIUM.value),
            ("moderate", DisciplinaryFitStrength.MEDIUM.value),
            ("weak_medium", DisciplinaryFitStrength.WEAK.value),
            ("weak", DisciplinaryFitStrength.WEAK.value),
            ("low", DisciplinaryFitStrength.WEAK.value),
            ("very_low", DisciplinaryFitStrength.INCOMPATIBLE.value),
            ("unknown", DisciplinaryFitStrength.UNKNOWN.value),
        ]:
            self.assertEqual(_STRENGTH_MAP.get(raw), expected, f"alias {raw!r}")

    def test_build_pathways_normalizes_strength(self):
        parsed = {"pathways": [
            {"discipline_name": "x", "fit_strength": "VERY_HIGH", "rank": 1},
        ]}
        out = _build_pathways(parsed, "art_x")
        self.assertEqual(out[0].fit_strength, DisciplinaryFitStrength.STRONG.value)


# ---------------------------------------------------------------------------
# Bug 7 — article_modeler coerces `protected_core` as string → list[str].
# ---------------------------------------------------------------------------

class TestBug7ProtectedCoreStringToList(unittest.TestCase):
    def test_protected_core_string_becomes_list(self):
        text = "Abstract: a short conceptual paper. " * 30
        manuscript = build_manuscript_model(text)
        parsed = {
            "title": "Some Title",
            "abstract_summary": "abstract",
            "problem_statement": "x",
            "core_claims": ["c1", "c2"],
            # ↓ LLM returned a single string under the wrong key
            "protected_core": (
                "The central core consists of (1) desire as excess; "
                "(2) interface as dispositif; (3) generous vs greedy distinction."
            ),
        }
        article = _build_article(parsed, manuscript, text, source_ref=None)
        self.assertIsInstance(article.protected_core, list)
        self.assertEqual(len(article.protected_core), 1)
        self.assertIn("desire", article.protected_core[0].lower())

    def test_protected_core_candidate_key_still_works(self):
        text = "draft body " * 50
        manuscript = build_manuscript_model(text)
        parsed = {
            "title": "T",
            "problem_statement": "p",
            "core_claims": [],
            "protected_core_candidate": ["a", "b"],
        }
        article = _build_article(parsed, manuscript, text, source_ref=None)
        self.assertEqual(article.protected_core, ["a", "b"])


# ---------------------------------------------------------------------------
# Bug 8 — fit_assessor accepts axes as dict[axis_name → detail].
# ---------------------------------------------------------------------------

class TestBug8FitAxesDictToList(unittest.TestCase):
    def test_axes_as_dict_converts_to_list(self):
        parsed = {
            "overall_label": "possible_but_costly",
            "axes": {
                "topic_fit": {"value": "strong", "reasoning": "topic ok"},
                "discipline_fit": {"value": "medium", "reasoning": "philtech-ish"},
                "method_fit": {"value": "weak", "reasoning": "no method"},
            },
        }
        fit = _build_fit(parsed, article_id="a", venue_id="v", scenario_id="s")
        self.assertEqual(len(fit.axes), 3)
        names = {a["axis"] for a in fit.axes}
        self.assertEqual(names, {"topic", "discipline", "method"})

    def test_axes_as_list_still_works(self):
        parsed = {
            "overall_label": "possible",
            "axes": [
                {"axis": "topic_fit", "value": "strong"},
                {"axis": "discipline_fit", "value": "medium"},
            ],
        }
        fit = _build_fit(parsed, article_id="a", venue_id="v", scenario_id="s")
        self.assertEqual(len(fit.axes), 2)

    def test_fit_vector_alias_accepted(self):
        parsed = {
            "overall_label": "possible",
            "fit_vector": {
                "school_fit": {"value": "weak", "reasoning": "lacan as foil"},
            },
        }
        fit = _build_fit(parsed, article_id="a", venue_id="v", scenario_id="s")
        self.assertEqual(len(fit.axes), 1)
        self.assertEqual(fit.axes[0]["axis"], "school_fit")

    def test_status_alias_for_value(self):
        parsed = {
            "overall_label": "possible",
            "axes": [{"axis": "x", "status": "strong"}],
        }
        fit = _build_fit(parsed, article_id="a", venue_id="v", scenario_id="s")
        self.assertEqual(fit.axes[0]["value"], "strong")


# ---------------------------------------------------------------------------
# Bug 9 — compute_field_position_fit handles {value: x} nested floats.
# ---------------------------------------------------------------------------

class TestBug9NumericCoercion(unittest.TestCase):
    def test_nested_value_dicts_in_vector(self):
        article_fpm = {
            "discipline_vector": {"phil_tech": {"value": 0.5}, "STS": 0.2},
            "school_affiliation_vector": {"Deleuze": 0.6, "Lacan": {"value": -0.3}},
            "argument_move_vector": {"concept_reconstruction": 0.4},
            "language_register": {"language": "ru"},
        }
        venue_fpm = {
            "discipline_vector": {"phil_tech": 0.4, "STS": 0.3},
            "discipline_envelope": {"phil_tech": [0.2, 0.7], "STS": [{"value": 0.0}, 0.5]},
            "school_affiliation_vector": {"Deleuze": 0.5, "Lacan": -0.2},
            "argument_move_vector": {"concept_reconstruction": 0.3},
            "language_register": {"language": "ru"},
        }
        # Used to crash with "unsupported operand type(s) for -: 'float' and 'dict'"
        result = compute_field_position_fit(article_fpm, venue_fpm)
        self.assertIn("axes", result)
        self.assertGreater(len(result["axes"]), 0)
        self.assertIn(
            result["overall_label"],
            {"strong_candidate", "possible", "possible_but_costly",
             "poor_fit", "not_enough_data"},
        )

    def test_vector_distance_with_dict_value(self):
        # Direct check of the helper.
        status, dist, _ = _vector_distance_to_envelope(
            point={"a": {"value": 0.5}},
            center={"a": 0.5},
            envelope=None,
        )
        self.assertEqual(dist, 0.0)


# ---------------------------------------------------------------------------
# Bonus regression — article_modeler accepts title under several aliases.
# ---------------------------------------------------------------------------

class TestBonusTitleAliases(unittest.TestCase):
    def test_title_current_alias(self):
        manuscript = build_manuscript_model("body " * 100)
        parsed = {"title_current": "From Aliased Key", "core_claims": []}
        article = _build_article(parsed, manuscript, "body", source_ref=None)
        self.assertEqual(article.title_current, "From Aliased Key")

    def test_title_ru_alias(self):
        manuscript = build_manuscript_model("body " * 100)
        parsed = {"title_ru": "Русский заголовок", "core_claims": []}
        article = _build_article(parsed, manuscript, "body", source_ref=None)
        self.assertEqual(article.title_current, "Русский заголовок")


if __name__ == "__main__":
    unittest.main()
