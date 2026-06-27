"""Evidence pack harvester — extracts SourcePackets and provisional records
from venue evidence pack markdown files (P7.3 Track 4).

Parses structured markdown (Journal Identity, Indexing Claims, VAK Status,
Article Types/Sections) into SourcePackets, then converts each SourcePacket
into the appropriate provisional registry record.

No LLM. No fabrication. If a field can't be parsed, it stays None/UNKNOWN.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..registry.models import (
    EvidenceRef,
    SourcePacket,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueMetricRecord,
    VenueClassificationRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Harvest result
# ---------------------------------------------------------------------------

@dataclass
class EvidencePackHarvestResult:
    source_file: str = ""
    venue_record: VenueRegistryRecord | None = None
    section_records: list[VenueSectionRecord] = field(default_factory=list)
    metric_records: list[VenueMetricRecord] = field(default_factory=list)
    classification_records: list[VenueClassificationRecord] = field(default_factory=list)
    source_packets: list[SourcePacket] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Section extraction helpers
# ---------------------------------------------------------------------------

def _extract_section(text: str, heading: str) -> str | None:
    pattern = rf"^## {re.escape(heading)}(?:\b| ).*?$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    next_h2 = re.search(r"^## ", text[start:], re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end].strip()


def _extract_section_fuzzy(text: str, *headings: str) -> str | None:
    for h in headings:
        result = _extract_section(text, h)
        if result:
            return result
    return None


def _extract_field(section: str, field_name: str) -> str | None:
    pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*(.+?)(?:\n|$)"
    match = re.search(pattern, section, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_issn(section: str, label: str) -> str | None:
    pattern = rf"\*\*{re.escape(label)}:\*\*\s*([\d]{{4}}-[\d]{{3}}[\dXx])"
    match = re.search(pattern, section, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Identity extraction → VenueRegistryRecord
# ---------------------------------------------------------------------------

def _parse_journal_identity(
    text: str,
    source_file: str,
) -> tuple[VenueRegistryRecord | None, SourcePacket | None, list[str]]:
    section = _extract_section(text, "Journal Identity")
    if not section:
        return None, None, ["No Journal Identity section found"]

    name = _extract_field(section, "Name")
    issn = _extract_issn(section, "ISSN")
    eissn = _extract_issn(section, "eISSN")
    publisher = _extract_field(section, "Publisher")
    url = _extract_field(section, "URL")

    if not name:
        return None, None, ["No journal Name found in Journal Identity"]

    # Clean URL — take first URL if multiple listed
    official_urls: list[str] = []
    if url:
        url_matches = re.findall(r"https?://[^\s,)]+", url)
        official_urls = url_matches if url_matches else [url]

    aliases: list[str] = []
    english_name = _extract_field(section, "English name")
    if english_name:
        aliases.append(english_name)
    # Split "Russian / English" name patterns
    if name and " / " in name:
        parts = [p.strip() for p in name.split(" / ")]
        canonical = parts[0]
        aliases.extend(parts[1:])
    else:
        canonical = name

    warnings: list[str] = []
    if not issn:
        warnings.append("ISSN not extracted")

    # Evidence ref from source file
    evidence_ref = EvidenceRef(
        source_type="venue_evidence_pack",
        source_id=source_file,
        excerpt=f"Journal Identity: {canonical}",
        evidence_status="corpus_grounded",
        confidence="high",
    )

    packet = SourcePacket(
        packet_type="venue_identity",
        source_type="venue_evidence_pack",
        source_id=source_file,
        title=canonical,
        excerpt=section[:500],
        adapter_name="evidence_pack_harvester",
        confidence="high",
        evidence_status="corpus_grounded",
    )

    venue = VenueRegistryRecord(
        canonical_name=canonical,
        aliases=aliases,
        issn=issn,
        eissn=eissn,
        publisher=publisher,
        official_urls=official_urls,
        evidence_refs=[evidence_ref],
        provenance=f"evidence_pack_harvester:{source_file}",
    )

    return venue, packet, warnings


# ---------------------------------------------------------------------------
# Sections extraction → VenueSectionRecord[]
# ---------------------------------------------------------------------------

def _parse_article_sections(
    text: str,
    venue_id: str,
    source_file: str,
) -> tuple[list[VenueSectionRecord], list[SourcePacket], list[str]]:
    section_text = _extract_section_fuzzy(
        text,
        "Article Types / Sections",
        "Article Types",
        "Article Types / Sections",
    )
    if not section_text:
        return [], [], ["No Article Types section found"]

    # Parse numbered list items: "1. Something (description)"
    items = re.findall(
        r"^\s*\d+\.\s+(.+?)(?:\n|$)",
        section_text,
        re.MULTILINE,
    )
    if not items:
        return [], [], ["No numbered article types found"]

    records: list[VenueSectionRecord] = []
    packets: list[SourcePacket] = []
    warnings: list[str] = []

    for item_text in items:
        # Clean up: remove trailing parenthetical evidence refs
        clean = re.sub(r"\s*\(.*?evidence.*?\)\s*$", "", item_text, flags=re.IGNORECASE)
        # Split "Russian name (English name)" or "Russian / English"
        name_parts = re.split(r"\s*/\s*|\s+\((?=[A-Z])", clean.rstrip(")"), maxsplit=1)
        section_name = name_parts[0].strip()

        evidence_ref = EvidenceRef(
            source_type="venue_evidence_pack",
            source_id=source_file,
            excerpt=f"Section: {section_name}",
            evidence_status="corpus_grounded",
            confidence="medium",
        )

        packet = SourcePacket(
            packet_type="venue_section",
            source_type="venue_evidence_pack",
            source_id=source_file,
            title=section_name,
            excerpt=item_text[:200],
            adapter_name="evidence_pack_harvester",
            confidence="medium",
            evidence_status="corpus_grounded",
        )

        record = VenueSectionRecord(
            parent_venue_id=venue_id,
            section_name=section_name,
            section_type="section",
            evidence_refs=[evidence_ref],
            provenance=f"evidence_pack_harvester:{source_file}",
        )

        records.append(record)
        packets.append(packet)

    return records, packets, warnings


# ---------------------------------------------------------------------------
# Indexing / Metrics extraction → VenueMetricRecord[]
# ---------------------------------------------------------------------------

_METRIC_PATTERNS = [
    (r"SJR\b[^\n]*?([\d]+\.[\d]+)", "sjr", "quartile", "Scopus/Scimago"),
    (r"CiteScore\b[^\n]*?(?:\*{0,2}\s*)([\d]+\.[\d]+)", "citescore", "cite_score", "Scopus"),
    (r"[hH]-?[iI]ndex[^\n]*?(\d+)", "h_index", "h_index", "Scopus"),
    (r"RSCI 2-year impact factor[^\n]*?([\d]+\.[\d]+)", "rsci_if", "impact_factor", "РИНЦ"),
]


def _parse_metrics(
    text: str,
    venue_id: str,
    source_file: str,
) -> tuple[list[VenueMetricRecord], list[SourcePacket], list[str]]:
    # Try multiple sections — some packs split Indexing and Metrics
    section_parts: list[str] = []
    for heading in ("Indexing Claims", "Metrics", "Indexing", "Bibliometric"):
        part = _extract_section(text, heading)
        if part:
            section_parts.append(part)
    section = "\n".join(section_parts) if section_parts else None
    if not section:
        return [], [], ["No Indexing Claims section found"]

    records: list[VenueMetricRecord] = []
    packets: list[SourcePacket] = []
    warnings: list[str] = []

    for pattern, system, metric_type, database in _METRIC_PATTERNS:
        match = re.search(pattern, section, re.IGNORECASE)
        if match:
            value = match.group(1)
            packet = SourcePacket(
                packet_type="venue_metric",
                source_type="venue_evidence_pack",
                source_id=source_file,
                title=f"{system}: {value}",
                excerpt=match.group(0),
                adapter_name="evidence_pack_harvester",
                confidence="high",
                evidence_status="corpus_grounded",
            )
            packets.append(packet)

            record = VenueMetricRecord(
                venue_id=venue_id,
                metric_system=system,
                database=database,
                metric_type=metric_type,
                metric_value=value,
                source_ref=source_file,
                evidence_status="corpus_grounded",
            )
            records.append(record)

    # Parse Scopus quartile data — try inline format first, then table rows
    inline_areas = re.findall(
        r"\*\*Scopus subject areas?:\*\*\s*(.+?)$",
        section,
        re.MULTILINE,
    )
    if inline_areas:
        area_matches = re.findall(
            r"([\w\s]+?)\s*\((Q[1-4])\)",
            inline_areas[0],
        )
    else:
        area_matches = re.findall(
            r"Scopus.*?([\w][\w\s]+?)\s*\((Q[1-4])\)",
            section,
            re.IGNORECASE,
        )

    for area, quartile in area_matches:
        packet = SourcePacket(
            packet_type="venue_metric",
            source_type="venue_evidence_pack",
            source_id=source_file,
            title=f"Scopus {area.strip()}: {quartile}",
            excerpt=f"{area.strip()} ({quartile})",
            adapter_name="evidence_pack_harvester",
            confidence="high",
            evidence_status="corpus_grounded",
        )
        packets.append(packet)

        record = VenueMetricRecord(
            venue_id=venue_id,
            metric_system="scopus_quartile",
            database="Scopus",
            metric_type="quartile",
            metric_value=quartile,
            source_ref=source_file,
            evidence_status="corpus_grounded",
        )
        records.append(record)

    # Parse "SJR: Q1 in X" format (not numeric SJR, but quartile info)
    sjr_q = re.findall(
        r"SJR:\s*(Q[1-4])\s+in\s+([\w\s]+?)(?:\n|$)",
        section,
        re.IGNORECASE,
    )
    for quartile, area in sjr_q:
        area = area.strip()
        packet = SourcePacket(
            packet_type="venue_metric",
            source_type="venue_evidence_pack",
            source_id=source_file,
            title=f"SJR {area}: {quartile}",
            excerpt=f"SJR: {quartile} in {area}",
            adapter_name="evidence_pack_harvester",
            confidence="medium",
            evidence_status="corpus_grounded",
        )
        packets.append(packet)
        record = VenueMetricRecord(
            venue_id=venue_id,
            metric_system="scopus_quartile",
            database="Scopus/Scimago",
            metric_type="quartile",
            metric_value=quartile,
            source_ref=source_file,
            evidence_status="corpus_grounded",
        )
        records.append(record)

    if not records:
        warnings.append("No metric values extracted from Indexing Claims")

    return records, packets, warnings


# ---------------------------------------------------------------------------
# VAK classification → VenueClassificationRecord
# ---------------------------------------------------------------------------

def _parse_vak_status(
    text: str,
    venue_id: str,
    source_file: str,
) -> tuple[list[VenueClassificationRecord], list[SourcePacket], list[str]]:
    section = _extract_section_fuzzy(text, "VAK Status", "VAK Specialties")
    if not section:
        return [], [], ["No VAK Status section found"]

    records: list[VenueClassificationRecord] = []
    packets: list[SourcePacket] = []
    warnings: list[str] = []

    # Check if VAK-included
    if re.search(r"(?:Included|Входит|included)\s+(?:in|в)\s+(?:the\s+)?VAK", section, re.IGNORECASE):
        packet = SourcePacket(
            packet_type="venue_classification",
            source_type="venue_evidence_pack",
            source_id=source_file,
            title="VAK list inclusion",
            excerpt=section[:300],
            adapter_name="evidence_pack_harvester",
            confidence="high",
            evidence_status="corpus_grounded",
        )
        packets.append(packet)

        record = VenueClassificationRecord(
            venue_id=venue_id,
            classification_system_id="vak_ru",
            source_ref=source_file,
            evidence_status="corpus_grounded",
        )
        records.append(record)

        # Try to extract category (К1/К2/К3)
        cat_match = re.search(r"[КK]([123])", section)
        if cat_match:
            cat_record = VenueClassificationRecord(
                venue_id=venue_id,
                classification_system_id="vak_ru_category",
                source_ref=source_file,
                evidence_status="corpus_grounded",
            )
            records.append(cat_record)
    else:
        warnings.append("VAK section found but inclusion not confirmed")

    return records, packets, warnings


# ---------------------------------------------------------------------------
# Main harvester
# ---------------------------------------------------------------------------

def harvest_evidence_pack(file_path: Path) -> EvidencePackHarvestResult:
    """Parse a single venue evidence pack file and extract all records."""
    result = EvidencePackHarvestResult(source_file=str(file_path))

    if not file_path.exists():
        result.warnings.append(f"File not found: {file_path}")
        return result

    text = file_path.read_text(encoding="utf-8")
    if len(text) < 100:
        result.warnings.append(f"File too short: {len(text)} chars")
        return result

    source_file = str(file_path)

    # 1. Journal Identity → VenueRegistryRecord
    venue, identity_packet, id_warnings = _parse_journal_identity(text, source_file)
    result.warnings.extend(id_warnings)
    if venue:
        result.venue_record = venue
        if identity_packet:
            result.source_packets.append(identity_packet)
    else:
        result.gaps.append("venue_identity")
        return result

    venue_id = venue.venue_id

    # 2. Article Types → VenueSectionRecord[]
    sections, sec_packets, sec_warnings = _parse_article_sections(
        text, venue_id, source_file,
    )
    result.section_records = sections
    result.source_packets.extend(sec_packets)
    result.warnings.extend(sec_warnings)
    if not sections:
        result.gaps.append("venue_sections")

    # 3. Indexing / Metrics → VenueMetricRecord[]
    metrics, met_packets, met_warnings = _parse_metrics(
        text, venue_id, source_file,
    )
    result.metric_records = metrics
    result.source_packets.extend(met_packets)
    result.warnings.extend(met_warnings)
    if not metrics:
        result.gaps.append("venue_metrics")

    # 4. VAK Status → VenueClassificationRecord[]
    classifications, cls_packets, cls_warnings = _parse_vak_status(
        text, venue_id, source_file,
    )
    result.classification_records = classifications
    result.source_packets.extend(cls_packets)
    result.warnings.extend(cls_warnings)

    return result


def harvest_all_evidence_packs(
    directory: Path,
) -> list[EvidencePackHarvestResult]:
    """Harvest all .md evidence packs in a directory."""
    results: list[EvidencePackHarvestResult] = []
    if not directory.exists():
        logger.warning("Evidence pack directory not found: %s", directory)
        return results

    for md_file in sorted(directory.glob("*_evidence_pack.md")):
        logger.info("Harvesting evidence pack: %s", md_file.name)
        result = harvest_evidence_pack(md_file)
        results.append(result)

    return results


def load_harvest_into_hub(
    results: list[EvidencePackHarvestResult],
    hub: Any,
) -> dict[str, int]:
    """Load harvested records into a RegistryHub. Returns counts."""
    counts: dict[str, int] = {
        "venues": 0,
        "sections": 0,
        "metrics": 0,
        "classifications": 0,
        "packets": 0,
    }

    for result in results:
        if result.venue_record:
            existing = hub.venues().find_duplicate(result.venue_record)
            if existing:
                logger.info(
                    "Venue already exists: %s (id=%s)",
                    existing.canonical_name,
                    existing.venue_id,
                )
                venue_id = existing.venue_id
                # Append new evidence refs
                for ref in result.venue_record.evidence_refs:
                    hub.venues().append_evidence_ref(venue_id, ref)
            else:
                hub.venues().add_provisional(result.venue_record)
                venue_id = result.venue_record.venue_id
                counts["venues"] += 1

            for sec in result.section_records:
                sec.parent_venue_id = venue_id
                hub.venue_sections().add_provisional(sec)
                counts["sections"] += 1

            for met in result.metric_records:
                met.venue_id = venue_id
                hub.venue_metrics().add_provisional(met)
                counts["metrics"] += 1

            for cls_rec in result.classification_records:
                cls_rec.venue_id = venue_id
                hub.venue_classifications().add_provisional(cls_rec)
                counts["classifications"] += 1

        for packet in result.source_packets:
            hub.packets.add(packet)
            counts["packets"] += 1

    return counts
