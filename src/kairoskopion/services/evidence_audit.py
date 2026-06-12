"""Evidence Audit Service (spec §15.10).

Checks that outputs have evidence backing and flags unsupported claims.
MVP: checks presence of source_refs, evidence_refs, unknowns on key entities.
Extended: optional source authority assessment and evidence conflict detection.
"""

from __future__ import annotations

from ..enums import (
    AuthorityStrength,
    ConflictResolutionStatus,
    QualityGateStatus,
)
from ..ids import quality_gate_id
from ..quality import QualityGateResult
from ..schema import (
    ArticleModel,
    ComplianceChecklist,
    FitAssessment,
    MismatchMap,
    RiskReport,
    VenueModel,
)
from ..source_authority import (
    EvidenceConflict,
    SourceAuthorityAssessment,
)


def audit_pipeline_evidence(
    article: ArticleModel,
    venue: VenueModel,
    fit: FitAssessment,
    mismatch_map: MismatchMap,
    risk: RiskReport,
    compliance: ComplianceChecklist,
    authority_assessments: list[SourceAuthorityAssessment] | None = None,
    evidence_conflicts: list[EvidenceConflict] | None = None,
) -> QualityGateResult:
    """Run evidence audit across pipeline outputs."""
    warnings: list[str] = []
    blocking: list[str] = []
    missing_sources: list[str] = []
    unsupported: list[str] = []

    # Article must have source refs
    if not article.source_refs:
        missing_sources.append("ArticleModel has no source_refs")

    # Venue must have source refs
    if not venue.source_refs:
        missing_sources.append("VenueModel has no source_refs")

    # Fit axes should have evidence where value is not unknown
    assessed_axes = [a for a in fit.axes if a.get("value") != "unknown"]
    axes_without_evidence = [
        a["axis"] for a in assessed_axes if not a.get("evidence_refs")
    ]
    if axes_without_evidence:
        warnings.append(
            f"FitAssessment axes without evidence_refs: {', '.join(axes_without_evidence)}"
        )

    # Check unknowns are preserved (not empty on entities that should have them)
    if fit.lifecycle_status == "preliminary" and not fit.unknowns:
        warnings.append("Preliminary FitAssessment has no unknowns listed — suspicious")

    # Check risk report has items
    if not risk.risk_items:
        warnings.append("RiskReport has no risk items — may be incomplete")

    # Check compliance has items
    if not compliance.checklist_items:
        warnings.append("ComplianceChecklist has no items — may not have parsed guidelines")

    # Mismatch map should exist if fit is not strong
    if fit.overall_label != "strong_candidate" and not mismatch_map.mismatches:
        warnings.append("Non-strong fit but MismatchMap is empty")

    # --- Source authority checks (optional) ---
    if authority_assessments:
        for assessment in authority_assessments:
            if assessment.unsupported_claims:
                for uc in assessment.unsupported_claims:
                    strength = uc.get("authority_strength", "")
                    if strength == AuthorityStrength.PROHIBITED.value:
                        blocking.append(
                            f"Prohibited authority use: source '{assessment.source_ref}' "
                            f"claim '{uc.get('claim_key', '?')}' "
                            f"scope '{uc.get('authority_scope', '?')}'"
                        )
                    else:
                        unsupported.append(
                            f"Unsupported authority: source '{assessment.source_ref}' "
                            f"claim '{uc.get('claim_key', '?')}'"
                        )

    # --- Evidence conflict checks (optional) ---
    if evidence_conflicts:
        for conflict in evidence_conflicts:
            if conflict.resolution_status == ConflictResolutionStatus.UNRESOLVED.value:
                msg = (
                    f"Unresolved evidence conflict: entity '{conflict.entity_id}' "
                    f"field '{conflict.field_name}' ({conflict.severity})"
                )
                if conflict.severity == "blocking":
                    blocking.append(msg)
                else:
                    warnings.append(msg)

    # Aggregate
    if blocking:
        status = QualityGateStatus.FAILED_BLOCKING.value
    elif missing_sources or warnings or unsupported:
        status = QualityGateStatus.PASSED_WITH_WARNINGS.value
    else:
        status = QualityGateStatus.PASSED.value

    return QualityGateResult(
        gate_id=quality_gate_id(),
        gate_name="evidence_audit",
        status=status,
        blocking_issues=blocking,
        warnings=warnings,
        missing_sources=missing_sources,
        unsupported_claims=unsupported,
        recommendation=(
            "Evidence audit passed with warnings — see details"
            if status == QualityGateStatus.PASSED_WITH_WARNINGS.value
            else "Evidence audit passed" if status == QualityGateStatus.PASSED.value
            else "Evidence audit failed — blocking issues found"
        ),
    )
