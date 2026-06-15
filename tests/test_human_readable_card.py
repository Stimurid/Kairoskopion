"""Human-readable model review card tests.

Covers:
  - 11-section ArticleModel human view (smoke + Mavrinsky regression);
  - 9-section VenueModel/VPKG human view (frozen top-5 venue regression);
  - Rabbit/early-modern fragment fixture-based smoke;
  - Field anchors per task spec §E;
  - No submission-recommendation leakage;
  - API endpoints are user-scoped via existing auth dep.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kairoskopion.services.human_readable_card import (
    EVIDENCE_STATUS_PROSE,
    GENRE_PROSE,
    METHOD_PROSE,
    NOVELTY_PROSE,
    article_model_human_view,
    venue_human_view,
)


# Forbidden phrases that would mean we leaked a submission recommendation
_FORBIDDEN_RECOMMENDATION_PHRASES = [
    "we recommend submitting",
    "submit to ",
    "submission recommendation",
    "best journal for you",
    "final recommendation",
]


def _assert_no_recommendation(md: str):
    low = md.lower()
    for phrase in _FORBIDDEN_RECOMMENDATION_PHRASES:
        assert phrase not in low, (
            f"Submission-recommendation leakage detected: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# Article view — basic shape
# ---------------------------------------------------------------------------

class TestArticleHumanViewShape(unittest.TestCase):
    def test_returns_markdown_not_json(self):
        article = {
            "article_model_id": "art_x",
            "title_current": "Test article",
            "object_of_inquiry": "интерфейс как онтологическая форма",
            "central_problem": "разрыв между феноменальным и техническим",
            "core_claims": ["claim A", "claim B"],
            "genre_current": "theoretical_essay",
            "method_status": "no_method_continental_argument",
            "novelty_mode": "concept_introduction_with_reconstruction",
            "protected_core": ["interface = dispositif/capture"],
            "lifecycle_status": "preliminary",
        }
        md = article_model_human_view(article)
        self.assertIsInstance(md, str)
        # not raw JSON dump
        self.assertFalse(md.lstrip().startswith("{"))
        # Markdown shape: has H1 + H2 sections
        self.assertIn("# ", md)
        self.assertIn("## ", md)
        # Author-facing sections (Russian labels per task spec)
        for section in (
            "Коротко",
            "Главный объект статьи",
            "Главная проблема",
            "Основные утверждения статьи",
            "Тип статьи",
            "Дисциплинарные регистры",
            "Теоретические плечи",
            "Неприкосновенное ядро",
            "Что система не знает",
            "Вопросы автору для проверки модели",
            "Что можно поправить",
        ):
            self.assertIn(section, md, f"missing required section: {section}")

    def test_preliminary_warning_visible(self):
        article = {"article_model_id": "x", "lifecycle_status": "preliminary"}
        md = article_model_human_view(article)
        self.assertIn("предварительная", md)
        self.assertIn("НЕ является", md.lower().replace("ё", "е") + md)

    def test_no_submission_recommendation_leakage(self):
        article = {
            "article_model_id": "art_x",
            "title_current": "Anything",
            "core_claims": ["Anything", "submit to Nature"],  # adversarial
            "genre_current": "theoretical_essay",
        }
        md = article_model_human_view(article)
        # The card itself never advises submission, even if a claim says so
        low = md.lower()
        # "submission" in unknowns ("сценарий подачи") is OK; the explicit
        # advisory phrases are not
        self.assertNotIn("we recommend submitting", low)
        self.assertNotIn("best journal for you", low)
        self.assertNotIn("final recommendation", low)

    def test_field_anchors_emitted(self):
        article = {
            "article_model_id": "x",
            "object_of_inquiry": "X",
            "core_claims": ["c1"],
        }
        md = article_model_human_view(article)
        for anchor in (
            "<!-- field: article_model.object_of_inquiry -->",
            "<!-- field: article_model.core_claims -->",
            "<!-- field: article_model.protected_core -->",
        ):
            self.assertIn(anchor, md)


# ---------------------------------------------------------------------------
# Protected core honest "missing" warning
# ---------------------------------------------------------------------------

class TestProtectedCoreHandling(unittest.TestCase):
    def test_missing_protected_core_emits_explicit_warning(self):
        article = {"article_model_id": "x", "protected_core": []}
        md = article_model_human_view(article)
        # Required exact warning text per task spec §C.8
        self.assertIn("Система пока не знает", md)
        self.assertIn("неприкосновенным ядром", md)
        self.assertIn("предварительными", md)

    def test_present_protected_core_listed(self):
        article = {
            "article_model_id": "x",
            "protected_core": [
                "desire-as-excess shift",
                "interface as dispositif/capture",
                "greedy/generous distinction as ontology, not UX",
            ],
        }
        md = article_model_human_view(article)
        self.assertIn("Неприкосновенное ядро", md)
        for item in article["protected_core"]:
            self.assertIn(item, md)
        # Missing-warning text must NOT appear in this case
        self.assertNotIn("Система пока не знает, что автор", md)


# ---------------------------------------------------------------------------
# Enum prose explanations
# ---------------------------------------------------------------------------

class TestEnumProse(unittest.TestCase):
    def test_genre_method_novelty_are_explained_in_prose(self):
        article = {
            "article_model_id": "x",
            "genre_current": "theoretical_essay",
            "method_status": "conceptual_method",
            "novelty_mode": "concept_introduction",
        }
        md = article_model_human_view(article)
        # The plain-language explanations must appear, not just the raw enum
        self.assertIn(GENRE_PROSE["theoretical_essay"], md)
        self.assertIn(METHOD_PROSE["conceptual_method"], md)
        self.assertIn(NOVELTY_PROSE["concept_introduction"], md)


# ---------------------------------------------------------------------------
# Pathways enrich section 6
# ---------------------------------------------------------------------------

class TestDisciplinaryRegisterPathways(unittest.TestCase):
    def test_pathways_with_reasoning_appear_in_section_6(self):
        article = {"article_model_id": "x", "title_current": "T"}
        pathways = [
            {
                "discipline_name": "Continental philosophy",
                "fit_strength": "strong",
                "reasoning": "The article uses Deleuze/Guattari vocabulary",
            },
            {
                "discipline_name": "STS",
                "fit_strength": "medium",
                "reasoning": "Partial overlap with assemblage theory",
            },
        ]
        md = article_model_human_view(article, pathways=pathways)
        self.assertIn("Continental philosophy", md)
        self.assertIn("strong", md)
        self.assertIn("The article uses Deleuze/Guattari vocabulary", md)
        self.assertIn("STS", md)
        self.assertIn("medium", md)


# ---------------------------------------------------------------------------
# Mavrinsky regression: structured model + human view
# ---------------------------------------------------------------------------

class TestMavrinskyRegression(unittest.TestCase):
    def _mavrinsky_article(self) -> dict:
        # Aligned with services/mavrinsky_venue_selection.mavrinsky_article_model()
        return {
            "article_model_id": "art_mavrinsky_gold",
            "title_current": (
                "Желание, виртуальность и интерфейс: к онтологии технических форм"
            ),
            "object_of_inquiry": (
                "Interface as ontological technical form, in continental "
                "register, treated through desire-as-excess (vs Lacanian "
                "desire-as-lack) and the dispositif/capture apparatus."
            ),
            "central_problem": (
                "How does interface mediate technicity-of-subject under "
                "post-structuralist accounts of desire and capture?"
            ),
            "core_claims": [
                "Desire-as-excess displaces Lacanian desire-as-lack",
                "Greedy interface = dispositif of capture; generous = opening",
                "The distinction is ontological, not ergonomic",
            ],
            "genre_current": "theoretical_essay",
            "method_status": "no_method_continental_argument",
            "novelty_mode": "concept_introduction_with_reconstruction",
            "disciplinary_registers": [
                "continental_philosophy",
                "philosophy_of_technology",
                "media_philosophy",
            ],
            "tribes_present": {
                "Deleuze_Guattari": "constructive",
                "Foucault": "constructive",
                "Lacan": "foil",
            },
            "protected_core": [
                "desire-as-excess shift",
                "interface as dispositif/capture",
                "greedy/generous distinction as ontology, not UX",
            ],
            "language_register": {
                "primary_language": "ru",
                "register": "academic_dense",
            },
            "lifecycle_status": "preliminary",
        }

    def test_mavrinsky_human_view_has_all_required_sections(self):
        article = self._mavrinsky_article()
        md = article_model_human_view(article)
        # Per task spec §H.3 — required sections
        for section in (
            "Коротко",                             # short summary
            "Главный объект статьи",               # object
            "Главная проблема",                    # problem
            "Основные утверждения статьи",         # claims
            "Тип статьи",                          # genre / method / novelty
            "Дисциплинарные регистры",             # disciplinary registers
            "Неприкосновенное ядро",               # protected core
            "Что система не знает",                # unknowns
            "Вопросы автору для проверки модели",  # author questions
        ):
            self.assertIn(section, md)
        # Content sanity
        self.assertIn("desire-as-excess", md)
        self.assertIn("dispositif", md)
        self.assertIn("Deleuze_Guattari", md)
        # Not raw JSON
        self.assertFalse(md.lstrip().startswith("{"))
        # No leakage
        _assert_no_recommendation(md)

    def test_mavrinsky_lists_5_to_9_author_questions(self):
        md = article_model_human_view(self._mavrinsky_article())
        # Section 10 — count of question bullets
        section_start = md.index("Вопросы автору для проверки модели")
        section = md[section_start:]
        # Pull out the questions block, end at next H2
        next_h2 = section.find("\n## ", 1)
        block = section[:next_h2 if next_h2 != -1 else len(section)]
        bullets = [
            l for l in block.splitlines()
            if l.startswith("- ") and "?" in l
        ]
        self.assertGreaterEqual(len(bullets), 5)
        self.assertLessEqual(len(bullets), 9)


# ---------------------------------------------------------------------------
# Rabbit / early-modern England fragment fixture
# ---------------------------------------------------------------------------

# Fixture was captured from a live LLM-driven run via /cases/<id>/intake/text
# in the prior tester-readiness pass. Frozen here so CI does not depend on
# live LLM availability.
_RABBIT_ARTICLE_FIXTURE = {
    "article_model_id": "art_rabbit_xvi",
    "title_current": "Архивные заметки о разведении кроликов в Англии XVI века",
    "object_of_inquiry": (
        "Management of rabbit fertility in early modern England as a "
        "conceptual lens for thinking about domestic order, abundance, "
        "and human authority over living beings."
    ),
    "central_problem": (
        "How does fertility management of rabbits sit within early modern "
        "frameworks of domestic order, surplus, and moral anxieties about "
        "excessive reproduction?"
    ),
    "core_claims": [
        "Management of animal fertility functions as a framework for thinking about domestic order, abundance, and bodily control in early modern England.",
        "Rabbit warrens and domestic breeding practices reflect broader early modern conceptions of fertility, surplus, and human authority over living beings.",
        "Moral anxieties surrounding excessive reproduction are embedded in historical understandings of animal breeding and its social meanings.",
    ],
    "genre_current": "theoretical_essay",
    "method_status": "conceptual_method",
    "novelty_mode": "translation_between_fields",
    "disciplinary_registers": [
        "history_of_science",
        "animal_studies",
        "historical_anthropology",
        "early_modern_history",
    ],
    "protected_core": [
        "Rabbit fertility management in early modern England operates as a conceptual lens through which domestic order, abundance, and human authority over living beings is theorized."
    ],
    "unknowns": [
        "no bibliography supplied",
        "no full manuscript yet",
        "method not detected",  # honest UNKNOWN even when LLM populated everything else
    ],
    "lifecycle_status": "preliminary",
}

_RABBIT_PATHWAYS_FIXTURE = [
    {
        "discipline_name": "History of science and technology / early modern science & knowledge practices",
        "fit_strength": "strong",
        "reasoning": "The article treats rabbit breeding and warren management as knowledge practices through which early modern categories of fertility, control, and order were articulated.",
    },
    {
        "discipline_name": "Science and Technology Studies (STS)",
        "fit_strength": "strong",
        "reasoning": "The article already conceptualizes animal fertility management as a site of socio-material ordering and governance of life.",
    },
    {
        "discipline_name": "Historical anthropology / anthropology of early modern domesticity",
        "fit_strength": "strong",
        "reasoning": "The framing of fertility management as embedded in moral, domestic, and bodily regimes strongly resonates with historical anthropology.",
    },
    {
        "discipline_name": "Animal studies / critical animal studies",
        "fit_strength": "strong",
        "reasoning": "The article directly engages animal reproduction, control, and human authority over nonhuman life, central concerns in animal studies.",
    },
    {
        "discipline_name": "Early modern economic history / agrarian history",
        "fit_strength": "medium",
        "reasoning": "Rabbit husbandry is economically grounded but the article is not primarily economic in analysis.",
    },
]


class TestRabbitFragmentRegression(unittest.TestCase):
    def test_rabbit_human_view_is_author_readable(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        # Topic markers per task spec §I
        low = md.lower()
        self.assertTrue(
            "rabbit" in low or "кролик" in low,
            "rabbit / кролик topic must be visible",
        )
        self.assertTrue(
            "early modern" in low or "xvi" in low or "раннемодерн" in low or "archival" in low or "англии" in low,
            "early-modern / XVI century marker must be visible",
        )
        self.assertTrue(
            "breeding" in low or "fertility" in low or "разведен" in low or "плодов" in low,
            "breeding/fertility marker must be visible",
        )

    def test_rabbit_pathways_render_multiple_trajectories(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        # All 5 pathways visible
        self.assertIn("History of science", md)
        self.assertIn("STS", md)
        self.assertIn("Historical anthropology", md)
        self.assertIn("Animal studies", md)
        self.assertIn("economic history", md)

    def test_rabbit_does_not_collapse_into_sexuality(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        # No sexuality / gender axis should appear unless the fixture had it.
        # The fixture deliberately does not. Card MUST NOT inject it.
        low = md.lower()
        self.assertNotIn("history of sexuality", low)
        self.assertNotIn("sexuality studies", low)
        self.assertNotIn("queer theory", low)

    def test_rabbit_unknowns_visible(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        self.assertIn("Что система не знает", md)
        self.assertTrue(
            "bibliography" in md.lower() or "источник" in md.lower()
            or "manuscript" in md.lower(),
            "unknowns section should mention bibliography or manuscript gap",
        )

    def test_rabbit_preliminary_warning_visible(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        self.assertIn("предварительная", md)

    def test_rabbit_no_submission_recommendation(self):
        md = article_model_human_view(
            _RABBIT_ARTICLE_FIXTURE, pathways=_RABBIT_PATHWAYS_FIXTURE,
        )
        _assert_no_recommendation(md)


# ---------------------------------------------------------------------------
# Venue / VPKG human view
# ---------------------------------------------------------------------------

class TestVenueHumanViewShape(unittest.TestCase):
    def test_minimal_venue_renders_with_all_sections(self):
        v = {
            "venue_profile_package_id": "vpkg_x",
            "canonical_name": "Foucault Studies",
            "publisher": "University of Copenhagen",
            "languages": ["en"],
            "venue_type": "journal",
            "issns": ["1832-5203"],
            "evidence_status": "operator_seed_canonical",
            "completeness": {
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
                "FormalSubmissionProfile": "partial",
            },
            "discovery_sources": ["OPERATOR_SEED_CANONICAL"],
            "editorial_board_cloud_id": "ebc_xyz",
            "homepage_url": "https://rauli.cbs.dk/index.php/foucault-studies",
            "unknowns": [
                "VAK status not verified",
            ],
        }
        md = venue_human_view(v)
        for section in (
            "Что это за журнал",
            "Что журнал сам о себе говорит",
            "Что видно по опубликованному корпусу",
            "Формальные требования",
            "Редколлегия",
            "Какой тип текстов журнал, вероятно, распознаёт",
            "Что система не знает",
            "Вопросы пользователю",
            "Что можно поправить",
        ):
            self.assertIn(section, md, f"missing required venue section: {section}")
        # Identity visible
        self.assertIn("Foucault Studies", md)
        self.assertIn("University of Copenhagen", md)
        # No JSON
        self.assertFalse(md.lstrip().startswith("{"))
        _assert_no_recommendation(md)

    def test_missing_board_emits_honest_status_no_speculation(self):
        v = {
            "venue_profile_package_id": "vpkg_x",
            "canonical_name": "Philosophy & Technology",
            "publisher": "Springer",
            "completeness": {
                "EditorialBoardCloud": "missing",
            },
        }
        md = venue_human_view(v)
        self.assertIn("Редколлегия", md)
        self.assertIn("не собрана", md.lower().replace("ё","е") + md)
        # No speculation about editor preferences
        low = md.lower()
        self.assertNotIn("editor tastes", low)
        self.assertNotIn("the editors prefer", low)

    def test_field_anchors_on_venue(self):
        v = {"venue_profile_package_id": "x", "canonical_name": "V"}
        md = venue_human_view(v)
        self.assertIn("<!-- field: venue_model.identity -->", md)
        self.assertIn("<!-- field: venue_model.formal_submission_profile -->", md)
        self.assertIn("<!-- field: venue_model.editorial_board_cloud -->", md)


# ---------------------------------------------------------------------------
# Frozen top-5 Mavrinsky venue (per v2.3 golden freeze)
# ---------------------------------------------------------------------------

class TestFrozenTop5VenueRegression(unittest.TestCase):
    def test_foucault_studies_renders_human_readable(self):
        v = {
            "venue_profile_package_id": "vpkg_fs",
            "canonical_name": "Foucault Studies",
            "publisher": "University of Copenhagen",
            "languages": ["en"],
            "venue_type": "journal",
            "issns": ["1832-5203"],
            "evidence_status": "operator_seed_canonical",
            "openalex_source_id": "S2735408488",
            "homepage_url": "https://rauli.cbs.dk/index.php/foucault-studies",
            "completeness": {
                "VenueIdentity": "partial",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
                "FormalSubmissionProfile": "partial",
            },
            "editorial_board_cloud_id": "ebc_8b866129d208",
            "discovery_sources": ["OPERATOR_SEED_CANONICAL"],
        }
        md = venue_human_view(v)
        # Author-facing identity sentence
        self.assertIn("Foucault Studies", md)
        self.assertIn("University of Copenhagen", md)
        # Board section reflects extracted state honestly
        self.assertIn("Редколлегия", md)
        self.assertIn("ebc_8b866129d208", md)
        # Corpus present
        self.assertIn("Корпус-хулл собран", md)
        # Inference marker on derived-signals language
        self.assertIn("inference", md.lower())
        # No submission recommendation
        _assert_no_recommendation(md)


if __name__ == "__main__":
    unittest.main()
