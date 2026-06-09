"""Venue Profile Builder (Sprint 4).

Builds a rich VenueProfile from multiple local source files:
  - Author guidelines
  - Aims and scope page
  - Policy pages (AI, data, ethics)
  - Issue pages / editorial board
  - Special issue CFPs

Each source is independently extracted and registered, then merged
into a single VenueModel + PublicationRegimeModel with provenance tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.source_intake import SourceRole, register_local_source
from ..ids import venue_model_id, publication_regime_id
from ..schema import VenueModel, PublicationRegimeModel, SourceSnapshot
from .venue_profiling import build_venue_model


# ---------------------------------------------------------------------------
# Source classification
# ---------------------------------------------------------------------------

_ROLE_BY_FILENAME_HINT: dict[str, SourceRole] = {
    "guidelines": SourceRole.AUTHOR_GUIDELINES,
    "author_guide": SourceRole.AUTHOR_GUIDELINES,
    "aims": SourceRole.AIMS_SCOPE,
    "scope": SourceRole.AIMS_SCOPE,
    "policy": SourceRole.POLICY_PAGE,
    "ethics": SourceRole.POLICY_PAGE,
    "editorial": SourceRole.EDITORIAL_BOARD,
    "cfp": SourceRole.SPECIAL_ISSUE_CFP,
    "call_for": SourceRole.SPECIAL_ISSUE_CFP,
    "issue": SourceRole.ISSUE_PAGE,
}


def _guess_role(path: Path) -> SourceRole:
    """Guess source role from filename."""
    name_lower = path.stem.lower()
    for hint, role in _ROLE_BY_FILENAME_HINT.items():
        if hint in name_lower:
            return role
    return SourceRole.VENUE_GUIDELINES


# ---------------------------------------------------------------------------
# VenueProfileSource — one registered input
# ---------------------------------------------------------------------------

class VenueProfileSource:
    """A single source file registered for venue profiling."""

    def __init__(
        self,
        snapshot: SourceSnapshot,
        text: str,
        role: SourceRole,
        path: Path,
    ):
        self.snapshot = snapshot
        self.text = text
        self.role = role
        self.path = path

    @property
    def source_id(self) -> str:
        return self.snapshot.source_id

    @property
    def extraction_status(self) -> str:
        return self.snapshot.extraction_status


# ---------------------------------------------------------------------------
# VenueProfileResult — merged output
# ---------------------------------------------------------------------------

class VenueProfileResult:
    """Result of multi-source venue profile building."""

    def __init__(
        self,
        venue: VenueModel,
        regime: PublicationRegimeModel,
        sources: list[VenueProfileSource],
        merge_log: list[str],
    ):
        self.venue = venue
        self.regime = regime
        self.sources = sources
        self.merge_log = merge_log

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def extracted_count(self) -> int:
        return sum(1 for s in self.sources if s.extraction_status == "extracted")


# ---------------------------------------------------------------------------
# Multi-source builder
# ---------------------------------------------------------------------------

def register_venue_sources(
    paths: list[Path],
    *,
    roles: dict[str, SourceRole] | None = None,
) -> list[VenueProfileSource]:
    """Register multiple local files as venue sources.

    Args:
        paths: List of file paths to register.
        roles: Optional mapping of filename → SourceRole overrides.

    Returns:
        List of VenueProfileSource objects with extracted text.
    """
    sources: list[VenueProfileSource] = []
    role_map = roles or {}

    for path in paths:
        path = Path(path)
        role = role_map.get(path.name, _guess_role(path))
        snapshot, text = register_local_source(path, role=role)
        sources.append(VenueProfileSource(
            snapshot=snapshot,
            text=text,
            role=role,
            path=path,
        ))

    return sources


def _merge_venue_models(
    models: list[tuple[VenueModel, PublicationRegimeModel, VenueProfileSource]],
) -> tuple[VenueModel, PublicationRegimeModel, list[str]]:
    """Merge multiple VenueModel extractions into one.

    Strategy: first model is the base, subsequent models enrich
    fields that are None/empty in the base. Never overwrite
    already-populated fields.
    """
    if not models:
        raise ValueError("No venue models to merge")

    if len(models) == 1:
        venue, regime, src = models[0]
        return venue, regime, [f"Single source: {src.path.name}"]

    base_venue, base_regime, base_src = models[0]
    log: list[str] = [f"Base source: {base_src.path.name} (role={base_src.role.value})"]

    for venue, regime, src in models[1:]:
        log.append(f"Merging: {src.path.name} (role={src.role.value})")

        # Enrich None/empty fields
        if not base_venue.canonical_name and venue.canonical_name:
            base_venue.canonical_name = venue.canonical_name
            log.append(f"  canonical_name ← {src.path.name}")

        if not base_venue.scope_summary and venue.scope_summary:
            base_venue.scope_summary = venue.scope_summary
            base_venue.aims_scope_summary = venue.aims_scope_summary
            log.append(f"  scope_summary ← {src.path.name}")

        if not base_venue.publisher_or_owner and venue.publisher_or_owner:
            base_venue.publisher_or_owner = venue.publisher_or_owner
            log.append(f"  publisher ← {src.path.name}")

        if not base_venue.language_policy and venue.language_policy:
            base_venue.language_policy = venue.language_policy
            log.append(f"  language_policy ← {src.path.name}")

        # Merge list fields (append new entries)
        for new_type in venue.article_types_supported:
            if new_type not in base_venue.article_types_supported:
                base_venue.article_types_supported.append(new_type)
                log.append(f"  article_type += {new_type}")

        if venue.indexing_claims:
            for claim in venue.indexing_claims:
                if claim not in base_venue.indexing_claims:
                    base_venue.indexing_claims.append(claim)
                    log.append(f"  indexing_claim += {claim}")

        for url in venue.official_urls:
            if url not in base_venue.official_urls:
                base_venue.official_urls.append(url)

        # Enrich policy fields
        if not base_venue.ai_policy and venue.ai_policy:
            base_venue.ai_policy = venue.ai_policy
            log.append(f"  ai_policy ← {src.path.name}")

        if not base_venue.data_policy and venue.data_policy:
            base_venue.data_policy = venue.data_policy
            log.append(f"  data_policy ← {src.path.name}")

        if not base_venue.ethics_policy and venue.ethics_policy:
            base_venue.ethics_policy = venue.ethics_policy
            log.append(f"  ethics_policy ← {src.path.name}")

        if not base_venue.open_access_status and venue.open_access_status:
            base_venue.open_access_status = venue.open_access_status
            log.append(f"  open_access ← {src.path.name}")

        if not base_venue.apc_policy and venue.apc_policy:
            base_venue.apc_policy = venue.apc_policy
            log.append(f"  apc_policy ← {src.path.name}")

        if not base_venue.anonymization_policy and venue.anonymization_policy:
            base_venue.anonymization_policy = venue.anonymization_policy
            log.append(f"  anonymization ← {src.path.name}")

        if not base_venue.word_limits and venue.word_limits:
            base_venue.word_limits = venue.word_limits
            log.append(f"  word_limits ← {src.path.name}")

        # Merge unknowns — remove resolved ones
        for unk in venue.unknowns:
            if unk not in base_venue.unknowns:
                base_venue.unknowns.append(unk)

        # Track source refs
        base_venue.source_refs.extend(venue.source_refs)
        base_venue.author_guidelines_refs.extend(venue.author_guidelines_refs)

        # Use better regime info if available
        if not base_regime.review_model and regime.review_model:
            base_regime.review_model = regime.review_model
            log.append(f"  review_model ← {src.path.name}")

    # Deduplicate source_refs
    base_venue.source_refs = list(dict.fromkeys(base_venue.source_refs))
    base_venue.author_guidelines_refs = list(dict.fromkeys(base_venue.author_guidelines_refs))

    # Re-evaluate confidence
    if base_venue.scope_summary and base_venue.canonical_name:
        base_venue.confidence = "medium"
    if (base_venue.scope_summary and base_venue.ai_policy and
            base_venue.data_policy and len(base_venue.indexing_claims) > 0):
        base_venue.confidence = "high"

    return base_venue, base_regime, log


def build_venue_profile(
    paths: list[Path],
    *,
    roles: dict[str, SourceRole] | None = None,
) -> VenueProfileResult:
    """Build a rich venue profile from multiple local source files.

    Each file is independently extracted, parsed into a VenueModel,
    and then merged into a single comprehensive profile.

    Args:
        paths: Local file paths (guidelines, aims, policies, etc.)
        roles: Optional filename→role mapping overrides.

    Returns:
        VenueProfileResult with merged VenueModel, regime, sources, and merge log.
    """
    sources = register_venue_sources(paths, roles=roles)

    # Build individual venue models from each extracted text
    models: list[tuple[VenueModel, PublicationRegimeModel, VenueProfileSource]] = []
    for src in sources:
        if src.text and src.extraction_status == "extracted":
            venue, regime = build_venue_model(src.text, source_ref=src.source_id)
            models.append((venue, regime, src))

    if not models:
        # No extractable sources — return empty venue with unknowns
        venue = VenueModel(
            venue_model_id=venue_model_id(),
            canonical_name=None,
            venue_type="journal",
            source_refs=[s.source_id for s in sources],
            unknowns=["No text could be extracted from any source file"],
            confidence="none",
        )
        regime = PublicationRegimeModel(
            publication_regime_id=publication_regime_id(),
        )
        return VenueProfileResult(
            venue=venue,
            regime=regime,
            sources=sources,
            merge_log=["No extractable sources found"],
        )

    venue, regime, merge_log = _merge_venue_models(models)

    return VenueProfileResult(
        venue=venue,
        regime=regime,
        sources=sources,
        merge_log=merge_log,
    )
