"""V2-D minimal-real lane tests.

Pins the contracts for the three new builders:

  - CitationPlan: real gap categories / search tasks / unknowns, NO
    invented references, NO fake DOIs;
  - ComplianceChecklist: unknown_not_verified for missing policies
    (NOT satisfied / NOT 'not required'), NO naive 'ai in string'
    substring zombie;
  - SubmissionPack: ready_status reflects upstream gates, NEVER
    ready_for_manual_submission with major rewrite / unknown
    compliance / missing bibliography.
"""

from __future__ import annotations

import re
import unittest

from kairoskopion.schema import (
    ArticleModel,
    FitAssessment,
    MismatchMap,
    RewritePlan,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.services.citation_plan_minimal import (
    STATUS_NEEDS_BIBLIOGRAPHY,
    STATUS_PARTIALLY_READY,
    STATUS_SEARCH_TASKS_READY,
    build_minimal_citation_plan,
)
from kairoskopion.services.compliance_checklist_minimal import (
    ITEM_NEEDS_USER_INPUT,
    ITEM_SATISFIED,
    ITEM_UNKNOWN_NOT_VERIFIED,
    build_minimal_compliance_checklist,
)
from kairoskopion.services.submission_pack_minimal import (
    READY_FOR_MANUAL_SUBMISSION,
    READY_NEEDS_COMPLIANCE_CHECK,
    READY_NEEDS_REFERENCE_VERIFICATION,
    READY_NEEDS_USER_INPUT,
    READY_NOT_READY,
    build_minimal_submission_pack,
)


def _fit_with(axes_map: dict[str, str]) -> FitAssessment:
    return FitAssessment(
        axes=[
            {"axis": k, "value": v, "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []}
            for k, v in axes_map.items()
        ],
        overall_label="possible_but_costly",
    )


def _venue(scope: str = "", types: list[str] | None = None,
           ai_policy: str = "", language_policy: str | None = None) -> VenueModel:
    return VenueModel(
        canonical_name="X",
        venue_type="journal",
        scope_summary=scope,
        article_types_supported=types or [],
        ai_policy=ai_policy,
        language_policy=language_policy,
    )


def _article(title: str | None = "T", genre: str = "theoretical_essay",
             abstract: str | None = "A", lang: str = "en",
             refs: int | None = None,
             method: str = "conceptual_method") -> ArticleModel:
    return ArticleModel(
        title_current=title,
        abstract_current=abstract,
        language=lang,
        genre_current=genre,
        reference_count=refs,
        method_status=method,
    )


# ----------------------- CITATION PLAN -----------------------

class TestCitationPlanNoFakeReferences(unittest.TestCase):
    def test_no_doi_or_year_in_any_output_field(self):
        cp = build_minimal_citation_plan(
            _article(),
            _venue(scope="Philosophy of technology venue. References, "
                         "bibliography, recent literature expected."),
            _fit_with({"discipline": "weak", "citation_ecology": "weak",
                       "novelty_positioning": "weak"}),
            mismatch_map=None, risk_report=None, rewrite_plan=None,
        )
        flat = " ".join(
            cp.citation_gap_categories
            + cp.missing_bridge_categories
            + cp.recommended_reference_search_tasks
            + cp.verification_tasks
            + cp.dangerous_padding_warnings
            + cp.unknowns
        )
        # No DOIs (10.NNNN/...) anywhere
        self.assertIsNone(re.search(r"10\.\d{4,}/\S+", flat),
                          "must not invent DOIs")
        # No fake "(Smith 2024)" / "Smith, 2024" style invented citations
        self.assertIsNone(re.search(r"\b[A-Z][a-z]+\s+\d{4}\b", flat),
                          "must not invent author-year citations")

    def test_no_concrete_reference_titles(self):
        """Search tasks describe WORK, not specific reference titles."""
        cp = build_minimal_citation_plan(
            _article(),
            _venue(scope="Philosophy of technology venue."),
            _fit_with({"discipline": "weak", "novelty_positioning": "weak"}),
            mismatch_map=None, risk_report=None, rewrite_plan=None,
        )
        for task in cp.recommended_reference_search_tasks:
            # Heuristic: search tasks should not look like reference entries
            self.assertNotRegex(task, r"^\s*[A-Z][a-z]+,\s")

    def test_bibliography_absent_marked_unknown(self):
        cp = build_minimal_citation_plan(
            _article(refs=None),
            _venue(scope="ok"),
            _fit_with({"citation_ecology": "weak"}),
            mismatch_map=None, risk_report=None, rewrite_plan=None,
        )
        self.assertEqual(cp.current_bibliography_status, "absent_unknown")
        # status must reflect blockage
        self.assertIn(
            cp.status,
            (STATUS_NEEDS_BIBLIOGRAPHY, "blocked_missing_evidence"),
        )
        self.assertTrue(
            any("Bibliography not parsed" in u for u in cp.unknowns)
            or any("not parsed" in u for u in cp.unknowns)
        )

    def test_padding_warning_not_emitted_by_code_round2(self):
        """Round II doctrine: padding warnings are editorial semantic
        advice. Deterministic code MUST NOT author them. Field stays
        empty with origin=needs_llm until LLM citation organ is wired."""
        cp = build_minimal_citation_plan(
            _article(refs=20),
            _venue(scope="philosophy of technology, bibliography expected"),
            _fit_with({"discipline": "weak", "novelty_positioning": "weak"}),
            mismatch_map=None, risk_report=None, rewrite_plan=None,
        )
        self.assertEqual(cp.dangerous_padding_warnings, [])
        self.assertEqual(
            cp.field_origins.get("dangerous_padding_warnings"), "needs_llm",
        )


# ------------------ COMPLIANCE CHECKLIST ------------------

class TestComplianceUnknownNotSatisfied(unittest.TestCase):
    def test_missing_venue_ai_policy_marks_unknown_not_satisfied(self):
        cc = build_minimal_compliance_checklist(
            _article(),
            _venue(ai_policy=""),
            scenario=None, risk_report=None,
        )
        ai_items = [i for i in cc.checklist_items if i["category"] == "ai_disclosure"]
        self.assertEqual(len(ai_items), 1)
        self.assertEqual(ai_items[0]["status"], ITEM_UNKNOWN_NOT_VERIFIED)
        self.assertNotEqual(ai_items[0]["status"], ITEM_SATISFIED)
        self.assertIn("not verified", ai_items[0]["notes"].lower())

    def test_no_naive_ai_substring_false_positive(self):
        """Z#3: 'ai' in 'available' must NOT trigger AI policy 'satisfied'."""
        venue = _venue(scope="Open access journal — manuscripts available "
                             "in repositories. Maintained by domain experts.")
        cc = build_minimal_compliance_checklist(
            _article(), venue, scenario=None, risk_report=None,
        )
        ai_items = [i for i in cc.checklist_items if i["category"] == "ai_disclosure"]
        self.assertEqual(ai_items[0]["status"], ITEM_UNKNOWN_NOT_VERIFIED)

    def test_missing_title_surfaces_honestly(self):
        cc = build_minimal_compliance_checklist(
            _article(title=None), _venue(), scenario=None, risk_report=None,
        )
        title = [i for i in cc.checklist_items if i["category"] == "title"][0]
        self.assertIn(title["status"], ("missing", ITEM_NEEDS_USER_INPUT))
        self.assertIn("title", " ".join(cc.missing_items).lower())

    def test_missing_bibliography_surfaces_honestly(self):
        cc = build_minimal_compliance_checklist(
            _article(refs=None), _venue(), scenario=None, risk_report=None,
        )
        refs = [i for i in cc.checklist_items if i["category"] == "references"][0]
        self.assertEqual(refs["status"], ITEM_NEEDS_USER_INPUT)
        self.assertIn("bibliography", " ".join(cc.missing_items).lower())

    def test_article_type_compatible_when_match(self):
        cc = build_minimal_compliance_checklist(
            _article(genre="theoretical_essay"),
            _venue(types=["theoretical_essay", "conceptual_article"]),
            scenario=None, risk_report=None,
        )
        at = [i for i in cc.checklist_items if i["category"] == "article_type"][0]
        self.assertEqual(at["status"], ITEM_SATISFIED)


# -------------------- SUBMISSION PACK --------------------

class TestSubmissionPackReadiness(unittest.TestCase):
    def _build_pack(self, **overrides):
        a = overrides.get("article", _article())
        v = overrides.get("venue", _venue(types=["theoretical_essay"]))
        f = overrides.get("fit", _fit_with({"topic": "medium"}))
        s = overrides.get("scenario", SubmissionScenario())
        r = overrides.get("risk", RiskReport())
        rw = overrides.get("rewrite", None)
        cp = overrides.get("citation_plan",
                           build_minimal_citation_plan(a, v, f, None, r, rw))
        cc = overrides.get("compliance",
                           build_minimal_compliance_checklist(a, v, s, r))
        return build_minimal_submission_pack(a, v, s, f, r, rw, cp, cc)

    def test_not_ready_when_rewrite_major(self):
        pack = self._build_pack(rewrite=RewritePlan(
            estimated_effort="major",
            field_core_risk="core_touching",
            changes=[{"change_id": "c1"}],
        ))
        self.assertNotEqual(pack.ready_status, READY_FOR_MANUAL_SUBMISSION)
        self.assertIn(pack.ready_status, (
            READY_NEEDS_USER_INPUT, READY_NOT_READY,
            READY_NEEDS_REFERENCE_VERIFICATION,
            READY_NEEDS_COMPLIANCE_CHECK,
        ))

    def test_not_ready_when_citation_needs_bibliography(self):
        a = _article(refs=None)
        v = _venue(
            scope="Journal scope present; references and bibliography expected.",
            types=["theoretical_essay"],
        )
        f = _fit_with({"topic": "medium"})
        s = SubmissionScenario()
        cp = build_minimal_citation_plan(a, v, f, None, None, None)
        self.assertEqual(cp.status, STATUS_NEEDS_BIBLIOGRAPHY)
        pack = self._build_pack(
            article=a, venue=v, fit=f, scenario=s, citation_plan=cp,
        )
        self.assertNotEqual(pack.ready_status, READY_FOR_MANUAL_SUBMISSION)

    def test_depends_on_includes_dependencies(self):
        pack = self._build_pack()
        self.assertIn("citation_plan", pack.depends_on)
        self.assertIn("compliance_checklist", pack.depends_on)

    def test_no_cover_letter_generated(self):
        """V2-D explicitly skips cover_letter to avoid fake content."""
        pack = self._build_pack()
        self.assertIsNone(pack.cover_letter)

    def test_metadata_marks_not_final_automation(self):
        pack = self._build_pack()
        self.assertFalse(pack.metadata["is_final_submission_package"])
        self.assertEqual(pack.metadata["automation_level"], "manual_only")

    def test_next_actions_include_boundary_statement(self):
        pack = self._build_pack()
        joined = " ".join(pack.next_actions).lower()
        self.assertIn("readiness skeleton", joined)
        self.assertIn("manual", joined)


# ------------------- SERIALIZATION -------------------

class TestSerializationRoundTrip(unittest.TestCase):
    def test_v2d_fields_survive_round_trip(self):
        a, v = _article(), _venue(types=["theoretical_essay"])
        f = _fit_with({"discipline": "weak"})
        cp = build_minimal_citation_plan(a, v, f, None, None, None)
        cc = build_minimal_compliance_checklist(a, v, None, None)
        pk = build_minimal_submission_pack(a, v, None, f, None, None, cp, cc)
        for obj, cls in (
            (cp, type(cp)), (cc, type(cc)), (pk, type(pk)),
        ):
            d = obj.to_dict()
            rebuilt = cls.from_dict(d)
            for attr in ("status", "created_from", "unknowns"):
                self.assertEqual(
                    getattr(obj, attr), getattr(rebuilt, attr),
                    f"{cls.__name__}.{attr} did not round-trip",
                )

    def test_no_raw_or_trace_keys_in_any_serialized_field(self):
        a, v = _article(), _venue()
        f = _fit_with({"topic": "medium"})
        cp = build_minimal_citation_plan(a, v, f, None, None, None)
        cc = build_minimal_compliance_checklist(a, v, None, None)
        pk = build_minimal_submission_pack(a, v, None, f, None, None, cp, cc)
        for obj in (cp, cc, pk):
            for k in obj.to_dict().keys():
                kl = k.lower()
                self.assertNotIn("raw", kl)
                self.assertNotIn("trace", kl)
                self.assertNotIn("stack", kl)
                self.assertNotIn("secret", kl)
                self.assertNotIn("api_key", kl)


if __name__ == "__main__":
    unittest.main()
