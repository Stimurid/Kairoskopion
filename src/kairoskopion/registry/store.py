"""Generic JSONL-backed registry store (P6).

Each registry type gets a JSONL file. Records are loaded into memory on
init, mutations are appended to JSONL on write.

No auto-promotion: new records default to provisional + pending.
Accept/reject requires explicit action.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar, Generic, Type

from .models import (
    EvidenceRef,
    SourcePacket,
    SourceAcquisitionTask,
    DisciplineRecord,
    EpistemicFrameworkRecord,
    VenueRegistryRecord,
    VenueSectionRecord,
    ClassificationSystemRecord,
    SubjectCategoryRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    SOURCE_STATUSES,
    REVIEW_STATUSES,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON in %s:%d: %s", path, i, exc)
    return records


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Record type registry (maps string names to classes)
# ---------------------------------------------------------------------------

_RECORD_TYPES: dict[str, tuple[Type, str]] = {
    "discipline": (DisciplineRecord, "discipline_id"),
    "epistemic_framework": (EpistemicFrameworkRecord, "framework_id"),
    "venue": (VenueRegistryRecord, "venue_id"),
    "venue_section": (VenueSectionRecord, "section_id"),
    "classification_system": (ClassificationSystemRecord, "system_id"),
    "subject_category": (SubjectCategoryRecord, "category_id"),
    "venue_classification": (VenueClassificationRecord, "record_id"),
    "venue_metric": (VenueMetricRecord, "metric_id"),
}


# ---------------------------------------------------------------------------
# BaseRegistry
# ---------------------------------------------------------------------------

class BaseRegistry:
    """In-memory registry backed by a JSONL file.

    Supports: list, get, search, add_provisional, accept, reject,
    update_review_status, append_evidence_ref, find_duplicate, export.
    """

    def __init__(
        self,
        record_type: str,
        jsonl_path: Path | None = None,
    ):
        if record_type not in _RECORD_TYPES:
            raise ValueError(f"Unknown record_type: {record_type!r}")
        self._record_type = record_type
        self._cls, self._id_field = _RECORD_TYPES[record_type]
        self._jsonl_path = jsonl_path
        self._by_id: dict[str, Any] = {}

        if jsonl_path:
            self._load()

    def _load(self) -> None:
        if not self._jsonl_path:
            return
        raw_records = _read_jsonl(self._jsonl_path)
        for raw in raw_records:
            rec = self._cls.from_dict(raw)
            rid = getattr(rec, self._id_field)
            self._by_id[rid] = rec

    def _persist(self, record: Any) -> None:
        if self._jsonl_path:
            _append_jsonl(self._jsonl_path, record.to_dict())

    # -- reads ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self._by_id)

    def list_all(self) -> list[Any]:
        return list(self._by_id.values())

    def get(self, record_id: str) -> Any | None:
        return self._by_id.get(record_id)

    def search(self, query: str, limit: int = 20) -> list[Any]:
        if not query or not query.strip():
            return self.list_all()[:limit]
        q = query.lower()
        scored: list[tuple[int, Any]] = []
        for rec in self._by_id.values():
            score = self._search_score(rec, q)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: -x[0])
        return [rec for _, rec in scored[:limit]]

    def _search_score(self, rec: Any, query: str) -> int:
        score = 0
        for attr in ("canonical_name", "label", "name", "section_name"):
            val = getattr(rec, attr, None)
            if val and query in val.lower():
                score += 5
        if hasattr(rec, "display_names"):
            for name in rec.display_names.values():
                if name and query in name.lower():
                    score += 5
        if hasattr(rec, "aliases"):
            for alias in rec.aliases:
                if alias and query in alias.lower():
                    score += 3
        if hasattr(rec, "code"):
            code = rec.code
            if code and query in code.lower():
                score += 4
        rid = getattr(rec, self._id_field, "")
        if rid and query in rid.lower():
            score += 2
        return score

    def find_duplicate(self, record: Any) -> Any | None:
        rid = getattr(record, self._id_field)
        if rid in self._by_id:
            return self._by_id[rid]
        if hasattr(record, "canonical_name") and record.canonical_name:
            name = record.canonical_name.lower()
            for existing in self._by_id.values():
                if hasattr(existing, "canonical_name") and existing.canonical_name:
                    if existing.canonical_name.lower() == name:
                        return existing
        if hasattr(record, "issn") and record.issn:
            for existing in self._by_id.values():
                if hasattr(existing, "issn") and existing.issn == record.issn:
                    return existing
        return None

    # -- writes --------------------------------------------------------

    def add_provisional(
        self,
        record: Any,
        evidence_refs: list[EvidenceRef] | None = None,
    ) -> Any:
        record.source_status = "provisional"
        record.review_status = "pending"
        record.updated_at = _now()
        if evidence_refs and hasattr(record, "evidence_refs"):
            record.evidence_refs = list(record.evidence_refs or []) + list(evidence_refs)
        rid = getattr(record, self._id_field)
        self._by_id[rid] = record
        self._persist(record)
        return record

    def accept(self, record_id: str, reviewer_note: str | None = None) -> Any | None:
        rec = self._by_id.get(record_id)
        if rec is None:
            return None
        rec.source_status = "accepted"
        rec.review_status = "curator_confirmed"
        rec.updated_at = _now()
        if reviewer_note and hasattr(rec, "provenance"):
            rec.provenance = (rec.provenance or "") + f" [accepted: {reviewer_note}]"
        self._persist(rec)
        return rec

    def reject(self, record_id: str, reviewer_note: str | None = None) -> Any | None:
        rec = self._by_id.get(record_id)
        if rec is None:
            return None
        rec.source_status = "rejected"
        rec.review_status = "rejected"
        rec.updated_at = _now()
        if reviewer_note and hasattr(rec, "provenance"):
            rec.provenance = (rec.provenance or "") + f" [rejected: {reviewer_note}]"
        self._persist(rec)
        return rec

    def update_review_status(
        self, record_id: str, review_status: str,
    ) -> Any | None:
        if review_status not in REVIEW_STATUSES:
            raise ValueError(f"Invalid review_status: {review_status!r}")
        rec = self._by_id.get(record_id)
        if rec is None:
            return None
        rec.review_status = review_status
        rec.updated_at = _now()
        self._persist(rec)
        return rec

    def append_evidence_ref(
        self, record_id: str, ref: EvidenceRef,
    ) -> Any | None:
        rec = self._by_id.get(record_id)
        if rec is None or not hasattr(rec, "evidence_refs"):
            return None
        rec.evidence_refs = list(rec.evidence_refs or []) + [ref]
        rec.updated_at = _now()
        self._persist(rec)
        return rec

    def export_snapshot(self) -> list[dict]:
        return [rec.to_dict() for rec in self._by_id.values()]


# ---------------------------------------------------------------------------
# SourcePacket / AcquisitionTask stores (simpler, no review lifecycle)
# ---------------------------------------------------------------------------

class SourcePacketStore:
    def __init__(self, jsonl_path: Path | None = None):
        self._jsonl_path = jsonl_path
        self._by_id: dict[str, SourcePacket] = {}
        if jsonl_path:
            for raw in _read_jsonl(jsonl_path):
                pkt = SourcePacket.from_dict(raw)
                self._by_id[pkt.packet_id] = pkt

    def __len__(self) -> int:
        return len(self._by_id)

    def list_all(self) -> list[SourcePacket]:
        return list(self._by_id.values())

    def get(self, packet_id: str) -> SourcePacket | None:
        return self._by_id.get(packet_id)

    def add(self, packet: SourcePacket) -> SourcePacket:
        self._by_id[packet.packet_id] = packet
        if self._jsonl_path:
            _append_jsonl(self._jsonl_path, packet.to_dict())
        return packet

    def export_snapshot(self) -> list[dict]:
        return [p.to_dict() for p in self._by_id.values()]


class AcquisitionTaskStore:
    def __init__(self, jsonl_path: Path | None = None):
        self._jsonl_path = jsonl_path
        self._by_id: dict[str, SourceAcquisitionTask] = {}
        if jsonl_path:
            for raw in _read_jsonl(jsonl_path):
                task = SourceAcquisitionTask.from_dict(raw)
                self._by_id[task.task_id] = task

    def __len__(self) -> int:
        return len(self._by_id)

    def list_all(self) -> list[SourceAcquisitionTask]:
        return list(self._by_id.values())

    def get(self, task_id: str) -> SourceAcquisitionTask | None:
        return self._by_id.get(task_id)

    def list_open(self) -> list[SourceAcquisitionTask]:
        return [t for t in self._by_id.values() if t.status in ("open", "in_progress")]

    def add(self, task: SourceAcquisitionTask) -> SourceAcquisitionTask:
        self._by_id[task.task_id] = task
        if self._jsonl_path:
            _append_jsonl(self._jsonl_path, task.to_dict())
        return task

    def update_status(
        self, task_id: str, status: str,
        result_packet_ids: list[str] | None = None,
    ) -> SourceAcquisitionTask | None:
        task = self._by_id.get(task_id)
        if task is None:
            return None
        task.status = status
        task.updated_at = _now()
        if result_packet_ids:
            task.result_packet_ids = list(task.result_packet_ids or []) + result_packet_ids
        if self._jsonl_path:
            _append_jsonl(self._jsonl_path, task.to_dict())
        return task

    def export_snapshot(self) -> list[dict]:
        return [t.to_dict() for t in self._by_id.values()]


# ---------------------------------------------------------------------------
# Convenience: load a full registry set from a directory
# ---------------------------------------------------------------------------

def load_registry(
    record_type: str,
    data_dir: Path | None = None,
) -> BaseRegistry:
    if data_dir is None:
        data_dir = Path("data/registry")
    filename = record_type.replace("_", "_") + "s.jsonl"
    if record_type == "venue":
        filename = "venues.jsonl"
    elif record_type == "discipline":
        filename = "disciplines.jsonl"
    elif record_type == "epistemic_framework":
        filename = "epistemic_frameworks.jsonl"
    elif record_type == "venue_section":
        filename = "venue_sections.jsonl"
    elif record_type == "classification_system":
        filename = "classification_systems.jsonl"
    elif record_type == "subject_category":
        filename = "subject_categories.jsonl"
    elif record_type == "venue_classification":
        filename = "venue_classifications.jsonl"
    elif record_type == "venue_metric":
        filename = "venue_metrics.jsonl"
    return BaseRegistry(record_type, data_dir / filename)
