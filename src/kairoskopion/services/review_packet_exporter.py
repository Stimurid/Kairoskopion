"""P9 Review Packet / Dossier Export.

Exports the full provenance dossier after harvest → acquisition → verification:
- source packets, evidence refs, venue records, metrics, classifications,
  disciplines, acquisition tasks, verification decisions, gaps, blocked items,
  provisional records, rejected records.

Formats: markdown report, JSONL export, TSV review table.

No fabrication. Deterministic output from registry state.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from ..registry.services import RegistryHub
from .verification_gate import (
    VerificationDecision,
    verify_registry,
    summarize_verification,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ReviewPacket model
# ---------------------------------------------------------------------------

@dataclass
class ReviewPacket:
    packet_id: str = ""
    created_at: str = field(default_factory=_now)
    venues: list[dict[str, Any]] = field(default_factory=list)
    venue_sections: list[dict[str, Any]] = field(default_factory=list)
    venue_metrics: list[dict[str, Any]] = field(default_factory=list)
    venue_classifications: list[dict[str, Any]] = field(default_factory=list)
    disciplines: list[dict[str, Any]] = field(default_factory=list)
    source_packets: list[dict[str, Any]] = field(default_factory=list)
    acquisition_tasks: list[dict[str, Any]] = field(default_factory=list)
    verification_decisions: list[dict[str, Any]] = field(default_factory=list)
    verification_summary: dict[str, Any] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    blocked_items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Build review packet from registry
# ---------------------------------------------------------------------------

def build_review_packet(
    hub: RegistryHub,
    *,
    gaps: list[str] | None = None,
    no_paid_api: bool = True,
) -> ReviewPacket:
    """Build a complete review packet from current registry state."""
    from ..ids import generate_id
    packet = ReviewPacket(packet_id=generate_id("rpkt"))

    # Registry records
    for reg_type, target_list in [
        ("venue", packet.venues),
        ("venue_section", packet.venue_sections),
        ("venue_metric", packet.venue_metrics),
        ("venue_classification", packet.venue_classifications),
        ("discipline", packet.disciplines),
    ]:
        try:
            reg = hub._get_registry(reg_type)
            for rec in reg.list_all():
                target_list.append(rec.to_dict())
        except (ValueError, KeyError):
            pass

    # Source packets
    for pkt in hub.packets.list_all():
        packet.source_packets.append(pkt.to_dict())

    # Acquisition tasks
    for task in hub.tasks.list_all():
        d = task.to_dict()
        packet.acquisition_tasks.append(d)
        if task.status in ("blocked", "open"):
            packet.blocked_items.append(d)

    # Verification
    decisions = verify_registry(hub, no_paid_api=no_paid_api)
    packet.verification_decisions = [d.to_dict() for d in decisions]
    packet.verification_summary = summarize_verification(decisions)

    # Gaps
    packet.gaps = list(gaps or [])

    return packet


# ---------------------------------------------------------------------------
# Export: Markdown
# ---------------------------------------------------------------------------

def export_markdown(packet: ReviewPacket) -> str:
    """Export review packet as a markdown report."""
    lines: list[str] = []
    lines.append("# Kairoskopion Review Packet")
    lines.append("")
    lines.append(f"**Generated:** {packet.created_at}")
    lines.append(f"**Packet ID:** {packet.packet_id}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    vs = packet.verification_summary.get("verdicts", {})
    lines.append(f"| category | count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Venues | {len(packet.venues)} |")
    lines.append(f"| Venue sections | {len(packet.venue_sections)} |")
    lines.append(f"| Venue metrics | {len(packet.venue_metrics)} |")
    lines.append(f"| Classifications | {len(packet.venue_classifications)} |")
    lines.append(f"| Disciplines | {len(packet.disciplines)} |")
    lines.append(f"| Source packets | {len(packet.source_packets)} |")
    lines.append(f"| Acquisition tasks | {len(packet.acquisition_tasks)} |")
    lines.append(f"| Blocked items | {len(packet.blocked_items)} |")
    lines.append(f"| Gaps | {len(packet.gaps)} |")
    lines.append("")

    # Verification verdicts
    lines.append("## Verification Verdicts")
    lines.append("")
    if vs:
        lines.append("| verdict | count |")
        lines.append("|---------|-------|")
        for verdict, count in sorted(vs.items()):
            lines.append(f"| {verdict} | {count} |")
        lines.append("")

    # Venues
    if packet.venues:
        lines.append("## Venues")
        lines.append("")
        lines.append("| name | ISSN | publisher | status |")
        lines.append("|------|------|-----------|--------|")
        for v in packet.venues:
            lines.append(
                f"| {v.get('canonical_name', '?')} "
                f"| {v.get('issn', '—')} "
                f"| {v.get('publisher', '—')} "
                f"| {v.get('source_status', '?')} |"
            )
        lines.append("")

    # Metrics
    if packet.venue_metrics:
        lines.append("## Venue Metrics")
        lines.append("")
        lines.append("| venue_id | system | type | value | evidence |")
        lines.append("|----------|--------|------|-------|----------|")
        for m in packet.venue_metrics:
            lines.append(
                f"| {_short_id(m.get('venue_id', ''))} "
                f"| {m.get('metric_system', '?')} "
                f"| {m.get('metric_type', '?')} "
                f"| {m.get('metric_value', '?')} "
                f"| {m.get('evidence_status', '?')} |"
            )
        lines.append("")

    # Source packets (top 10)
    if packet.source_packets:
        lines.append("## Source Packets (top 10)")
        lines.append("")
        lines.append("| id | type | source | evidence |")
        lines.append("|----|------|--------|----------|")
        for sp in packet.source_packets[:10]:
            lines.append(
                f"| {_short_id(sp.get('packet_id', ''))} "
                f"| {sp.get('packet_type', '?')} "
                f"| {sp.get('source_type', '?')} "
                f"| {sp.get('evidence_status', '?')} |"
            )
        if len(packet.source_packets) > 10:
            lines.append(f"| ... | {len(packet.source_packets) - 10} more | | |")
        lines.append("")

    # Gaps
    if packet.gaps:
        lines.append("## Open Gaps")
        lines.append("")
        for g in packet.gaps:
            lines.append(f"- {g}")
        lines.append("")

    # Blocked
    if packet.blocked_items:
        lines.append("## Blocked Items")
        lines.append("")
        for b in packet.blocked_items:
            lines.append(f"- **{b.get('task_type', '?')}**: {b.get('query', '?')} — {b.get('status', '?')}")
        lines.append("")

    # What user must supply
    lines.append("## Next Steps (Manual)")
    lines.append("")
    open_tasks = [t for t in packet.acquisition_tasks if t.get("status") == "open"]
    blocked_tasks = [t for t in packet.acquisition_tasks if t.get("status") == "blocked"]
    if open_tasks:
        lines.append(f"- {len(open_tasks)} acquisition tasks need manual resolution")
    if blocked_tasks:
        lines.append(f"- {len(blocked_tasks)} tasks blocked (paid API required)")
    if packet.gaps:
        lines.append(f"- {len(packet.gaps)} gaps require additional evidence")
    prov_count = vs.get("keep_provisional", 0)
    if prov_count:
        lines.append(f"- {prov_count} records remain provisional")
    if not open_tasks and not blocked_tasks and not packet.gaps:
        lines.append("- No outstanding items")
    lines.append("")

    return "\n".join(lines)


def _short_id(full_id: str) -> str:
    if len(full_id) > 16:
        return full_id[:16] + "..."
    return full_id


# ---------------------------------------------------------------------------
# Export: JSONL
# ---------------------------------------------------------------------------

def export_jsonl(packet: ReviewPacket) -> str:
    """Export review packet as JSONL (one record per line)."""
    lines: list[str] = []

    lines.append(json.dumps({
        "record_type": "review_packet_header",
        "packet_id": packet.packet_id,
        "created_at": packet.created_at,
        "summary": packet.verification_summary,
    }, ensure_ascii=False))

    for v in packet.venues:
        v["record_type"] = "venue"
        lines.append(json.dumps(v, ensure_ascii=False))

    for s in packet.venue_sections:
        s["record_type"] = "venue_section"
        lines.append(json.dumps(s, ensure_ascii=False))

    for m in packet.venue_metrics:
        m["record_type"] = "venue_metric"
        lines.append(json.dumps(m, ensure_ascii=False))

    for c in packet.venue_classifications:
        c["record_type"] = "venue_classification"
        lines.append(json.dumps(c, ensure_ascii=False))

    for d in packet.disciplines:
        d["record_type"] = "discipline"
        lines.append(json.dumps(d, ensure_ascii=False))

    for sp in packet.source_packets:
        sp["record_type"] = "source_packet"
        lines.append(json.dumps(sp, ensure_ascii=False))

    for t in packet.acquisition_tasks:
        t["record_type"] = "acquisition_task"
        lines.append(json.dumps(t, ensure_ascii=False))

    for vd in packet.verification_decisions:
        vd["record_type"] = "verification_decision"
        lines.append(json.dumps(vd, ensure_ascii=False))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Export: TSV review table
# ---------------------------------------------------------------------------

TSV_COLUMNS = (
    "record_type", "record_id", "name_or_label", "status",
    "verification_verdict", "evidence_count", "evidence_kinds",
    "needs_action",
)


def export_tsv(packet: ReviewPacket) -> str:
    """Export review packet as a TSV review table."""
    lines: list[str] = ["\t".join(TSV_COLUMNS)]

    decision_map: dict[str, dict] = {}
    for vd in packet.verification_decisions:
        decision_map[vd.get("record_id", "")] = vd

    for v in packet.venues:
        vid = v.get("venue_id", "")
        vd = decision_map.get(vid, {})
        lines.append("\t".join([
            "venue",
            vid,
            v.get("canonical_name", ""),
            v.get("source_status", ""),
            vd.get("verdict", ""),
            str(vd.get("evidence_refs_count", 0)),
            ",".join(vd.get("evidence_kinds", [])),
            "yes" if vd.get("verdict") in ("keep_provisional", "needs_manual_review") else "no",
        ]))

    for m in packet.venue_metrics:
        mid = m.get("metric_id", "")
        vd = decision_map.get(mid, {})
        label = f"{m.get('metric_system', '')}:{m.get('metric_type', '')}={m.get('metric_value', '')}"
        lines.append("\t".join([
            "venue_metric",
            mid,
            label,
            m.get("evidence_status", ""),
            vd.get("verdict", ""),
            str(vd.get("evidence_refs_count", 0)),
            ",".join(vd.get("evidence_kinds", [])),
            "yes" if vd.get("verdict") in ("keep_provisional", "needs_manual_review") else "no",
        ]))

    for d in packet.disciplines:
        did = d.get("discipline_id", "")
        vd = decision_map.get(did, {})
        names = d.get("display_names", {})
        label = next(iter(names.values()), "")
        lines.append("\t".join([
            "discipline",
            did,
            label,
            d.get("source_status", ""),
            vd.get("verdict", ""),
            str(vd.get("evidence_refs_count", 0)),
            ",".join(vd.get("evidence_kinds", [])),
            "yes" if vd.get("verdict") in ("keep_provisional", "needs_manual_review") else "no",
        ]))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Write to disk
# ---------------------------------------------------------------------------

def write_review_packet(
    packet: ReviewPacket,
    output_dir: Path,
) -> dict[str, Path]:
    """Write review packet in all formats to output_dir.

    Returns dict of format → file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    md_path = output_dir / "review_packet.md"
    md_path.write_text(export_markdown(packet), encoding="utf-8")
    paths["markdown"] = md_path

    jsonl_path = output_dir / "review_packet.jsonl"
    jsonl_path.write_text(export_jsonl(packet), encoding="utf-8")
    paths["jsonl"] = jsonl_path

    tsv_path = output_dir / "review_packet.tsv"
    tsv_path.write_text(export_tsv(packet), encoding="utf-8")
    paths["tsv"] = tsv_path

    return paths
