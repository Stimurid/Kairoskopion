"""Round II semantic governance tests.

Pin the doctrine rules: deterministic code must NOT emit semantic
content for citation ecology, missing bridges, search tasks, padding
warnings, or strategic submission prose. Per-field origins must be
present on V2-D objects.
"""

from __future__ import annotations

import unittest

from kairoskopion.schema import (
    ArticleModel,
    FitAssessment,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.services.bibliography_profile import (
    build_minimal_bibliography_profile,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.compliance_checklist_minimal import (
    build_minimal_compliance_checklist,
)
from kairoskopion.services.submission_pack_minimal import (
    build_minimal_submission_pack,
)
from kairoskopion.services.narrator_coverage import (
    PARSE_FAIL_INVALID_JSON,
    PARSE_FAIL_REPAIR_FAILED,
    PARSE_FAIL_EMPTY_AFTER_REPAIR,
    classify_parse_failure,
)
from kairoskopion.services.semantic_provenance import (
    ORIGIN_NEEDS_LLM,
    ORIGIN_STRUCTURAL_EXTRACTION,
    ORIGIN_DETERMINISTIC_AGGREGATION,
    SEMANTIC_STATUS_STRUCTURAL_ONLY,
    SEMANTIC_STATUS_NEEDS_LLM,
    aggregate_semantic_status,
)


REFS = """# Test article
Body.
## References
1. Author A. (2020). Title. Venue. https://doi.org/10.1234/x
2. Author B. (2021). Title. Venue.
"""


def _article() -> ArticleModel:
    return ArticleModel(
        title_current="X", abstract_current="A", language="en",
        genre_current="theoretical_essay",
    )


def _venue() -> VenueModel:
    return VenueModel(
        canonical_name="V", venue_type="journal",
        scope_summary="Journal of philosophy of technology. References expected.",
        article_types_supported=["theoretical_essay"],
    )


def _fit_weak() -> FitAssessment:
    """Fit with multiple weak axes — would have triggered semantic emission pre-Round-II."""
    return FitAssessment(
        axes=[
            {"axis": "topic", "value": "weak", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
            {"axis": "discipline", "value": "weak", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
            {"axis": "novelty_positioning", "value": "weak", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
            {"axis": "method", "value": "bad", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
            {"axis": "citation_ecology", "value": "weak", "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []},
        ],
        overall_label="possible_but_costly",
    )


# ---------------- CitationPlan: no deterministic semantic emission ----------------

class TestCitationPlanNoDeterministicSemantic(unittest.TestCase):
    def test_no_gap_categories_emitted_without_llm(self):
        bp = build_minimal_bibliography_profile(REFS)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit_weak(),
            None, None, None, bibliography_profile=bp,
        )
        # Round-II: semantic content fields stay empty
        self.assertEqual(cp.citation_gap_categories, [])
        self.assertEqual(cp.missing_bridge_categories, [])
        self.assertEqual(cp.recommended_reference_search_tasks, [])
        self.assertEqual(cp.dangerous_padding_warnings, [])

    def test_semantic_fields_origin_is_needs_llm(self):
        bp = build_minimal_bibliography_profile(REFS)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit_weak(),
            None, None, None, bibliography_profile=bp,
        )
        self.assertEqual(
            cp.field_origins.get("citation_gap_categories"),
            ORIGIN_NEEDS_LLM,
        )
        self.assertEqual(
            cp.field_origins.get("missing_bridge_categories"),
            ORIGIN_NEEDS_LLM,
        )
        self.assertEqual(
            cp.field_origins.get("recommended_reference_search_tasks"),
            ORIGIN_NEEDS_LLM,
        )
        self.assertEqual(
            cp.field_origins.get("dangerous_padding_warnings"),
            ORIGIN_NEEDS_LLM,
        )

    def test_structural_fields_origin_is_structural(self):
        bp = build_minimal_bibliography_profile(REFS)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit_weak(),
            None, None, None, bibliography_profile=bp,
        )
        self.assertEqual(
            cp.field_origins.get("status"),
            ORIGIN_STRUCTURAL_EXTRACTION,
        )
        self.assertEqual(
            cp.field_origins.get("current_bibliography_status"),
            ORIGIN_STRUCTURAL_EXTRACTION,
        )

    def test_risk_flags_are_structural_not_semantic(self):
        """risk_flags echo fit-axis labels structurally, not authored prose."""
        bp = build_minimal_bibliography_profile(REFS)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit_weak(),
            None, None, None, bibliography_profile=bp,
        )
        # Every risk_flag should look like fit_axis_X=label, not prose
        for f in cp.risk_flags:
            self.assertTrue(
                f.startswith("fit_axis_")
                or f in ("citation_gap", "reference_validity",
                         "scope_mismatch",
                         "mismatch_axis_citation_ecology",
                         "rewrite_plan_requests_citation_work"),
                f"unexpected non-structural risk_flag: {f!r}",
            )


# ---------------- BibliographyProfile is structural-only ----------------

class TestBibliographyStructuralOnly(unittest.TestCase):
    def test_semantic_status_is_structural(self):
        bp = build_minimal_bibliography_profile(REFS)
        self.assertEqual(bp.semantic_status, SEMANTIC_STATUS_STRUCTURAL_ONLY)
        # Every field origin is structural
        for k, v in bp.field_origins.items():
            self.assertEqual(
                v, ORIGIN_STRUCTURAL_EXTRACTION,
                f"BibliographyProfile field {k!r} has non-structural origin {v!r}",
            )

    def test_unknown_status_is_still_structural(self):
        bp = build_minimal_bibliography_profile(None)
        self.assertEqual(bp.semantic_status, SEMANTIC_STATUS_STRUCTURAL_ONLY)

    def test_not_found_status_is_still_structural(self):
        bp = build_minimal_bibliography_profile("# Article body without bibliography")
        self.assertEqual(bp.semantic_status, SEMANTIC_STATUS_STRUCTURAL_ONLY)

    def test_no_semantic_adequacy_claim(self):
        """parsed_structural status must not imply 'citation ecology is good'."""
        bp = build_minimal_bibliography_profile(REFS)
        flat = " ".join(bp.warnings + bp.unknowns + bp.verification_tasks)
        forbidden = [
            "good for venue", "venue-appropriate", "citation ecology adequate",
            "sufficient for", "expected by", "venue prefers",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase.lower(), flat.lower(),
                f"BibliographyProfile must not claim semantic adequacy: {phrase!r}",
            )


# ---------------- Compliance: per-item origins; AI policy unknown remains unknown ----------------

class TestComplianceProvenance(unittest.TestCase):
    def test_field_origins_present(self):
        cc = build_minimal_compliance_checklist(
            _article(), _venue(), None, None,
        )
        self.assertIn("checklist_items", cc.field_origins)
        self.assertIn("status", cc.field_origins)

    def test_no_semantic_status_means_satisfied(self):
        cc = build_minimal_compliance_checklist(
            _article(), _venue(), None, None,
        )
        # If venue ai_policy is empty, AI item must be unknown_not_verified
        ai = [i for i in cc.checklist_items if i["category"] == "ai_disclosure"][0]
        self.assertEqual(ai["status"], "unknown_not_verified")


# ---------------- SubmissionPack: next_actions are aggregation, not interpretation ----------------

class TestSubmissionPackAggregationOnly(unittest.TestCase):
    def test_field_origins_aggregation(self):
        a, v = _article(), _venue()
        f = _fit_weak()
        s = SubmissionScenario()
        cp = build_minimal_citation_plan(a, v, f, None, None, None,
                                          bibliography_profile=build_minimal_bibliography_profile(REFS))
        cc = build_minimal_compliance_checklist(a, v, s, None)
        pk = build_minimal_submission_pack(
            a, v, s, f, None, None, cp, cc,
            bibliography_profile=build_minimal_bibliography_profile(REFS),
        )
        self.assertEqual(
            pk.field_origins.get("next_actions"),
            ORIGIN_DETERMINISTIC_AGGREGATION,
        )
        self.assertEqual(
            pk.field_origins.get("ready_status"),
            ORIGIN_DETERMINISTIC_AGGREGATION,
        )

    def test_next_actions_no_article_interpretation(self):
        """Next actions must not contain semantic claims about article
        content beyond status aggregation (no 'identify recent
        articles', 'position novelty', 'reframe the introduction'
        type strategic prose)."""
        a, v = _article(), _venue()
        f = _fit_weak()
        s = SubmissionScenario()
        cp = build_minimal_citation_plan(a, v, f, None, None, None,
                                          bibliography_profile=build_minimal_bibliography_profile(REFS))
        cc = build_minimal_compliance_checklist(a, v, s, None)
        pk = build_minimal_submission_pack(
            a, v, s, f, None, None, cp, cc,
            bibliography_profile=build_minimal_bibliography_profile(REFS),
        )
        flat = " ".join(pk.next_actions).lower()
        # Forbidden strategic-prose markers (post-Round-II)
        forbidden = [
            "identify 5-8 recent articles",
            "extract the theoretical anchors",
            "position the article's novelty claim",
            "recent issues on this topic",
            "current debate markers",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, flat,
                             f"SubmissionPack.next_actions must not contain "
                             f"strategic prose: {phrase!r}")


# ---------------- V2-B2 classifier precedence ----------------

class TestClassifierPrecedence(unittest.TestCase):
    def test_repair_failed_takes_precedence_over_hardcoded_reason(self):
        """When narrator hardcodes fallback_reason=schema_validation_failed
        but parse_status=repair_failed, classifier must report
        REPAIR_FAILED (concrete) not SCHEMA_VALIDATION_FAILED."""
        attempt = {
            "llm_attempted": True,
            "parse_status": "repair_failed",
            "fallback_reason": "schema_validation_failed",  # old hardcoded
            "repair_steps": ["smart_quotes_replaced", "trailing_commas_stripped"],
            "validation_errors_summary": [],
        }
        out = classify_parse_failure(attempt)
        self.assertEqual(out["parse_failure_category"], PARSE_FAIL_REPAIR_FAILED)

    def test_invalid_json_takes_precedence(self):
        attempt = {
            "llm_attempted": True,
            "parse_status": "invalid_json",
            "fallback_reason": "schema_validation_failed",
            "repair_steps": [],
            "validation_errors_summary": [],
        }
        out = classify_parse_failure(attempt)
        self.assertEqual(out["parse_failure_category"], PARSE_FAIL_INVALID_JSON)

    def test_repair_failed_with_no_steps_is_empty_after_repair(self):
        attempt = {
            "llm_attempted": True,
            "parse_status": "repair_failed",
            "fallback_reason": "schema_validation_failed",
            "repair_steps": [],
            "validation_errors_summary": [],
        }
        out = classify_parse_failure(attempt)
        self.assertEqual(out["parse_failure_category"], PARSE_FAIL_EMPTY_AFTER_REPAIR)


# ---------------- aggregate_semantic_status ----------------

class TestSemanticStatusAggregator(unittest.TestCase):
    def test_needs_llm_status_when_all_semantic_needs_llm(self):
        st = aggregate_semantic_status({
            "citation_gap_categories": ORIGIN_NEEDS_LLM,
            "missing_bridge_categories": ORIGIN_NEEDS_LLM,
            "status": ORIGIN_STRUCTURAL_EXTRACTION,
        })
        self.assertEqual(st, SEMANTIC_STATUS_NEEDS_LLM)

    def test_structural_only_when_all_structural(self):
        st = aggregate_semantic_status({
            "status": ORIGIN_STRUCTURAL_EXTRACTION,
            "reference_count": ORIGIN_STRUCTURAL_EXTRACTION,
        })
        self.assertEqual(st, SEMANTIC_STATUS_STRUCTURAL_ONLY)

    def test_empty_yields_not_built(self):
        self.assertEqual(aggregate_semantic_status({}), "not_built")


if __name__ == "__main__":
    unittest.main()
