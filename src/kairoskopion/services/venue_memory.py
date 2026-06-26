"""VenueMemory — cross-session venue knowledge persistence.

Append-only JSONL registry for venue facts, user notes, and prior
submission outcomes. Used to speed up repeat visits to known venues
and accumulate tacit knowledge.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..ids import generate_id
from ..schema import _now

logger = logging.getLogger(__name__)


def _venue_memory_id() -> str:
    return generate_id("vmem")


_VALID_REVIEW_STATUSES = ("provisional", "candidate", "accepted", "rejected", "superseded")


class VenueMemoryRecord:
    """One venue's accumulated knowledge.

    Every record tracks provenance, record_type, and review_status.
    Records start as 'provisional' and must be explicitly promoted
    to 'accepted' before being treated as canonical venue knowledge.
    Tacit notes remain notes; outcomes remain outcomes — neither
    auto-promotes to facts.
    """

    def __init__(
        self,
        venue_memory_id: str | None = None,
        canonical_name: str = "",
        issn: str | None = None,
        venue_model_id: str | None = None,
        facts: list[dict[str, Any]] | None = None,
        tacit_signals: list[dict[str, Any]] | None = None,
        prior_outcomes: list[dict[str, Any]] | None = None,
        staleness_status: str = "fresh",
        review_status: str = "provisional",
        record_type: str = "case_investigation",
        created_from_case_id: str | None = None,
        source_refs: list[str] | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        self.venue_memory_id = venue_memory_id or _venue_memory_id()
        self.canonical_name = canonical_name
        self.issn = issn
        self.venue_model_id = venue_model_id
        self.facts = facts or []
        self.tacit_signals = tacit_signals or []
        self.prior_outcomes = prior_outcomes or []
        self.staleness_status = staleness_status
        self.review_status = review_status
        self.record_type = record_type
        self.created_from_case_id = created_from_case_id
        self.source_refs = source_refs or []
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()

    @property
    def is_canonical(self) -> bool:
        return self.review_status == "accepted"

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_memory_id": self.venue_memory_id,
            "canonical_name": self.canonical_name,
            "issn": self.issn,
            "venue_model_id": self.venue_model_id,
            "facts": self.facts,
            "tacit_signals": self.tacit_signals,
            "prior_outcomes": self.prior_outcomes,
            "staleness_status": self.staleness_status,
            "review_status": self.review_status,
            "record_type": self.record_type,
            "created_from_case_id": self.created_from_case_id,
            "source_refs": self.source_refs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VenueMemoryRecord:
        return cls(**{k: v for k, v in d.items() if k in {
            "venue_memory_id", "canonical_name", "issn", "venue_model_id",
            "facts", "tacit_signals", "prior_outcomes", "staleness_status",
            "review_status", "record_type", "created_from_case_id",
            "source_refs", "created_at", "updated_at",
        }})

    def add_note(self, text: str) -> None:
        self.tacit_signals.append({"text": text, "added_at": _now()})
        self.updated_at = _now()

    def add_outcome(self, outcome: dict[str, Any]) -> None:
        outcome.setdefault("recorded_at", _now())
        self.prior_outcomes.append(outcome)
        self.updated_at = _now()


class VenueMemoryRegistry:
    """Append-only JSONL registry for VenueMemory records."""

    def __init__(self, data_dir: Path):
        self._path = data_dir / "venue_memory.jsonl"
        self._records: dict[str, VenueMemoryRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                rec = VenueMemoryRecord.from_dict(d)
                self._records[rec.venue_memory_id] = rec
            except Exception as exc:
                logger.warning("Skipping malformed venue_memory line: %s", exc)

    def _append(self, record: VenueMemoryRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def lookup(
        self, *, issn: str | None = None, name: str | None = None,
    ) -> VenueMemoryRecord | None:
        for rec in self._records.values():
            if issn and rec.issn == issn:
                return rec
            if name and rec.canonical_name and name.lower() in rec.canonical_name.lower():
                return rec
        return None

    def upsert_from_venue(
        self,
        canonical_name: str,
        issn: str | None = None,
        venue_model_id: str | None = None,
        facts: list[dict[str, Any]] | None = None,
    ) -> VenueMemoryRecord:
        existing = self.lookup(issn=issn, name=canonical_name)
        if existing:
            if facts:
                existing.facts.extend(facts)
            existing.updated_at = _now()
            self._append(existing)
            self._records[existing.venue_memory_id] = existing
            return existing
        rec = VenueMemoryRecord(
            canonical_name=canonical_name,
            issn=issn,
            venue_model_id=venue_model_id,
            facts=facts or [],
        )
        self._append(rec)
        self._records[rec.venue_memory_id] = rec
        return rec

    def list_all(self) -> list[VenueMemoryRecord]:
        return list(self._records.values())

    def get(self, venue_memory_id: str) -> VenueMemoryRecord | None:
        return self._records.get(venue_memory_id)

    def add_note(self, venue_memory_id: str, text: str) -> VenueMemoryRecord | None:
        rec = self._records.get(venue_memory_id)
        if not rec:
            return None
        rec.add_note(text)
        self._append(rec)
        return rec

    def add_outcome(
        self, venue_memory_id: str, outcome: dict[str, Any],
    ) -> VenueMemoryRecord | None:
        rec = self._records.get(venue_memory_id)
        if not rec:
            return None
        rec.add_outcome(outcome)
        self._append(rec)
        return rec

    def set_review_status(
        self, venue_memory_id: str, status: str,
    ) -> VenueMemoryRecord | None:
        """Promote or reject a venue memory record."""
        if status not in _VALID_REVIEW_STATUSES:
            return None
        rec = self._records.get(venue_memory_id)
        if not rec:
            return None
        rec.review_status = status
        rec.updated_at = _now()
        self._append(rec)
        return rec
