"""Test fixtures for Kairoskopion MVP-0.

Spec §158 acceptance: "fixtures load; sample ArticleModel and VenueModel
can be written/read; sample FitAssessment can be created with preliminary
status."
"""

from kairoskopion.enums import (
    ArticleStage,
    EvidenceStatus,
    FitLabel,
    Genre,
    LifecycleStatus,
    MethodStatus,
    NoveltyMode,
    RegimeType,
    SubmissionReadiness,
    VenueType,
)
from kairoskopion.schema import (
    ArticleModel,
    CitationPlan,
    ComplianceChecklist,
    FitAssessment,
    ManuscriptModel,
    MismatchMap,
    PublicationRegimeModel,
    RewritePlan,
    RiskReport,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)


def sample_article_model() -> ArticleModel:
    return ArticleModel(
        title_current="The Impossibility of Artificial Subjectivity: A Conceptual Argument",
        abstract_current=(
            "This paper argues that artificial subjectivity is a category error. "
            "Drawing on phenomenological and analytic traditions, it shows that "
            "current AI systems cannot possess genuine first-person experience."
        ),
        language="en",
        article_stage=ArticleStage.DRAFT.value,
        problem_statement="Can AI systems have genuine subjectivity?",
        research_question="What are the conceptual barriers to artificial subjectivity?",
        object_of_inquiry="The concept of artificial subjectivity",
        core_claims=[
            "Artificial subjectivity is a category error",
            "Current AI lacks phenomenal consciousness",
        ],
        genre_current=Genre.THEORETICAL_ESSAY.value,
        disciplinary_register_current="philosophy_of_mind / AI_ethics",
        novelty_mode=NoveltyMode.CRITIQUE.value,
        method_status=MethodStatus.CONCEPTUAL_METHOD.value,
        method_description="Conceptual analysis with phenomenological engagement",
        theoretical_shoulders=["Nagel", "Chalmers", "Dreyfus", "Heidegger"],
        citation_ecology_current="Philosophy of mind + AI ethics crossover",
        protected_core=[
            "Central thesis: artificial subjectivity is a category error",
            "Philosophical stance: phenomenological",
            "Object: genuine first-person experience",
        ],
        unknowns=[
            "Audience reception in STS venues unclear",
            "Empirical AI papers not yet reviewed",
        ],
        confidence="medium",
        source_refs=["src_manuscript_draft_v1"],
    )


def sample_venue_model() -> VenueModel:
    return VenueModel(
        canonical_name="Social Studies of Science",
        venue_type=VenueType.JOURNAL.value,
        official_urls=["https://journals.sagepub.com/home/sss"],
        scope_summary=(
            "Publishes research on the social dimensions of science and technology. "
            "STS-focused, interdisciplinary, empirical and theoretical work."
        ),
        author_guidelines_refs=["src_sss_guidelines_2026"],
        article_types_supported=["research_article", "review", "commentary"],
        language_policy="English",
        publisher_or_owner="SAGE",
        publication_regime_id="reg_classic_journal",
        source_refs=["src_sss_homepage", "src_sss_guidelines_2026"],
        unknowns=["AI disclosure policy", "APC details"],
        confidence="medium",
        lifecycle_status=LifecycleStatus.DRAFT.value,
    )


def sample_manuscript_model() -> ManuscriptModel:
    return ManuscriptModel(
        article_model_id="art_sample",
        title="The Impossibility of Artificial Subjectivity",
        abstract="This paper argues that artificial subjectivity is a category error.",
        keywords=["artificial subjectivity", "AI ethics", "phenomenology", "category error"],
        sections=["Introduction", "Phenomenological Background", "The Category Error Argument",
                   "Implications for AI Ethics", "Conclusion"],
        word_count=8500,
        language="en",
    )


def sample_submission_scenario() -> SubmissionScenario:
    return SubmissionScenario(
        goal="Publish in Q1 STS/philosophy journal",
        target_indexing="Scopus",
        deadline="2026-12-01",
        language_constraints="English",
        unknowns=["APC tolerance not discussed"],
    )


def sample_fit_assessment_preliminary() -> FitAssessment:
    return FitAssessment(
        article_model_id="art_sample",
        venue_model_id="ven_sample",
        submission_scenario_id="scn_sample",
        overall_label=FitLabel.POSSIBLE_BUT_COSTLY.value,
        axes=[
            {"axis": "topic", "value": "medium", "notes": "AI subjectivity is tangential to core STS"},
            {"axis": "discipline", "value": "weak", "notes": "Philosophy-heavy, STS expects empirical grounding"},
            {"axis": "genre", "value": "medium", "notes": "Theoretical essay acceptable but uncommon"},
            {"axis": "method", "value": "weak", "notes": "Conceptual only, no empirical component"},
            {"axis": "citation_ecology", "value": "unknown", "notes": "Not yet checked"},
        ],
        unknowns=["citation ecology not checked", "editorial board preferences unknown"],
        recommendation="Consider adding STS-oriented empirical material or target a philosophy venue instead",
        lifecycle_status=LifecycleStatus.PRELIMINARY.value,
    )


def sample_publication_regime() -> PublicationRegimeModel:
    return PublicationRegimeModel(
        regime_type=RegimeType.CLASSIC_JOURNAL_ARTICLE.value,
        description="Standard single-blind peer review, 6-12 month timeline",
        review_model="single_blind",
        typical_article_forms=["research_article", "review"],
    )
