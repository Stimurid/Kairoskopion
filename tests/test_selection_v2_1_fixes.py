"""Regression tests for v2.1 stabilization fixes.

B1: bucket-first ranker
B2: completeness merge must not downgrade existing partial/present subobjects
"""

from __future__ import annotations

import pytest

from kairoskopion.schema import VenueProfilePackage
from kairoskopion.services.mavrinsky_venue_selection import (
    rank_top_candidates,
    select_shortlist,
)
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry


# ---------------------------------------------------------------------------
# B1: bucket-first ranker
# ---------------------------------------------------------------------------

def _mk_fit(*, vid, name, bucket_signals, confidence="medium",
            has_corpus=True, has_formal=False, sv="medium",
            fcr="strong", topic="medium", rewrite="strong",
            argument_form="medium", method="medium",
            citation_ecology="medium"):
    """Build a minimal fit dict + matching bucket entry."""
    def _ax(v):
        return {"value": v, "evidence": "test", "note": ""}

    axes = {
        "topic_fit": _ax(topic),
        "disciplinary_fit": _ax("medium"),
        "genre_fit": _ax("medium"),
        "argument_form_fit": _ax(argument_form),
        "method_fit": _ax(method),
        "novelty_mode_fit": _ax("medium"),
        "citation_ecology_fit": _ax(citation_ecology),
        "language_register_fit": _ax("medium"),
        "formal_compliance_fit": _ax("medium" if has_formal else "unknown"),
        "publication_regime_fit": _ax("medium"),
        "rewrite_effort": _ax(rewrite),
        "citation_effort": _ax("medium"),
        "field_core_risk": _ax(fcr),
        "strategic_value": _ax(sv),
        "evidence_confidence": _ax(confidence),
        "unknowns_axis": _ax("strong"),
    }
    return {
        "venue_profile_package_id": vid,
        "canonical_name": name,
        "axes": axes,
        "_signals_used": {
            "continental_hits": 0, "philtech_hits": 0,
            "sts_hits": 0, "hci_hits": 0,
            "theory_hits": 0, "empirical_hits": 0,
            "corpus_works_n": 25 if has_corpus else 0,
            "has_corpus": has_corpus,
            "has_board": False,
            "has_formal_profile": has_formal,
            "is_russian_venue": False,
        },
    }


class TestBucketFirstRanker:
    def test_good_fit_outranks_possible_but_costly(self):
        f_pbc = _mk_fit(
            vid="A", name="alpha", bucket_signals=None,
            confidence="strong", topic="weak", citation_ecology="weak",
        )
        f_gf = _mk_fit(
            vid="B", name="bravo", bucket_signals=None,
            confidence="medium", topic="medium",
        )
        buckets = select_shortlist([f_pbc, f_gf], calibrated=True)
        # Sanity: B in good_fit, A in possible_but_costly
        gf_ids = {x["venue_profile_package_id"] for x in buckets["good_fit"]}
        pbc_ids = {x["venue_profile_package_id"]
                   for x in buckets["possible_but_costly"]}
        assert "B" in gf_ids
        assert "A" in pbc_ids
        top = rank_top_candidates([f_pbc, f_gf], buckets, n=5)
        # Good_fit must come first regardless of confidence
        assert top[0]["venue_profile_package_id"] == "B"

    def test_high_confidence_insufficient_does_not_outrank_lower_conf_good_fit(self):
        # An insufficient_data venue with confidence=strong
        f_ins = _mk_fit(
            vid="X", name="x-name", bucket_signals=None,
            confidence="strong", topic="unknown", has_corpus=False,
        )
        # A good_fit with confidence=medium
        f_gf = _mk_fit(
            vid="Y", name="y-name", bucket_signals=None,
            confidence="medium", topic="medium",
        )
        buckets = select_shortlist([f_ins, f_gf], calibrated=True)
        gf_ids = {x["venue_profile_package_id"] for x in buckets["good_fit"]}
        ins_ids = {x["venue_profile_package_id"]
                   for x in buckets["insufficient_data"]}
        assert "Y" in gf_ids
        assert "X" in ins_ids
        top = rank_top_candidates([f_ins, f_gf], buckets, n=5)
        assert top[0]["venue_profile_package_id"] == "Y"

    def test_sibling_separable_from_possible_but_costly(self):
        f_sib = _mk_fit(
            vid="S", name="sib", bucket_signals=None,
            confidence="medium", topic="medium",
            argument_form="bad",
        )
        f_pbc = _mk_fit(
            vid="P", name="pbc", bucket_signals=None,
            confidence="medium", topic="weak",
            citation_ecology="weak",
        )
        buckets = select_shortlist([f_sib, f_pbc], calibrated=True)
        sib_ids = {x["venue_profile_package_id"]
                   for x in buckets["sibling_manuscript"]}
        pbc_ids = {x["venue_profile_package_id"]
                   for x in buckets["possible_but_costly"]}
        assert "S" in sib_ids and "P" in pbc_ids
        top = rank_top_candidates([f_sib, f_pbc], buckets, n=5)
        # Possible_but_costly precedes sibling
        assert [t["bucket"] for t in top] == [
            "possible_but_costly", "sibling_manuscript",
        ]

    def test_within_bucket_confidence_dominates_then_corpus(self):
        f1 = _mk_fit(vid="1", name="aaa", bucket_signals=None,
                     confidence="strong", topic="medium", has_corpus=True)
        f2 = _mk_fit(vid="2", name="bbb", bucket_signals=None,
                     confidence="medium", topic="medium", has_corpus=True)
        f3 = _mk_fit(vid="3", name="ccc", bucket_signals=None,
                     confidence="medium", topic="medium", has_corpus=False,
                     argument_form="medium", method="medium",
                     citation_ecology="medium")
        buckets = select_shortlist([f1, f2, f3], calibrated=True)
        top = rank_top_candidates([f1, f2, f3], buckets, n=5)
        # f1 first (strong confidence), then f2 (corpus over f3)
        assert top[0]["venue_profile_package_id"] == "1"
        # Either f2 or f3 next, but f2 has has_corpus advantage
        ids_in_order = [t["venue_profile_package_id"] for t in top]
        assert ids_in_order.index("2") < ids_in_order.index("3") or "3" not in ids_in_order

    def test_canonical_name_is_stable_tiebreaker(self):
        # Identical signals; only canonical_name differs
        f_a = _mk_fit(vid="a", name="aardvark", bucket_signals=None,
                      confidence="medium")
        f_b = _mk_fit(vid="b", name="zebra", bucket_signals=None,
                      confidence="medium")
        buckets = select_shortlist([f_a, f_b], calibrated=True)
        top = rank_top_candidates([f_a, f_b], buckets, n=5)
        # a before z (lexicographic)
        ids = [t["venue_profile_package_id"] for t in top]
        assert ids.index("a") < ids.index("b")


# ---------------------------------------------------------------------------
# B2: registry upsert must not downgrade existing completeness subobjects
# ---------------------------------------------------------------------------

class TestUpsertPreservesSubobjects:
    def test_completeness_present_not_downgraded_to_missing(self, tmp_path):
        """Reproduces the v2 board=1 -> 0 collapse."""
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        existing = VenueProfilePackage(
            canonical_name="Memory, Mind & Media",
            issns=["2635-0238"],
            languages=["en"],
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "partial",
                "FormalSubmissionProfile": "missing",
            },
            editorial_board_cloud_id="ebc_xyz_123",
        )
        reg.upsert(existing)

        # Now upsert a "re-enriched" version that has board as missing
        re_enriched = VenueProfilePackage(
            canonical_name="Memory, Mind & Media",
            issns=["2635-0238"],
            languages=["en"],
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "missing",  # <-- the bug input
                "FormalSubmissionProfile": "missing",
            },
            # editorial_board_cloud_id is None — bug input
        )
        reg.upsert(re_enriched)

        # Reload to make sure persistence carried the fix
        reg2 = VenueProfileRegistry(storage_root=str(tmp_path))
        records = reg2.list_all()
        assert len(records) == 1
        v = records[0]
        # Board completeness must NOT have been downgraded.
        assert v.completeness["EditorialBoardCloud"] == "partial"
        # Subobject id must not have been erased.
        assert v.editorial_board_cloud_id == "ebc_xyz_123"

    def test_completeness_upgrade_path_still_works(self, tmp_path):
        """If new VPKG has present and old has partial, must upgrade."""
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        existing = VenueProfilePackage(
            canonical_name="J",
            issns=["0000-0000"],
            completeness={"PublishedCorpusHull": "partial"},
        )
        reg.upsert(existing)
        better = VenueProfilePackage(
            canonical_name="J",
            issns=["0000-0000"],
            completeness={"PublishedCorpusHull": "present"},
        )
        reg.upsert(better)
        reg2 = VenueProfileRegistry(storage_root=str(tmp_path))
        v = reg2.list_all()[0]
        assert v.completeness["PublishedCorpusHull"] == "present"

    def test_new_completeness_keys_get_added(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        existing = VenueProfilePackage(
            canonical_name="K",
            issns=["1111-1111"],
            completeness={"VenueIdentity": "partial"},
        )
        reg.upsert(existing)
        added = VenueProfilePackage(
            canonical_name="K",
            issns=["1111-1111"],
            completeness={
                "VenueIdentity": "partial",
                "PublishedCorpusHull": "present",  # new key
            },
        )
        reg.upsert(added)
        v = reg.list_all()[0]
        assert v.completeness["VenueIdentity"] == "partial"
        assert v.completeness["PublishedCorpusHull"] == "present"

    def test_subobject_ids_not_erased_by_none(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        existing = VenueProfilePackage(
            canonical_name="L",
            issns=["2222-2222"],
            published_corpus_hull_id="hull_abc",
            editorial_board_cloud_id="ebc_def",
            venue_field_position_id="vfp_ghi",
        )
        reg.upsert(existing)
        empty = VenueProfilePackage(
            canonical_name="L",
            issns=["2222-2222"],
        )
        reg.upsert(empty)
        v = reg.list_all()[0]
        assert v.published_corpus_hull_id == "hull_abc"
        assert v.editorial_board_cloud_id == "ebc_def"
        assert v.venue_field_position_id == "vfp_ghi"
