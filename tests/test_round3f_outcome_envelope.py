"""Round III-F outcome-envelope tests.

Pins the new base_shell contract:
  - try_llm_call_with_outcome never returns bare None.
  - On any failure the LLMAttemptOutcome carries provider_status /
    parse_status / parse_failure_category / redacted shape / no raw
    content.
  - Adapter rescues via loose_parsed and alternative top-level keys.
  - Helpers never raise; on exception they emit needs_llm placeholder
    with diagnostics.
"""

from __future__ import annotations


def _ok_outcome(parsed_dict):
    from kairoskopion.agents.base_shell import LLMAttemptOutcome
    return LLMAttemptOutcome(
        ok=True, parsed=parsed_dict, content_present=True,
        parse_status="parsed_ok",
    )


def _loose_outcome(loose_dict, parse_status="parsed_ok"):
    """Loose-parsed candidate the strict path missed."""
    from kairoskopion.agents.base_shell import LLMAttemptOutcome
    o = LLMAttemptOutcome(
        ok=False, parsed=None, loose_parsed=loose_dict,
        content_present=True,
        parse_status=parse_status,
        content_length=240, content_hash_prefix="abcdef0123456789",
    )
    o.redacted_top_level_type = "object"
    o.redacted_top_level_keys = list(loose_dict.keys()) if isinstance(loose_dict, dict) else []
    return o


def _failed_outcome(reason="provider_exception", parse_status="not_attempted"):
    from kairoskopion.agents.base_shell import LLMAttemptOutcome
    return LLMAttemptOutcome(
        ok=False, parsed=None, loose_parsed=None,
        content_present=False,
        parse_status=parse_status,
        provider_status="exception",
        fallback_reason=reason,
        parse_failure_category=reason,
    )


import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.agents.base_shell import LLMAttemptOutcome
from kairoskopion.schema import (
    ArticleModel, FitAssessment, MismatchMap, VenueModel,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.llm_semantic_organs import (
    try_llm_risk_officer,
    try_llm_rewrite_planner,
    upgrade_citation_plan_with_llm,
)
from kairoskopion.services.semantic_provenance import (
    SEMANTIC_STATUS_LLM_GROUNDED,
    SEMANTIC_STATUS_NEEDS_LLM,
)


def _a(): return ArticleModel(title_current="X", genre_current="theoretical_essay")
def _v(): return VenueModel(canonical_name="V", venue_type="journal", scope_summary="scope")
def _f(): return FitAssessment(axes=[], overall_label="possible")
def _mm(): return MismatchMap(mismatches=[
    {"axis": "topic", "severity": "major", "article_side": "X",
     "venue_side": "", "description": "", "possible_actions": [],
     "field_core_risk": "unknown_core_impact"},
])


class TestOutcomeEnvelopeContract(unittest.TestCase):
    """LLMAttemptOutcome never carries raw content; to_dict is safe."""

    def test_to_dict_has_no_raw_content_keys(self):
        o = _loose_outcome({"risks": [{"x": 1}]})
        d = o.to_dict()
        # No raw output, no traceback, no key/secret keys
        for k in d.keys():
            kl = k.lower()
            self.assertNotIn("raw", kl)
            self.assertNotIn("trace", kl)
            self.assertNotIn("secret", kl)
            self.assertNotIn("api_key", kl)

    def test_envelope_fields_present(self):
        o = _failed_outcome("provider_exception")
        d = o.to_dict()
        for k in ("provider_status", "parse_status",
                  "parse_failure_category", "fallback_reason",
                  "redacted_top_level_type", "redacted_top_level_keys",
                  "content_present", "content_length",
                  "content_hash_prefix", "agent_role", "model_role"):
            self.assertIn(k, d)


class TestRiskOutcomeAdapter(unittest.TestCase):
    """Adapter rescues from loose_parsed; sees alternative top-level keys."""

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_loose_parsed_with_alternative_key_is_rescued(self, mock):
        mock.return_value = _loose_outcome({
            "risks": [  # NOT under "risk_items"
                {"risk_type": "scope_mismatch", "severity": "high",
                 "description": "X", "evidence": "scope"},
            ],
            "unknowns": [],
        })
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        # Round III-F adapter normalizes container — produces LLM-grounded
        # output even though strict provider path failed.
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertEqual(len(rr.risk_items), 1)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_failed_outcome_yields_needs_llm_with_diagnostics(self, mock):
        mock.return_value = _failed_outcome("provider_exception")
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)
        d = rr.attempt_diagnostics or {}
        # Diagnostics carry actual envelope state
        self.assertEqual(d.get("provider_status"), "exception")
        self.assertEqual(d.get("fallback_reason"), "provider_exception")

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_helper_swallows_exception(self, mock):
        mock.side_effect = RuntimeError("oops")
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)


class TestRewriteOutcomeAdapter(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_loose_parsed_with_changes_alias_rescued(self, mock):
        mock.return_value = _loose_outcome({
            "changes": [
                {"action_id": 1, "target_mismatch": "topic",
                 "description": "reframe intro",
                 "field_core_impact": "core_touching"},
            ],
            "unknowns": [],
        })
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertTrue(rp.requires_user_acceptance)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_failed_outcome_yields_needs_llm(self, mock):
        mock.return_value = _failed_outcome("repair_failed")
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)


class TestCitationOutcomeAdapter(unittest.TestCase):
    def _base(self):
        return build_minimal_citation_plan(
            _a(), _v(), _f(), _mm(), None, None,
            bibliography_profile=None,
        )

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_loose_parsed_source_work_tasks_rescued(self, mock):
        mock.return_value = _loose_outcome({
            "tradition_gaps": ["postphenomenology missing"],
            "source_work_tasks": [
                "Предоставить библиографию рукописи",
                "Собрать набор первоисточников",
            ],
            "unknowns": [],
        })
        cp = upgrade_citation_plan_with_llm(
            self._base(), _a(), _v(), None, MagicMock(),
        )
        # Source-work tasks were rescued from loose-parsed via aliases
        joined = " ".join(cp.recommended_reference_search_tasks)
        self.assertIn("библиограф", joined)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_failed_outcome_keeps_needs_llm(self, mock):
        mock.return_value = _failed_outcome("invalid_json")
        cp = upgrade_citation_plan_with_llm(
            self._base(), _a(), _v(), None, MagicMock(),
        )
        self.assertEqual(cp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)


if __name__ == "__main__":
    unittest.main()
