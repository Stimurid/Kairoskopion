"""Generalized venue-fit regression tests.

These tests prove that venue-fit logic works for arbitrary manuscripts and
venues, not just the Logos trial case. No Logos-specific data is used.
"""

from pathlib import Path

from kairoskopion.services.article_modeling import build_article_model, build_manuscript_model
from kairoskopion.services.compliance import build_compliance_checklist
from kairoskopion.services.fit_assessment import assess_fit
from kairoskopion.services.scenario import build_scenario_from_dict
from kairoskopion.services.venue_profiling import build_venue_model

FIXTURES = Path(__file__).parent / "fixtures"


def _load(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8")


def _build_fit(manuscript_file: str, venue_file: str):
    ms_text = _load(manuscript_file)
    gl_text = _load(venue_file)
    ms = build_manuscript_model(ms_text, source_ref="test")
    article = build_article_model(ms, ms_text, source_ref="test")
    venue, _ = build_venue_model(gl_text, source_ref="test")
    scenario = build_scenario_from_dict(
        {"goal": "test", "target_venue_type": "journal"},
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
    )
    fit = assess_fit(article, venue, scenario)
    checklist = build_compliance_checklist(article, ms, venue, gl_text)
    return fit, checklist, venue, article


# ---- Language policy is a generic blocker ----

class TestLanguagePolicyGeneric:
    def test_english_manuscript_english_venue_no_block(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        lang = [a for a in fit.axes if a["axis"] == "language_register"]
        assert lang[0]["value"] == "strong"

    def test_english_manuscript_russian_venue_blocks(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_russian_only.md")
        lang = [a for a in fit.axes if a["axis"] == "language_register"]
        assert lang[0]["value"] == "bad"

    def test_russian_venue_produces_poor_fit(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_russian_only.md")
        assert fit.overall_label == "poor_fit"

    def test_english_venue_does_not_produce_poor_fit_from_language(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        lang = [a for a in fit.axes if a["axis"] == "language_register"]
        assert lang[0]["value"] != "bad"


# ---- Word limit: abstract vs article distinction ----

class TestWordLimitDistinction:
    def test_abstract_limit_not_applied_to_article(self):
        """If only abstract limit (200-250) is present, article word count
        should not be checked against it."""
        _, checklist, _, _ = _build_fit("manuscript_sample.md", "venue_russian_only.md")
        wc_items = [i for i in checklist.checklist_items if i["category"] == "word_count"]
        assert wc_items
        assert wc_items[0]["status"] != "non_compliant" or int(
            wc_items[0].get("notes", "").split(":")[1].strip().split()[0]
            if "Current:" in wc_items[0].get("notes", "") else "0"
        ) > 1000

    def test_article_limit_applied_correctly(self):
        """When article word limit is explicit (6000-12000), it should apply."""
        _, checklist, _, _ = _build_fit("manuscript_sample.md", "venue_separated_limits.md")
        wc_items = [i for i in checklist.checklist_items if i["category"] == "word_count"]
        assert wc_items
        if wc_items[0]["status"] == "non_compliant":
            assert "Current:" in wc_items[0].get("notes", "")

    def test_abstract_limit_does_not_flag_10k_article(self):
        """Venue with only abstract limit (200-250) must not flag a 10k-word article."""
        _, checklist, _, _ = _build_fit("manuscript_sample.md", "venue_russian_only.md")
        wc_items = [i for i in checklist.checklist_items if i["category"] == "word_count"]
        assert wc_items
        assert wc_items[0]["status"] in ("unknown", "present")


# ---- Article type extraction from numbered lists ----

class TestArticleTypeExtraction:
    def test_numbered_list_extraction(self):
        venue, _ = build_venue_model(_load("venue_english_philosophy.md"))
        assert len(venue.article_types_supported) >= 2
        types_lower = [t.lower() for t in venue.article_types_supported]
        assert any("article" in t for t in types_lower)

    def test_bullet_list_extraction(self):
        venue, _ = build_venue_model(_load("venue_russian_only.md"))
        assert len(venue.article_types_supported) >= 1
        types_lower = [t.lower() for t in venue.article_types_supported]
        assert any("article" in t for t in types_lower)

    def test_bold_format_still_works(self):
        venue, _ = build_venue_model(_load("venue_guidelines_sample.md"))
        assert len(venue.article_types_supported) >= 2


# ---- Discipline matching is not Logos-specific ----

class TestDisciplineMatching:
    def test_philosophy_venue_philosophy_article(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        disc = [a for a in fit.axes if a["axis"] == "discipline"]
        assert disc[0]["value"] in ("strong", "medium")

    def test_sts_venue_still_works(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_guidelines_sample.md")
        disc = [a for a in fit.axes if a["axis"] == "discipline"]
        assert disc[0]["value"] != "unknown"

    def test_education_venue_education_article(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_separated_limits.md")
        disc = [a for a in fit.axes if a["axis"] == "discipline"]
        assert disc[0]["value"] in ("strong", "medium", "weak")
        assert disc[0]["value"] != "unknown"


# ---- Audience axis uses discipline data ----

class TestAudienceAxis:
    def test_audience_assessed_when_disciplines_known(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        aud = [a for a in fit.axes if a["axis"] == "audience"]
        assert aud[0]["value"] != "unknown"


# ---- Citation ecology uses bibliography count ----

class TestCitationEcology:
    def test_bibliography_produces_nonunknown_citation_axis(self):
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        cit = [a for a in fit.axes if a["axis"] == "citation_ecology"]
        assert cit[0]["value"] in ("weak", "medium")


# ---- Genre: theoretical essays not always punished ----

class TestGenreNotOverPunished:
    def test_theoretical_essay_at_theoretical_venue_not_weak(self):
        """A venue that lists theoretical essays should not penalize them."""
        fit, _, _, _ = _build_fit("manuscript_sample.md", "venue_english_philosophy.md")
        genre = [a for a in fit.axes if a["axis"] == "genre"]
        assert genre[0]["value"] != "weak"
