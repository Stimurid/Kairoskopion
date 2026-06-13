"""Quality gate evaluation for Kairoskopion pipelines."""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from .enums import QualityGateStatus
from .ids import quality_gate_id
from .schema import _DictMixin, _field, _list, _now


@dc.dataclass
class QualityGateResult(_DictMixin):
    gate_id: str = dc.field(default_factory=quality_gate_id)
    gate_name: str = ""
    pipeline_run_id: str | None = _field()
    status: str = QualityGateStatus.NOT_APPLICABLE.value
    blocking_issues: list[str] = _list()
    warnings: list[str] = _list()
    missing_sources: list[str] = _list()
    unknown_fields: list[str] = _list()
    stale_sources: list[str] = _list()
    unsupported_claims: list[str] = _list()
    required_user_decisions: list[str] = _list()
    recommendation: str | None = _field()
    evaluated_at: str = dc.field(default_factory=_now)


def evaluate_fit_gate(
    *,
    has_article_source: bool = False,
    has_venue_source: bool = False,
    has_scenario: bool = False,
    has_evidence_per_axis: bool = False,
    has_context_pack: bool = False,
) -> QualityGateResult:
    """Evaluate the one-venue fit quality gate (spec §30.1)."""
    gate = QualityGateResult(gate_name="one_venue_fit")
    issues: list[str] = []
    warnings: list[str] = []

    if not has_article_source:
        issues.append("No article source registered")
    if not has_venue_source:
        issues.append("No venue source registered")
    if not has_scenario:
        warnings.append("SubmissionScenario missing — fit is preliminary")

    if not has_evidence_per_axis:
        warnings.append("Not all fit axes have evidence refs")
    if not has_context_pack:
        warnings.append("No ContextPack created")

    if issues:
        gate.status = QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value
        gate.recommendation = "Preliminary fit only — collect missing sources"
    elif warnings:
        gate.status = QualityGateStatus.PASSED_WITH_WARNINGS.value
        gate.recommendation = "Light profile fit — evidence gaps remain"
    else:
        gate.status = QualityGateStatus.PASSED.value
        gate.recommendation = "Evidence-backed fit assessment possible"

    gate.blocking_issues = issues
    gate.warnings = warnings
    return gate


def evaluate_evidence_completeness_gate(
    *,
    adapter_results: list[dict] | None = None,
    required_sources: list[str] | None = None,
    stale_threshold_days: int = 90,
) -> QualityGateResult:
    """Evaluate evidence source completeness and freshness (spec §30.2).

    Checks:
    - All required sources are present and not errored
    - Source freshness (fetched_at within stale_threshold_days)
    - No sources have UNKNOWN evidence status
    """
    gate = QualityGateResult(gate_name="evidence_completeness")
    issues: list[str] = []
    warnings: list[str] = []

    results = adapter_results or []
    required = set(required_sources or [])

    present_adapters: set[str] = set()
    for r in results:
        adapter_id = r.get("adapter_id", "")
        present_adapters.add(adapter_id)
        status = r.get("status", "")

        if status in ("error", "unavailable"):
            issues.append(f"Source {adapter_id} returned {status}")
            continue

        if r.get("evidence_status") == "UNKNOWN":
            warnings.append(f"Source {adapter_id} has UNKNOWN evidence status")

        fetched = r.get("fetched_at") or r.get("cached_at")
        if fetched:
            from datetime import datetime, timezone, timedelta
            try:
                fetched_dt = datetime.fromisoformat(fetched)
                age = datetime.now(timezone.utc) - fetched_dt
                if age > timedelta(days=stale_threshold_days):
                    gate.stale_sources.append(adapter_id)
                    warnings.append(
                        f"Source {adapter_id} is {age.days} days old "
                        f"(threshold: {stale_threshold_days})"
                    )
            except (ValueError, TypeError):
                pass

    missing = required - present_adapters
    if missing:
        for src in sorted(missing):
            gate.missing_sources.append(src)
            warnings.append(f"Required source {src} not found in results")

    if not results:
        issues.append("No evidence sources provided")

    if issues:
        gate.status = QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value
        gate.recommendation = "Evidence gaps — collect missing or errored sources"
    elif warnings:
        gate.status = QualityGateStatus.PASSED_WITH_WARNINGS.value
        gate.recommendation = "Evidence present with gaps — review stale or missing sources"
    else:
        gate.status = QualityGateStatus.PASSED.value
        gate.recommendation = "Evidence sources complete and fresh"

    gate.blocking_issues = issues
    gate.warnings = warnings
    return gate


def evaluate_reference_integrity_gate(
    *,
    verification_result: dict | None = None,
    min_doi_coverage: float = 0.3,
    max_padding_risk_ratio: float = 0.2,
) -> QualityGateResult:
    """Evaluate reference verification results for submission readiness.

    Checks:
    - DOI coverage above threshold
    - Padding risk below threshold
    - No unresolved DOIs that could indicate fabricated references
    """
    gate = QualityGateResult(gate_name="reference_integrity")
    issues: list[str] = []
    warnings: list[str] = []

    if not verification_result:
        gate.status = QualityGateStatus.NOT_APPLICABLE.value
        gate.recommendation = "No reference verification data available"
        return gate

    total = verification_result.get("total_references", 0)
    if total == 0:
        warnings.append("No references found in manuscript")
        gate.status = QualityGateStatus.PASSED_WITH_WARNINGS.value
        gate.warnings = warnings
        gate.recommendation = "No references to verify"
        return gate

    metrics = verification_result.get("aggregate_metrics", {})
    doi_coverage = metrics.get("doi_coverage", 0.0)
    padding_count = verification_result.get("padding_risk_count", 0)
    padding_ratio = padding_count / total if total > 0 else 0.0
    unresolved = verification_result.get("doi_unresolved_count", 0)

    if doi_coverage < min_doi_coverage:
        warnings.append(
            f"DOI coverage {doi_coverage:.0%} below threshold {min_doi_coverage:.0%}"
        )

    if padding_ratio > max_padding_risk_ratio:
        issues.append(
            f"Padding risk ratio {padding_ratio:.0%} exceeds threshold "
            f"{max_padding_risk_ratio:.0%} ({padding_count}/{total} references)"
        )

    if unresolved > 0:
        warnings.append(
            f"{unresolved} DOI(s) could not be resolved — verify these references"
        )

    if not metrics.get("retraction_checked", False):
        gate.unknown_fields.append("retraction_status")
    if not metrics.get("pubpeer_checked", False):
        gate.unknown_fields.append("pubpeer_status")

    if issues:
        gate.status = QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value
        gate.recommendation = "Reference integrity concerns — review flagged references"
    elif warnings:
        gate.status = QualityGateStatus.PASSED_WITH_WARNINGS.value
        gate.recommendation = "References pass basic checks with caveats"
    else:
        gate.status = QualityGateStatus.PASSED.value
        gate.recommendation = "Reference integrity verified"

    gate.blocking_issues = issues
    gate.warnings = warnings
    return gate


def evaluate_protected_core_gate(
    *,
    core_validation: dict | None = None,
) -> QualityGateResult:
    """Evaluate whether protected core is respected in rewrite plan.

    Blocks submission if changes touch protected core without consent.
    """
    gate = QualityGateResult(gate_name="protected_core")

    if not core_validation:
        gate.status = QualityGateStatus.NOT_APPLICABLE.value
        gate.recommendation = "No core validation data available"
        return gate

    blocked = core_validation.get("blocked_count", 0)
    requires_consent = core_validation.get("requires_user_consent", False)

    if requires_consent and blocked > 0:
        gate.status = QualityGateStatus.FAILED_BLOCKING.value
        gate.blocking_issues = [
            f"{blocked} change(s) touch protected core without user consent"
        ]
        gate.required_user_decisions = [
            "Review and approve/reject changes that affect protected core elements"
        ]
        gate.recommendation = "Cannot proceed — protected core changes need user consent"
    else:
        gate.status = QualityGateStatus.PASSED.value
        gate.recommendation = "Protected core respected"

    return gate


def evaluate_submission_gate(
    *,
    has_fresh_guidelines: bool = False,
    has_metadata: bool = False,
    has_files_list: bool = False,
    has_statements: bool = False,
    blocking_risks_resolved: bool = False,
) -> QualityGateResult:
    """Evaluate the submission-pack readiness gate (spec §30.3)."""
    gate = QualityGateResult(gate_name="submission_pack")
    issues: list[str] = []
    warnings: list[str] = []

    if not has_fresh_guidelines:
        issues.append("Author guidelines not fresh")
    if not has_metadata:
        issues.append("Required metadata missing")
    if not has_files_list:
        warnings.append("Files list incomplete")
    if not has_statements:
        warnings.append("Required statements not present")
    if not blocking_risks_resolved:
        issues.append("Blocking risks unresolved")

    if issues:
        gate.status = QualityGateStatus.FAILED_BLOCKING.value
        gate.recommendation = "Not ready for submission — resolve blocking issues"
    elif warnings:
        gate.status = QualityGateStatus.PASSED_WITH_WARNINGS.value
        gate.recommendation = "Ready with caveats — review warnings"
    else:
        gate.status = QualityGateStatus.PASSED.value
        gate.recommendation = "Ready for manual submission"

    gate.blocking_issues = issues
    gate.warnings = warnings
    return gate
