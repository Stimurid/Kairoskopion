"""Venue cache-miss policy hook (VF-C7).

Decides which CacheMissCategory applies to a (VPKG, fit_question)
pair, and what specifically needs refreshing. Per canon §7
(`docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md`):

    Горячий путь — детерминированная композиция из базы.
    LLM на сети — только при cache-miss соответствующей категории.

Categories (from `enums.CacheMissCategory`):
  - ABSENT          → no VPKG-side data for the question; build from scratch
  - STALE           → data exists but past freshness_window for its source
  - WEAK_EVIDENCE   → data exists but evidence doesn't cover the asked axes
  - FRESH_SUFFICIENT → all required subobjects present and fresh;
                       NO network, NO LLM. Hot-path answer.

NO LLM. NO network. Pure read-side classifier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..enums import CacheMissCategory, VenueSourceCategory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Freshness windows per source category (days)
# ---------------------------------------------------------------------------

DEFAULT_FRESHNESS_WINDOWS_DAYS: dict[str, int] = {
    VenueSourceCategory.A_JOURNAL_SITE.value: 90,
    VenueSourceCategory.B_PUBLISHER.value: 180,
    VenueSourceCategory.C_INDEXER_REGISTRY.value: 30,
    VenueSourceCategory.D_CORPUS.value: 60,
    VenueSourceCategory.E_EDITORIAL_BOARD.value: 90,
    VenueSourceCategory.F_CORPUS_AUTHORS.value: 90,
    VenueSourceCategory.G_METADATA_API.value: 30,
    VenueSourceCategory.H_FULL_TEXT_RESOLVER.value: 365,
    VenueSourceCategory.I_CFP_SOCIETY_CHANNEL.value: 7,
    VenueSourceCategory.J_TACIT_SIGNAL.value: 365,
}


# ---------------------------------------------------------------------------
# Fit-question → required subobjects mapping
# ---------------------------------------------------------------------------

# Each axis in the 16-axis FitAssessment names which VPKG completeness
# keys it depends on. Multi-axis questions union the sets.
AXIS_TO_REQUIRED_SUBOBJECTS: dict[str, set[str]] = {
    "topic_fit": {"PublishedCorpusHull"},
    "disciplinary_fit": {"PublishedCorpusHull", "VenueFieldPosition"},
    "genre_fit": {"PublishedCorpusHull"},
    "argument_form_fit": {"PublishedCorpusHull"},
    "method_fit": {"PublishedCorpusHull", "FormalSubmissionProfile"},
    "novelty_mode_fit": {"PublishedCorpusHull"},
    "citation_ecology_fit": {"CitationExpectationProfile", "PublishedCorpusHull"},
    "language_register_fit": {"FormalSubmissionProfile"},
    "formal_compliance_fit": {"FormalSubmissionProfile"},
    "publication_regime_fit": {"FormalSubmissionProfile"},
    "rewrite_effort": {"PublishedCorpusHull", "FormalSubmissionProfile"},
    "citation_effort": {"CitationExpectationProfile", "PublishedCorpusHull"},
    "field_core_risk": {"EditorialBoardCloud", "PublishedCorpusHull"},
    "strategic_value": {"VenueIdentity", "PublishedCorpusHull"},
    "evidence_confidence": {"VenueIdentity"},
    "unknowns": set(),  # meta-axis; no subobject requirement
}

# Each subobject completeness key → source category whose freshness
# window applies to it. Used for STALE classification.
SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY: dict[str, str] = {
    "VenueIdentity": VenueSourceCategory.C_INDEXER_REGISTRY.value,
    "VenueFieldPosition": VenueSourceCategory.D_CORPUS.value,
    "PublishedCorpusHull": VenueSourceCategory.D_CORPUS.value,
    "EditorialBoardCloud": VenueSourceCategory.E_EDITORIAL_BOARD.value,
    "FormalSubmissionProfile": VenueSourceCategory.A_JOURNAL_SITE.value,
    "CitationExpectationProfile": VenueSourceCategory.D_CORPUS.value,
    "SourceEvidencePacket": VenueSourceCategory.C_INDEXER_REGISTRY.value,
}


# ---------------------------------------------------------------------------
# Decision record
# ---------------------------------------------------------------------------

@dataclass
class CacheMissDecision:
    category: str  # CacheMissCategory value
    required_subobjects: list[str] = field(default_factory=list)
    present_subobjects: list[str] = field(default_factory=list)
    missing_subobjects: list[str] = field(default_factory=list)
    partial_subobjects: list[str] = field(default_factory=list)
    stale_subobjects: list[str] = field(default_factory=list)
    fresh_subobjects: list[str] = field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = field(default_factory=list)
    network_budget_subobjects: list[str] = field(default_factory=list)
    would_burn_llm_key: bool = False
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "required_subobjects": list(self.required_subobjects),
            "present_subobjects": list(self.present_subobjects),
            "missing_subobjects": list(self.missing_subobjects),
            "partial_subobjects": list(self.partial_subobjects),
            "stale_subobjects": list(self.stale_subobjects),
            "fresh_subobjects": list(self.fresh_subobjects),
            "recommended_actions": list(self.recommended_actions),
            "network_budget_subobjects": list(self.network_budget_subobjects),
            "would_burn_llm_key": self.would_burn_llm_key,
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def required_subobjects_for_question(
    fit_axes: list[str],
) -> set[str]:
    """Union of subobjects required to answer the listed fit axes."""
    required: set[str] = set()
    for axis in fit_axes:
        required |= AXIS_TO_REQUIRED_SUBOBJECTS.get(axis, set())
    return required


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # Handle both 'Z' and '+00:00' suffixes
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _is_stale(
    last_refreshed_at: str | None,
    source_category: str,
    windows_days: dict[str, int],
    now: datetime | None = None,
) -> bool:
    """True iff the timestamp is older than the source's freshness window.

    Honest default: if no timestamp is provided, treat as NOT stale —
    the upstream missing/partial classification will catch it first.
    """
    if not last_refreshed_at:
        return False
    ts = _parse_iso(last_refreshed_at)
    if ts is None:
        return False
    window = windows_days.get(source_category)
    if window is None:
        return False
    now = now or _now_utc()
    # Make sure both timezones-aware
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = now - ts
    return age > timedelta(days=window)


def classify_cache_miss(
    *,
    vpkg,
    fit_axes: list[str],
    freshness_windows_days: dict[str, int] | None = None,
    now: datetime | None = None,
) -> CacheMissDecision:
    """Decide the cache-miss category for one VPKG against a fit-question.

    Args:
      vpkg: a `VenueProfilePackage` (or dict with the same shape).
      fit_axes: which axes the caller needs answered. Drives which
        subobjects are required.
      freshness_windows_days: per source-category override map.
      now: optional fixed reference time for testing.
    """
    vd = vpkg.to_dict() if hasattr(vpkg, "to_dict") else dict(vpkg)
    windows = dict(DEFAULT_FRESHNESS_WINDOWS_DAYS)
    if freshness_windows_days:
        windows.update(freshness_windows_days)

    required = required_subobjects_for_question(fit_axes)
    completeness = vd.get("completeness") or {}

    present: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    stale: list[str] = []
    fresh: list[str] = []

    last_refreshed = vd.get("last_refreshed_at")

    for sub in sorted(required):
        state = completeness.get(sub, "missing")
        if state == "present":
            present.append(sub)
            src_cat = SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.get(sub)
            if src_cat and _is_stale(last_refreshed, src_cat, windows, now):
                stale.append(sub)
            else:
                fresh.append(sub)
        elif state == "partial":
            partial.append(sub)
            src_cat = SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.get(sub)
            if src_cat and _is_stale(last_refreshed, src_cat, windows, now):
                stale.append(sub)
        else:
            missing.append(sub)

    # Classification (order matters — first matching rule wins per
    # canon §7 priority):
    category: str
    rationale: str
    recommended_actions: list[dict[str, Any]] = []
    network_budget: list[str] = []
    would_burn = False

    if not required:
        # Meta question or empty axes — treat as fresh.
        category = CacheMissCategory.FRESH_SUFFICIENT.value
        rationale = "no subobjects required by the requested axes"
    elif missing:
        category = CacheMissCategory.ABSENT.value
        rationale = (
            f"{len(missing)} required subobject(s) missing: {missing}"
        )
        for sub in missing:
            src_cat = SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.get(sub)
            recommended_actions.append({
                "subobject": sub,
                "action": "full_build",
                "source_category": src_cat,
                "reason": "missing in VPKG",
            })
            network_budget.append(sub)
        would_burn = True
    elif partial:
        category = CacheMissCategory.WEAK_EVIDENCE.value
        rationale = (
            f"{len(partial)} required subobject(s) only partial: {partial}"
        )
        for sub in partial:
            src_cat = SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.get(sub)
            recommended_actions.append({
                "subobject": sub,
                "action": "targeted_fill",
                "source_category": src_cat,
                "reason": "partial coverage of axes",
            })
            network_budget.append(sub)
        would_burn = True
    elif stale:
        category = CacheMissCategory.STALE.value
        rationale = (
            f"{len(stale)} required subobject(s) past freshness window: {stale}"
        )
        for sub in stale:
            src_cat = SUBOBJECT_TO_PRIMARY_SOURCE_CATEGORY.get(sub)
            window = windows.get(src_cat) if src_cat else None
            recommended_actions.append({
                "subobject": sub,
                "action": "targeted_refresh",
                "source_category": src_cat,
                "freshness_window_days": window,
                "reason": f"older than {window}d window for {src_cat}",
            })
            network_budget.append(sub)
        would_burn = True
    else:
        category = CacheMissCategory.FRESH_SUFFICIENT.value
        rationale = (
            f"all {len(present)} required subobject(s) present and fresh"
        )
        # NO actions, NO budget — hot path serves from DB.

    return CacheMissDecision(
        category=category,
        required_subobjects=sorted(required),
        present_subobjects=sorted(present),
        missing_subobjects=sorted(missing),
        partial_subobjects=sorted(partial),
        stale_subobjects=sorted(stale),
        fresh_subobjects=sorted(fresh),
        recommended_actions=recommended_actions,
        network_budget_subobjects=sorted(network_budget),
        would_burn_llm_key=would_burn,
        rationale=rationale,
    )


def classify_batch(
    *,
    vpkgs: list,
    fit_axes: list[str],
    freshness_windows_days: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify a batch of VPKGs. Returns per-VPKG decisions + a summary."""
    decisions: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {
        CacheMissCategory.ABSENT.value: 0,
        CacheMissCategory.STALE.value: 0,
        CacheMissCategory.WEAK_EVIDENCE.value: 0,
        CacheMissCategory.FRESH_SUFFICIENT.value: 0,
    }
    for v in vpkgs:
        d = classify_cache_miss(
            vpkg=v, fit_axes=fit_axes,
            freshness_windows_days=freshness_windows_days, now=now,
        )
        vid = (
            v.venue_profile_package_id
            if hasattr(v, "venue_profile_package_id")
            else v.get("venue_profile_package_id")
        )
        decisions[vid] = d.to_dict()
        counts[d.category] = counts.get(d.category, 0) + 1
    return {
        "per_vpkg": decisions,
        "category_counts": counts,
        "burns_llm_count": sum(
            1 for d in decisions.values() if d["would_burn_llm_key"]
        ),
        "hot_path_count": counts[CacheMissCategory.FRESH_SUFFICIENT.value],
    }
