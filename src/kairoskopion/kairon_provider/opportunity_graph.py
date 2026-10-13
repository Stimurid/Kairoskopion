"""Evidence-bound publication opportunity graph, separate from article batch execution.

This is a first CODE_ONLY slice of Indago W12 handoff PR #22.  It does not
import inaccessible XLSX bytes, create Article objects, rewrite manuscripts,
or send anything to an editorial system.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


READ_DEPTHS = frozenset({"FULL_TEXT", "SECTIONS", "ABSTRACT", "INDEX_ONLY"})
ROUTE_TYPES = frozenset({
    "FORMAL_ABSTRACT_CFP",
    "OPTIONAL_EDITORIAL_PRECHECK",
    "PRESUBMISSION_INQUIRY",
    "FULL_MANUSCRIPT_ONLY",
    "POLICY_UNVERIFIED",
})
AUTHOR_DECISIONS = frozenset({"HOLD", "ACCEPT", "REJECT"})
ENTITY_TYPES = frozenset({
    "Evidence", "World", "ArticleSeed", "ArticleOpportunity", "Journal",
    "VenueWorld", "JournalIssue", "OpportunityRoute", "TargetVariant", "EditorialPacket",
    "AuthorProfile", "HuntTrace",
})
EXPECTED_W12 = {
    "seed_families": 6,
    "semantic_variants": 27,
    "venue_candidates": 81,
    "editorial_routes": 53,
    "editorial_actions": 67,
    "cited_source_records": 43,
}
_RELEVANT_POLICY = frozenset({"OFFICIAL_POLICY", "OFFICIAL_CFP", "EDITOR_CONFIRMATION"})
_REAL_CHANNELS = frozenset({"OFFICIAL_PORTAL", "OFFICIAL_FORM", "EDITOR_CONFIRMED_EMAIL"})


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _required(value: Any, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{name} is required")
    return result


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_record(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    """Validate typed identity and essential authority/provenance requirements."""
    if kind not in ENTITY_TYPES:
        raise ValueError(f"unknown entity kind: {kind}")
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    _required(record.get("id"), "id")
    _required(record.get("revision"), "revision")
    if "kind" in record and record["kind"] != kind:
        raise ValueError("entity kind cannot be overwritten")

    if kind == "Evidence":
        _required(record.get("source_ref"), "source_ref")
        if record.get("read_depth") not in READ_DEPTHS:
            raise ValueError("evidence read_depth must be explicit")
        if not isinstance(record.get("passage_anchors", []), list):
            raise ValueError("passage_anchors must be a list")
        _required(record.get("source_kind"), "source_kind")
    elif kind == "ArticleSeed":
        _required(record.get("source_ref"), "seed source_ref")
        _required(record.get("author_authority"), "author_authority")
        if not isinstance(record.get("protected_core", []), list):
            raise ValueError("protected_core must be a list")
    elif kind == "ArticleOpportunity":
        _required(record.get("seed_id"), "seed_id")
        _required(record.get("scholarly_problem"), "scholarly_problem")
        _required(record.get("independent_claim"), "independent_claim")
        if record.get("author_decision", "HOLD") not in AUTHOR_DECISIONS:
            raise ValueError("author_decision must be HOLD, ACCEPT, or REJECT")
    elif kind == "Journal":
        _required(record.get("canonical_name"), "canonical_name")
        if not record.get("issn") and not record.get("official_url"):
            raise ValueError("journal needs official_url or ISSN")
    elif kind == "JournalIssue":
        _required(record.get("journal_id"), "journal_id")
        _required(record.get("official_url"), "official_url")
    elif kind == "VenueWorld":
        _required(record.get("journal_id"), "journal_id")
        _required(record.get("target_world_version"), "target_world_version")
    elif kind == "OpportunityRoute":
        _required(record.get("opportunity_id"), "opportunity_id")
        _required(record.get("journal_id"), "journal_id")
        if record.get("route_type") not in ROUTE_TYPES:
            raise ValueError("route_type must be a known editorial action")
        if record.get("deadline") and record.get("deadline_stage") != record["route_type"]:
            raise ValueError("deadline_stage must match the exact editorial route type")
    elif kind == "TargetVariant":
        _required(record.get("seed_id"), "seed_id")
        _required(record.get("opportunity_id"), "opportunity_id")
        _required(record.get("target_world_version"), "target_world_version")
    elif kind == "EditorialPacket":
        _required(record.get("route_id"), "route_id")
        if record.get("send_status", "NOT_SENT") != "NOT_SENT":
            raise ValueError("external submission is outside the factory authority")
        if record.get("author_decision", "HOLD") not in AUTHOR_DECISIONS:
            raise ValueError("invalid author decision")
    return dict(record)


def venue_world_status(world: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> str:
    """Only actually read and anchored fulltexts count as deep venue exemplars."""
    refs = world.get("published_example_evidence_ids") or []
    fully_read = {
        ref for ref in refs
        if ref in evidence
        and evidence[ref].get("read_depth") == "FULL_TEXT"
        and (evidence[ref].get("source_kind") or evidence[ref].get("kind")) == "PUBLISHED_ARTICLE"
        and bool(evidence[ref].get("passage_anchors"))
    }
    return "FULL_EVIDENCE" if len(fully_read) >= 3 else "PARTIAL_EVIDENCE"


def assess_route(
    route: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    world: dict[str, Any] | None,
    *,
    author_decision: str = "HOLD",
    coauthor_consent: bool = True,
) -> dict[str, Any]:
    """Fail-closed decision support. Never returns SENT or submission authorization."""
    validate_record("OpportunityRoute", route)
    if author_decision not in AUTHOR_DECISIONS:
        raise ValueError("invalid author_decision")
    blockers: list[str] = []
    if route["route_type"] == "POLICY_UNVERIFIED":
        blockers.append("route_policy_unverified")
    policy_ids = route.get("policy_evidence_ids") or []
    policies = [
        evidence[ref] for ref in policy_ids
        if ref in evidence
        and (evidence[ref].get("source_kind") or evidence[ref].get("kind")) in _RELEVANT_POLICY
        and evidence[ref].get("read_depth") in {"FULL_TEXT", "SECTIONS"}
        and evidence[ref].get("official", False) is True
    ]
    if not policies:
        blockers.append("no_official_policy_evidence")
    if route["route_type"] == "FORMAL_ABSTRACT_CFP" and not any(
        (policy.get("source_kind") or policy.get("kind")) == "OFFICIAL_CFP" for policy in policies
    ):
        blockers.append("formal_cfp_not_verified")
    if route.get("submission_channel_kind") not in _REAL_CHANNELS:
        blockers.append("unverified_editorial_channel")
    if world is None or venue_world_status(world, evidence) != "FULL_EVIDENCE":
        blockers.append("venue_world_partial_evidence")
    if not coauthor_consent:
        blockers.append("coauthor_consent_missing")
    if author_decision == "REJECT":
        blockers.append("author_rejected")
    if author_decision == "HOLD":
        blockers.append("author_decision_pending")
    status = "BLOCKED" if blockers else "AUTHOR_APPROVED_FOR_REVIEW"
    # Even an accepted route is not a sent item or a journal submission.
    return {
        "route_id": route["id"],
        "status": status,
        "blockers": sorted(set(blockers)),
        "external_action": "NOT_SENT",
        "human_submission_gate": "AUTHOR_ONLY",
    }


def inspect_w12_workbook(raw: bytes | None, expected_sha256: str | None = None) -> dict[str, Any]:
    """Prove actual XLSX bytes before mapping rows. Metadata or a Drive URL cannot pass."""
    if raw is None:
        return {
            "status": "BLOCKED_SOURCE_BYTES_UNAVAILABLE",
            "expected_counts_unverified": dict(EXPECTED_W12),
            "imported_records": 0,
        }
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ValueError("source sha256 mismatch")
    try:
        with ZipFile(BytesIO(raw)) as archive:
            if "xl/workbook.xml" not in archive.namelist():
                raise ValueError("not an OOXML workbook")
            xml = archive.read("xl/workbook.xml")
    except BadZipFile as exc:
        raise ValueError("not a valid xlsx ZIP container") from exc
    root = ElementTree.fromstring(xml)
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheets = [
        node.get("name") for node in root.findall(".//x:sheet", ns)
        if node.get("name")
    ]
    if not sheets:
        raise ValueError("workbook contains no named sheets")
    return {
        "status": "SOURCE_BYTES_VERIFIED_MAPPING_PENDING",
        "sha256": digest,
        "sheet_names": sheets,
        "sheet_count": len(sheets),
        "expected_counts_unverified": dict(EXPECTED_W12),
        "imported_records": 0,
    }


class OpportunityGraphStore:
    """Versioned, immutable records and idempotent hunt/decision events.

    It lives beside Kairon's existing filesystem stores, but holds research
    opportunities, not authoritative Artikl articles or journal submissions.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "opportunity_graph"
        self.records = self.root / "records"
        self.events = self.root / "events"
        self.records.mkdir(parents=True, exist_ok=True)
        self.events.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_once(path: Path, obj: dict[str, Any]) -> dict[str, Any]:
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if _canonical(existing) != _canonical(obj):
                raise ValueError("same immutable identity used with different content")
            return existing
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return obj

    def put(self, kind: str, record: dict[str, Any]) -> dict[str, Any]:
        value = validate_record(kind, record)
        if kind == "Journal":
            issn = str(value.get("issn") or "").replace("-", "").upper()
            official = str(value.get("official_url") or "").rstrip("/").lower()
            for path in self.records.glob("*.json"):
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("kind") != "Journal" or existing.get("id") == value["id"]:
                    continue
                prev_issn = str(existing.get("issn") or "").replace("-", "").upper()
                prev_url = str(existing.get("official_url") or "").rstrip("/").lower()
                if (issn and issn == prev_issn) or (official and official == prev_url):
                    raise ValueError("journal identity already registered under another id")
        key = _digest([kind, value["id"], value["revision"]])
        return self._write_once(self.records / f"{key}.json", {"kind": kind, **value})

    def get(self, kind: str, record_id: str, revision: str) -> dict[str, Any] | None:
        key = _digest([kind, record_id, revision])
        path = self.records / f"{key}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_records(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Read immutable records. Versions remain separate, never silently promote."""
        if kind is not None and kind not in ENTITY_TYPES:
            raise ValueError("unknown entity type")
        out = []
        for path in sorted(self.records.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("kind") not in ENTITY_TYPES:
                raise ValueError("corrupt opportunity record: invalid entity kind")
            if kind is None or record["kind"] == kind:
                out.append(record)
        return sorted(
            out, key=lambda r: (
                str(r.get("kind", "")),
                str(r.get("id", "")),
                str(r.get("revision", "")),
            ),
        )

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = _required(event.get("event_id"), "event_id")
        _required(event.get("kind"), "event kind")
        _required(event.get("subject_id"), "subject_id")
        _required(event.get("source_ref"), "source_ref")
        if event.get("kind") == "AUTHOR_DECISION" and event.get("decision") not in AUTHOR_DECISIONS:
            raise ValueError("author decision event needs an explicit decision")
        key = _digest(event_id)
        return self._write_once(self.events / f"{key}.json", dict(event))

    def replay_events(self) -> list[dict[str, Any]]:
        events = [json.loads(p.read_text(encoding="utf-8")) for p in self.events.glob("*.json")]
        return sorted(events, key=lambda event: (str(event.get("at", "")), str(event["event_id"])))
