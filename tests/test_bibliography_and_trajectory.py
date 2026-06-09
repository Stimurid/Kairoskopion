"""Tests for Sprint 5: Bibliography Robustness + Report Quality."""

from __future__ import annotations

import pytest

from kairoskopion.services.bibliography_parsing import (
    build_bibliography_profile,
    detect_reference_style,
    extract_references_section,
    split_references,
)
from kairoskopion.services.trajectory_report import build_trajectory_report
from kairoskopion.services.fit_assessment import assess_fit
from kairoskopion.services.risk_reporting import build_risk_report
from kairoskopion.schema import (
    ArticleModel,
    BibliographyProfile,
    FitAssessment,
    MismatchMap,
    PublicationTrajectoryReport,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.ids import (
    article_model_id,
    fit_assessment_id,
    submission_scenario_id,
    venue_model_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_APA_REFS = """## References

Smith, J. A. (2020). The nature of consciousness. Journal of Philosophy, 117(3), 135-155. https://doi.org/10.1234/test1
Jones, B. C., & Williams, D. E. (2019). Cognitive frameworks revisited. Psychological Review, 126(2), 200-220.
Chalmers, D. J. (1996). The Conscious Mind. Oxford University Press.
"""

_NUMBERED_REFS = """## References

[1] Smith JA. The nature of consciousness. Journal of Philosophy. 2020;117(3):135-155.
[2] Jones BC, Williams DE. Cognitive frameworks revisited. Psych Rev. 2019;126(2):200-220.
[3] Chalmers DJ. The Conscious Mind. Oxford: Oxford University Press; 1996.
"""

_CHICAGO_REFS = """## References

Smith, John A. 2020. "The Nature of Consciousness." Journal of Philosophy 117 (3): 135-155.
Jones, Brian C., and David E. Williams. 2019. "Cognitive Frameworks Revisited." Psychological Review 126 (2): 200-220.
Chalmers, David J. 1996. The Conscious Mind. Oxford: Oxford University Press.
"""

_BULLET_REFS = """## References

- Smith, J.A. (2020). The nature of consciousness. Journal of Philosophy, 117(3), 135-155.
- Jones, B.C. & Williams, D.E. (2019). Cognitive frameworks revisited. Psychological Review, 126(2), 200-220.
- Chalmers, D.J. (1996). The Conscious Mind. Oxford University Press.
"""


def _make_manuscript(refs_section: str = _APA_REFS) -> str:
    return f"""# Test Paper

## Abstract

This paper examines the nature of consciousness.

## Introduction

Consciousness remains one of the hardest problems.

## Method

Conceptual analysis of the literature.

## Discussion

We find interesting patterns.

{refs_section}
"""


def _minimal_article(**kw) -> ArticleModel:
    defaults = dict(
        article_model_id=article_model_id(),
        source_refs=["local:test"],
        title_current="Test",
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
    defaults.update(kw)
    return ArticleModel(**defaults)


def _minimal_venue(**kw) -> VenueModel:
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
    defaults.update(kw)
    return VenueModel(**defaults)


def _minimal_scenario(**kw) -> SubmissionScenario:
    defaults = dict(
        submission_scenario_id=submission_scenario_id(),
        article_model_id="art_test",
        target_venue_ids=["ven_test"],
        goal="Publish research",
        deadline=None,
    )
    defaults.update(kw)
    return SubmissionScenario(**defaults)


def _minimal_mismatch(**kw) -> MismatchMap:
    defaults = dict(mismatch_map_id="mm_test", fit_assessment_id="fit_test", mismatches=[])
    defaults.update(kw)
    return MismatchMap(**defaults)


# ---------------------------------------------------------------------------
# Reference style detection
# ---------------------------------------------------------------------------

class TestReferenceStyleDetection:
    def test_apa_style(self):
        section = extract_references_section(_make_manuscript(_APA_REFS))
        assert section is not None
        style = detect_reference_style(section)
        assert style == "apa"

    def test_numbered_style(self):
        section = extract_references_section(_make_manuscript(_NUMBERED_REFS))
        assert section is not None
        style = detect_reference_style(section)
        assert style in ("numbered", "vancouver")  # Vancouver is a numbered style

    def test_bullet_style(self):
        section = extract_references_section(_make_manuscript(_BULLET_REFS))
        assert section is not None
        style = detect_reference_style(section)
        assert style in ("apa", "author_date")  # bullet with APA content

    def test_empty_returns_unknown(self):
        assert detect_reference_style("") == "unknown"


# ---------------------------------------------------------------------------
# Multi-style reference splitting
# ---------------------------------------------------------------------------

class TestMultiStyleSplitting:
    def test_apa_splitting(self):
        section = extract_references_section(_make_manuscript(_APA_REFS))
        refs = split_references(section)
        assert len(refs) == 3

    def test_numbered_splitting(self):
        section = extract_references_section(_make_manuscript(_NUMBERED_REFS))
        refs = split_references(section)
        assert len(refs) == 3

    def test_bullet_splitting(self):
        section = extract_references_section(_make_manuscript(_BULLET_REFS))
        refs = split_references(section)
        assert len(refs) == 3

    def test_chicago_splitting(self):
        section = extract_references_section(_make_manuscript(_CHICAGO_REFS))
        refs = split_references(section)
        assert len(refs) == 3


# ---------------------------------------------------------------------------
# Bibliography profile with style
# ---------------------------------------------------------------------------

class TestBibliographyProfile:
    def test_profile_includes_style(self):
        profile = build_bibliography_profile(_make_manuscript(_APA_REFS))
        assert profile.reference_style == "apa"

    def test_profile_includes_style_numbered(self):
        profile = build_bibliography_profile(_make_manuscript(_NUMBERED_REFS))
        assert profile.reference_style in ("numbered", "vancouver")

    def test_profile_total_refs(self):
        profile = build_bibliography_profile(_make_manuscript(_APA_REFS))
        assert profile.total_references == 3

    def test_profile_year_range(self):
        profile = build_bibliography_profile(_make_manuscript(_APA_REFS))
        assert profile.year_min == 1996
        assert profile.year_max == 2020

    def test_profile_doi_detection(self):
        profile = build_bibliography_profile(_make_manuscript(_APA_REFS))
        assert profile.doi_count >= 1

    def test_profile_roundtrip(self):
        profile = build_bibliography_profile(_make_manuscript(_APA_REFS))
        d = profile.to_dict()
        assert d["reference_style"] == "apa"
        assert d["total_references"] == 3


# ---------------------------------------------------------------------------
# Publication Trajectory Report
# ---------------------------------------------------------------------------

class TestTrajectoryReport:
    def _build_report(self, bib=None):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = assess_fit(art, ven, sc)
        mm = _minimal_mismatch()
        risk = build_risk_report(art, ven, sc, fit, mm)
        return build_trajectory_report(art, ven, fit, risk, bib)

    def test_report_has_required_fields(self):
        report = self._build_report()
        assert report.report_id.startswith("ptr_")
        assert report.fit_summary is not None
        assert report.risk_summary is not None
        assert report.overall_recommendation is not None
        assert report.confidence in ("low", "medium", "high")

    def test_report_aggregates_strengths(self):
        report = self._build_report()
        assert isinstance(report.strengths, list)

    def test_report_aggregates_weaknesses(self):
        report = self._build_report()
        assert isinstance(report.weaknesses, list)

    def test_report_includes_critical_actions(self):
        report = self._build_report()
        assert isinstance(report.critical_actions, list)

    def test_report_includes_unknowns(self):
        report = self._build_report()
        assert isinstance(report.unknowns, list)
        assert len(report.unknowns) > 0  # there should always be some unknowns

    def test_report_with_bibliography(self):
        bib = build_bibliography_profile(_make_manuscript(_APA_REFS))
        report = self._build_report(bib=bib)
        assert report.bibliography_summary is not None
        assert "3 references" in report.bibliography_summary

    def test_report_without_bibliography(self):
        report = self._build_report(bib=None)
        assert report.bibliography_summary is None

    def test_report_serialization(self):
        report = self._build_report()
        d = report.to_dict()
        assert "fit_summary" in d
        assert "risk_summary" in d
        assert "overall_recommendation" in d
        assert isinstance(d["strengths"], list)

    def test_thin_bibliography_flagged(self):
        """Manuscript with very few refs should have a weakness."""
        text = """# Paper

## Abstract

Abstract.

## Intro

Text.

## Method

Method.

## References

- Smith (2020). One reference only. Journal of Testing, 1(1), 1-10.
"""
        bib = build_bibliography_profile(text)
        report = self._build_report(bib=bib)
        weak_texts = " ".join(report.weaknesses)
        assert "thin bibliography" in weak_texts or "references" in weak_texts
