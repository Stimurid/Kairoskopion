"""Source Authority Service.

Deterministic rules for what a source access mode is allowed to claim,
detection of unsupported authority use, and evidence conflict reconciliation.

Architectural rule: full-text access is not metadata authority; metadata
authority is not publication-pattern authority; official venue claim is not
independent verification; corpus evidence is not formal policy; user memory
is not public fact.
"""

from __future__ import annotations

from ..enums import (
    AuthorityStrength,
    ConflictResolutionStatus,
    ConflictSeverity,
    ConflictType,
    SourceAccessMode,
    SourceAuthorityScope,
)
from ..source_authority import (
    EvidenceConflict,
    EvidenceReconciliationResult,
    SourceAuthorityAssessment,
    SourceAuthorityClaim,
)


# ---------------------------------------------------------------------------
# Authority matrix: which access modes can support which scopes
# ---------------------------------------------------------------------------

# Each entry: access_mode -> set of (scope, max_strength) pairs.
# Scopes not listed are PROHIBITED for that access mode.

_AUTHORITY_MATRIX: dict[str, dict[str, str]] = {
    SourceAccessMode.METADATA_API.value: {
        SourceAuthorityScope.VENUE_IDENTITY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.ISSN_IDENTITY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.PUBLISHER_IDENTITY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.ARTICLE_METADATA.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.CITATION_RELATIONS.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.INDEXING_STATUS.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.PUBLICATION_REGIME.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.FULL_TEXT_PDF.value: {
        SourceAuthorityScope.ARTICLE_FULL_TEXT.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.CORPUS_PATTERN.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.CITATION_RELATIONS.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.ARTICLE_METADATA.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.FULL_TEXT_HTML.value: {
        SourceAuthorityScope.ARTICLE_FULL_TEXT.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.CORPUS_PATTERN.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.CITATION_RELATIONS.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.ARTICLE_METADATA.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.OFFICIAL_WEBPAGE.value: {
        SourceAuthorityScope.VENUE_IDENTITY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.FORMAL_REQUIREMENTS.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.SUBMISSION_POLICY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.PUBLICATION_REGIME.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.AI_DISCLOSURE_POLICY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.REPORTING_GUIDELINE.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.EDITORIAL_BOARD_SIGNAL.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.PUBLISHER_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
    },
    SourceAccessMode.SUBMISSION_SYSTEM_PAGE.value: {
        SourceAuthorityScope.FORMAL_REQUIREMENTS.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.SUBMISSION_POLICY.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.AUTHOR_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.AFFILIATION_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.FUNDING_STATEMENT.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.AI_DISCLOSURE_POLICY.value: AuthorityStrength.SUPPORTED.value,
    },
    SourceAccessMode.EDITORIAL_BOARD_PAGE.value: {
        SourceAuthorityScope.EDITORIAL_BOARD_SIGNAL.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.VENUE_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.COMMUNITY_SIGNAL.value: AuthorityStrength.SUPPORTED.value,
    },
    SourceAccessMode.CORPUS_SAMPLE.value: {
        SourceAuthorityScope.CORPUS_PATTERN.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.CITATION_RELATIONS.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.PUBLICATION_REGIME.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.CITATION_GRAPH.value: {
        SourceAuthorityScope.CITATION_RELATIONS.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.ARTICLE_METADATA.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.INDEX_REGISTRY.value: {
        SourceAuthorityScope.INDEXING_STATUS.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.VENUE_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.ISSN_IDENTITY.value: AuthorityStrength.SUPPORTED.value,
    },
    SourceAccessMode.USER_MEMORY.value: {
        SourceAuthorityScope.PRIOR_OUTCOME.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.TACIT_SIGNAL.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.COMMUNITY_SIGNAL.value: AuthorityStrength.WEAK.value,
    },
    SourceAccessMode.REVIEW_HISTORY.value: {
        SourceAuthorityScope.PRIOR_OUTCOME.value: AuthorityStrength.AUTHORITATIVE.value,
        SourceAuthorityScope.EDITORIAL_BOARD_SIGNAL.value: AuthorityStrength.WEAK.value,
        SourceAuthorityScope.TACIT_SIGNAL.value: AuthorityStrength.SUPPORTED.value,
    },
    SourceAccessMode.MANUAL_NOTE.value: {
        SourceAuthorityScope.TACIT_SIGNAL.value: AuthorityStrength.SUPPORTED.value,
        SourceAuthorityScope.PRIOR_OUTCOME.value: AuthorityStrength.WEAK.value,
    },
}

_ALL_SCOPES = {s.value for s in SourceAuthorityScope}


def _get_max_strength(access_mode: str, scope: str) -> str | None:
    """Return max authority strength for an access_mode/scope pair, or None if prohibited."""
    mode_rules = _AUTHORITY_MATRIX.get(access_mode, {})
    return mode_rules.get(scope)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assess_source_authority(
    source_ref: str,
    access_modes: list[str],
) -> SourceAuthorityAssessment:
    """Assess what authority scopes a source can support given its access modes."""
    supported_scopes: set[str] = set()
    prohibited_scopes: set[str] = set()
    notes: list[str] = []

    for mode in access_modes:
        mode_rules = _AUTHORITY_MATRIX.get(mode, {})
        for scope in mode_rules:
            supported_scopes.add(scope)

    prohibited_scopes = _ALL_SCOPES - supported_scopes
    if not access_modes:
        notes.append("No access modes provided; all scopes prohibited")
        prohibited_scopes = _ALL_SCOPES.copy()

    return SourceAuthorityAssessment(
        source_ref=source_ref,
        access_modes=list(access_modes),
        authority_scopes=sorted(supported_scopes),
        prohibited_scopes=sorted(prohibited_scopes),
        notes=notes,
    )


def check_claim_authority(claim: SourceAuthorityClaim) -> SourceAuthorityClaim:
    """Validate and potentially downgrade a claim based on authority rules.

    Returns the claim with adjusted authority_strength and limitations.
    """
    max_strength = _get_max_strength(claim.access_mode, claim.authority_scope)

    if max_strength is None:
        return SourceAuthorityClaim(
            claim_id=claim.claim_id,
            source_ref=claim.source_ref,
            evidence_ref=claim.evidence_ref,
            access_mode=claim.access_mode,
            authority_scope=claim.authority_scope,
            claim_key=claim.claim_key,
            claim_value=claim.claim_value,
            authority_strength=AuthorityStrength.PROHIBITED.value,
            supported_entity_id=claim.supported_entity_id,
            limitations=claim.limitations + [
                f"Access mode '{claim.access_mode}' cannot support "
                f"scope '{claim.authority_scope}'"
            ],
            confidence="none",
            created_at=claim.created_at,
            unknowns=claim.unknowns,
        )

    strength_order = [
        AuthorityStrength.AUTHORITATIVE.value,
        AuthorityStrength.SUPPORTED.value,
        AuthorityStrength.WEAK.value,
        AuthorityStrength.UNSUPPORTED.value,
    ]
    claimed_idx = (
        strength_order.index(claim.authority_strength)
        if claim.authority_strength in strength_order
        else len(strength_order)
    )
    max_idx = strength_order.index(max_strength)

    if claimed_idx < max_idx:
        return SourceAuthorityClaim(
            claim_id=claim.claim_id,
            source_ref=claim.source_ref,
            evidence_ref=claim.evidence_ref,
            access_mode=claim.access_mode,
            authority_scope=claim.authority_scope,
            claim_key=claim.claim_key,
            claim_value=claim.claim_value,
            authority_strength=max_strength,
            supported_entity_id=claim.supported_entity_id,
            limitations=claim.limitations + [
                f"Downgraded from '{claim.authority_strength}' to "
                f"'{max_strength}': access mode '{claim.access_mode}' "
                f"caps scope '{claim.authority_scope}' at '{max_strength}'"
            ],
            confidence=claim.confidence,
            created_at=claim.created_at,
            unknowns=claim.unknowns,
        )

    return claim


def detect_conflicts(
    entity_id: str,
    field_name: str,
    claims: list[SourceAuthorityClaim],
) -> EvidenceConflict | None:
    """Detect if claims for the same entity field conflict."""
    if len(claims) < 2:
        return None

    values = set()
    for c in claims:
        val = c.claim_value
        if isinstance(val, dict):
            val = str(sorted(val.items()))
        values.add(str(val))

    if len(values) <= 1:
        return None

    severity = ConflictSeverity.WARNING.value
    strength_values = [c.authority_strength for c in claims]
    if AuthorityStrength.AUTHORITATIVE.value in strength_values:
        severity = ConflictSeverity.BLOCKING.value

    return EvidenceConflict(
        entity_id=entity_id,
        field_name=field_name,
        conflicting_claims=[c.to_dict() for c in claims],
        conflict_type=ConflictType.VALUE_MISMATCH.value,
        severity=severity,
        resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
    )


def reconcile_evidence(
    entity_id: str,
    claims: list[SourceAuthorityClaim],
    conflicts: list[EvidenceConflict],
) -> EvidenceReconciliationResult:
    """Produce a reconciliation result from claims and conflicts."""
    checked = [check_claim_authority(c) for c in claims]
    resolved: list[dict] = []
    downgraded: list[dict] = []
    authority_notes: list[str] = []
    unknowns: list[str] = []

    for c in checked:
        d = c.to_dict()
        if c.authority_strength == AuthorityStrength.PROHIBITED.value:
            downgraded.append(d)
            authority_notes.append(
                f"Claim '{c.claim_key}' from '{c.access_mode}' prohibited "
                f"for scope '{c.authority_scope}'"
            )
        elif c.limitations and c.limitations != claims[checked.index(c)].limitations:
            downgraded.append(d)
        else:
            resolved.append(d)

    unresolved = [c.to_dict() for c in conflicts
                  if c.resolution_status == ConflictResolutionStatus.UNRESOLVED.value]

    if unresolved:
        unknowns.append(
            f"{len(unresolved)} conflict(s) remain unresolved for entity {entity_id}"
        )

    return EvidenceReconciliationResult(
        entity_id=entity_id,
        resolved_claims=resolved,
        unresolved_conflicts=unresolved,
        downgraded_claims=downgraded,
        authority_notes=authority_notes,
        unknowns=unknowns,
    )
