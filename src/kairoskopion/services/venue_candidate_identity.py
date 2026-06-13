"""Venue candidate identity normalization and deduplication.

Normalizes names, compares ISSN/ISSN-L, detects duplicates and conflicts.
Uses SourceAuthority model. Never silently chooses conflicting metadata.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from ..enums import VenueCandidateStatus


def normalize_venue_name(name: str) -> str:
    """Normalize venue name for comparison."""
    n = name.strip()
    n = unicodedata.normalize("NFKD", n)
    n = n.lower()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    # Remove common prefixes/suffixes
    for word in ("the", "a", "an"):
        if n.startswith(word + " "):
            n = n[len(word) + 1:]
    return n


def normalize_issn(issn: str | None) -> str | None:
    """Normalize ISSN to XXXX-XXXX format."""
    if not issn:
        return None
    cleaned = re.sub(r"[^0-9Xx]", "", issn)
    if len(cleaned) == 8:
        return f"{cleaned[:4]}-{cleaned[4:]}".upper()
    return issn.strip()


def dedupe_candidates(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Deduplicate candidate list.

    Returns: (deduped_candidates, dedupe_notes, conflicts)
    """
    if not candidates:
        return [], [], []

    dedupe_notes: list[str] = []
    conflicts: list[dict[str, Any]] = []

    # Index by normalized ISSN and name
    by_issn: dict[str, list[int]] = {}
    by_name: dict[str, list[int]] = {}

    for i, c in enumerate(candidates):
        issn = normalize_issn(c.get("issn"))
        issn_l = normalize_issn(c.get("issn_l"))

        for key in (issn, issn_l):
            if key:
                by_issn.setdefault(key, []).append(i)

        norm_name = normalize_venue_name(c.get("canonical_name", ""))
        if norm_name:
            by_name.setdefault(norm_name, []).append(i)

    merged_groups: list[set[int]] = []
    assigned: set[int] = set()

    # Strong merge: same ISSN
    for issn, indices in by_issn.items():
        if len(indices) > 1:
            group = set(indices)
            # Check for conflicting names within same ISSN
            names_in_group = {
                normalize_venue_name(candidates[i].get("canonical_name", ""))
                for i in group
            }
            if len(names_in_group) > 1:
                conflicts.append({
                    "type": "same_issn_different_name",
                    "issn": issn,
                    "names": [candidates[i].get("canonical_name") for i in group],
                    "severity": "warning",
                })

            existing = None
            for mg in merged_groups:
                if mg & group:
                    existing = mg
                    break
            if existing:
                existing.update(group)
            else:
                merged_groups.append(group)
            assigned.update(group)

    # Weak merge: same normalized name (only if no ISSN conflict)
    for name, indices in by_name.items():
        if len(indices) > 1:
            unassigned = [i for i in indices if i not in assigned]
            if len(unassigned) > 1:
                issns_in_group = set()
                for i in unassigned:
                    issn = normalize_issn(candidates[i].get("issn"))
                    if issn:
                        issns_in_group.add(issn)

                if len(issns_in_group) > 1:
                    conflicts.append({
                        "type": "same_name_different_issn",
                        "name": name,
                        "issns": list(issns_in_group),
                        "severity": "blocking",
                    })
                    for i in unassigned:
                        candidates[i]["status"] = VenueCandidateStatus.IDENTITY_UNCERTAIN.value
                        candidates[i].setdefault("unknowns", []).append(
                            f"Same name '{name}' but conflicting ISSNs"
                        )
                else:
                    group = set(unassigned)
                    merged_groups.append(group)
                    assigned.update(group)
                    dedupe_notes.append(
                        f"Weak merge by name: '{name}' ({len(unassigned)} candidates)"
                    )

    # Build deduplicated output
    result: list[dict[str, Any]] = []
    used: set[int] = set()

    for group in merged_groups:
        indices = sorted(group)
        primary = candidates[indices[0]]
        merged = _merge_candidates(primary, [candidates[i] for i in indices[1:]])
        dedupe_notes.append(
            f"Merged {len(indices)} candidates into '{merged.get('canonical_name', '')}'"
        )
        result.append(merged)
        used.update(indices)

    for i, c in enumerate(candidates):
        if i not in used:
            result.append(c)

    return result, dedupe_notes, conflicts


def _merge_candidates(
    primary: dict[str, Any],
    others: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge duplicate candidates, preserving all sources."""
    merged = dict(primary)
    all_sources: list[str] = list(primary.get("sources", []))
    all_reasons: list[str] = list(primary.get("discovery_reasons", []))
    all_aliases: list[str] = list(primary.get("aliases", []))
    all_unknowns: list[str] = list(primary.get("unknowns", []))
    all_refs: list[str] = list(primary.get("adapter_result_refs", []))
    all_assessments: list[dict[str, Any]] = list(primary.get("authority_assessments", []))
    raw_data: dict[str, Any] = dict(primary.get("raw_adapter_data", {}))

    for other in others:
        for src in other.get("sources", []):
            if src not in all_sources:
                all_sources.append(src)
        for reason in other.get("discovery_reasons", []):
            if reason not in all_reasons:
                all_reasons.append(reason)

        other_name = other.get("canonical_name", "")
        if other_name and other_name != primary.get("canonical_name", ""):
            if other_name not in all_aliases:
                all_aliases.append(other_name)

        all_unknowns.extend(other.get("unknowns", []))
        all_refs.extend(other.get("adapter_result_refs", []))
        all_assessments.extend(other.get("authority_assessments", []))
        raw_data.update(other.get("raw_adapter_data", {}))

    merged["sources"] = all_sources
    merged["discovery_reasons"] = all_reasons
    merged["aliases"] = all_aliases
    merged["unknowns"] = all_unknowns
    merged["adapter_result_refs"] = all_refs
    merged["authority_assessments"] = all_assessments
    merged["raw_adapter_data"] = raw_data

    if len(all_sources) >= 2:
        merged["confidence"] = "medium"

    merged["status"] = VenueCandidateStatus.DISCOVERED.value
    return merged


def detect_identity_conflicts(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect cross-candidate metadata conflicts."""
    conflicts: list[dict[str, Any]] = []

    # Check for publisher mismatches on same ISSN
    by_issn: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        issn = normalize_issn(c.get("issn"))
        if issn:
            by_issn.setdefault(issn, []).append(c)

    for issn, group in by_issn.items():
        if len(group) < 2:
            continue
        publishers = set()
        for c in group:
            raw = c.get("raw_adapter_data", {})
            for src_data in raw.values():
                pub = src_data.get("publisher")
                if pub:
                    publishers.add(pub)
        if len(publishers) > 1:
            conflicts.append({
                "type": "publisher_mismatch",
                "issn": issn,
                "publishers": list(publishers),
                "severity": "warning",
            })

    return conflicts
