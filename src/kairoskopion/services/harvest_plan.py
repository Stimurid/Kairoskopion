"""Authority-driven harvest plan builder (P7.3 Track 3).

Maps SourceAuthorityRecords to concrete HarvestTasks: what to fetch,
from where, using which adapter, and what provisional records to create.

No LLM. No fabrication. Plan only — execution is separate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _harvest_task_id() -> str:
    import uuid
    return f"htask_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# HarvestTask model
# ---------------------------------------------------------------------------

HARVEST_TASK_TYPES = (
    "ingest_local_evidence_pack",
    "ingest_discipline_seed",
    "fetch_venue_by_issn",
    "fetch_venue_by_name",
    "fetch_metrics_by_venue",
    "fetch_classifications",
    "fetch_citations",
    "import_source_list",
    "manual_web_lookup",
)

HARVEST_TASK_STATUSES = (
    "planned",
    "ready",
    "in_progress",
    "completed",
    "blocked",
    "skipped",
)


@dataclass
class HarvestTask:
    task_id: str = field(default_factory=_harvest_task_id)
    task_type: str = "manual_web_lookup"
    authority_id: str | None = None
    authority_name: str | None = None
    adapter_hint: str | None = None
    query: str | None = None
    target_venue_ids: list[str] = field(default_factory=list)
    target_issns: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    local_source_ref: str | None = None
    status: str = "planned"
    priority: str = "normal"
    blocked_reason: str | None = None
    result_packet_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> HarvestTask:
        return cls(
            task_id=d.get("task_id", _harvest_task_id()),
            task_type=d.get("task_type", "manual_web_lookup"),
            authority_id=d.get("authority_id"),
            authority_name=d.get("authority_name"),
            adapter_hint=d.get("adapter_hint"),
            query=d.get("query"),
            target_venue_ids=list(d.get("target_venue_ids", [])),
            target_issns=list(d.get("target_issns", [])),
            expected_outputs=list(d.get("expected_outputs", [])),
            local_source_ref=d.get("local_source_ref"),
            status=d.get("status", "planned"),
            priority=d.get("priority", "normal"),
            blocked_reason=d.get("blocked_reason"),
            result_packet_ids=list(d.get("result_packet_ids", [])),
            warnings=list(d.get("warnings", [])),
            created_at=d.get("created_at", _now()),
        )


# ---------------------------------------------------------------------------
# Harvest plan result
# ---------------------------------------------------------------------------

@dataclass
class HarvestPlan:
    plan_id: str = ""
    target_country: str = "RU"
    target_domain: str = "education"
    tasks: list[HarvestTask] = field(default_factory=list)
    ready_count: int = 0
    blocked_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tasks"] = [t.to_dict() for t in self.tasks]
        return d


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

# Maps authority_type to harvest task parameters
_AUTHORITY_TO_HARVEST: dict[str, dict[str, Any]] = {
    "national_journal_registry": {
        "task_types": ["fetch_venue_by_issn", "fetch_venue_by_name"],
        "expected_outputs": ["venue_record", "venue_section_records"],
    },
    "discipline_classification": {
        "task_types": ["ingest_discipline_seed"],
        "expected_outputs": ["discipline_records"],
    },
    "metric_source": {
        "task_types": ["fetch_metrics_by_venue"],
        "expected_outputs": ["venue_metric_records"],
    },
    "citation_database": {
        "task_types": ["fetch_venue_by_issn", "fetch_citations"],
        "expected_outputs": ["venue_record", "citation_data"],
    },
    "journal_index": {
        "task_types": ["fetch_venue_by_issn"],
        "expected_outputs": ["venue_record"],
    },
    "journal_archive_source": {
        "task_types": ["fetch_venue_by_name"],
        "expected_outputs": ["venue_record", "article_archive"],
    },
    "scholarly_search": {
        "task_types": ["fetch_venue_by_name"],
        "expected_outputs": ["venue_record"],
    },
}

# Adapters that are free and enabled
_FREE_ADAPTERS = {
    "openalex", "crossref", "opencitations", "doaj", "unpaywall",
    "cyberleninka",
}

# Adapters that need auth/payment
_BLOCKED_ADAPTERS = {
    "scopus", "wos", "elibrary_ru", "semantic_scholar",
}


def build_authority_harvest_plan(
    authority_records: list[dict[str, Any]],
    target_country: str = "RU",
    target_domain: str = "education",
    evidence_pack_dir: Path | None = None,
    discipline_seed_path: Path | None = None,
    no_paid_api: bool = True,
) -> HarvestPlan:
    """Build a harvest plan from source authority records.

    Returns a HarvestPlan with concrete tasks ordered by priority.
    """
    import uuid
    plan = HarvestPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        target_country=target_country,
        target_domain=target_domain,
    )

    # Phase 1: local evidence pack ingestion (highest priority)
    if evidence_pack_dir and evidence_pack_dir.exists():
        pack_files = sorted(evidence_pack_dir.glob("*_evidence_pack.md"))
        if pack_files:
            task = HarvestTask(
                task_type="ingest_local_evidence_pack",
                query=f"Ingest {len(pack_files)} venue evidence packs",
                local_source_ref=str(evidence_pack_dir),
                expected_outputs=[
                    "venue_records", "venue_section_records",
                    "venue_metric_records", "venue_classification_records",
                ],
                status="ready",
                priority="high",
            )
            plan.tasks.append(task)
            plan.ready_count += 1

    # Phase 2: discipline seed ingestion
    if discipline_seed_path and discipline_seed_path.exists():
        task = HarvestTask(
            task_type="ingest_discipline_seed",
            query=f"Ingest discipline seeds from {discipline_seed_path.name}",
            local_source_ref=str(discipline_seed_path),
            expected_outputs=["discipline_records"],
            status="ready",
            priority="high",
        )
        plan.tasks.append(task)
        plan.ready_count += 1

    # Phase 3: authority-driven tasks
    for auth in authority_records:
        auth_type = auth.get("authority_type", "other")
        auth_id = auth.get("authority_id", "")
        auth_name = auth.get("authority_name", "")
        adapter = auth.get("adapter_hint", "")
        country = auth.get("country", "INTERNATIONAL")

        # Skip if authority country doesn't match target
        if country not in (target_country, "INTERNATIONAL"):
            continue

        harvest_spec = _AUTHORITY_TO_HARVEST.get(auth_type, {})
        task_types = harvest_spec.get("task_types", ["manual_web_lookup"])
        expected = harvest_spec.get("expected_outputs", [])

        for task_type in task_types:
            task = HarvestTask(
                task_type=task_type,
                authority_id=auth_id,
                authority_name=auth_name,
                adapter_hint=adapter,
                query=f"{task_type} via {auth_name}",
                expected_outputs=expected,
            )

            # Determine status based on adapter availability
            if adapter in _FREE_ADAPTERS:
                task.status = "ready"
                task.priority = "normal"
                plan.ready_count += 1
            elif adapter in _BLOCKED_ADAPTERS:
                if no_paid_api:
                    task.status = "blocked"
                    task.blocked_reason = f"Adapter {adapter} requires auth/payment (no_paid_api=True)"
                    plan.blocked_count += 1
                else:
                    task.status = "ready"
                    plan.ready_count += 1
            elif adapter == "manual_url":
                task.status = "planned"
                task.warnings.append("Requires manual web lookup or Chrome MCP")
            else:
                task.status = "planned"

            plan.tasks.append(task)

    plan.tasks.sort(key=lambda t: (
        0 if t.priority == "high" else 1,
        0 if t.status == "ready" else (1 if t.status == "planned" else 2),
    ))

    return plan


def persist_harvest_plan(plan: HarvestPlan, output_path: Path) -> None:
    """Write harvest plan as JSONL (one task per line)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for task in plan.tasks:
            fh.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Harvest plan written: %d tasks → %s", len(plan.tasks), output_path)
