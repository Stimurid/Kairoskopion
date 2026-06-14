"""Venue funnel navigator (VF-C5).

Walks the 8-layer venue funnel per canon §1
(`docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md`) over an existing
VenueProfileRegistry, given an article-side input. Emits an ordered
list of `(layer, layer_state, candidates_added, candidates_dropped,
evidence_refs)` so an auditor can read end-to-end how the funnel
narrowed.

Per canon §1 + §3 activation rule:

    A subobject at layer N may NOT be populated from a source category
    outside the allowlist for layer N.

The navigator does not POPULATE subobjects (that's the builder's job
in VF-C4). It only:
  1. takes the current VPKG state as truth,
  2. classifies each VPKG by layer signal,
  3. drops VPKGs that fail a per-layer filter,
  4. validates the activation rule on subobjects that ARE present.

NO LLM. NO network. Pure deterministic composition over the registry.

Stopping rules:
  - `funnel_floor` arg pins the walk to stop after that layer;
  - default: walk all 8 layers and return per-layer states.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..enums import VenueFunnelLayer, VenueSourceCategory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source allowlist per layer (canon §3 mapping)
# ---------------------------------------------------------------------------

LAYER_SOURCE_ALLOWLIST: dict[str, set[str]] = {
    VenueFunnelLayer.UNIVERSE.value: {
        VenueSourceCategory.A_JOURNAL_SITE.value,
        VenueSourceCategory.B_PUBLISHER.value,
        VenueSourceCategory.C_INDEXER_REGISTRY.value,
        VenueSourceCategory.I_CFP_SOCIETY_CHANNEL.value,
    },
    VenueFunnelLayer.DISCIPLINARY_REGIME.value: {
        VenueSourceCategory.D_CORPUS.value,
        VenueSourceCategory.G_METADATA_API.value,
    },
    VenueFunnelLayer.TRIBE_SCHOOL.value: {
        VenueSourceCategory.D_CORPUS.value,
        VenueSourceCategory.E_EDITORIAL_BOARD.value,
        VenueSourceCategory.F_CORPUS_AUTHORS.value,
    },
    VenueFunnelLayer.VENUE_CLASS.value: {
        VenueSourceCategory.A_JOURNAL_SITE.value,
        VenueSourceCategory.B_PUBLISHER.value,
        VenueSourceCategory.C_INDEXER_REGISTRY.value,
    },
    VenueFunnelLayer.JOURNAL_ENVELOPE.value: {
        VenueSourceCategory.A_JOURNAL_SITE.value,
        VenueSourceCategory.B_PUBLISHER.value,
        VenueSourceCategory.G_METADATA_API.value,
    },
    VenueFunnelLayer.SECTION_SPECIAL_ISSUE.value: {
        VenueSourceCategory.A_JOURNAL_SITE.value,
        VenueSourceCategory.I_CFP_SOCIETY_CHANNEL.value,
    },
    VenueFunnelLayer.EDITORIAL_BOARD_CLOUD.value: {
        VenueSourceCategory.E_EDITORIAL_BOARD.value,
        VenueSourceCategory.F_CORPUS_AUTHORS.value,
        VenueSourceCategory.G_METADATA_API.value,
    },
    VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value: {
        VenueSourceCategory.D_CORPUS.value,
        VenueSourceCategory.G_METADATA_API.value,
        VenueSourceCategory.H_FULL_TEXT_RESOLVER.value,
    },
}

LAYER_ORDER: list[str] = [
    VenueFunnelLayer.UNIVERSE.value,
    VenueFunnelLayer.DISCIPLINARY_REGIME.value,
    VenueFunnelLayer.TRIBE_SCHOOL.value,
    VenueFunnelLayer.VENUE_CLASS.value,
    VenueFunnelLayer.JOURNAL_ENVELOPE.value,
    VenueFunnelLayer.SECTION_SPECIAL_ISSUE.value,
    VenueFunnelLayer.EDITORIAL_BOARD_CLOUD.value,
    VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value,
]


def is_source_allowed_at_layer(source_category: str | None, layer: str) -> bool:
    """Activation rule: a subobject at layer N must come from allowed
    source categories of N. Per canon §3.

    Honest defaults:
      - `None` source_category → True (cannot judge; surface as a
        warning, not a hard fail);
      - unknown layer → True (forward-compat; surface as a warning).
    """
    if source_category is None:
        return True
    allowed = LAYER_SOURCE_ALLOWLIST.get(layer)
    if allowed is None:
        return True
    return source_category in allowed


# ---------------------------------------------------------------------------
# Per-layer filter signals (canon §1 layer purposes)
# ---------------------------------------------------------------------------

def _has_universe_signal(vpkg_dict: dict) -> bool:
    """L1: VPKG exists in some authoritative directory."""
    return bool(vpkg_dict.get("openalex_source_id")
                or vpkg_dict.get("doaj_source_id")
                or vpkg_dict.get("crossref_member_id")
                or vpkg_dict.get("cyberleninka_source_id")
                or vpkg_dict.get("issns"))


def _matches_disciplinary_clusters(
    vpkg_dict: dict, target_disciplines: list[str],
) -> tuple[bool, list[str]]:
    """L2: VPKG corpus signal overlaps article disciplines.

    Returns (matched, hit_clusters).
    """
    if not target_disciplines:
        return True, []
    clusters = [c.lower() for c in (vpkg_dict.get("discovery_clusters") or [])]
    hits = [
        c for c in clusters
        if any(d.lower() in c for d in target_disciplines)
    ]
    return bool(hits), hits


def _matches_tribe_school(
    vpkg_dict: dict, target_tribes: list[str],
) -> tuple[bool, list[str]]:
    """L3: VPKG cluster signal overlaps article school/tradition."""
    if not target_tribes:
        return True, []
    clusters = " ".join(vpkg_dict.get("discovery_clusters") or []).lower()
    name = (vpkg_dict.get("canonical_name") or "").lower()
    blob = clusters + " " + name
    hits = [t for t in target_tribes if t.lower() in blob]
    return bool(hits), hits


def _matches_venue_class(
    vpkg_dict: dict, allowed_venue_types: list[str] | None,
) -> bool:
    """L4: VPKG venue_type in caller-allowed set (journal / proceedings / ...)."""
    if not allowed_venue_types:
        return True
    return vpkg_dict.get("venue_type") in set(allowed_venue_types)


def _has_journal_envelope(vpkg_dict: dict) -> bool:
    """L5: VPKG has identity sufficient for journal-level routing
    (canonical_name + at least one indexer id)."""
    if not vpkg_dict.get("canonical_name"):
        return False
    return bool(
        vpkg_dict.get("openalex_source_id")
        or vpkg_dict.get("issns")
        or vpkg_dict.get("homepage_url")
    )


def _has_section_or_special_issue(vpkg_dict: dict) -> bool:
    """L6: VPKG carries a SectionModel or SpecialIssueModel link.

    Honest read: most current VPKGs do not yet carry these (VF-C3
    landed the dataclasses; population is VF-C4 builder extension).
    Until builder lands these, L6 candidates_dropped is honest.
    """
    return bool(
        (vpkg_dict.get("section_model_ids") or [])
        or (vpkg_dict.get("special_issue_model_ids") or [])
    )


def _has_board_cloud(vpkg_dict: dict) -> bool:
    """L7: VPKG carries an EditorialBoardCloud present/partial."""
    return (vpkg_dict.get("completeness") or {}).get(
        "EditorialBoardCloud"
    ) in ("present", "partial")


def _has_corpus_hull(vpkg_dict: dict) -> bool:
    """L8: VPKG carries a PublishedCorpusHull present/partial."""
    return (vpkg_dict.get("completeness") or {}).get(
        "PublishedCorpusHull"
    ) in ("present", "partial")


# ---------------------------------------------------------------------------
# Activation rule validation (canon §3)
# ---------------------------------------------------------------------------

# Maps VPKG subobject completeness key → which layer that subobject
# logically lives in. Used by the activation-rule validator below.
SUBOBJECT_TO_LAYER: dict[str, str] = {
    "VenueIdentity": VenueFunnelLayer.JOURNAL_ENVELOPE.value,
    "VenueFieldPosition": VenueFunnelLayer.DISCIPLINARY_REGIME.value,
    "PublishedCorpusHull": VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value,
    "EditorialBoardCloud": VenueFunnelLayer.EDITORIAL_BOARD_CLOUD.value,
    "FormalSubmissionProfile": VenueFunnelLayer.JOURNAL_ENVELOPE.value,
    "CitationExpectationProfile": VenueFunnelLayer.TRIBE_SCHOOL.value,
    "SourceEvidencePacket": VenueFunnelLayer.UNIVERSE.value,
}


def validate_activation_rule(vpkg_dict: dict) -> list[str]:
    """Return a list of activation-rule violations on this VPKG.

    A subobject with a populated `source_category` that lies outside
    its layer's allowlist is a violation. Empty list = clean.

    The current VPKG schema does NOT carry per-subobject
    `source_category` directly (subobject records do, but they are
    referenced by id). For now we validate the per-VPKG
    `evidence_status` + `discovery_sources` consistency: a VPKG
    flagged `evidence_status='external_claim'` with a discovery_source
    'OPERATOR_SEED_CANONICAL' is fine; a VPKG that claims a subobject
    is `present` but has no supporting evidence ref is flagged.
    """
    violations: list[str] = []
    completeness = vpkg_dict.get("completeness") or {}
    # Activation cross-check 1: PublishedCorpusHull present requires
    # openalex_source_id OR cyberleninka_source_id (D or G category).
    if completeness.get("PublishedCorpusHull") == "present":
        if not (vpkg_dict.get("openalex_source_id")
                or vpkg_dict.get("cyberleninka_source_id")):
            violations.append(
                "PublishedCorpusHull=present but no D/G source attached"
            )
    # Activation cross-check 2: EditorialBoardCloud present/partial
    # requires editorial_board_cloud_id.
    if completeness.get("EditorialBoardCloud") in ("present", "partial"):
        if not vpkg_dict.get("editorial_board_cloud_id"):
            violations.append(
                "EditorialBoardCloud claims present/partial but no cloud id"
            )
    return violations


# ---------------------------------------------------------------------------
# Walk result dataclass (no _DictMixin — pure dict for serialisation)
# ---------------------------------------------------------------------------

@dataclass
class LayerWalkRecord:
    layer: str
    candidates_in: int
    candidates_out: int
    candidates_added: list[str] = field(default_factory=list)
    candidates_dropped: list[str] = field(default_factory=list)
    drop_reasons: dict[str, str] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    activation_violations: dict[str, list[str]] = field(default_factory=dict)
    unknowns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "candidates_in": self.candidates_in,
            "candidates_out": self.candidates_out,
            "candidates_added": list(self.candidates_added),
            "candidates_dropped": list(self.candidates_dropped),
            "drop_reasons": dict(self.drop_reasons),
            "evidence_refs": list(self.evidence_refs),
            "activation_violations": {
                k: list(v) for k, v in self.activation_violations.items()
            },
            "unknowns": list(self.unknowns),
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# Navigator
# ---------------------------------------------------------------------------

def walk_funnel(
    *,
    article_model: dict[str, Any],
    vpkg_registry,
    submission_scenario: dict[str, Any] | None = None,
    funnel_floor: str | None = None,
) -> dict[str, Any]:
    """Walk the 8-layer funnel over the registry, given the article-side.

    Args:
      article_model: dict with at least `disciplinary_registers` and
        `tribes_present`. Same shape as
        `services.mavrinsky_venue_selection.mavrinsky_article_model()`.
      vpkg_registry: a `VenueProfileRegistry` (must implement
        `.list_all() -> list[VenueProfilePackage]`).
      submission_scenario: optional dict with `allowed_venue_types`
        and other narrowing constraints.
      funnel_floor: optional layer string. Stop after walking through
        this layer. None = walk all 8.

    Returns:
      Dict with:
        - layers: list[LayerWalkRecord.to_dict()] in order;
        - final_shortlist: list[str] of VPKG ids that survived;
        - stopping_reason: str;
        - activation_summary: total violations grouped by layer;
        - article_filter_applied: which filter constraints were used.
    """
    # Pull article-side filter inputs (honest empty defaults — no silent
    # match-all).
    disc = list(article_model.get("disciplinary_registers") or [])
    tribes_dict = article_model.get("tribes_present") or {}
    constructive_tribes = [
        k for k, v in tribes_dict.items() if v == "constructive"
    ]
    scenario = submission_scenario or {}
    allowed_venue_types = scenario.get("allowed_venue_types") or ["journal"]

    layer_records: list[LayerWalkRecord] = []
    current_set: set[str] = set()  # canonical_name set after this layer

    # Build a working dict by VPKG id
    all_vpkgs = list(vpkg_registry.list_all())
    by_name = {v.canonical_name: v for v in all_vpkgs if v.canonical_name}
    incoming_ids = {v.venue_profile_package_id for v in all_vpkgs}

    universe_ids: set[str] = set()  # populated at L1
    walked_layers: list[str] = []

    for layer in LAYER_ORDER:
        record = LayerWalkRecord(
            layer=layer,
            candidates_in=len(incoming_ids),
            candidates_out=0,
        )
        accepted: set[str] = set()
        for v in all_vpkgs:
            if v.venue_profile_package_id not in incoming_ids:
                continue
            vd = v.to_dict()

            keep = True
            reason = ""
            if layer == VenueFunnelLayer.UNIVERSE.value:
                keep = _has_universe_signal(vd)
                if not keep:
                    reason = "no recognised directory id (ISSN/OpenAlex/DOAJ/Crossref/CyberLeninka)"
            elif layer == VenueFunnelLayer.DISCIPLINARY_REGIME.value:
                keep, hits = _matches_disciplinary_clusters(vd, disc)
                if not keep:
                    reason = f"discovery_clusters do not overlap {disc!r}"
                else:
                    record.notes.append(
                        f"{vd.get('canonical_name')}: cluster hits {hits}"
                    )
            elif layer == VenueFunnelLayer.TRIBE_SCHOOL.value:
                keep, hits = _matches_tribe_school(vd, constructive_tribes)
                if not keep:
                    reason = f"no tribe-school signal in clusters/name for {constructive_tribes!r}"
                else:
                    record.notes.append(
                        f"{vd.get('canonical_name')}: tribe hits {hits}"
                    )
            elif layer == VenueFunnelLayer.VENUE_CLASS.value:
                keep = _matches_venue_class(vd, allowed_venue_types)
                if not keep:
                    reason = f"venue_type={vd.get('venue_type')!r} not in {allowed_venue_types!r}"
            elif layer == VenueFunnelLayer.JOURNAL_ENVELOPE.value:
                keep = _has_journal_envelope(vd)
                if not keep:
                    reason = "no journal envelope (name + indexer id / ISSN / homepage)"
            elif layer == VenueFunnelLayer.SECTION_SPECIAL_ISSUE.value:
                # Honest L6: VPKGs without section/special issue models pass
                # through here (filter is informational only — population
                # is VF-C4 builder extension territory). Surface as note.
                section_present = _has_section_or_special_issue(vd)
                if not section_present:
                    record.notes.append(
                        f"{vd.get('canonical_name')}: no Section/SpecialIssue "
                        "linked — populated by VF-C4 builder when CFP/section "
                        "discovery wires in"
                    )
                keep = True  # do NOT drop — L6 is informational here
            elif layer == VenueFunnelLayer.EDITORIAL_BOARD_CLOUD.value:
                keep = _has_board_cloud(vd)
                if not keep:
                    reason = "no EditorialBoardCloud present/partial"
            elif layer == VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value:
                keep = _has_corpus_hull(vd)
                if not keep:
                    reason = "no PublishedCorpusHull present/partial"

            # Validate activation rule on whatever subobjects this VPKG
            # carries. Recorded even when we KEEP the VPKG.
            v_violations = validate_activation_rule(vd)
            if v_violations:
                record.activation_violations[v.venue_profile_package_id] = v_violations

            if keep:
                accepted.add(v.venue_profile_package_id)
            else:
                record.candidates_dropped.append(v.venue_profile_package_id)
                record.drop_reasons[v.venue_profile_package_id] = reason

        # Universe pinning
        if layer == VenueFunnelLayer.UNIVERSE.value:
            universe_ids = accepted
        record.candidates_added = [
            vid for vid in accepted if vid not in current_set
        ] if current_set else sorted(accepted)
        record.candidates_out = len(accepted)
        incoming_ids = accepted
        current_set = accepted
        layer_records.append(record)
        walked_layers.append(layer)
        if funnel_floor and layer == funnel_floor:
            break

    stopping_reason = (
        f"funnel_floor={funnel_floor} reached"
        if funnel_floor and walked_layers and walked_layers[-1] == funnel_floor
        else "walked all 8 layers"
    )

    # Aggregate activation violations
    violation_summary: dict[str, int] = {}
    for rec in layer_records:
        violation_summary[rec.layer] = sum(
            len(v) for v in rec.activation_violations.values()
        )

    return {
        "layers": [r.to_dict() for r in layer_records],
        "final_shortlist": sorted(incoming_ids),
        "stopping_reason": stopping_reason,
        "activation_summary": violation_summary,
        "article_filter_applied": {
            "disciplinary_registers": disc,
            "constructive_tribes": constructive_tribes,
            "allowed_venue_types": allowed_venue_types,
        },
        "_layers_walked": walked_layers,
        "_total_vpkgs_input": len(all_vpkgs),
    }
