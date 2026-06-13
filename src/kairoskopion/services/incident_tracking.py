"""Incident tracking — record and query pipeline failures and anomalies.

Tracks:
- Quality gate failures (blocking/non-blocking)
- Review loop incidents (blocked changes, user rejections, core violations)
- Adapter failures (timeouts, errors, degradation)
- Agent execution failures

Each incident has severity, affected entity, and resolution status.
"""

from __future__ import annotations

import dataclasses as dc
from enum import Enum
from typing import Any

from ..ids import generate_id
from ..schema import _DictMixin, _field, _list, _now


class IncidentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IncidentCategory(str, Enum):
    QUALITY_GATE_FAILURE = "quality_gate_failure"
    REVIEW_LOOP_BLOCKED = "review_loop_blocked"
    REVIEW_LOOP_REJECTION = "review_loop_rejection"
    CORE_VIOLATION = "core_violation"
    ADAPTER_FAILURE = "adapter_failure"
    AGENT_FAILURE = "agent_failure"
    DATA_INTEGRITY = "data_integrity"
    REFERENCE_INTEGRITY = "reference_integrity"


class ResolutionStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


@dc.dataclass
class Incident(_DictMixin):
    """A tracked incident in the pipeline."""
    incident_id: str = dc.field(default_factory=lambda: generate_id("inc"))
    pipeline_run_id: str | None = _field()
    category: str = IncidentCategory.QUALITY_GATE_FAILURE.value
    severity: str = IncidentSeverity.WARNING.value
    title: str = ""
    description: str = ""
    affected_entity_type: str = ""
    affected_entity_id: str = ""
    source_agent: str = ""
    source_gate: str = ""
    resolution_status: str = ResolutionStatus.OPEN.value
    resolution_note: str = ""
    metadata: dict[str, Any] = dc.field(default_factory=dict)
    created_at: str = dc.field(default_factory=_now)
    resolved_at: str | None = _field()


@dc.dataclass
class IncidentLog(_DictMixin):
    """Collection of incidents from a pipeline run or session."""
    log_id: str = dc.field(default_factory=lambda: generate_id("ilog"))
    pipeline_run_id: str | None = _field()
    incidents: list[dict[str, Any]] = _list()
    total_count: int = 0
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    open_count: int = 0
    resolved_count: int = 0
    has_blocking_incidents: bool = False
    created_at: str = dc.field(default_factory=_now)


class IncidentTracker:
    """Collects and queries incidents during a pipeline run."""

    def __init__(self, pipeline_run_id: str | None = None) -> None:
        self._pipeline_run_id = pipeline_run_id
        self._incidents: list[Incident] = []

    @property
    def incidents(self) -> list[Incident]:
        return list(self._incidents)

    def record(
        self,
        category: str,
        severity: str,
        title: str,
        *,
        description: str = "",
        affected_entity_type: str = "",
        affected_entity_id: str = "",
        source_agent: str = "",
        source_gate: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Incident:
        """Record a new incident."""
        incident = Incident(
            pipeline_run_id=self._pipeline_run_id,
            category=category,
            severity=severity,
            title=title,
            description=description,
            affected_entity_type=affected_entity_type,
            affected_entity_id=affected_entity_id,
            source_agent=source_agent,
            source_gate=source_gate,
            metadata=metadata or {},
        )
        self._incidents.append(incident)
        return incident

    def record_gate_failure(
        self,
        gate_name: str,
        blocking_issues: list[str],
        *,
        severity: str = IncidentSeverity.ERROR.value,
        metadata: dict[str, Any] | None = None,
    ) -> Incident:
        """Record a quality gate failure incident."""
        return self.record(
            category=IncidentCategory.QUALITY_GATE_FAILURE.value,
            severity=severity,
            title=f"Gate '{gate_name}' failed",
            description="; ".join(blocking_issues),
            source_gate=gate_name,
            metadata=metadata or {},
        )

    def record_review_block(
        self,
        change_id: str,
        reason: str,
        *,
        matched_core_elements: list[str] | None = None,
    ) -> Incident:
        """Record a review loop blocked change."""
        return self.record(
            category=IncidentCategory.REVIEW_LOOP_BLOCKED.value,
            severity=IncidentSeverity.WARNING.value,
            title=f"Change '{change_id}' blocked by protected core",
            description=reason,
            affected_entity_type="RewritePlanChange",
            affected_entity_id=change_id,
            metadata={"matched_core_elements": matched_core_elements or []},
        )

    def record_review_rejection(
        self,
        change_id: str,
        user_reason: str,
    ) -> Incident:
        """Record a user rejection from the review loop."""
        return self.record(
            category=IncidentCategory.REVIEW_LOOP_REJECTION.value,
            severity=IncidentSeverity.INFO.value,
            title=f"Change '{change_id}' rejected by user",
            description=user_reason,
            affected_entity_type="RewritePlanChange",
            affected_entity_id=change_id,
        )

    def record_adapter_failure(
        self,
        adapter_id: str,
        error: str,
    ) -> Incident:
        """Record an adapter failure."""
        return self.record(
            category=IncidentCategory.ADAPTER_FAILURE.value,
            severity=IncidentSeverity.ERROR.value,
            title=f"Adapter '{adapter_id}' failed",
            description=error,
            source_agent=adapter_id,
        )

    def record_reference_issue(
        self,
        reference_id: str,
        issue: str,
        *,
        severity: str = IncidentSeverity.WARNING.value,
    ) -> Incident:
        """Record a reference integrity issue."""
        return self.record(
            category=IncidentCategory.REFERENCE_INTEGRITY.value,
            severity=severity,
            title=f"Reference '{reference_id}' has integrity issue",
            description=issue,
            affected_entity_type="ReferenceItem",
            affected_entity_id=reference_id,
        )

    def resolve(self, incident_id: str, note: str = "") -> bool:
        """Mark an incident as resolved."""
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                inc.resolution_status = ResolutionStatus.RESOLVED.value
                inc.resolution_note = note
                inc.resolved_at = _now()
                return True
        return False

    def by_category(self, category: str) -> list[Incident]:
        return [i for i in self._incidents if i.category == category]

    def by_severity(self, severity: str) -> list[Incident]:
        return [i for i in self._incidents if i.severity == severity]

    def open_incidents(self) -> list[Incident]:
        return [
            i for i in self._incidents
            if i.resolution_status == ResolutionStatus.OPEN.value
        ]

    def has_blocking(self) -> bool:
        """Check if there are any critical or error-severity open incidents."""
        for i in self._incidents:
            if (
                i.resolution_status == ResolutionStatus.OPEN.value
                and i.severity in (IncidentSeverity.CRITICAL.value, IncidentSeverity.ERROR.value)
            ):
                return True
        return False

    def to_log(self) -> IncidentLog:
        """Build an IncidentLog summary."""
        log = IncidentLog(pipeline_run_id=self._pipeline_run_id)
        log.incidents = [i.to_dict() for i in self._incidents]
        log.total_count = len(self._incidents)
        log.critical_count = len(self.by_severity(IncidentSeverity.CRITICAL.value))
        log.error_count = len(self.by_severity(IncidentSeverity.ERROR.value))
        log.warning_count = len(self.by_severity(IncidentSeverity.WARNING.value))
        log.info_count = len(self.by_severity(IncidentSeverity.INFO.value))
        log.open_count = len(self.open_incidents())
        log.resolved_count = log.total_count - log.open_count
        log.has_blocking_incidents = self.has_blocking()
        return log
