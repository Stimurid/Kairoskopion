"""Build evidence-bearing scientific profiles for selected editors."""

from __future__ import annotations

from typing import Any

from ..adapters.venue.editor_scientific_profile import resolve_editor_scientific_record
from .models import EditorScientificProfile


def _work_record(work: dict[str, Any]) -> dict[str, Any]:
    return {
        "openalex_id": work.get("id"),
        "title": work.get("title"),
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "cited_by_count": work.get("cited_by_count"),
        "type": work.get("type"),
        "primary_location": (work.get("primary_location") or {}).get("landing_page_url"),
    }


def acquire_editor_scientific_profiles(
    members: list[dict[str, Any]],
    *,
    max_editors: int = 12,
    max_works_per_editor: int = 10,
    fixtures: dict[str, dict[str, Any]] | None = None,
) -> list[EditorScientificProfile]:
    """Resolve public scientific trajectories for a bounded editor sample.

    fixtures may provide {"Name": {"author": {...}, "works": [...]}} for
    deterministic tests. The result intentionally stops at public scholarship:
    no acceptance-preference inference is generated.
    """
    out: list[EditorScientificProfile] = []
    fixtures = fixtures or {}

    for idx, member in enumerate(members[:max_editors]):
        name = str(member.get("full_name") or member.get("name") or "").strip()
        if not name:
            continue
        fx = fixtures.get(name, {})
        record = resolve_editor_scientific_record(
            name=name,
            affiliation_hint=member.get("affiliation") or member.get("affiliation_hint"),
            role=member.get("role"),
            max_works=max_works_per_editor,
            fixture_author=fx.get("author"),
            fixture_works=fx.get("works"),
        )
        works = list(record.get("works") or [])
        concepts = list(record.get("x_concepts") or [])
        profile = EditorScientificProfile(
            editor_id=str(record.get("openalex_author_id") or f"editor:{idx}:{name}"),
            name=str(record.get("name") or name),
            editorial_roles=[str(record["role"])] if record.get("role") else [],
            affiliations=list(dict.fromkeys(record.get("affiliations") or [])),
            disciplines=concepts[:5],
            research_topics=concepts,
            key_works=[_work_record(w) for w in works[:max_works_per_editor]],
            source_refs=[
                x for x in [
                    record.get("openalex_author_id"),
                    member.get("source_url"),
                ] if x
            ],
            evidence_status=str(record.get("evidence_status") or "unknown"),
            confidence="medium" if record.get("openalex_author_id") and works else (
                "low" if record.get("openalex_author_id") else "unknown"
            ),
            unknowns=list(record.get("unknowns") or []),
        )
        if record.get("openalex_author_id") and not works:
            profile.unknowns.append("author identity resolved but work sample unavailable")
        out.append(profile)
    return out
