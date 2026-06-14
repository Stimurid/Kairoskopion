"""Tests for v2 selection calibration + operator-seeded canonical venues."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kairoskopion.config import env as env_cfg
from kairoskopion.services.mavrinsky_venue_selection import (
    _bucket_v2,
    assess_fit_for_vpkg,
    mavrinsky_article_model,
    select_shortlist,
)
from kairoskopion.services.venue_operator_seed import (
    CANONICAL_SEEDS,
    SEED_ORIGIN,
    build_seed_vpkg,
    seed_canonical_venues_into_registry,
)
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_axes(**overrides):
    base = {
        "topic_fit": "medium",
        "disciplinary_fit": "medium",
        "genre_fit": "medium",
        "argument_form_fit": "medium",
        "method_fit": "medium",
        "novelty_mode_fit": "medium",
        "citation_ecology_fit": "medium",
        "language_register_fit": "medium",
        "formal_compliance_fit": "medium",
        "publication_regime_fit": "medium",
        "rewrite_effort": "strong",
        "citation_effort": "medium",
        "field_core_risk": "strong",
        "strategic_value": "medium",
        "evidence_confidence": "medium",
        "unknowns_axis": "strong",
    }
    base.update(overrides)
    return {k: {"value": v, "evidence": "test", "note": ""} for k, v in base.items()}


def _make_fit(*, axes_overrides=None, signals=None):
    return {
        "venue_profile_package_id": "test-vpkg-id",
        "canonical_name": "Test Venue",
        "_lifecycle_status": "PRELIMINARY",
        "axes": _make_axes(**(axes_overrides or {})),
        "_signals_used": signals or {
            "continental_hits": 0, "philtech_hits": 0,
            "sts_hits": 0, "hci_hits": 0,
            "theory_hits": 0, "empirical_hits": 0,
            "corpus_works_n": 10, "has_corpus": True,
            "has_board": False, "has_formal_profile": False,
            "is_russian_venue": False,
        },
    }


# ---------------------------------------------------------------------------
# Label calibration — five mandated cases (acceptance criterion D)
# ---------------------------------------------------------------------------

class TestBucketV2:
    def test_good_fit_strict(self):
        """topic medium+, rewrite strong, fcr strong, citation medium+, confidence medium+."""
        fit = _make_fit(axes_overrides={
            "topic_fit": "medium",
            "rewrite_effort": "strong",
            "field_core_risk": "strong",
            "citation_ecology_fit": "medium",
            "evidence_confidence": "medium",
        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "good_fit", reasons

    def test_good_fit_rejected_when_citation_weak(self):
        fit = _make_fit(axes_overrides={
            "topic_fit": "medium",
            "rewrite_effort": "strong",
            "field_core_risk": "strong",
            "citation_ecology_fit": "weak",  # blocks good_fit
        })
        bucket, _ = _bucket_v2(fit)
        assert bucket != "good_fit"

    def test_possible_but_costly_with_bounded_effort(self):
        fit = _make_fit(axes_overrides={
            "topic_fit": "medium",
            "rewrite_effort": "medium",
            "field_core_risk": "medium",
            "citation_ecology_fit": "weak",
            "citation_effort": "medium",
            "evidence_confidence": "medium",
        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "possible_but_costly", reasons

    def test_poor_fit_when_field_core_risk_bad(self):
        fit = _make_fit(axes_overrides={
            "field_core_risk": "bad",
        }, signals={
            "continental_hits": 0, "philtech_hits": 0,
            "sts_hits": 0, "hci_hits": 4,
            "theory_hits": 0, "empirical_hits": 0,
            "corpus_works_n": 20, "has_corpus": True,
            "has_board": False, "has_formal_profile": False,
            "is_russian_venue": False,
        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "poor_fit", reasons

    def test_poor_fit_when_topic_and_disc_bad(self):
        fit = _make_fit(axes_overrides={
            "topic_fit": "bad",
            "disciplinary_fit": "bad",
        })
        bucket, _ = _bucket_v2(fit)
        assert bucket == "poor_fit"

    def test_sibling_manuscript_when_argument_form_bad(self):
        fit = _make_fit(axes_overrides={
            "argument_form_fit": "bad",
            "field_core_risk": "medium",
        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "sibling_manuscript", reasons

    def test_sibling_manuscript_when_method_and_genre_weak(self):
        fit = _make_fit(axes_overrides={
            "method_fit": "weak",
            "genre_fit": "weak",
        })
        bucket, _ = _bucket_v2(fit)
        assert bucket == "sibling_manuscript"

    def test_sibling_manuscript_when_fcr_weak_and_arg_unknown(self):
        fit = _make_fit(axes_overrides={
            "field_core_risk": "weak",
            "argument_form_fit": "unknown",
        })
        bucket, _ = _bucket_v2(fit)
        assert bucket == "sibling_manuscript"

    def test_insufficient_data_when_no_corpus_and_topic_unknown(self):
        fit = _make_fit(axes_overrides={"topic_fit": "unknown"},
                        signals={
                            "continental_hits": 0, "philtech_hits": 0,
                            "sts_hits": 0, "hci_hits": 0,
                            "theory_hits": 0, "empirical_hits": 0,
                            "corpus_works_n": 0, "has_corpus": False,
                            "has_board": False, "has_formal_profile": False,
                            "is_russian_venue": False,
                        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "insufficient_data", reasons

    def test_insufficient_data_when_many_unknown_axes(self):
        fit = _make_fit(axes_overrides={
            "topic_fit": "unknown",
            "disciplinary_fit": "unknown",
            "genre_fit": "unknown",
            "argument_form_fit": "unknown",
            "method_fit": "unknown",
            "novelty_mode_fit": "unknown",
            "citation_ecology_fit": "unknown",
            "language_register_fit": "unknown",
            "evidence_confidence": "weak",
        })
        bucket, reasons = _bucket_v2(fit)
        assert bucket == "insufficient_data", reasons

    def test_no_silent_catchall_to_possible_but_costly(self):
        """Verify rule 6 sends ambiguous fits to insufficient_data, not PBC."""
        fit = _make_fit(axes_overrides={
            "topic_fit": "unknown",
            "disciplinary_fit": "weak",
            "argument_form_fit": "weak",
            "rewrite_effort": "weak",
            "field_core_risk": "weak",
            "evidence_confidence": "weak",
        }, signals={
            "continental_hits": 0, "philtech_hits": 0,
            "sts_hits": 0, "hci_hits": 0,
            "theory_hits": 0, "empirical_hits": 0,
            "corpus_works_n": 0, "has_corpus": False,
            "has_board": False, "has_formal_profile": False,
            "is_russian_venue": False,
        })
        bucket, _ = _bucket_v2(fit)
        assert bucket == "insufficient_data"


# ---------------------------------------------------------------------------
# Operator seed module
# ---------------------------------------------------------------------------

class TestOperatorSeed:
    def test_canonical_seed_list_has_expected_anchors(self):
        names = {s["canonical_name"] for s in CANONICAL_SEEDS}
        # Anchor venues required by task spec section B
        assert "Philosophy & Technology" in names
        assert "Foucault Studies" in names
        assert "Big Data & Society" in names
        assert "Логос" in names
        assert "Вопросы философии" in names

    def test_build_seed_vpkg_marks_origin(self):
        seed = CANONICAL_SEEDS[0]
        vpkg = build_seed_vpkg(seed)
        assert SEED_ORIGIN in vpkg.discovery_sources
        assert vpkg.evidence_status == "operator_seed_canonical"
        assert vpkg.canonical_name == seed["canonical_name"]
        # No homepage, no formal profile, no board claimed at seed time
        assert vpkg.completeness["EditorialBoardCloud"] == "missing"
        assert vpkg.completeness["FormalSubmissionProfile"] == "missing"

    def test_build_seed_vpkg_no_invented_publisher(self):
        # The 'Russian Journal of Philosophical Sciences' seed has
        # publisher=None — must not be silently replaced.
        for s in CANONICAL_SEEDS:
            if s["canonical_name"] == "Russian Journal of Philosophical Sciences":
                vpkg = build_seed_vpkg(s)
                assert vpkg.publisher is None
                # carries the operator-noted ambiguity
                assert any(
                    "Философские науки" in u for u in vpkg.unknowns
                )
                break

    def test_seed_into_empty_registry(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        assert reg.count() == 0
        summary = seed_canonical_venues_into_registry(reg)
        assert summary["total_seeds"] == len(CANONICAL_SEEDS)
        assert summary["newly_inserted"] == len(CANONICAL_SEEDS)
        assert summary["merged_into_existing"] == 0
        assert reg.count() == len(CANONICAL_SEEDS)

    def test_seed_is_idempotent(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        seed_canonical_venues_into_registry(reg)
        n1 = reg.count()
        # Second run on same registry must not duplicate
        summary2 = seed_canonical_venues_into_registry(reg)
        assert reg.count() == n1
        assert summary2["merged_into_existing"] == len(CANONICAL_SEEDS)
        assert summary2["newly_inserted"] == 0

    def test_seed_survives_reload(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        seed_canonical_venues_into_registry(reg)
        n = reg.count()
        # Fresh instance — must read from JSONL
        reg2 = VenueProfileRegistry(storage_root=str(tmp_path))
        assert reg2.count() == n
        # Each survived record carries the origin marker
        for v in reg2.list_all():
            assert SEED_ORIGIN in v.discovery_sources


# ---------------------------------------------------------------------------
# Env config — zero-cost auth improvements
# ---------------------------------------------------------------------------

class TestEnvConfig:
    def test_openalex_polite_url_noop_without_env(self, monkeypatch):
        monkeypatch.delenv("KAIROSKOPION_OPENALEX_MAILTO", raising=False)
        url = "https://api.openalex.org/works?filter=primary_location.source.id:S1"
        assert env_cfg.openalex_polite_url(url) == url

    def test_openalex_polite_url_appends_mailto(self, monkeypatch):
        monkeypatch.setenv(
            "KAIROSKOPION_OPENALEX_MAILTO", "test@example.org"
        )
        url = "https://api.openalex.org/works?filter=primary_location.source.id:S1"
        result = env_cfg.openalex_polite_url(url)
        assert "mailto=test%40example.org" in result
        # Idempotent
        assert env_cfg.openalex_polite_url(result) == result

    def test_config_summary_only_booleans(self, monkeypatch):
        monkeypatch.setenv(
            "KAIROSKOPION_SEMANTIC_SCHOLAR_API_KEY", "super-secret-do-not-leak"
        )
        summary = env_cfg.config_summary()
        # Only boolean presence, no value
        assert summary["semantic_scholar_key_configured"] is True
        for v in summary.values():
            assert isinstance(v, bool)
        # No secret in any string field
        assert "super-secret-do-not-leak" not in repr(summary)

    def test_orcid_requires_both_credentials(self, monkeypatch):
        monkeypatch.setenv("KAIROSKOPION_ORCID_CLIENT_ID", "client")
        monkeypatch.delenv("KAIROSKOPION_ORCID_CLIENT_SECRET", raising=False)
        assert env_cfg.orcid_client_credentials() is None


# ---------------------------------------------------------------------------
# End-to-end: seeded registry + selection v2
# ---------------------------------------------------------------------------

class TestEndToEndV2:
    def test_selection_over_seeded_registry_produces_calibrated_buckets(
        self, tmp_path
    ):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        seed_canonical_venues_into_registry(reg)

        article = mavrinsky_article_model()
        fits = []
        for vpkg in reg.list_all():
            vd = vpkg.to_dict()
            is_ru = "ru" in (vd.get("languages") or [])
            fits.append(assess_fit_for_vpkg(
                article, vd,
                corpus_titles=None,
                corpus_works_n=0,
                has_formal_profile=False,
                is_russian_venue=is_ru,
            ))

        buckets = select_shortlist(fits, calibrated=True)
        # Without enrichment (no corpus hulls yet), seeds with rich
        # cluster tags still produce SOME bucket. But many will
        # land in insufficient_data, which is correct per calibration.
        total = sum(len(v) for v in buckets.values())
        assert total == len(CANONICAL_SEEDS)
        # Calibration ensures we can SEE insufficient_data, not silently hide it.
        assert "insufficient_data" in buckets
        # Each entry has label_reasons
        for entries in buckets.values():
            for e in entries:
                assert e["label_reasons"]
