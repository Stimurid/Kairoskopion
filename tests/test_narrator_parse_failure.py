"""V2-B2: redacted parse-failure classification tests.

These tests pin the V2-B2 parse-failure taxonomy. Every input is an
already-redacted ``extraction_attempt`` dict (the same shape
``LLMAttemptMetadata.to_dict()`` emits), never raw LLM content. The
classifier must:

1. Distinguish invalid_json, repair_failed, schema_validation_failed,
   missing_required (with path), missing_narratives_key,
   wrong_top_level_shape, and empty_after_repair.
2. Leak no raw model text, no Traceback, no API secrets, no prompt.
3. Stay all-None when parse succeeded.
"""

from __future__ import annotations

import unittest

from kairoskopion.services.narrator_coverage import (
    PARSE_FAIL_EMPTY_AFTER_REPAIR,
    PARSE_FAIL_INVALID_JSON,
    PARSE_FAIL_MISSING_NARRATIVES_KEY,
    PARSE_FAIL_MISSING_REQUIRED,
    PARSE_FAIL_REPAIR_FAILED,
    PARSE_FAIL_SCHEMA_VALIDATION_FAILED,
    PARSE_FAIL_WRONG_TOP_LEVEL_SHAPE,
    STATUS_FILLED,
    STATUS_PARSE_FAILED,
    classify_narrator_coverage,
    classify_parse_failure,
)


def _attempt(
    parse_status="schema_validation_failed",
    fallback_reason="schema_validation_failed",
    errors=None,
    repair_steps=None,
):
    return {
        "llm_attempted": True,
        "llm_provider": "openai_compatible",
        "llm_model": "sonnet",
        "llm_latency_ms": 42.0,
        "llm_raw_output_present": True,
        "parse_status": parse_status,
        "repair_attempted": bool(repair_steps),
        "repair_status": "failed" if repair_steps else "not_needed",
        "repair_steps": list(repair_steps or []),
        "fallback_used": True,
        "fallback_reason": fallback_reason,
        "validation_errors_summary": list(errors or []),
        "warning_for_user": "...",
        "raw_output_ref": None,
    }


class TestInvalidJSON(unittest.TestCase):
    def test_pure_invalid_json(self):
        out = classify_parse_failure(_attempt(
            parse_status="invalid_json",
            fallback_reason="invalid_json",
            repair_steps=[],
        ))
        self.assertEqual(out["parse_failure_category"], PARSE_FAIL_INVALID_JSON)
        self.assertIsNotNone(out["parse_failure_reason"])
        self.assertIsNone(out["schema_failure_path"])
        self.assertEqual(out["repair_steps_attempted"], [])


class TestRepairFailed(unittest.TestCase):
    def test_repair_attempted_and_failed(self):
        out = classify_parse_failure(_attempt(
            parse_status="repair_failed",
            fallback_reason="repair_failed",
            repair_steps=["smart_quotes_replaced", "trailing_commas_stripped"],
        ))
        self.assertEqual(out["parse_failure_category"], PARSE_FAIL_REPAIR_FAILED)
        self.assertEqual(
            out["repair_failure_stage"], "trailing_commas_stripped",
        )
        self.assertEqual(
            out["repair_steps_attempted"],
            ["smart_quotes_replaced", "trailing_commas_stripped"],
        )

    def test_empty_after_repair_when_no_steps(self):
        out = classify_parse_failure(_attempt(
            parse_status="repair_failed",
            fallback_reason="repair_failed",
            repair_steps=[],
        ))
        self.assertEqual(
            out["parse_failure_category"], PARSE_FAIL_EMPTY_AFTER_REPAIR,
        )


class TestMissingNarrativesKey(unittest.TestCase):
    def test_missing_narratives_specifically(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            errors=["missing required field: narratives"],
        ))
        self.assertEqual(
            out["parse_failure_category"], PARSE_FAIL_MISSING_NARRATIVES_KEY,
        )
        self.assertEqual(out["schema_failure_path"], "narratives")
        self.assertEqual(out["schema_failure_rule"], "required")


class TestMissingRequiredOther(unittest.TestCase):
    def test_other_required_field(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            errors=["missing required field: axis"],
        ))
        self.assertEqual(
            out["parse_failure_category"], PARSE_FAIL_MISSING_REQUIRED,
        )
        self.assertEqual(out["schema_failure_path"], "axis")
        self.assertEqual(out["schema_failure_rule"], "required")


class TestWrongTopLevelShape(unittest.TestCase):
    def test_top_level_marker(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            errors=["top-level value is not an object as schema requires"],
        ))
        self.assertEqual(
            out["parse_failure_category"], PARSE_FAIL_WRONG_TOP_LEVEL_SHAPE,
        )
        self.assertEqual(out["schema_failure_rule"], "type")


class TestGenericSchemaFailure(unittest.TestCase):
    def test_no_path_info(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            errors=[],
        ))
        self.assertEqual(
            out["parse_failure_category"],
            PARSE_FAIL_SCHEMA_VALIDATION_FAILED,
        )
        self.assertIsNone(out["schema_failure_path"])


class TestSuccessfulParse(unittest.TestCase):
    def test_parsed_ok_returns_blank(self):
        out = classify_parse_failure(_attempt(
            parse_status="parsed_ok",
            fallback_reason="not_applicable",
        ))
        self.assertIsNone(out["parse_failure_category"])
        self.assertIsNone(out["parse_failure_reason"])
        self.assertIsNone(out["schema_failure_path"])
        self.assertEqual(out["repair_steps_attempted"], [])

    def test_repaired_ok_returns_blank(self):
        out = classify_parse_failure(_attempt(
            parse_status="repaired_ok",
            fallback_reason="not_applicable",
            repair_steps=["smart_quotes_replaced"],
        ))
        self.assertIsNone(out["parse_failure_category"])

    def test_not_attempted_returns_blank(self):
        out = classify_parse_failure(_attempt(
            parse_status="not_attempted",
            fallback_reason="llm_unavailable",
        ))
        self.assertIsNone(out["parse_failure_category"])

    def test_attempt_none_returns_blank(self):
        out = classify_parse_failure(None)
        self.assertIsNone(out["parse_failure_category"])
        self.assertEqual(out["repair_steps_attempted"], [])


class TestProviderErrorNotClassifiedHere(unittest.TestCase):
    """Provider/timeout errors are reported at the coverage level
    (STATUS_PROVIDER_ERROR), not duplicated as a parse failure."""

    def test_provider_error_yields_no_parse_category(self):
        out = classify_parse_failure(_attempt(
            parse_status="not_attempted",
            fallback_reason="provider_error",
        ))
        self.assertIsNone(out["parse_failure_category"])


class TestAntiLeak(unittest.TestCase):
    """Classifier must never echo raw LLM output, stack traces, prompts,
    or secrets. All inputs are already-redacted metadata; classifier
    only outputs stable category strings + extracted paths."""

    def test_no_traceback_no_raw_in_output(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            # Imagine a real production error string. None of these
            # may surface in classifier output (only the path is
            # extracted).
            errors=[
                "missing required field: narratives",
                "Traceback (most recent call last):",
                "API_KEY=sk-secret-12345",
            ],
        ))
        flat = " ".join(str(v) for v in out.values() if v is not None)
        self.assertNotIn("Traceback", flat)
        self.assertNotIn("sk-secret", flat)
        self.assertNotIn("API_KEY", flat)

    def test_no_raw_output_keys(self):
        out = classify_parse_failure(_attempt(
            parse_status="schema_validation_failed",
            errors=["missing required field: narratives"],
        ))
        for k in out.keys():
            kl = k.lower()
            self.assertNotIn("raw", kl)
            self.assertNotIn("trace", kl)
            self.assertNotIn("stack", kl)


class TestCoverageIntegration(unittest.TestCase):
    """End-to-end: classify_narrator_coverage embeds the parse-failure
    fields when parse fails, and leaves them None when parse succeeds."""

    def test_coverage_carries_parse_failure_category(self):
        axes = ["topic", "method"]
        narr_out = {
            "narratives": [],
            "extraction_attempt": _attempt(
                parse_status="repair_failed",
                fallback_reason="repair_failed",
                repair_steps=["smart_quotes_replaced"],
            ),
        }
        cov = classify_narrator_coverage(axes, narr_out)
        self.assertEqual(cov["narrator_status"], STATUS_PARSE_FAILED)
        self.assertEqual(
            cov["parse_failure_category"], PARSE_FAIL_REPAIR_FAILED,
        )
        self.assertEqual(
            cov["repair_failure_stage"], "smart_quotes_replaced",
        )
        self.assertEqual(cov["filled_count"], 0)
        # downstream chain decision still works
        self.assertEqual(cov["missing_axes"], ["topic", "method"])

    def test_coverage_blank_failure_fields_on_success(self):
        axes = ["topic"]
        narr_out = {
            "narratives": [{
                "axis": "topic",
                "venue_side": "venue expects X",
                "description": "Y",
                "possible_actions": ["a"],
            }],
            "extraction_attempt": _attempt(
                parse_status="parsed_ok",
                fallback_reason="not_applicable",
            ),
        }
        cov = classify_narrator_coverage(axes, narr_out)
        self.assertEqual(cov["narrator_status"], STATUS_FILLED)
        self.assertIsNone(cov["parse_failure_category"])
        self.assertIsNone(cov["parse_failure_reason"])
        self.assertEqual(cov["repair_steps_attempted"], [])


if __name__ == "__main__":
    unittest.main()
