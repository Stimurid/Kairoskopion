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
