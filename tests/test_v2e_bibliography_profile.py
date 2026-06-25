"""V2-E BibliographyProfile builder tests + chain integration tests."""

from __future__ import annotations

import unittest

from kairoskopion.schema import (
    ArticleModel,
    FitAssessment,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.services.bibliography_profile import (
    STATUS_NOT_FOUND,
    STATUS_PARSED_STRUCTURAL,
    STATUS_PRESENT_UNPARSED,
    STATUS_UNKNOWN,
    VERIFY_BLOCKED_MISSING,
    VERIFY_IDENTIFIERS_DETECTED,
    VERIFY_STRUCTURAL_ONLY,
    build_minimal_bibliography_profile,
)
from kairoskopion.services.citation_plan_minimal import (
    STATUS_BLOCKED_MISSING_EVIDENCE,
    STATUS_NEEDS_BIBLIOGRAPHY,
    STATUS_VERIFICATION_TASKS_READY,
    build_minimal_citation_plan,
)
from kairoskopion.services.compliance_checklist_minimal import (
    ITEM_MISSING,
    ITEM_NEEDS_USER_INPUT,
    ITEM_SATISFIED,
    ITEM_UNKNOWN_NOT_VERIFIED,
    build_minimal_compliance_checklist,
)
from kairoskopion.services.submission_pack_minimal import (
    READY_FOR_MANUAL_SUBMISSION,
    READY_NEEDS_REFERENCE_VERIFICATION,
    build_minimal_submission_pack,
)


REFS_ENGLISH = """
# Some article body...
Lots of theoretical discussion.

## References

1. Ihde, D. (1990). Technology and the Lifeworld. Indiana University Press. https://doi.org/10.1234/example
2. Verbeek, P-P. (2005). What Things Do. Penn State University Press.
3. Heidegger, M. (1977). The Question Concerning Technology. Harper.
4. Latour, B. 2005. Reassembling the Social. Oxford. doi:10.1093/example
5. Smith, J. 2020. https://example.org/paper
"""

REFS_RUSSIAN = """
# Статья...
Текст статьи.

## Список литературы

1. Энгельмейер П. К. 1912. Философия техники. Москва.
2. Кутырев В. А. 1994. Естественное и искусственное: борьба миров. Нижний Новгород.
3. Хайдеггер М. 1993. Время и бытие. Москва.
"""

NO_REFS = """
# Theoretical paper

This article is a conceptual essay with no bibliography section
provided to the parser.
"""


def _venue(scope: str = "Journal scope present, references expected.",
           types: list[str] | None = None) -> VenueModel:
    return VenueModel(
        canonical_name="Test Journal",
        venue_type="journal",
        scope_summary=scope,
        article_types_supported=types or ["theoretical_essay"],
    )


def _fit(axes_map: dict[str, str] | None = None) -> FitAssessment:
    return FitAssessment(
        axes=[
            {"axis": k, "value": v, "evidence_refs": [],
             "confidence": "low", "notes": "", "unknowns": []}
            for k, v in (axes_map or {"topic": "medium"}).items()
        ],
        overall_label="possible",
    )


def _article(refs=None) -> ArticleModel:
    return ArticleModel(
        title_current="X",
        abstract_current="A",
        language="en",
        genre_current="theoretical_essay",
        reference_count=refs,
    )


# ----------------- BibliographyProfile builder -----------------

class TestBibBuilder(unittest.TestCase):
    def test_raw_text_none_status_unknown(self):
        bp = build_minimal_bibliography_profile(None)
        self.assertEqual(bp.status, STATUS_UNKNOWN)
        self.assertEqual(bp.verification_status, VERIFY_BLOCKED_MISSING)
        self.assertFalse(bp.bibliography_section_detected)
        self.assertFalse(bp.bibliography_text_available)
        self.assertEqual(bp.reference_count, 0)
        self.assertTrue(bp.verification_tasks)
        self.assertEqual(bp.references, [])

    def test_no_heading_status_not_found(self):
        bp = build_minimal_bibliography_profile(NO_REFS)
        self.assertEqual(bp.status, STATUS_NOT_FOUND)
        self.assertTrue(bp.bibliography_text_available)
        self.assertFalse(bp.bibliography_section_detected)
        self.assertEqual(bp.reference_count, 0)

    def test_english_refs_parsed(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        self.assertEqual(bp.status, STATUS_PARSED_STRUCTURAL)
        self.assertTrue(bp.bibliography_section_detected)
        self.assertGreaterEqual(bp.reference_count, 5)
        self.assertEqual(bp.reference_count, len(bp.references))
        # DOI detected on at least 2 entries
        self.assertGreaterEqual(bp.doi_count, 2)
        # URL detected on at least 1 entry
        self.assertGreaterEqual(bp.url_count, 1)
        # Year stats populated
        self.assertEqual(bp.year_min, 1977)
        self.assertEqual(bp.year_max, 2020)
        # verification status reflects identifier presence
        self.assertEqual(
            bp.verification_status, VERIFY_IDENTIFIERS_DETECTED,
        )

    def test_russian_refs_parsed(self):
        bp = build_minimal_bibliography_profile(REFS_RUSSIAN)
        self.assertEqual(bp.status, STATUS_PARSED_STRUCTURAL)
        self.assertEqual(bp.reference_count, 3)
        self.assertEqual(bp.doi_count, 0)
        # Russian no DOIs → verification status structural_only
        self.assertEqual(bp.verification_status, VERIFY_STRUCTURAL_ONLY)
        years = sorted(int(y) for y in bp.year_distribution.keys())
        self.assertIn(1912, years)
        self.assertIn(1994, years)

    def test_no_invented_titles_or_authors(self):
        """Parser must not fill in title_text / authors_text from regex."""
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        for ref in bp.references:
            self.assertIsNone(ref["title_text"])
            self.assertIsNone(ref["authors_text"])
            self.assertIsNone(ref["venue_text"])

    def test_no_doi_invented(self):
        """For refs without an actual DOI substring, doi must be None."""
        bp = build_minimal_bibliography_profile(REFS_RUSSIAN)
        for ref in bp.references:
            self.assertIsNone(ref["doi"])

    def test_bold_wrapped_heading_detected(self):
        """Heading with **bold** markers must be detected (live article bug)."""
        text = (
            "Body text.\n\n"
            "## **Список литературы**\n\n"
            "###\n\n"
            "1. Бергсон А. Материя и память. М., 1992.\n"
            "2. Ihde D. Technology and the Lifeworld. 1990.\n"
            "3. Verbeek P.-P. What Things Do. 2005.\n"
        )
        bp = build_minimal_bibliography_profile(text)
        self.assertTrue(bp.bibliography_section_detected)
        self.assertEqual(bp.status, STATUS_PARSED_STRUCTURAL)
        self.assertGreaterEqual(bp.reference_count, 3)

    def test_italic_wrapped_heading_detected(self):
        """Heading with *italic* markers must also be detected."""
        text = (
            "Body.\n\n"
            "## *References*\n\n"
            "1. Foo, A. (2020). Some important research paper. Journal of X, 5(2), 100-120.\n"
            "2. Baz, B. (2021). Another significant contribution. Journal of Y, 3(1), 50-80.\n"
        )
        bp = build_minimal_bibliography_profile(text)
        self.assertTrue(bp.bibliography_section_detected)
        self.assertGreaterEqual(bp.reference_count, 2)

    def test_live_article_format_produces_references(self):
        """Simulate the exact heading format from the live article."""
        text = (
            "Текст статьи.\n\n"
            "## **Список литературы**\n\n"
            "### \n\n"
            "1. Бергсон А. Материя и память / А. Бергсон; пер. с фр. — М. : ИТДГК «Гнозис», 1992. — 271 с.\n"
            "2. Бергсон А. Творческая эволюция / А. Бергсон; пер. с фр. — М., 1998. — 384 с.\n"
            "3. Мол - Множественные тела\n"
            "3. Berntsen J. Robust and Generalizable Embryo Selection // PLOS ONE. — 2022. — DOI: 10.1371/journal.pone.0262661.\n"
            "5. Dimitriadis I. Artificial Intelligence in the Embryology Laboratory // Reproductive BioMedicine Online. — 2022. — Vol. 44.\n"
            "6. Ihde D. Technology and the Lifeworld / D. Ihde. — Bloomington : Indiana University Press, 1990. — 226 p.\n"
            "7. Ihde D. Postphenomenology and Technoscience / D. Ihde. — Albany : SUNY Press, 2009. — 135 p.\n"
            "8. Kragh M. F. Embryo Selection with Artificial Intelligence // JARG. — 2021. — DOI: 10.1007/s10815-021-02254-6.\n"
            "9. Liu Y. AI for Earth // Proceedings of ACM SIGKDD. — 2019. — URL: https://arxiv.org/pdf/1908.07517.\n"
            "10. Mol A. Ontological Politics // The Sociological Review. — 1999. — DOI: 10.1111/j.1467-954X.1999.tb03483.x.\n"
            "11. Mykhailov D. Back to the Technologies Themselves // Phenomenology. — 2023. — DOI: 10.1007/s11097-023-09905-2.\n"
            "13. Pavanini M. Postphenomenology and Human Constitutive Technicity // JHTR. — 2024.\n"
            "14. Rasmussen J. H. Sound Evidence for Biodiversity // Science. — 2024. — DOI: 10.1126/science.adh2716.\n"
            "15. Rosenberger R. Postphenomenological Investigations / R. Rosenberger. — 2015. — 265 p\n"
            "16. Stowell D. Computational Bioacoustics // PeerJ. — 2022. — DOI: 10.7717/peerj.13152.\n"
            "17. Tahar M. Bergson's Vitalisms // Parrhesia. — 2022.\n"
            "18. Verbeek P.-P. What Things Do / P.-P. Verbeek. — 2005. — 249 p.\n"
            "19. Verbeek P.-P. Moralizing Technology / P.-P. Verbeek. — 2011. — 198 p.\n"
            "20. Wahabzada M. Plant Phenotyping // Scientific Reports. — 2016. — DOI: 10.1038/srep22482.\n"
        )
        bp = build_minimal_bibliography_profile(text)
        self.assertTrue(bp.bibliography_section_detected)
        self.assertEqual(bp.status, STATUS_PARSED_STRUCTURAL)
        self.assertGreaterEqual(bp.reference_count, 10)
        self.assertGreaterEqual(bp.doi_count, 5)
        self.assertGreaterEqual(bp.url_count, 1)


class TestCitationPlanBibAware(unittest.TestCase):
    def test_no_bibliography_marks_needs_bibliography(self):
        bp = build_minimal_bibliography_profile(NO_REFS)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit(),
            None, None, None,
            bibliography_profile=bp,
        )
        self.assertEqual(cp.status, STATUS_NEEDS_BIBLIOGRAPHY)
        self.assertEqual(
            cp.current_bibliography_status,
            f"bib_profile:{bp.status}:{bp.verification_status}",
        )

    def test_unknown_raw_marks_blocked_missing_evidence(self):
        bp = build_minimal_bibliography_profile(None)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit(),
            None, None, None,
            bibliography_profile=bp,
        )
        self.assertEqual(cp.status, STATUS_BLOCKED_MISSING_EVIDENCE)

    def test_parsed_marks_verification_tasks_ready(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit(),
            None, None, None,
            bibliography_profile=bp,
        )
        self.assertEqual(cp.status, STATUS_VERIFICATION_TASKS_READY)
        self.assertIn("bibliography_profile", cp.created_from)
        self.assertTrue(cp.verification_tasks)

    def test_no_fake_references_in_citation_plan(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        cp = build_minimal_citation_plan(
            _article(), _venue(), _fit({"discipline": "weak"}),
            None, None, None,
            bibliography_profile=bp,
        )
        import re
        flat = " ".join(
            cp.recommended_reference_search_tasks
            + cp.verification_tasks
            + cp.missing_bridge_categories
        )
        # No invented DOIs in citation plan output
        self.assertIsNone(re.search(r"10\.\d{4,}/\S+", flat),
                          "citation plan must not echo DOIs as if invented")


class TestComplianceBibAware(unittest.TestCase):
    def test_missing_bibliography_marks_references_missing(self):
        bp = build_minimal_bibliography_profile(NO_REFS)
        cc = build_minimal_compliance_checklist(
            _article(), _venue(), None, None,
            bibliography_profile=bp,
        )
        refs = [i for i in cc.checklist_items if i["category"] == "references"][0]
        self.assertEqual(refs["status"], ITEM_MISSING)

    def test_unknown_bibliography_marks_references_unknown(self):
        bp = build_minimal_bibliography_profile(None)
        cc = build_minimal_compliance_checklist(
            _article(), _venue(), None, None,
            bibliography_profile=bp,
        )
        refs = [i for i in cc.checklist_items if i["category"] == "references"][0]
        self.assertEqual(refs["status"], ITEM_UNKNOWN_NOT_VERIFIED)

    def test_structural_parse_needs_verification_not_satisfied(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        cc = build_minimal_compliance_checklist(
            _article(), _venue(), None, None,
            bibliography_profile=bp,
        )
        refs = [i for i in cc.checklist_items if i["category"] == "references"][0]
        # Must NOT be satisfied — external verification not performed
        self.assertNotEqual(refs["status"], ITEM_SATISFIED)
        self.assertEqual(refs["status"], ITEM_NEEDS_USER_INPUT)


class TestSubmissionPackBibAware(unittest.TestCase):
    def _build(self, bp):
        a = _article(); v = _venue(); f = _fit({"topic": "medium"})
        s = SubmissionScenario()
        cp = build_minimal_citation_plan(a, v, f, None, None, None, bibliography_profile=bp)
        cc = build_minimal_compliance_checklist(a, v, s, None, bibliography_profile=bp)
        return build_minimal_submission_pack(
            a, v, s, f, None, None, cp, cc,
            bibliography_profile=bp,
        )

    def test_not_ready_when_bibliography_missing(self):
        bp = build_minimal_bibliography_profile(NO_REFS)
        pack = self._build(bp)
        self.assertNotEqual(pack.ready_status, READY_FOR_MANUAL_SUBMISSION)
        self.assertEqual(pack.ready_status, READY_NEEDS_REFERENCE_VERIFICATION)
        # bibliography action in next_actions
        joined = " ".join(pack.next_actions).lower()
        self.assertTrue(
            "bibliography" in joined or "reference" in joined,
            "submission pack must mention bibliography/reference action",
        )

    def test_needs_reference_verification_when_structural_only(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        pack = self._build(bp)
        self.assertEqual(pack.ready_status, READY_NEEDS_REFERENCE_VERIFICATION)
        self.assertIn("bibliography_profile", pack.depends_on)

    def test_not_ready_when_bibliography_unknown(self):
        bp = build_minimal_bibliography_profile(None)
        pack = self._build(bp)
        self.assertNotEqual(pack.ready_status, READY_FOR_MANUAL_SUBMISSION)


class TestRoundTrip(unittest.TestCase):
    def test_bibliography_profile_round_trip(self):
        from kairoskopion.schema import BibliographyProfile
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        d = bp.to_dict()
        bp2 = BibliographyProfile.from_dict(d)
        self.assertEqual(bp2.status, bp.status)
        self.assertEqual(bp2.reference_count, bp.reference_count)
        self.assertEqual(bp2.doi_count, bp.doi_count)
        self.assertEqual(bp2.verification_status, bp.verification_status)

    def test_no_raw_or_credential_keys(self):
        bp = build_minimal_bibliography_profile(REFS_ENGLISH)
        d = bp.to_dict()
        for k in d.keys():
            kl = k.lower()
            self.assertNotIn("api_key", kl)
            self.assertNotIn("secret", kl)
            self.assertNotIn("traceback", kl)


if __name__ == "__main__":
    unittest.main()
