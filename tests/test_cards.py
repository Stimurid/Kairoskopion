"""Tests for Kairoskopion markdown card generation."""

from kairoskopion.cards import (
    article_model_card,
    fit_assessment_card,
    generate_card,
    risk_report_card,
    submission_pack_card,
    venue_model_card,
)


class TestArticleModelCard:
    def test_basic(self):
        data = {
            "article_model_id": "art_abc123",
            "title_current": "On AI Subjectivity",
            "article_stage": "draft",
            "genre_current": "theoretical_essay",
            "lifecycle_status": "draft",
            "problem_statement": "Can AI systems exhibit genuine subjectivity?",
            "core_claims": ["AI subjectivity is a category error"],
            "protected_core": ["central thesis", "philosophical stance"],
            "unknowns": ["empirical evidence unclear"],
            "source_refs": ["src_001"],
        }
        md = article_model_card(data)
        assert "---" in md
        assert "art_abc123" in md
        assert "# On AI Subjectivity" in md
        assert "category error" in md
        assert "central thesis" in md

    def test_minimal(self):
        md = article_model_card({"article_model_id": "art_x"})
        assert "# Untitled Article" in md


class TestVenueModelCard:
    def test_basic(self):
        data = {
            "venue_model_id": "ven_xyz",
            "canonical_name": "Social Studies of Science",
            "venue_type": "journal",
            "scope_summary": "STS research and analysis",
            "official_urls": ["https://journals.sagepub.com/home/sss"],
            "unknowns": ["APC policy"],
        }
        md = venue_model_card(data)
        assert "Social Studies of Science" in md
        assert "STS research" in md
        assert "APC policy" in md


class TestFitAssessmentCard:
    def test_with_axes(self):
        data = {
            "fit_assessment_id": "fit_001",
            "overall_label": "possible_but_costly",
            "assessment_level": "light_profile",
            "lifecycle_status": "preliminary",
            "recommendation": "Consider deep venue profiling first",
            "axes": [
                {"axis": "topic", "value": "strong", "notes": "Good topic match"},
                {"axis": "method", "value": "weak", "notes": "Needs empirical section"},
            ],
            "unknowns": ["citation ecology unknown"],
        }
        md = fit_assessment_card(data)
        assert "possible_but_costly" in md
        assert "| topic |" in md
        assert "| method |" in md
        assert "citation ecology" in md


class TestRiskReportCard:
    def test_basic(self):
        data = {
            "risk_report_id": "risk_001",
            "overall_risk_label": "medium",
            "blocking_risks": ["AI disclosure policy unclear"],
            "risk_items": [
                {"risk_type": "AI_disclosure", "severity": "major", "description": "No AI policy found"},
            ],
        }
        md = risk_report_card(data)
        assert "AI disclosure" in md
        assert "medium" in md


class TestSubmissionPackCard:
    def test_basic(self):
        data = {
            "submission_pack_id": "sp_001",
            "ready_status": "not_ready",
            "missing_items": ["cover letter", "data availability"],
            "blocking_issues": ["references not verified"],
        }
        md = submission_pack_card(data)
        assert "not_ready" in md
        assert "cover letter" in md


class TestGenerateCard:
    def test_known_type(self):
        md = generate_card("ArticleModel", {"article_model_id": "art_x"})
        assert md is not None
        assert "Untitled Article" in md

    def test_unknown_type(self):
        assert generate_card("UnknownType", {}) is None
