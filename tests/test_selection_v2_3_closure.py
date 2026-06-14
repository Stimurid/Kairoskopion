"""v2.3 closure tests: board completeness threshold + Springer fallback."""

from __future__ import annotations

import pytest

from kairoskopion.schema import VenueProfilePackage
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry
from kairoskopion.services.venue_topcand_deeplite import (
    board_completeness_from_status,
    enrich_board_for_vpkg,
    enrich_board_with_springer_fallback,
    springer_board_url_candidates,
)


# ---------------------------------------------------------------------------
# C. Board completeness threshold rule
# ---------------------------------------------------------------------------

class TestBoardCompletenessThreshold:
    def test_9_member_official_extraction_is_present(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 9,
        ) == "present"

    def test_18_member_official_extraction_is_present(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 18,
        ) == "present"

    def test_25_member_present(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 25,
        ) == "present"

    def test_30_member_present(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 30,
        ) == "present"

    def test_5_member_partial(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 5,
        ) == "partial"

    def test_1_member_partial(self):
        assert board_completeness_from_status(
            "EXTRACTED_FROM_OFFICIAL_HTML", 1,
        ) == "partial"

    def test_unverified_with_9_members_still_present(self):
        # Threshold is sample-count-based; verification status doesn't gate it.
        assert board_completeness_from_status(
            "EXTRACTED_UNVERIFIED", 9,
        ) == "present"

    def test_zero_members_failed_extraction_is_missing(self):
        for status in ("INACCESSIBLE", "JS_ONLY",
                        "NOT_FOUND_AFTER_SEARCH", "UNKNOWN"):
            assert board_completeness_from_status(status, 0) == "missing", \
                f"status={status} should map to missing"

    def test_empty_extraction_does_not_become_present(self):
        # Even with status that says extraction happened: 0 members is not present.
        for n in (0,):
            for status in ("EXTRACTED_FROM_OFFICIAL_HTML",
                            "EXTRACTED_UNVERIFIED"):
                # n=0 + extracted statuses: per the rule, no positive
                # members means we don't have a real board to claim.
                # The rule maps to missing.
                assert board_completeness_from_status(status, n) == "missing"


class TestThresholdMergeSafety:
    def test_empty_failed_extraction_does_not_erase_present_board(
        self, tmp_path
    ):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        # Existing: a present board with 18 members already attached
        reg.upsert(VenueProfilePackage(
            canonical_name="V",
            issns=["9999-9999"],
            editorial_board_cloud_id="ebc_keep_18",
            completeness={"EditorialBoardCloud": "present"},
        ))
        # Failed re-extraction (e.g., publisher rolled their site over)
        empty_completeness = board_completeness_from_status(
            "INACCESSIBLE", 0,
        )
        assert empty_completeness == "missing"
        # Caller emits a patch with NO id and completeness=missing
        reg.upsert(VenueProfilePackage(
            canonical_name="V",
            issns=["9999-9999"],
            completeness={"EditorialBoardCloud": empty_completeness},
        ))
        # Verify B2 protection holds: no downgrade, id intact
        v = reg.list_all()[0]
        assert v.editorial_board_cloud_id == "ebc_keep_18"
        assert v.completeness["EditorialBoardCloud"] == "present"


# ---------------------------------------------------------------------------
# B. Springer fallback URL pattern derivation
# ---------------------------------------------------------------------------

class TestSpringerFallbackUrlPatterns:
    def test_extracts_journal_id_from_springer_homepage(self):
        urls = springer_board_url_candidates(
            "https://www.springer.com/journal/13347"
        )
        assert len(urls) == 3
        assert urls[0] == "https://www.springer.com/journal/13347/editors"
        assert "editorial-board" in urls[1]
        assert "editorial-team" in urls[2]

    def test_extracts_with_trailing_slash(self):
        urls = springer_board_url_candidates(
            "https://www.springer.com/journal/13347/"
        )
        assert len(urls) == 3

    def test_non_springer_url_returns_empty(self):
        for u in (
            "https://www.cambridge.org/core/journals/memory-mind-and-media",
            "https://rauli.cbs.dk/index.php/foucault-studies",
            "https://example.org/",
            "",
            None,
        ):
            assert springer_board_url_candidates(u) == []

    def test_only_journal_path_supported(self):
        # We intentionally only match /journal/ — /article/ is per-article
        # and not a journal identifier.
        urls = springer_board_url_candidates(
            "https://www.springer.com/article/12345"
        )
        assert urls == []


class TestSpringerFallbackOutcomes:
    def test_no_pattern_match_returns_stable_failure(self):
        vpkg = VenueProfilePackage(
            canonical_name="X",
            homepage_url="https://example.org/",
        )
        out = enrich_board_with_springer_fallback(vpkg)
        assert out["extraction_status"] == \
            "SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND"
        assert out["candidates_tried"] == []

    def test_all_urls_fail_returns_stable_failure_tag(self, monkeypatch):
        """When every Springer candidate URL produces no extractable board."""
        import kairoskopion.services.venue_topcand_deeplite as mod

        def _fake_enrich(vpkg, board_page_url):
            return {
                "vpkg_id": vpkg.venue_profile_package_id,
                "canonical_name": vpkg.canonical_name,
                "board_page_url": board_page_url,
                "extraction_status": "INACCESSIBLE",
                "editorial_board_cloud": None,
                "members_sampled": 0,
                "notes": [],
            }
        monkeypatch.setattr(mod, "enrich_board_for_vpkg", _fake_enrich)

        vpkg = VenueProfilePackage(
            canonical_name="P&T",
            homepage_url="https://www.springer.com/journal/13347",
        )
        out = enrich_board_with_springer_fallback(vpkg)
        assert out["extraction_status"] == \
            "SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND"
        # Tried all 3 candidates honestly
        assert len(out["per_url_status"]) == 3
        # No board cloud invented
        assert out["editorial_board_cloud"] is None
        assert out["members_sampled"] == 0

    def test_first_success_wins(self, monkeypatch):
        import kairoskopion.services.venue_topcand_deeplite as mod
        calls = []
        def _fake_enrich(vpkg, board_page_url):
            calls.append(board_page_url)
            members = 12 if "editorial-board" in board_page_url else 0
            return {
                "vpkg_id": vpkg.venue_profile_package_id,
                "canonical_name": vpkg.canonical_name,
                "board_page_url": board_page_url,
                "extraction_status": (
                    "EXTRACTED_FROM_OFFICIAL_HTML" if members else "INACCESSIBLE"
                ),
                "editorial_board_cloud": (
                    {"members": [{}] * members} if members else None
                ),
                "members_sampled": members,
                "notes": [],
            }
        monkeypatch.setattr(mod, "enrich_board_for_vpkg", _fake_enrich)

        vpkg = VenueProfilePackage(
            canonical_name="P&T",
            homepage_url="https://www.springer.com/journal/13347",
        )
        out = enrich_board_with_springer_fallback(vpkg)
        assert out["extraction_status"] == "EXTRACTED_FROM_OFFICIAL_HTML"
        assert out["members_sampled"] == 12
        assert "editorial-board" in out["board_page_url"]
        # Stopped at second URL — third never attempted
        assert len(calls) == 2
