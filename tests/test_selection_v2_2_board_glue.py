"""Tests for the v2.2 EditorialBoardCloud glue pass.

Covers:
  - enrich_board_for_vpkg returns honest extraction_status per failure mode;
  - safe upsert: empty board extraction does NOT erase existing board cloud;
  - safe upsert: partial board extraction merges without damaging corpus
    or formal profile;
  - top-candidate VPKG can carry identity + corpus + formal profile +
    board cloud simultaneously;
  - non-empty board cloud survives unrelated re-enrichment.
"""

from __future__ import annotations

import pytest

from kairoskopion.schema import VenueProfilePackage
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry
from kairoskopion.services.venue_topcand_deeplite import (
    enrich_board_for_vpkg,
)


# ---------------------------------------------------------------------------
# enrich_board_for_vpkg — extraction_status taxonomy
# ---------------------------------------------------------------------------

class TestBoardExtractionStatusTaxonomy:
    def test_no_url_returns_not_found(self):
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url=None)
        assert out["extraction_status"] == "NOT_FOUND_AFTER_SEARCH"
        assert out["editorial_board_cloud"] is None
        assert out["members_sampled"] == 0

    def test_empty_url_returns_not_found(self):
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url="")
        assert out["extraction_status"] == "NOT_FOUND_AFTER_SEARCH"

    def test_inaccessible_url(self, monkeypatch):
        """Adapter returns cloud with 'fetch failed' in unknowns."""
        # Patch build_editorial_board_cloud to return such a result
        import kairoskopion.services.venue_topcand_deeplite as mod

        class _FakeCloud:
            unknowns = ["editorial board page fetch failed: http_403"]
            warnings = []
            members = []
            members_sampled = 0
            def to_dict(self):
                return {"unknowns": list(self.unknowns)}

        def _fake_build(**kw):
            return _FakeCloud()

        monkeypatch.setattr(
            "kairoskopion.adapters.venue.editorial_board.build_editorial_board_cloud",
            _fake_build,
        )
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url="https://x.example/")
        assert out["extraction_status"] == "INACCESSIBLE"
        assert out["members_sampled"] == 0

    def test_js_only(self, monkeypatch):
        class _FakeCloud:
            unknowns = ["page text shorter than 200 chars after HTML strip"]
            warnings = ["JS-only or very thin HTML board page"]
            members = []
            members_sampled = 0
            def to_dict(self):
                return {"warnings": list(self.warnings)}

        monkeypatch.setattr(
            "kairoskopion.adapters.venue.editorial_board.build_editorial_board_cloud",
            lambda **kw: _FakeCloud(),
        )
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url="https://x.example/")
        assert out["extraction_status"] == "JS_ONLY"

    def test_unverified_when_no_openalex_match(self, monkeypatch):
        class _FakeCloud:
            unknowns = []
            warnings = []
            members = [
                {"full_name": "Jane Doe", "evidence_status": "external_claim"},
                {"full_name": "John Roe", "evidence_status": "external_claim"},
            ]
            members_sampled = 2
            def to_dict(self):
                return {"members": list(self.members)}

        monkeypatch.setattr(
            "kairoskopion.adapters.venue.editorial_board.build_editorial_board_cloud",
            lambda **kw: _FakeCloud(),
        )
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url="https://x.example/")
        assert out["extraction_status"] == "EXTRACTED_UNVERIFIED"
        assert out["members_sampled"] == 2

    def test_extracted_from_official_html_when_openalex_match(self, monkeypatch):
        class _FakeCloud:
            unknowns = []
            warnings = []
            members = [
                {"full_name": "Jane Doe",
                 "evidence_status": "metadata_api_openalex"},
            ]
            members_sampled = 1
            def to_dict(self):
                return {"members": list(self.members)}

        monkeypatch.setattr(
            "kairoskopion.adapters.venue.editorial_board.build_editorial_board_cloud",
            lambda **kw: _FakeCloud(),
        )
        vpkg = VenueProfilePackage(canonical_name="X")
        out = enrich_board_for_vpkg(vpkg, board_page_url="https://x.example/")
        assert out["extraction_status"] == "EXTRACTED_FROM_OFFICIAL_HTML"


# ---------------------------------------------------------------------------
# Safe merge: empty board extraction must not erase existing board
# ---------------------------------------------------------------------------

class TestBoardMergeSafety:
    def test_empty_board_extraction_does_not_erase_existing(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))

        # Seed: full VPKG with identity + corpus + formal + board
        existing = VenueProfilePackage(
            canonical_name="Top Venue",
            issns=["1234-5678"],
            languages=["en"],
            openalex_source_id="S99999",
            homepage_url="https://example.org/",
            published_corpus_hull_id="hull_X",
            editorial_board_cloud_id="ebc_X",
            citation_expectation_profile_id="cep_X",
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "partial",
                "FormalSubmissionProfile": "partial",
                "CitationExpectationProfile": "partial",
            },
        )
        reg.upsert(existing)

        # Empty board update: caller decides NOT to attach a new cloud id,
        # but mistakenly emits a VPKG that doesn't carry the prior id and
        # has board=missing in completeness. The upsert must protect it.
        empty_update = VenueProfilePackage(
            canonical_name="Top Venue",
            issns=["1234-5678"],
            languages=["en"],
            openalex_source_id="S99999",
            homepage_url="https://example.org/",
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "missing",  # accidental downgrade
                "FormalSubmissionProfile": "partial",
            },
        )
        reg.upsert(empty_update)

        # Reload and verify nothing was lost.
        reg2 = VenueProfileRegistry(storage_root=str(tmp_path))
        v = reg2.list_all()[0]
        assert v.editorial_board_cloud_id == "ebc_X"
        assert v.completeness["EditorialBoardCloud"] == "partial"
        # Other subobjects also intact
        assert v.published_corpus_hull_id == "hull_X"
        assert v.completeness["PublishedCorpusHull"] == "present"
        assert v.citation_expectation_profile_id == "cep_X"

    def test_partial_board_extraction_merges_without_damaging_corpus(
        self, tmp_path
    ):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        existing = VenueProfilePackage(
            canonical_name="Top Venue",
            issns=["1234-5678"],
            openalex_source_id="S99999",
            published_corpus_hull_id="hull_X",
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "missing",
            },
        )
        reg.upsert(existing)
        partial_board = VenueProfilePackage(
            canonical_name="Top Venue",
            issns=["1234-5678"],
            openalex_source_id="S99999",
            editorial_board_cloud_id="ebc_NEW",
            completeness={
                "EditorialBoardCloud": "partial",
            },
        )
        reg.upsert(partial_board)
        v = reg.list_all()[0]
        # Board added
        assert v.editorial_board_cloud_id == "ebc_NEW"
        assert v.completeness["EditorialBoardCloud"] == "partial"
        # Corpus survived
        assert v.published_corpus_hull_id == "hull_X"
        assert v.completeness["PublishedCorpusHull"] == "present"

    def test_full_stack_top_candidate(self, tmp_path):
        """A top-candidate VPKG carries identity + corpus + formal + board
        simultaneously after a sequence of safe upserts.
        """
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        # Step 1: identity + corpus
        reg.upsert(VenueProfilePackage(
            canonical_name="Top",
            issns=["1111-2222"],
            openalex_source_id="S1",
            published_corpus_hull_id="hull_1",
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
            },
        ))
        # Step 2: add formal profile from deeplite extractor
        reg.upsert(VenueProfilePackage(
            canonical_name="Top",
            issns=["1111-2222"],
            openalex_source_id="S1",
            completeness={"FormalSubmissionProfile": "partial"},
        ))
        # Step 3: add board cloud from glue
        reg.upsert(VenueProfilePackage(
            canonical_name="Top",
            issns=["1111-2222"],
            openalex_source_id="S1",
            editorial_board_cloud_id="ebc_1",
            completeness={"EditorialBoardCloud": "partial"},
        ))
        # Reload — verify ALL four are present simultaneously
        reg2 = VenueProfileRegistry(storage_root=str(tmp_path))
        v = reg2.list_all()[0]
        assert v.openalex_source_id == "S1"
        assert v.published_corpus_hull_id == "hull_1"
        assert v.editorial_board_cloud_id == "ebc_1"
        c = v.completeness
        assert c["VenueIdentity"] == "present"
        assert c["PublishedCorpusHull"] == "present"
        assert c["FormalSubmissionProfile"] == "partial"
        assert c["EditorialBoardCloud"] == "partial"

    def test_non_empty_board_survives_unrelated_reenrichment(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        # Existing: full board
        reg.upsert(VenueProfilePackage(
            canonical_name="Top",
            issns=["3333-4444"],
            editorial_board_cloud_id="ebc_KEEP",
            completeness={"EditorialBoardCloud": "present"},
        ))
        # Unrelated enrichment: just touches identity, no board info
        reg.upsert(VenueProfilePackage(
            canonical_name="Top",
            issns=["3333-4444"],
            openalex_source_id="S_new",
            homepage_url="https://x.example/",
            completeness={"VenueIdentity": "present"},
        ))
        v = reg.list_all()[0]
        assert v.editorial_board_cloud_id == "ebc_KEEP"
        assert v.completeness["EditorialBoardCloud"] == "present"
        assert v.openalex_source_id == "S_new"
        assert v.homepage_url == "https://x.example/"
