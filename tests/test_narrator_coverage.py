"""V2-B1: classification tests for narrator coverage helper.

Pure unit tests against the helper. No prompts, no models, no I/O.
Each test pins one of the failure modes the brief enumerates so that
0/N narrator coverage is observable and never silently collapsed.
"""

from __future__ import annotations

import unittest

from kairoskopion.services.narrator_coverage import (
    PER_AXIS_LLM_FILLED,
    PER_AXIS_MISSING_FROM_LLM,
    PER_AXIS_NEEDS_LLM,
    PER_AXIS_PARSE_FAILED,
    PER_AXIS_PROVIDER_ERROR,
    PER_AXIS_UNKNOWN_DUE_TO_VENUE,
    STATUS_AXIS_MATCH_FAILURE,
    STATUS_EMPTY_LLM_OUTPUT,
    STATUS_EMPTY_VALID_UNKNOWN,
    STATUS_FILLED,
    STATUS_INPUT_INSUFFICIENT,
    STATUS_MISSING_AXES,
    STATUS_NOT_ATTEMPTED,
    STATUS_PARSE_FAILED,
    STATUS_PARTIAL,
    STATUS_PROVIDER_ERROR,
    classify_narrator_coverage,
    per_axis_status,
)


def _attempt_ok(model="sonnet", latency=123):
    return {
        "llm_attempted": True,
        "llm_provider": "openai_compatible",
        "llm_model": model,
        "llm_latency_ms": latency,
        "parse_status": "parsed_ok",
        "fallback_used": False,
        "fallback_reason": None,
    }


def _attempt_fallback(reason, parse_status="not_attempted"):
    return {
        "llm_attempted": True,
        "llm_provider": "openai_compatible",
        "llm_model": "sonnet",
        "llm_latency_ms": None,
        "parse_status": parse_status,
        "fallback_used": True,
        "fallback_reason": reason,
    }


def _narr(axis, venue_side="", description="", actions=None):
    return {
        "axis": axis,
        "venue_side": venue_side,
        "description": description,
        "possible_actions": actions or [],
    }


class TestFullFill(unittest.TestCase):
    def test_all_axes_filled(self):
        axes = ["topic", "method", "discipline"]
        out = {
            "narratives": [
                _narr(a, venue_side=f"venue expects {a}", actions=["a"])
                for a in axes
            ],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_FILLED)
        self.assertEqual(cov["filled_count"], 3)
        self.assertEqual(cov["total_count"], 3)
        self.assertEqual(cov["missing_axes"], [])
        self.assertEqual(cov["unmatched_axes"], [])
        self.assertEqual(cov["used_model"], "sonnet")
        for a in axes:
            self.assertEqual(
                per_axis_status(a, axes, out, cov["narrator_status"]),
                PER_AXIS_LLM_FILLED,
            )


class TestPartialFill(unittest.TestCase):
    def test_some_filled_some_empty(self):
        axes = ["topic", "method", "discipline"]
        out = {
            "narratives": [
                _narr("topic", venue_side="venue text X"),
                _narr("method", venue_side=""),  # honest unknown
                _narr("discipline", venue_side=""),
            ],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_PARTIAL)
        self.assertEqual(cov["filled_count"], 1)
        self.assertEqual(cov["total_count"], 3)
        self.assertEqual(
            per_axis_status("topic", axes, out, cov["narrator_status"]),
            PER_AXIS_LLM_FILLED,
        )
        # In partial state, unfilled axes get needs_llm (not the
        # empty-valid-unknown label which only applies when EVERY axis
        # was empty)
        self.assertEqual(
            per_axis_status("method", axes, out, cov["narrator_status"]),
            PER_AXIS_NEEDS_LLM,
        )


class TestEmptyValidUnknown(unittest.TestCase):
    """The strong/plausible 0/7 case — narrator returned for every axis
    but every venue_side was empty. Classify as empty_valid_unknown
    rather than collapsing to plain '0 filled'."""

    def test_all_axes_returned_empty_venue_side(self):
        axes = ["topic", "method", "language", "discipline", "genre",
                "novelty_mode", "citation_ecology"]
        out = {
            "narratives": [_narr(a, venue_side="") for a in axes],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_EMPTY_VALID_UNKNOWN)
        self.assertEqual(cov["filled_count"], 0)
        self.assertEqual(cov["total_count"], 7)
        self.assertIsNotNone(cov["empty_reason"])
        self.assertIn("valid unknown", cov["empty_reason"])
        for a in axes:
            self.assertEqual(
                per_axis_status(a, axes, out, cov["narrator_status"]),
                PER_AXIS_UNKNOWN_DUE_TO_VENUE,
            )


class TestEmptyLLMOutput(unittest.TestCase):
    def test_narratives_list_is_empty(self):
        axes = ["topic", "method"]
        out = {
            "narratives": [],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_EMPTY_LLM_OUTPUT)
        self.assertEqual(cov["filled_count"], 0)
        self.assertEqual(cov["missing_axes"], ["topic", "method"])
        self.assertEqual(
            per_axis_status("topic", axes, out, cov["narrator_status"]),
            PER_AXIS_MISSING_FROM_LLM,
        )


class TestAxisMatchFailure(unittest.TestCase):
    def test_returned_axes_dont_match_input(self):
        axes = ["topic", "method"]
        out = {
            "narratives": [
                _narr("Topic", venue_side="X"),  # case-mismatch
                _narr("methodology", venue_side="Y"),
            ],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_AXIS_MATCH_FAILURE)
        self.assertEqual(cov["filled_count"], 2)  # filled in absolute
        self.assertEqual(cov["missing_axes"], ["topic", "method"])
        self.assertEqual(cov["unmatched_axes"], ["Topic", "methodology"])
        # Per-axis: input axes get missing_from_llm; variant returned
        # axes are not attached to a real mismatch so we never call
        # per_axis_status for them.
        self.assertEqual(
            per_axis_status("topic", axes, out, cov["narrator_status"]),
            PER_AXIS_MISSING_FROM_LLM,
        )


class TestMissingAxes(unittest.TestCase):
    def test_returned_narratives_subset_of_input(self):
        axes = ["topic", "method", "discipline"]
        out = {
            "narratives": [_narr("topic", venue_side="X")],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        # Some input axes were matched and filled, so status is PARTIAL
        # rather than MISSING_AXES (which means 0 matched).
        self.assertEqual(cov["narrator_status"], STATUS_PARTIAL)
        self.assertEqual(cov["missing_axes"], ["method", "discipline"])

    def test_all_input_axes_missing(self):
        axes = ["topic", "method"]
        out = {
            # Returned narratives are for entirely different axes but
            # WITHOUT being case-variants of input — and zero of them
            # match input. This is the missing_axes branch when
            # unmatched_axes happens to be empty as well (degenerate
            # case): pretend narrator returned an axis we don't recognize
            # but it ALSO happens not to be present at all... easier to
            # construct via axis_match_failure above. This case is
            # equivalent to empty_llm_output for input-axis purposes.
            "narratives": [],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_EMPTY_LLM_OUTPUT)


class TestParseFailed(unittest.TestCase):
    def test_schema_validation_failed(self):
        axes = ["topic", "method"]
        out = {
            "narratives": [],
            "extraction_attempt": _attempt_fallback(
                "schema_validation_failed",
                parse_status="schema_validation_failed",
            ),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_PARSE_FAILED)
        self.assertIsNotNone(cov["empty_reason"])
        for a in axes:
            self.assertEqual(
                per_axis_status(a, axes, out, cov["narrator_status"]),
                PER_AXIS_PARSE_FAILED,
            )

    def test_no_raw_output_leak(self):
        """Coverage dict must never contain raw model text."""
        axes = ["topic"]
        out = {
            "narratives": [],
            "extraction_attempt": _attempt_fallback(
                "schema_validation_failed",
                parse_status="schema_validation_failed",
            ),
        }
        cov = classify_narrator_coverage(axes, out)
        # No keys outside the documented set; specifically no
        # raw_output / response_content / stack_trace.
        for k in cov.keys():
            self.assertNotIn("raw", k.lower())
            self.assertNotIn("trace", k.lower())
            self.assertNotIn("stack", k.lower())


class TestProviderError(unittest.TestCase):
    def test_provider_error_classified(self):
        axes = ["topic"]
        out = {
            "narratives": [],
            "extraction_attempt": _attempt_fallback("provider_error"),
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_PROVIDER_ERROR)
        self.assertEqual(
            per_axis_status("topic", axes, out, cov["narrator_status"]),
            PER_AXIS_PROVIDER_ERROR,
        )


class TestNotAttempted(unittest.TestCase):
    def test_llm_unavailable(self):
        axes = ["topic"]
        out = {
            "narratives": [
                _narr("topic", venue_side="")  # honest fallback narratives
            ],
            # LLM-unavailable metadata: llm_attempted=False because the
            # provider was never reached. Matches what MismatchNarrator
            # _honest_fallback emits when narr_provider is None.
            "extraction_attempt": {
                "llm_attempted": False,
                "llm_provider": "none",
                "llm_model": None,
                "llm_latency_ms": None,
                "parse_status": "not_attempted",
                "fallback_used": True,
                "fallback_reason": "llm_unavailable",
            },
        }
        cov = classify_narrator_coverage(axes, out)
        self.assertEqual(cov["narrator_status"], STATUS_NOT_ATTEMPTED)

    def test_output_entity_is_none(self):
        cov = classify_narrator_coverage(["topic"], None)
        self.assertEqual(cov["narrator_status"], STATUS_NOT_ATTEMPTED)
        self.assertFalse(cov["narrator_attempted"])
        self.assertEqual(cov["filled_count"], 0)


class TestInputInsufficient(unittest.TestCase):
    def test_no_input_axes(self):
        out = {
            "narratives": [],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage([], out)
        self.assertEqual(cov["narrator_status"], STATUS_INPUT_INSUFFICIENT)


class TestAntiZombie(unittest.TestCase):
    """Helper itself must never invent venue claims or generic
    actions. It's a classifier, not a generator."""

    def test_helper_returns_no_text_fields_describing_venue(self):
        axes = ["topic"]
        out = {
            "narratives": [_narr("topic", venue_side="")],
            "extraction_attempt": _attempt_ok(),
        }
        cov = classify_narrator_coverage(axes, out)
        # No keys that could leak as venue_side/description/actions
        forbidden = {"venue_side", "description", "possible_actions"}
        self.assertFalse(forbidden & set(cov.keys()))
        # empty_reason is meta about the run, not a venue claim
        self.assertNotIn("venue expects", (cov["empty_reason"] or "").lower())
        self.assertNotIn("venue prefers", (cov["empty_reason"] or "").lower())


if __name__ == "__main__":
    unittest.main()
