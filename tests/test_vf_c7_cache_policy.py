"""VF-C7 tests — venue_cache_policy: 4-category cache-miss classification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kairoskopion.enums import CacheMissCategory, VenueSourceCategory
from kairoskopion.schema import VenueProfilePackage
from kairoskopion.services.venue_cache_policy import (
    AXIS_TO_REQUIRED_SUBOBJECTS,
    DEFAULT_FRESHNESS_WINDOWS_DAYS,
    SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY,
    CacheMissDecision,
    classify_batch,
    classify_cache_miss,
    required_subobjects_for_question,
)


NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


def _vpkg_with_completeness(name: str, completeness: dict[str, str],
                              **overrides) -> VenueProfilePackage:
    base = dict(
        canonical_name=name,
        completeness=dict(completeness),
        last_refreshed_at=overrides.pop("last_refreshed_at", None),
    )
    base.update(overrides)
    return VenueProfilePackage(**base)


# ---------------------------------------------------------------------------
# Axis → required subobjects mapping
# ---------------------------------------------------------------------------

class TestAxisRequirements:
    def test_topic_fit_needs_published_corpus_hull(self):
        assert "PublishedCorpusHull" in AXIS_TO_REQUIRED_SUBOBJECTS["topic_fit"]

    def test_field_core_risk_needs_board(self):
        assert "EditorialBoardCloud" in AXIS_TO_REQUIRED_SUBOBJECTS["field_core_risk"]

    def test_formal_compliance_needs_formal_profile(self):
        assert "FormalSubmissionProfile" in AXIS_TO_REQUIRED_SUBOBJECTS[
            "formal_compliance_fit"
        ]

    def test_unknowns_axis_requires_nothing(self):
        # Meta axis — no subobject dependency
        assert AXIS_TO_REQUIRED_SUBOBJECTS["unknowns"] == set()

    def test_required_subobjects_unions_across_axes(self):
        req = required_subobjects_for_question(
            ["topic_fit", "field_core_risk"]
        )
        assert "PublishedCorpusHull" in req
        assert "EditorialBoardCloud" in req


# ---------------------------------------------------------------------------
# FRESH_SUFFICIENT: hot path, no key burned
# ---------------------------------------------------------------------------

class TestFreshSufficient:
    def test_all_present_recent_is_fresh_sufficient(self):
        v = _vpkg_with_completeness(
            "V", {
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
            },
            last_refreshed_at=(NOW - timedelta(days=5)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value
        assert d.would_burn_llm_key is False
        assert d.recommended_actions == []
        assert d.network_budget_subobjects == []

    def test_empty_axes_treated_as_fresh(self):
        v = _vpkg_with_completeness("V", {})
        d = classify_cache_miss(vpkg=v, fit_axes=[], now=NOW)
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value
        assert d.would_burn_llm_key is False

    def test_no_last_refreshed_is_not_stale(self):
        # Honest default: if we never recorded a refresh time, don't flag stale.
        # (the upstream missing/partial classifier picks up real gaps.)
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "present"},
            last_refreshed_at=None,
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value


# ---------------------------------------------------------------------------
# ABSENT: full build needed
# ---------------------------------------------------------------------------

class TestAbsent:
    def test_missing_subobject_is_absent(self):
        v = _vpkg_with_completeness("V", {"PublishedCorpusHull": "missing"})
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.ABSENT.value
        assert "PublishedCorpusHull" in d.missing_subobjects
        assert d.would_burn_llm_key is True
        assert len(d.recommended_actions) == 1
        assert d.recommended_actions[0]["action"] == "full_build"

    def test_absent_recommends_correct_source_category(self):
        v = _vpkg_with_completeness("V", {"EditorialBoardCloud": "missing"})
        d = classify_cache_miss(
            vpkg=v, fit_axes=["field_core_risk"], now=NOW,
        )
        ebc_action = next(
            a for a in d.recommended_actions
            if a["subobject"] == "EditorialBoardCloud"
        )
        assert ebc_action["source_category"] == \
            VenueSourceCategory.E_EDITORIAL_BOARD.value

    def test_multiple_missing_subobjects(self):
        v = _vpkg_with_completeness("V", {})  # everything missing
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit", "field_core_risk",
                               "formal_compliance_fit"],
            now=NOW,
        )
        assert d.category == CacheMissCategory.ABSENT.value
        # All three subobjects show up as missing
        for sub in ("PublishedCorpusHull", "EditorialBoardCloud",
                     "FormalSubmissionProfile"):
            assert sub in d.missing_subobjects


# ---------------------------------------------------------------------------
# WEAK_EVIDENCE: targeted fill of partial subobjects
# ---------------------------------------------------------------------------

class TestWeakEvidence:
    def test_partial_subobject_is_weak_evidence(self):
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "partial"},
            last_refreshed_at=(NOW - timedelta(days=1)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.WEAK_EVIDENCE.value
        assert "PublishedCorpusHull" in d.partial_subobjects
        assert d.recommended_actions[0]["action"] == "targeted_fill"

    def test_weak_evidence_takes_priority_over_stale(self):
        # If a subobject is partial AND past freshness window, the
        # partial classification wins (priority order per canon §7).
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "partial"},
            last_refreshed_at=(NOW - timedelta(days=365)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.WEAK_EVIDENCE.value


# ---------------------------------------------------------------------------
# STALE: targeted refresh
# ---------------------------------------------------------------------------

class TestStale:
    def test_old_corpus_hull_is_stale(self):
        # D_CORPUS window is 60 days; 90d ago is stale.
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "present"},
            last_refreshed_at=(NOW - timedelta(days=90)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.STALE.value
        assert "PublishedCorpusHull" in d.stale_subobjects
        assert d.recommended_actions[0]["action"] == "targeted_refresh"

    def test_recent_corpus_hull_not_stale(self):
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "present"},
            last_refreshed_at=(NOW - timedelta(days=30)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value

    def test_indexer_window_30_days(self):
        v = _vpkg_with_completeness(
            "V", {"VenueIdentity": "present"},
            last_refreshed_at=(NOW - timedelta(days=45)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["evidence_confidence"], now=NOW,
        )
        # VenueIdentity maps to C_INDEXER_REGISTRY (30-day window) → stale
        assert d.category == CacheMissCategory.STALE.value

    def test_stale_recommendation_includes_window_days(self):
        # Both required subobjects must be present so the stale-on-E
        # classification isn't masked by a missing subobject (ABSENT
        # would win per priority order).
        v = _vpkg_with_completeness(
            "V", {
                "EditorialBoardCloud": "present",
                "PublishedCorpusHull": "present",
            },
            last_refreshed_at=(NOW - timedelta(days=120)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["field_core_risk"], now=NOW,
        )
        # 120d > E_EDITORIAL_BOARD window (90d) AND > D_CORPUS window
        # (60d) — both subobjects flagged stale.
        assert d.category == CacheMissCategory.STALE.value
        ebc_action = next(
            a for a in d.recommended_actions
            if a["subobject"] == "EditorialBoardCloud"
        )
        assert ebc_action["freshness_window_days"] == \
            DEFAULT_FRESHNESS_WINDOWS_DAYS[
                VenueSourceCategory.E_EDITORIAL_BOARD.value
            ]

    def test_field_core_risk_with_present_board_and_corpus_is_fresh(self):
        v = _vpkg_with_completeness(
            "V", {
                "EditorialBoardCloud": "present",
                "PublishedCorpusHull": "present",
            },
            last_refreshed_at=(NOW - timedelta(days=5)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["field_core_risk"], now=NOW,
        )
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value


# ---------------------------------------------------------------------------
# Priority order (canon §7)
# ---------------------------------------------------------------------------

class TestPriorityOrder:
    def test_absent_beats_partial_beats_stale(self):
        """When multiple categories apply at once, ABSENT > WEAK_EVIDENCE > STALE."""
        # Both missing AND partial → ABSENT
        v = _vpkg_with_completeness(
            "V", {
                "PublishedCorpusHull": "missing",
                "EditorialBoardCloud": "partial",
            },
            last_refreshed_at=(NOW - timedelta(days=365)).isoformat(),
        )
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit", "field_core_risk"], now=NOW,
        )
        assert d.category == CacheMissCategory.ABSENT.value


# ---------------------------------------------------------------------------
# Freshness window override
# ---------------------------------------------------------------------------

class TestFreshnessWindowOverride:
    def test_custom_window_relaxes_stale_classification(self):
        # Default D_CORPUS window is 60 days; relax to 365.
        v = _vpkg_with_completeness(
            "V", {"PublishedCorpusHull": "present"},
            last_refreshed_at=(NOW - timedelta(days=90)).isoformat(),
        )
        custom = {VenueSourceCategory.D_CORPUS.value: 365}
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"],
            freshness_windows_days=custom, now=NOW,
        )
        assert d.category == CacheMissCategory.FRESH_SUFFICIENT.value


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

class TestClassifyBatch:
    def test_batch_returns_per_vpkg_and_counts(self):
        v_fresh = _vpkg_with_completeness(
            "Fresh", {"PublishedCorpusHull": "present"},
            last_refreshed_at=(NOW - timedelta(days=1)).isoformat(),
        )
        v_absent = _vpkg_with_completeness(
            "Absent", {},
        )
        v_partial = _vpkg_with_completeness(
            "Partial", {"PublishedCorpusHull": "partial"},
            last_refreshed_at=(NOW - timedelta(days=1)).isoformat(),
        )
        out = classify_batch(
            vpkgs=[v_fresh, v_absent, v_partial],
            fit_axes=["topic_fit"], now=NOW,
        )
        assert out["category_counts"][
            CacheMissCategory.FRESH_SUFFICIENT.value
        ] == 1
        assert out["category_counts"][CacheMissCategory.ABSENT.value] == 1
        assert out["category_counts"][
            CacheMissCategory.WEAK_EVIDENCE.value
        ] == 1
        # Only the fresh one is hot-path
        assert out["hot_path_count"] == 1
        # 2 of 3 would burn an LLM key
        assert out["burns_llm_count"] == 2


# ---------------------------------------------------------------------------
# Decision serialisation
# ---------------------------------------------------------------------------

class TestDecisionSerialisation:
    def test_to_dict_round_trippable_fields(self):
        v = _vpkg_with_completeness("V", {"PublishedCorpusHull": "missing"})
        d = classify_cache_miss(
            vpkg=v, fit_axes=["topic_fit"], now=NOW,
        )
        out = d.to_dict()
        # All expected keys present
        for k in ("category", "required_subobjects", "present_subobjects",
                  "missing_subobjects", "partial_subobjects", "stale_subobjects",
                  "fresh_subobjects", "recommended_actions",
                  "network_budget_subobjects", "would_burn_llm_key",
                  "rationale"):
            assert k in out


# ---------------------------------------------------------------------------
# Subobject ↔ source category coverage sanity
# ---------------------------------------------------------------------------

class TestSourceCategoryCoverage:
    def test_every_required_subobject_has_source_category(self):
        all_required: set[str] = set()
        for s in AXIS_TO_REQUIRED_SUBOBJECTS.values():
            all_required |= s
        for sub in all_required:
            assert sub in SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY, \
                f"{sub} has no primary source category mapped"

    def test_every_source_category_has_freshness_window(self):
        for cat in SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.values():
            assert cat in DEFAULT_FRESHNESS_WINDOWS_DAYS, \
                f"{cat} has no freshness window"
