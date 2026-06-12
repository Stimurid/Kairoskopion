"""Venue Registry Services (venue-registry-source-collector v0).

Import seed corpus and build evidence packs from registry claims.
No network access, no LLM calls, no mass crawling.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..enums import VenueClaimStatus, VenueSourceType
from ..schema import VenueClaim, VenueEvidencePack, VenueRecord, VenueSource


_SOURCE_TYPE_FRESHNESS: dict[str, int] = {
    VenueSourceType.OFFICIAL_HOMEPAGE.value: 180,
    VenueSourceType.OFFICIAL_AUTHOR_GUIDELINES.value: 90,
    VenueSourceType.OFFICIAL_EDITORIAL_POLICY.value: 180,
    VenueSourceType.OFFICIAL_ARCHIVE.value: 365,
    VenueSourceType.OFFICIAL_CONTACTS.value: 60,
    VenueSourceType.REGISTRY_CARD.value: 365,
    VenueSourceType.INDEXER_PAGE.value: 365,
    VenueSourceType.PUBLISHER_PAGE.value: 180,
    VenueSourceType.THIRD_PARTY_SUMMARY.value: 90,
    VenueSourceType.MANUAL_NOTE.value: 0,
}

_OFFICIAL_SOURCE_TYPES = {
    VenueSourceType.OFFICIAL_HOMEPAGE.value,
    VenueSourceType.OFFICIAL_AUTHOR_GUIDELINES.value,
    VenueSourceType.OFFICIAL_EDITORIAL_POLICY.value,
    VenueSourceType.OFFICIAL_ARCHIVE.value,
    VenueSourceType.OFFICIAL_CONTACTS.value,
}

_PROFILE_FIELDS = [
    "aims_scope", "accepted_article_types", "accepted_languages",
    "submission_route", "author_guidelines_summary", "word_limits",
    "abstract_limits", "citation_style", "review_model",
    "anonymization_policy", "apc_oa", "indexing_claims",
    "ethics_policy", "ai_policy", "data_policy", "conflict_policy",
    "editorial_board_signal", "recent_issue_signal",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{lineno}: invalid JSON: {exc}") from exc
    return records


def _validate_venue(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("venue_record_id"):
        errors.append("missing venue_record_id")
    if not data.get("canonical_name"):
        errors.append("missing canonical_name")
    return errors


def _validate_source(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("venue_source_id"):
        errors.append("missing venue_source_id")
    if not data.get("venue_record_id"):
        errors.append("missing venue_record_id")
    if not data.get("source_type"):
        errors.append("missing source_type")
    return errors


def _validate_claim(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("venue_claim_id"):
        errors.append("missing venue_claim_id")
    if not data.get("venue_record_id"):
        errors.append("missing venue_record_id")
    if not data.get("venue_source_id"):
        errors.append("missing venue_source_id")
    if not data.get("claim_path"):
        errors.append("missing claim_path")
    if not data.get("evidence_status"):
        errors.append("missing evidence_status")
    return errors


class ImportResult:
    def __init__(self) -> None:
        self.venues: list[VenueRecord] = []
        self.sources: list[VenueSource] = []
        self.claims: list[VenueClaim] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


def import_venue_seed_corpus(corpus_dir: Path) -> ImportResult:
    """Read JSONL seed corpus (venues, sources, claims) and return parsed objects."""
    result = ImportResult()

    venues_path = corpus_dir / "venues.jsonl"
    sources_path = corpus_dir / "sources.jsonl"
    claims_path = corpus_dir / "claims.jsonl"

    for p, label in [(venues_path, "venues"), (sources_path, "sources"), (claims_path, "claims")]:
        if not p.exists():
            result.errors.append(f"{label}.jsonl not found in {corpus_dir}")

    if result.errors:
        return result

    venue_ids: set[str] = set()
    source_ids: set[str] = set()

    for data in _read_jsonl(venues_path):
        errs = _validate_venue(data)
        if errs:
            result.errors.append(f"venue {data.get('venue_record_id', '?')}: {'; '.join(errs)}")
            continue
        venue = VenueRecord.from_dict(data)
        venue_ids.add(venue.venue_record_id)
        result.venues.append(venue)

    for data in _read_jsonl(sources_path):
        errs = _validate_source(data)
        if errs:
            result.errors.append(f"source {data.get('venue_source_id', '?')}: {'; '.join(errs)}")
            continue
        if data["venue_record_id"] not in venue_ids:
            result.warnings.append(
                f"source {data['venue_source_id']}: venue_record_id "
                f"{data['venue_record_id']} not found in venues.jsonl"
            )
        source = VenueSource.from_dict(data)
        source_ids.add(source.venue_source_id)
        result.sources.append(source)

    for data in _read_jsonl(claims_path):
        errs = _validate_claim(data)
        if errs:
            result.errors.append(f"claim {data.get('venue_claim_id', '?')}: {'; '.join(errs)}")
            continue
        if data["venue_record_id"] not in venue_ids:
            result.warnings.append(
                f"claim {data['venue_claim_id']}: venue_record_id "
                f"{data['venue_record_id']} not found"
            )
        if data["venue_source_id"] not in source_ids:
            result.warnings.append(
                f"claim {data['venue_claim_id']}: venue_source_id "
                f"{data['venue_source_id']} not found"
            )
        claim = VenueClaim.from_dict(data)
        result.claims.append(claim)

    return result


def persist_import_result(
    result: ImportResult,
    storage_root: Path,
) -> dict[str, Path]:
    """Write imported venue registry data to JSONL registries."""
    from .. import registry as reg
    from ..persistence import ensure_registry_root

    reg_root = ensure_registry_root(storage_root)
    written: dict[str, Path] = {}

    for venue in result.venues:
        written["venue_records"] = reg.append(
            "venue_records", venue.to_dict(), base_dir=reg_root
        )
    for source in result.sources:
        written["venue_sources"] = reg.append(
            "venue_sources", source.to_dict(), base_dir=reg_root
        )
    for claim in result.claims:
        written["venue_claims"] = reg.append(
            "venue_claims", claim.to_dict(), base_dir=reg_root
        )
    return written


def _is_source_stale(source: VenueSource, now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(timezone.utc)
    if source.source_type == VenueSourceType.MANUAL_NOTE.value:
        return False
    window = source.freshness_window_days
    if window is None:
        window = _SOURCE_TYPE_FRESHNESS.get(source.source_type or "", 90)
    if not source.retrieved_at:
        return True
    try:
        retrieved = datetime.fromisoformat(source.retrieved_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True
    from datetime import timedelta
    return (now - retrieved).days > window


def _resolve_claims(
    claims: list[VenueClaim],
    sources_by_id: dict[str, VenueSource],
    now: datetime | None = None,
) -> tuple[dict[str, Any], list[str], list[str], list[str], list[dict[str, Any]], list[str], list[str]]:
    """Resolve claims into a profile dict with provenance tracking.

    Returns (profile, official_fact_ids, external_claim_ids, inference_ids,
             conflicts, stale_warnings, build_log).
    """
    profile: dict[str, Any] = {}
    official_facts: list[str] = []
    external_claims: list[str] = []
    inferences: list[str] = []
    conflicts: list[dict[str, Any]] = []
    stale_warnings: list[str] = []
    build_log: list[str] = []

    by_path: dict[str, list[VenueClaim]] = {}
    for claim in claims:
        path = claim.claim_path or ""
        by_path.setdefault(path, []).append(claim)

    for path, path_claims in sorted(by_path.items()):
        for claim in path_claims:
            src = sources_by_id.get(claim.venue_source_id or "")
            if src and _is_source_stale(src, now):
                stale_warnings.append(
                    f"{claim.venue_claim_id}: source {claim.venue_source_id} is stale"
                )

            status = claim.evidence_status
            if status == VenueClaimStatus.OFFICIAL_FACT.value:
                official_facts.append(claim.venue_claim_id)
            elif status == VenueClaimStatus.EXTERNAL_CLAIM.value:
                external_claims.append(claim.venue_claim_id)
            elif status == VenueClaimStatus.INFERENCE.value:
                inferences.append(claim.venue_claim_id)

        has_conflict_marker = any(c.conflict_group is not None for c in path_claims)

        if has_conflict_marker:
            marked = [c for c in path_claims if c.conflict_group is not None]
            unmarked_with_same_path = [c for c in path_claims if c.conflict_group is None]
            all_involved = marked + [
                c for c in unmarked_with_same_path
                if any(
                    json.dumps(c.claim_value, sort_keys=True, default=str)
                    != json.dumps(m.claim_value, sort_keys=True, default=str)
                    for m in marked
                ) or any(
                    c.claim_path == m.claim_path for m in marked
                )
            ]
            if len(all_involved) > 1:
                conflicts.append({
                    "claim_path": path,
                    "claim_ids": [c.venue_claim_id for c in all_involved],
                    "values": [c.claim_value for c in all_involved],
                })
                build_log.append(
                    f"CONFLICT on '{path}': {len(all_involved)} claims with conflict marker "
                    f"— not resolved, all reported"
                )
            elif len(marked) == 1:
                conflicts.append({
                    "claim_path": path,
                    "claim_ids": [marked[0].venue_claim_id],
                    "values": [marked[0].claim_value],
                })
                build_log.append(
                    f"CONFLICT on '{path}': claim {marked[0].venue_claim_id} "
                    f"has conflict marker but no matching counterpart — flagged"
                )
            continue

        if len(path_claims) == 1:
            claim = path_claims[0]
            profile[path] = claim.claim_value
            build_log.append(
                f"'{path}': single claim {claim.venue_claim_id} ({claim.evidence_status})"
            )
            continue

        unique_values = set()
        for c in path_claims:
            v = json.dumps(c.claim_value, sort_keys=True, default=str) if isinstance(c.claim_value, (list, dict)) else str(c.claim_value)
            unique_values.add(v)

        if len(unique_values) == 1:
            winner = _pick_winner(path_claims, sources_by_id)
            profile[path] = winner.claim_value
            build_log.append(
                f"'{path}': {len(path_claims)} claims agree, "
                f"used {winner.venue_claim_id} ({winner.evidence_status})"
            )
        else:
            officials = [
                c for c in path_claims
                if c.evidence_status == VenueClaimStatus.OFFICIAL_FACT.value
            ]
            non_officials = [
                c for c in path_claims
                if c.evidence_status != VenueClaimStatus.OFFICIAL_FACT.value
            ]

            if len(officials) == 1 and non_officials:
                profile[path] = officials[0].claim_value
                build_log.append(
                    f"'{path}': official fact {officials[0].venue_claim_id} "
                    f"wins over {len(non_officials)} non-official claim(s)"
                )
            elif len(officials) > 1:
                off_values = set()
                for c in officials:
                    v = json.dumps(c.claim_value, sort_keys=True, default=str) if isinstance(c.claim_value, (list, dict)) else str(c.claim_value)
                    off_values.add(v)
                if len(off_values) == 1:
                    profile[path] = officials[0].claim_value
                    build_log.append(
                        f"'{path}': {len(officials)} official claims agree"
                    )
                else:
                    conflicts.append({
                        "claim_path": path,
                        "claim_ids": [c.venue_claim_id for c in officials],
                        "values": [c.claim_value for c in officials],
                    })
                    build_log.append(
                        f"CONFLICT on '{path}': {len(officials)} official claims disagree "
                        f"— not resolved"
                    )
            else:
                conflicts.append({
                    "claim_path": path,
                    "claim_ids": [c.venue_claim_id for c in path_claims],
                    "values": [c.claim_value for c in path_claims],
                })
                build_log.append(
                    f"CONFLICT on '{path}': {len(path_claims)} claims with different values, "
                    f"no official fact to resolve — not resolved"
                )

    return (profile, official_facts, external_claims, inferences,
            conflicts, stale_warnings, build_log)


def _pick_winner(
    claims: list[VenueClaim],
    sources_by_id: dict[str, VenueSource],
) -> VenueClaim:
    """Pick the best claim from a list of agreeing claims."""
    priority = {
        VenueClaimStatus.OFFICIAL_FACT.value: 0,
        VenueClaimStatus.EXTERNAL_CLAIM.value: 1,
        VenueClaimStatus.INFERENCE.value: 2,
        VenueClaimStatus.UNKNOWN.value: 3,
    }
    return min(claims, key=lambda c: priority.get(c.evidence_status or "", 99))


def build_venue_evidence_pack(
    venue_id_or_alias: str,
    venues: list[VenueRecord],
    sources: list[VenueSource],
    claims: list[VenueClaim],
    now: datetime | None = None,
) -> VenueEvidencePack | None:
    """Build an evidence pack for a venue from registry data."""
    venue = None
    for v in venues:
        if v.venue_record_id == venue_id_or_alias:
            venue = v
            break
        if venue_id_or_alias in (v.aliases or []):
            venue = v
            break
        if v.canonical_name and v.canonical_name.lower() == venue_id_or_alias.lower():
            venue = v
            break

    if venue is None:
        return None

    venue_sources = [s for s in sources if s.venue_record_id == venue.venue_record_id]
    venue_claims = [c for c in claims if c.venue_record_id == venue.venue_record_id]
    sources_by_id = {s.venue_source_id: s for s in venue_sources}

    (profile, official_fact_ids, external_claim_ids, inference_ids,
     conflicts, stale_warnings, build_log) = _resolve_claims(
        venue_claims, sources_by_id, now
    )

    profile["name"] = venue.canonical_name
    profile["aliases"] = venue.aliases or []
    if venue.issn:
        profile["issn"] = venue.issn
    if venue.eissn:
        profile["eissn"] = venue.eissn
    if venue.publisher:
        profile["publisher"] = venue.publisher
    if venue.official_urls:
        profile["official_urls"] = venue.official_urls

    unknown_fields = []
    for field in _PROFILE_FIELDS:
        if field not in profile:
            unknown_fields.append(field)

    return VenueEvidencePack(
        venue_record_id=venue.venue_record_id,
        profile=profile,
        official_facts=official_fact_ids,
        external_claims=external_claim_ids,
        inferences=inference_ids,
        unknowns=unknown_fields,
        conflicts=conflicts,
        stale_warnings=stale_warnings,
        build_log=build_log,
    )


def evidence_pack_to_markdown(
    pack: VenueEvidencePack,
    venues: list[VenueRecord] | None = None,
    sources: list[VenueSource] | None = None,
    claims: list[VenueClaim] | None = None,
) -> str:
    """Render an evidence pack as Markdown suitable for run-local --venue-guidelines."""
    p = pack.profile
    lines: list[str] = []

    name = p.get("name", "Unknown Venue")
    lines.append(f"# {name}")
    lines.append("")

    if p.get("aliases"):
        lines.append(f"**Aliases:** {', '.join(p['aliases'])}")
    if p.get("issn"):
        lines.append(f"**ISSN:** {p['issn']}")
    if p.get("eissn"):
        lines.append(f"**eISSN:** {p['eissn']}")
    if p.get("publisher"):
        lines.append(f"**Publisher:** {p['publisher']}")
    if p.get("official_urls"):
        lines.append(f"**Official URLs:** {', '.join(p['official_urls'])}")
    lines.append("")

    if p.get("aims_scope"):
        lines.append("## Aims and Scope")
        lines.append("")
        lines.append(str(p["aims_scope"]))
        lines.append("")

    if p.get("accepted_article_types"):
        lines.append("## Article Types")
        lines.append("")
        types = p["accepted_article_types"]
        if isinstance(types, list):
            for t in types:
                lines.append(f"- **{t}**")
        else:
            lines.append(str(types))
        lines.append("")

    if p.get("accepted_languages"):
        lines.append("## Language Policy")
        lines.append("")
        lines.append(str(p["accepted_languages"]))
        lines.append("")

    has_word_info = False
    for key in sorted(k for k in p if k.startswith("word_limits")):
        if not has_word_info:
            lines.append("## Word Limits")
            lines.append("")
            has_word_info = True
        label = key.replace("word_limits.", "").replace("_", " ").title()
        lines.append(f"- {label}: {p[key]}")
    if has_word_info:
        lines.append("")

    if p.get("abstract_limits.max_words"):
        lines.append("## Abstract")
        lines.append("")
        lines.append(f"Maximum {p['abstract_limits.max_words']} words.")
        lines.append("")

    if p.get("citation_style"):
        lines.append("## Citation Style")
        lines.append("")
        lines.append(str(p["citation_style"]))
        lines.append("")

    if p.get("review_model"):
        lines.append("## Review Process")
        lines.append("")
        lines.append(str(p["review_model"]))
        lines.append("")

    if p.get("apc_oa"):
        lines.append("## Open Access / APC")
        lines.append("")
        lines.append(str(p["apc_oa"]))
        lines.append("")

    if p.get("indexing_claims"):
        lines.append("## Indexing")
        lines.append("")
        idx = p["indexing_claims"]
        if isinstance(idx, list):
            lines.append(", ".join(idx))
        else:
            lines.append(str(idx))
        lines.append("")

    for policy_field in ["ethics_policy", "ai_policy", "data_policy", "conflict_policy"]:
        if p.get(policy_field):
            label = policy_field.replace("_", " ").title()
            lines.append(f"## {label}")
            lines.append("")
            lines.append(str(p[policy_field]))
            lines.append("")

    lines.append("## Evidence Provenance")
    lines.append("")
    lines.append(f"- Official facts: {len(pack.official_facts)}")
    lines.append(f"- External claims: {len(pack.external_claims)}")
    lines.append(f"- Inferences: {len(pack.inferences)}")
    lines.append(f"- Unknown fields: {len(pack.unknowns)}")
    if pack.unknowns:
        lines.append(f"- Unknown: {', '.join(pack.unknowns)}")
    lines.append(f"- Conflicts: {len(pack.conflicts)}")
    if pack.conflicts:
        for conflict in pack.conflicts:
            lines.append(f"  - {conflict['claim_path']}: {len(conflict['claim_ids'])} competing claims")
    lines.append(f"- Stale warnings: {len(pack.stale_warnings)}")
    if pack.stale_warnings:
        for w in pack.stale_warnings:
            lines.append(f"  - {w}")
    lines.append("")

    if pack.unknowns:
        lines.append("## UNKNOWN Fields")
        lines.append("")
        for field in pack.unknowns:
            lines.append(f"- {field}: UNKNOWN — no evidence available")
        lines.append("")

    return "\n".join(lines)
