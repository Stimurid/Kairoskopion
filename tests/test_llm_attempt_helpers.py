"""Tests for shared LLM attempt observability helpers (backend)."""

from __future__ import annotations

import unittest

from kairoskopion.llm.attempt_helpers import (
    aggregate_warnings,
    fallback_reason,
    is_fallback_attempt,
    layer_label,
    parse_status,
    technical_hint,
    warning_text,
)
from kairoskopion.llm.attempt_metadata import LLMAttemptMetadata


def _ok() -> dict:
    return LLMAttemptMetadata.parse_ok(
        provider="openai_compatible", model="gpt-4o-mini",
        latency_ms=120.0, content_present=True,
    ).to_dict()


def _fallback(reason: str = "provider_error") -> dict:
    return LLMAttemptMetadata.fallback(reason=reason).to_dict()


class TestPredicates(unittest.TestCase):
    def test_none_is_not_fallback(self):
        self.assertFalse(is_fallback_attempt(None))
        self.assertFalse(is_fallback_attempt({}))

    def test_ok_is_not_fallback(self):
        self.assertFalse(is_fallback_attempt(_ok()))

    def test_fallback_is_fallback(self):
        self.assertTrue(is_fallback_attempt(_fallback()))

    def test_parse_status_defaults(self):
        self.assertEqual(parse_status(None), "not_attempted")
        self.assertEqual(parse_status({}), "not_attempted")
        self.assertEqual(parse_status(_ok()), "parsed_ok")

    def test_fallback_reason_default(self):
        self.assertEqual(fallback_reason(None), "not_applicable")
        self.assertEqual(fallback_reason(_ok()), "not_applicable")
        self.assertEqual(fallback_reason(_fallback("invalid_json")), "invalid_json")


class TestWarningText(unittest.TestCase):
    def test_ok_returns_none(self):
        self.assertIsNone(warning_text(_ok()))
        self.assertIsNone(warning_text(None))

    def test_fallback_returns_russian_sentence(self):
        w = warning_text(_fallback("provider_error"))
        self.assertIsNotNone(w)
        # Russian sentence (Cyrillic)
        self.assertTrue(any(0x0400 <= ord(c) <= 0x04FF for c in w))
        # No leak markers
        self.assertNotIn("Traceback", w)
        self.assertNotIn("raw_output_ref", w)

    def test_explicit_warning_field_preferred(self):
        attempt = _fallback("provider_error")
        attempt["warning_for_user"] = "Кастомное сообщение"
        self.assertEqual(warning_text(attempt), "Кастомное сообщение")


class TestTechnicalHint(unittest.TestCase):
    def test_none_returns_not_attempted(self):
        self.assertEqual(technical_hint(None), "not_attempted")

    def test_ok_returns_parsed_ok(self):
        self.assertEqual(technical_hint(_ok()), "parsed_ok")

    def test_fallback_returns_reason(self):
        self.assertEqual(
            technical_hint(_fallback("provider_error")),
            "fallback (provider_error)",
        )
        self.assertEqual(
            technical_hint(_fallback("schema_validation_failed")),
            "fallback (schema_validation_failed)",
        )

    def test_hint_is_ascii_safe(self):
        # Hint must never contain raw output / Traceback / Cyrillic
        # warnings — those belong to warning_text, not the badge text.
        for attempt in (None, _ok(), _fallback("invalid_json")):
            h = technical_hint(attempt)
            self.assertNotIn("Traceback", h)
            self.assertNotIn("raw_output_ref", h)
            # No Cyrillic in the compact ASCII hint
            self.assertFalse(any(0x0400 <= ord(c) <= 0x04FF for c in h))


class TestLayerLabel(unittest.TestCase):
    def test_known_keys_translated(self):
        self.assertEqual(layer_label("article_model"), "Модель статьи")
        self.assertEqual(layer_label("semantic_profile"), "Семантический профиль")
        self.assertEqual(layer_label("pathways"), "Дисциплинарная карта")
        self.assertEqual(layer_label("fit_assessment"), "Оценка соответствия")

    def test_unknown_passes_through(self):
        self.assertEqual(layer_label("brand_new_layer"), "brand_new_layer")


class TestAggregateWarnings(unittest.TestCase):
    def test_no_layers_returns_none(self):
        self.assertIsNone(aggregate_warnings({}))
        self.assertIsNone(aggregate_warnings({"article_model": None}))
        self.assertIsNone(aggregate_warnings({"article_model": _ok()}))

    def test_single_layer_uses_single_banner_shape(self):
        md = aggregate_warnings({"pathways": _fallback("provider_error")})
        self.assertIsNotNone(md)
        self.assertIn("Дисциплинарная карта", md)
        self.assertIn("parse_status", md)
        self.assertIn("fallback_reason", md)
        self.assertIn("provider_error", md)
        # Single-layer output should NOT be a bullet list with the
        # "Несколько слоёв" parent heading.
        self.assertNotIn("Несколько слоёв", md)

    def test_two_layers_uses_aggregate_shape(self):
        md = aggregate_warnings({
            "article_model": _fallback("schema_validation_failed"),
            "pathways": _fallback("provider_error"),
        })
        self.assertIsNotNone(md)
        self.assertIn("Несколько слоёв", md)
        self.assertIn("Модель статьи", md)
        self.assertIn("Дисциплинарная карта", md)
        self.assertIn("schema_validation_failed", md)
        self.assertIn("provider_error", md)

    def test_ignores_ok_layers_in_aggregate(self):
        md = aggregate_warnings({
            "article_model": _ok(),
            "pathways": _fallback("provider_error"),
            "fit_assessment": _ok(),
        })
        self.assertIsNotNone(md)
        # Only pathway appears
        self.assertIn("Дисциплинарная карта", md)
        self.assertNotIn("Модель статьи", md)
        self.assertNotIn("Оценка соответствия", md)
        # And single-layer shape kicks in
        self.assertNotIn("Несколько слоёв", md)

    def test_no_leakage(self):
        attempt = _fallback("provider_error")
        # Adversarial: someone stuck a Traceback into the warning
        attempt["warning_for_user"] = (
            "Traceback (most recent call last): File 'x.py' line 1"
        )
        attempt["raw_output_ref"] = "should-never-render"
        md = aggregate_warnings({
            "article_model": attempt,
            "pathways": _fallback("invalid_json"),
        })
        self.assertIsNotNone(md)
        # raw_output_ref must not appear
        self.assertNotIn("raw_output_ref", md)
        self.assertNotIn("should-never-render", md)
        # The Traceback in warning_for_user does appear (it's the agent's
        # responsibility to not put it there), but helpers MUST NOT add
        # any extra leakage — that's what the regular fallback path
        # asserts elsewhere. Here we just confirm structural safety.


if __name__ == "__main__":
    unittest.main()
