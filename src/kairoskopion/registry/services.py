"""Registry-first service layer (P6 Tracks 7-8).

Provides registry-first lookup wrappers that check local registries
before creating acquisition tasks for missing data.

Doctrine: search local base first → if found, return record →
if not found, create acquisition task → do NOT invent facts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import (
    EvidenceRef,
    SourceAcquisitionTask,
    SourcePacket,
    DisciplineRecord,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueMetricRecord,
)
from .store import (
    BaseRegistry,
    AcquisitionTaskStore,
    SourcePacketStore,
    load_registry,
)
from .status import record_usage_status

logger = logging.getLogger(__name__)


class RegistryHub:
    """Central access point for all P6 registries.

    Lazy-loads registries from a data directory. Provides registry-first
    lookup methods that check local records before creating acquisition tasks.
    """

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or Path("data/registry")
        self._registries: dict[str, BaseRegistry] = {}
        self._tasks: AcquisitionTaskStore | None = None
        self._packets: SourcePacketStore | None = None

    def _get_registry(self, record_type: str) -> BaseRegistry:
        if record_type not in self._registries:
            self._registries[record_type] = load_registry(
                record_type, self._data_dir,
            )
        return self._registries[record_type]

    @property
    def tasks(self) -> AcquisitionTaskStore:
        if self._tasks is None:
            self._tasks = AcquisitionTaskStore(
                self._data_dir / "acquisition_tasks.jsonl",
            )
        return self._tasks

    @property
    def packets(self) -> SourcePacketStore:
        if self._packets is None:
            self._packets = SourcePacketStore(
                self._data_dir / "source_packets.jsonl",
            )
        return self._packets

    def disciplines(self) -> BaseRegistry:
        return self._get_registry("discipline")

    def venues(self) -> BaseRegistry:
        return self._get_registry("venue")

    def venue_sections(self) -> BaseRegistry:
        return self._get_registry("venue_section")

    def venue_metrics(self) -> BaseRegistry:
        return self._get_registry("venue_metric")

    def venue_classifications(self) -> BaseRegistry:
        return self._get_registry("venue_classification")

    def epistemic_frameworks(self) -> BaseRegistry:
        return self._get_registry("epistemic_framework")

    def classification_systems(self) -> BaseRegistry:
        return self._get_registry("classification_system")

    def subject_categories(self) -> BaseRegistry:
        return self._get_registry("subject_category")

    # -- registry-first lookups ----------------------------------------

    def lookup_discipline(
        self,
        query: str,
        *,
        agent_name: str | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """Search discipline registry. If found, return record + status.
        If not found, create an acquisition task.

        Returns: {"found": bool, "record": DisciplineRecord|None,
                  "usage_status": str, "task": SourceAcquisitionTask|None}
        """
        reg = self.disciplines()
        results = reg.search(query, limit=1)
        if results:
            rec = results[0]
            return {
                "found": True,
                "record": rec,
                "usage_status": record_usage_status(rec),
                "task": None,
            }
        task = SourceAcquisitionTask(
            task_type="discipline_lookup",
            query=query,
            reason=f"No local discipline record for {query!r}",
            target_sources=["vak", "oecd_ford", "openalex"],
            created_by_agent=agent_name,
            related_case_id=case_id,
        )
        self.tasks.add(task)
        return {
            "found": False,
            "record": None,
            "usage_status": "unknown",
            "task": task,
        }

    def lookup_venue(
        self,
        query: str,
        *,
        issn: str | None = None,
        agent_name: str | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """Search venue registry by name or ISSN."""
        reg = self.venues()
        if issn:
            for rec in reg.list_all():
                if rec.issn == issn or rec.eissn == issn:
                    return {
                        "found": True,
                        "record": rec,
                        "usage_status": record_usage_status(rec),
                        "task": None,
                    }
        results = reg.search(query, limit=1)
        if results:
            rec = results[0]
            return {
                "found": True,
                "record": rec,
                "usage_status": record_usage_status(rec),
                "task": None,
            }
        task = SourceAcquisitionTask(
            task_type="venue_lookup",
            query=f"{query} (ISSN: {issn})" if issn else query,
            reason=f"No local venue record for {query!r}",
            target_sources=["crossref", "openalex", "doaj"],
            created_by_agent=agent_name,
            related_case_id=case_id,
        )
        self.tasks.add(task)
        return {
            "found": False,
            "record": None,
            "usage_status": "unknown",
            "task": task,
        }

    def lookup_venue_sections(
        self,
        venue_id: str,
    ) -> list[VenueSectionRecord]:
        """Return all sections for a given venue."""
        reg = self.venue_sections()
        return [
            rec for rec in reg.list_all()
            if rec.parent_venue_id == venue_id
        ]

    def lookup_venue_metrics(
        self,
        venue_id: str,
        *,
        year: str | None = None,
        database: str | None = None,
    ) -> list[VenueMetricRecord]:
        """Return metrics for a venue, optionally filtered."""
        reg = self.venue_metrics()
        results = []
        for rec in reg.list_all():
            if rec.venue_id != venue_id:
                continue
            if year and rec.year != year:
                continue
            if database and rec.database != database:
                continue
            results.append(rec)
        return results

    def ingest_source_packet(
        self,
        packet: SourcePacket,
        *,
        target_registry: str | None = None,
    ) -> SourcePacket:
        """Store a source packet and optionally create a provisional record."""
        self.packets.add(packet)
        return packet
