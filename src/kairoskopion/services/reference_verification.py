"""Reference verification service — DOI resolution, citation integrity checks.

Verifies references from a BibliographyProfile:
  1. Resolve DOIs via Crossref adapter (mock or real)
  2. Build CitationIntegrityCheck per reference
  3. Compute padding risk heuristic
  4. Aggregate metrics (parse rate, DOI resolution rate)

Standing constraints:
  - Retraction/PubPeer lookup is NOT implemented (stays not_checked)
  - citation_supports_claim stays not_checked (requires LLM)
"""

from __future__ import annotations

import dataclasses as dc
import logging
from typing import Any

from ..adapters.crossref import lookup_doi_auto
from ..enums import RetractionStatus
from ..ids import citation_integrity_check_id, generate_id
from ..schema import BibliographyProfile, ReferenceItem, _DictMixin, _field, _list, _now
from ..source_authority import CitationIntegrityCheck

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dc.dataclass
class ReferenceVerificationResult(_DictMixin):
    verification_id: str = dc.field(default_factory=lambda: generate_id("rvr"))
    bibliography_profile_id: str | None = _field()
    total_references: int = 0
    doi_present_count: int = 0
    doi_resolved_count: int = 0
    doi_unresolved_count: int = 0
    doi_not_in_bibliography: int = 0
    padding_risk_count: int = 0
    checks: list[dict[str, Any]] = _list()
    aggregate_metrics: dict[str, Any] = dc.field(default_factory=dict)
    unknowns: list[str] = _list()
    disclaimer: str = (
        "Reference verification is heuristic. "
        "Retraction/PubPeer status not checked. "
        "citation_supports_claim requires LLM analysis."
    )
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# DOI resolution
# ---------------------------------------------------------------------------

def _resolve_doi(
    doi: str,
    *,
    mode: str = "mock",
    cache_dir: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Resolve a single DOI via Crossref adapter.

    Returns (status, resolved_record_dict | None).
    Status: "resolved", "not_found", "error".
    """
    try:
        from pathlib import Path
        cd = Path(cache_dir) if cache_dir else None
        result = lookup_doi_auto(doi, mode=mode, cache_dir=cd)
        if result.records:
            return "resolved", result.records[0]
        return "not_found", None
    except Exception as exc:
        logger.warning("DOI resolution failed for %s: %s", doi, exc)
        return "error", None


# ---------------------------------------------------------------------------
# Padding risk heuristic
# ---------------------------------------------------------------------------

def _assess_padding_risk(ref: dict[str, Any]) -> str:
    """Heuristic padding risk assessment for a single reference.

    A reference is flagged as potential padding if:
    - No DOI AND no title fragment (unreferenceable)
    - source_kind is "unknown" AND no venue_fragment
    - Appears to be a generic web source with no specifics

    Returns: "low", "medium", "high", or "not_assessed".
    """
    doi = ref.get("doi")
    title = ref.get("title_fragment") or ""
    venue = ref.get("venue_fragment") or ""
    source_kind = ref.get("source_kind", "unknown")
    raw = ref.get("raw_text", "")

    if not doi and not title.strip() and not venue.strip():
        return "high"

    if source_kind == "unknown" and not venue.strip() and not doi:
        return "medium"

    if source_kind == "web_source" and len(raw) < 40:
        return "medium"

    return "low"


# ---------------------------------------------------------------------------
# Main verification function
# ---------------------------------------------------------------------------

def verify_references(
    bib_profile: BibliographyProfile,
    *,
    mode: str = "mock",
    cache_dir: str | None = None,
    article_text: str | None = None,
) -> ReferenceVerificationResult:
    """Verify all references in a bibliography profile.

    Args:
        bib_profile: Parsed bibliography profile with references list.
        mode: "mock" (default) or "real" for Crossref adapter.
        cache_dir: HTTP cache directory for real mode.
        article_text: Manuscript text (reserved for future LLM-based checks).

    Returns:
        ReferenceVerificationResult with per-reference checks and aggregates.
    """
    result = ReferenceVerificationResult(
        bibliography_profile_id=bib_profile.bibliography_profile_id,
    )

    refs = bib_profile.references or []
    result.total_references = len(refs)

    if not refs:
        result.unknowns.append("No references to verify")
        return result

    checks: list[dict[str, Any]] = []
    doi_present = 0
    doi_resolved = 0
    doi_unresolved = 0
    doi_absent = 0
    padding_risk_count = 0

    for ref_data in refs:
        ref = ref_data if isinstance(ref_data, dict) else {}
        ref_id = ref.get("reference_item_id", "")
        doi = ref.get("doi")

        check = CitationIntegrityCheck(
            reference_id=ref_id,
            citation_key=ref.get("author_fragment", "") or "",
        )

        # DOI resolution
        if doi:
            doi_present += 1
            status, resolved = _resolve_doi(doi, mode=mode, cache_dir=cache_dir)
            if status == "resolved":
                check.doi_resolution_status = "resolved"
                check.checked_sources.append("crossref")
                check.status = "verified_partial"
                doi_resolved += 1
                if resolved:
                    check.notes.append(
                        f"Crossref: {resolved.get('title', '?')}"
                    )
            elif status == "not_found":
                check.doi_resolution_status = "not_found"
                check.checked_sources.append("crossref")
                check.status = "unresolved"
                doi_unresolved += 1
                check.notes.append(f"DOI {doi} not found in Crossref")
            else:
                check.doi_resolution_status = "error"
                check.status = "check_failed"
                doi_unresolved += 1
                check.notes.append(f"DOI resolution error for {doi}")
        else:
            doi_absent += 1
            check.doi_resolution_status = "no_doi"
            check.status = "no_doi"
            check.unknowns.append("No DOI — cannot resolve via Crossref")

        # Padding risk
        padding = _assess_padding_risk(ref)
        check.citation_padding_risk = padding
        if padding in ("medium", "high"):
            padding_risk_count += 1

        checks.append(check.to_dict())

    result.checks = checks
    result.doi_present_count = doi_present
    result.doi_resolved_count = doi_resolved
    result.doi_unresolved_count = doi_unresolved
    result.doi_not_in_bibliography = doi_absent
    result.padding_risk_count = padding_risk_count

    # Aggregate metrics
    result.aggregate_metrics = _compute_aggregate_metrics(result)

    return result


def _compute_aggregate_metrics(result: ReferenceVerificationResult) -> dict[str, Any]:
    total = result.total_references
    if total == 0:
        return {"parse_rate": 0.0, "doi_coverage": 0.0, "doi_resolution_rate": 0.0}

    doi_coverage = result.doi_present_count / total
    doi_res_rate = (
        result.doi_resolved_count / result.doi_present_count
        if result.doi_present_count > 0
        else 0.0
    )

    return {
        "total_references": total,
        "doi_coverage": round(doi_coverage, 3),
        "doi_resolution_rate": round(doi_res_rate, 3),
        "doi_resolved": result.doi_resolved_count,
        "doi_unresolved": result.doi_unresolved_count,
        "doi_absent": result.doi_not_in_bibliography,
        "padding_risk_flagged": result.padding_risk_count,
        "retraction_checked": False,
        "pubpeer_checked": False,
    }
