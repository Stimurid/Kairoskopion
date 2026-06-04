"""Tests for fit assessment service."""

from pathlib import Path

from kairoskopion.enums import FitAxisValue, FitLabel, LifecycleStatus
from kairoskopion.services.article_modeling import build_article_model, build_manuscript_model
from kairoskopion.services.fit_assessment import assess_fit
from kairoskopion.services.scenario import build_scenario_from_dict
from kairoskopion.services.venue_profiling import build_venue_model

FIXTURES = Path(__file__).parent / "fixtures"


def _build_all():
    ms_text = (FIXTURES / "manuscript_sample.md").read_text(encoding="utf-8")
    gl_text = (FIXTURES / "venue_guidelines_sample.md").read_text(encoding="utf-8")
    import json
    sc_data = json.loads((FIXTURES / "submission_scenario_sample.json").read_text(encoding="utf-8"))

    ms = build_manuscript_model(ms_text, source_ref="src_ms")
    article = build_article_model(ms, ms_text, source_ref="src_ms")
    venue, regime = build_venue_model(gl_text, source_ref="src_gl")
    scenario = build_scenario_from_dict(sc_data, article_model_id=article.article_model_id,
                                        venue_model_id=venue.venue_model_id)
    return article, venue, scenario


class TestAssessFit:
    def test_produces_multiple_axes(self):
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        assert len(fit.axes) >= 5, "FitAssessment must have multiple axes, not single score"

    def test_no_numeric_score(self):
        """Spec forbids single numeric score in MVP."""
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        for ax in fit.axes:
            assert ax["value"] in {v.value for v in FitAxisValue}, (
                f"Axis value '{ax['value']}' is not a valid FitAxisValue"
            )

    def test_has_overall_label(self):
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        assert fit.overall_label in {l.value for l in FitLabel}

    def test_has_unknowns(self):
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        assert len(fit.unknowns) > 0, "FitAssessment should have unknowns"

    def test_has_recommendation(self):
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        assert fit.recommendation is not None
        assert len(fit.recommendation) > 10

    def test_links_to_article_and_venue(self):
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        assert fit.article_model_id == article.article_model_id
        assert fit.venue_model_id == venue.venue_model_id
        assert fit.submission_scenario_id == scenario.submission_scenario_id

    def test_method_weakness_detected(self):
        """Conceptual article vs empirical venue should show method weakness."""
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        method_axes = [a for a in fit.axes if a["axis"] == "method"]
        assert method_axes
        assert method_axes[0]["value"] == "weak"

    def test_citation_ecology_unknown(self):
        """Citation ecology should be unknown without corpus profiling."""
        article, venue, scenario = _build_all()
        fit = assess_fit(article, venue, scenario)
        cit_axes = [a for a in fit.axes if a["axis"] == "citation_ecology"]
        assert cit_axes
        assert cit_axes[0]["value"] == "unknown"
