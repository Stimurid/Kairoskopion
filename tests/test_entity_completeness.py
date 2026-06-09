"""Tests for Sprint 2: Entity Completeness (12 fit axes, 18 risk types, enriched models)."""

from __future__ import annotations

import json

import pytest

from kairoskopion.schema import (
    ArticleModel,
    FitAssessment,
    MismatchMap,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.services.fit_assessment import assess_fit
from kairoskopion.services.risk_reporting import RISK_TYPES, build_risk_report
from kairoskopion.services.article_modeling import build_article_model, build_manuscript_model
from kairoskopion.services.venue_profiling import build_venue_model
from kairoskopion.ids import (
    article_model_id,
    fit_assessment_id,
    submission_scenario_id,
    venue_model_id,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _minimal_article(**overrides) -> ArticleModel:
    defaults = dict(
        article_model_id=article_model_id(),
        source_refs=[],
        title_current="Test Article",
        abstract_current="An abstract about science.",
        language="en",
        input_mode="full_manuscript",
        article_stage="full_manuscript",
        genre_current="research_article",
        method_status="conceptual_method",
        novelty_mode="critique",
        citation_ecology_current="5 references found",
        unknowns=[],
        confidence="medium",
        lifecycle_status="preliminary",
        evidence_refs=[],
    )
    defaults.update(overrides)
    return ArticleModel(**defaults)


def _minimal_venue(**overrides) -> VenueModel:
    defaults = dict(
        venue_model_id=venue_model_id(),
        canonical_name="Test Journal",
        venue_type="journal",
        official_urls=["https://example.com"],
        scope_summary="Science and technology studies, STS, social ethics",
        author_guidelines_refs=[],
        article_types_supported=["research_article"],
        language_policy="English",
        publication_regime_id="regime_1",
        publisher_or_owner="Test Publisher",
        source_refs=["local:test"],
        unknowns=[],
        confidence="medium",
        staleness_status="fresh",
        lifecycle_status="draft",
    )
    defaults.update(overrides)
    return VenueModel(**defaults)


def _minimal_scenario(**overrides) -> SubmissionScenario:
    defaults = dict(
        submission_scenario_id=submission_scenario_id(),
        article_model_id="art_test",
        target_venue_ids=["ven_test"],
        goal="Publish research",
        deadline=None,
    )
    defaults.update(overrides)
    return SubmissionScenario(**defaults)


def _minimal_mismatch(**overrides) -> MismatchMap:
    defaults = dict(
        mismatch_map_id="mm_test",
        fit_assessment_id="fit_test",
        mismatches=[],
    )
    defaults.update(overrides)
    return MismatchMap(**defaults)


# ---------------------------------------------------------------------------
# FitAssessment: 12 axes, no single score
# ---------------------------------------------------------------------------

class TestFitAssessment12Axes:
    def test_produces_12_axes(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        assert len(fit.axes) == 12

    def test_all_axis_names_present(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        axis_names = {a["axis"] for a in fit.axes}
        expected = {
            "topic", "discipline", "genre", "argument_structure", "method",
            "citation_ecology", "novelty_positioning", "language_register",
            "audience", "formal_compliance", "author_eligibility",
            "publication_regime",
        }
        assert axis_names == expected

    def test_no_single_numeric_score(self):
        """Fit assessment must NEVER have a single numeric score."""
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        # Check that there is no numeric score field
        d = fit.__dict__ if hasattr(fit, '__dict__') else {}
        for key, val in d.items():
            if "score" in key.lower():
                assert not isinstance(val, (int, float)), \
                    f"Found numeric score: {key}={val}"

    def test_overall_label_is_qualitative(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        valid_labels = {
            "strong_candidate", "possible", "possible_but_costly",
            "poor_fit", "not_enough_data",
        }
        assert fit.overall_label in valid_labels

    def test_missing_data_yields_unknown_axes(self):
        """Article with minimal data should have many unknown axes."""
        sparse = _minimal_article(
            abstract_current=None,
            genre_current="unknown",
            method_status="unknown",
            novelty_mode="unknown",
            citation_ecology_current=None,
            disciplinary_register_current=None,
            core_claims=[],
        )
        venue = _minimal_venue(scope_summary=None, language_policy=None)
        fit = assess_fit(sparse, venue, _minimal_scenario())
        unknown_count = sum(1 for a in fit.axes if a["value"] == "unknown")
        assert unknown_count >= 6, f"Expected >= 6 unknowns, got {unknown_count}"

    def test_each_axis_has_required_fields(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        for axis in fit.axes:
            assert "axis" in axis
            assert "value" in axis
            assert "notes" in axis
            assert axis["value"] in ("strong", "medium", "weak", "bad", "unknown")


# ---------------------------------------------------------------------------
# Sprint 2 new axes
# ---------------------------------------------------------------------------

class TestNewFitAxes:
    def test_argument_structure_strong_when_all_present(self):
        art = _minimal_article(
            core_claims=["claim 1"],
            problem_statement="A problem",
            research_question="A question?",
        )
        fit = assess_fit(art, _minimal_venue(), _minimal_scenario())
        arg_axis = next(a for a in fit.axes if a["axis"] == "argument_structure")
        assert arg_axis["value"] == "strong"

    def test_argument_structure_unknown_without_claims(self):
        art = _minimal_article(core_claims=[])
        fit = assess_fit(art, _minimal_venue(), _minimal_scenario())
        arg_axis = next(a for a in fit.axes if a["axis"] == "argument_structure")
        assert arg_axis["value"] == "unknown"

    def test_novelty_positioning_detected(self):
        art = _minimal_article(novelty_mode="critique")
        fit = assess_fit(art, _minimal_venue(), _minimal_scenario())
        nov_axis = next(a for a in fit.axes if a["axis"] == "novelty_positioning")
        assert nov_axis["value"] == "medium"

    def test_author_eligibility_always_unknown(self):
        """Author eligibility requires author metadata we don't have."""
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        ae_axis = next(a for a in fit.axes if a["axis"] == "author_eligibility")
        assert ae_axis["value"] == "unknown"

    def test_audience_axis_present(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        aud_axis = next(a for a in fit.axes if a["axis"] == "audience")
        assert aud_axis["value"] in ("strong", "medium", "weak", "bad", "unknown")


# ---------------------------------------------------------------------------
# Risk taxonomy: 18 types
# ---------------------------------------------------------------------------

class TestRiskTaxonomy:
    def test_18_risk_types_defined(self):
        assert len(RISK_TYPES) == 18

    def test_all_risk_types_are_strings(self):
        for rt in RISK_TYPES:
            assert isinstance(rt, str)

    def test_required_risk_types_present(self):
        required = {
            "desk_reject_risk", "scope_mismatch", "methodology_mismatch",
            "citation_gap", "language_quality", "ethical_concern",
            "formatting_violation", "predatory_venue", "author_eligibility",
            "duplicate_submission", "copyright_conflict", "data_availability",
            "reviewer_pool_mismatch", "timeline_risk", "cost_risk",
            "reputational_risk", "ai_policy_risk", "core_transformation_risk",
        }
        assert required == set(RISK_TYPES)

    def test_risk_report_builds(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = assess_fit(art, ven, sc)
        mm = _minimal_mismatch()
        report = build_risk_report(art, ven, sc, fit, mm)
        assert report.risk_report_id.startswith("risk_")
        assert report.overall_risk_label in ("low", "medium", "high")

    def test_risk_items_have_required_fields(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = assess_fit(art, ven, sc)
        report = build_risk_report(art, ven, sc, fit, _minimal_mismatch())
        for item in report.risk_items:
            assert "risk_id" in item
            assert "risk_type" in item
            assert "severity" in item
            assert "likelihood" in item
            assert "description" in item

    def test_desk_reject_on_bad_axes(self):
        """Bad axes should trigger desk_reject_risk."""
        art = _minimal_article(language="zh")  # will cause language mismatch
        ven = _minimal_venue(language_policy="English only")
        fit = assess_fit(art, ven, _minimal_scenario())
        # Force a bad axis for desk reject
        for axis in fit.axes:
            if axis["axis"] == "language_register":
                axis["value"] = "bad"
        report = build_risk_report(art, ven, _minimal_scenario(), fit, _minimal_mismatch())
        types = [i["risk_type"] for i in report.risk_items]
        assert "desk_reject_risk" in types

    def test_core_transformation_risk_on_core_mismatches(self):
        mm = _minimal_mismatch(
            mismatches=[{"field_core_risk": "core_transforming", "field": "method"}],
        )
        art = _minimal_article()
        ven = _minimal_venue()
        fit = assess_fit(art, ven, _minimal_scenario())
        report = build_risk_report(art, ven, _minimal_scenario(), fit, mm)
        types = [i["risk_type"] for i in report.risk_items]
        assert "core_transformation_risk" in types


# ---------------------------------------------------------------------------
# ArticleModel: Sprint 2 fields
# ---------------------------------------------------------------------------

class TestArticleModelFields:
    def test_new_fields_populate_from_markdown(self):
        text = """# My Paper

## Abstract

This is the abstract of the paper about categories.

## Introduction

Introduction text goes here with plenty of words.

## Method

Conceptual analysis of scientific categories and their structures.

## Data Availability

Data is available on request.

## References

- Smith 2020. Title of paper.
- Jones 2021. Another paper.
"""
        ms = build_manuscript_model(text, source_ref="local:test.md")
        art = build_article_model(ms, text, source_ref="local:test.md")
        assert art.word_count is not None and art.word_count > 0
        assert art.section_count >= 3
        assert art.reference_count == 2
        assert art.has_references_section is True
        assert art.has_methods_section is True
        assert art.has_data_availability_statement is True
        assert art.extraction_status == "heuristic"

    def test_missing_sections_yield_false(self):
        text = "# Short Paper\n\nJust a brief note.\n"
        ms = build_manuscript_model(text)
        art = build_article_model(ms, text)
        assert art.has_references_section is False
        assert art.has_methods_section is False
        assert art.reference_count == 0

    def test_protected_core_always_unknown(self):
        text = "# Paper\n\n## Abstract\n\nText.\n\n## Intro\n\nMore text.\n\n## Method\n\nAnalysis.\n"
        ms = build_manuscript_model(text)
        art = build_article_model(ms, text)
        assert "protected core not confirmed by user" in art.unknowns


# ---------------------------------------------------------------------------
# VenueModel: Sprint 2 fields
# ---------------------------------------------------------------------------

class TestVenueModelFields:
    def test_new_fields_populate_from_guidelines(self):
        text = """# Journal of Science Studies

**Journal:** Journal of Science Studies
**Publisher:** Academic Press

## Aims and Scope

This journal publishes research on science and technology studies.
We are indexed in Scopus and Web of Science.
Open access: gold open access with APC.

## Peer Review

All submissions undergo double-blind peer review.

## AI Disclosure

Authors must disclose the use of AI writing tools.

## Data Availability

Authors must provide a data availability statement.

## Ethics

All research must have ethics approval from an ethics committee.
"""
        venue, regime = build_venue_model(text, source_ref="local:test.md")
        assert venue.aims_scope_summary is not None
        assert "scopus" in venue.indexing_claims
        assert venue.open_access_status == "gold_open_access"
        assert venue.anonymization_policy == "double_blind"
        assert venue.ai_policy == "ai_policy_present"
        assert venue.data_policy == "data_policy_present"
        assert venue.ethics_policy == "ethics_policy_present"

    def test_missing_policies_yield_none(self):
        text = """# Minimal Journal

**Journal:** Minimal
**Publisher:** Unknown

## Aims and Scope

A journal.
"""
        venue, _ = build_venue_model(text)
        assert venue.ai_policy is None
        assert venue.data_policy is None
        assert venue.ethics_policy is None


# ---------------------------------------------------------------------------
# Serialization roundtrip
# ---------------------------------------------------------------------------

class TestSerializationRoundtrip:
    def test_article_model_roundtrip(self):
        text = "# Paper\n\n## Abstract\n\nAbstract text.\n\n## Method\n\nConceptual.\n\n## References\n\n- Ref 1\n"
        ms = build_manuscript_model(text)
        art = build_article_model(ms, text)
        d = art.to_dict()
        js = json.dumps(d)
        loaded = json.loads(js)
        assert loaded["word_count"] == art.word_count
        assert loaded["section_count"] == art.section_count
        assert loaded["reference_count"] == art.reference_count
        assert loaded["has_references_section"] == art.has_references_section
        assert loaded["extraction_status"] == art.extraction_status

    def test_venue_model_roundtrip(self):
        text = "**Journal:** Test\n**Publisher:** Pub\n\n## Aims and Scope\n\nScience.\n"
        venue, _ = build_venue_model(text)
        d = venue.to_dict()
        js = json.dumps(d)
        loaded = json.loads(js)
        assert loaded["aims_scope_summary"] == venue.aims_scope_summary
        assert loaded["freshness_status"] == venue.freshness_status

    def test_fit_assessment_roundtrip(self):
        fit = assess_fit(_minimal_article(), _minimal_venue(), _minimal_scenario())
        d = fit.to_dict()
        js = json.dumps(d)
        loaded = json.loads(js)
        assert len(loaded["axes"]) == 12
        assert loaded["overall_label"] == fit.overall_label


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_article_model_without_new_fields(self):
        """ArticleModel should accept construction without Sprint 2 fields."""
        art = ArticleModel(
            article_model_id=article_model_id(),
            source_refs=[],
            title_current="Old Style",
            language="en",
            input_mode="abstract_only",
            article_stage="abstract",
            genre_current="unknown",
            method_status="unknown",
            novelty_mode="unknown",
            citation_ecology_current=None,
            unknowns=[],
            confidence="low",
            lifecycle_status="preliminary",
            evidence_refs=[],
        )
        assert art.word_count is None
        assert art.section_count is None
        assert art.has_references_section is None

    def test_venue_model_without_new_fields(self):
        """VenueModel should accept construction without Sprint 2 fields."""
        ven = VenueModel(
            venue_model_id=venue_model_id(),
            canonical_name="Old Journal",
            venue_type="journal",
            official_urls=[],
            scope_summary=None,
            author_guidelines_refs=[],
            article_types_supported=[],
            language_policy=None,
            publication_regime_id=None,
            publisher_or_owner=None,
            source_refs=[],
            unknowns=[],
            confidence="low",
            staleness_status="fresh",
            lifecycle_status="draft",
        )
        assert ven.ai_policy is None
        assert ven.data_policy is None
        assert ven.indexing_claims is None or ven.indexing_claims == []
