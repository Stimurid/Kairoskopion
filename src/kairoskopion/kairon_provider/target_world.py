"""Build a durable Kairoskopion TargetWorldSnapshot.

A target world freezes the evidence used to pressure an Artikl text state:
venue identity, selected editor scholarship, corpus acquisition state and
corpus-derived publication models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from ..adapters.venue.editorial_board import build_editorial_board_cloud
from ..adapters.venue.openalex_works import fetch_works_for_venue
from .corpus import manifest_from_openalex_works
from .editor_profiles import acquire_editor_scientific_profiles
from .models import TargetWorldSnapshot
from .target_models import extract_target_models


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_target_world_snapshot(
    *,
    target_id: str,
    openalex_source_id: str | None = None,
    venue_profile_ref: str | None = None,
    board_page_url: str | None = None,
    board_page_html: str | None = None,
    editor_members: list[dict[str, Any]] | None = None,
    max_works: int = 30,
    max_editors: int = 10,
    selection_strategy: str = "recent_articles",
    fixture_works: list[dict[str, Any]] | None = None,
    editor_fixtures: dict[str, dict[str, Any]] | None = None,
    provider_commit: str | None = None,
) -> TargetWorldSnapshot:
    """Build one immutable-by-convention target-world snapshot.

    Network access is bounded by the caller's supplied locators. Tests can use
    fixture_works and editor_members/editor_fixtures for deterministic runs.
    """
    works: list[dict[str, Any]] = []
    unknowns: list[str] = []
    evidence_refs: list[str] = []

    if fixture_works is not None:
        works = list(fixture_works)
    elif openalex_source_id:
        works = fetch_works_for_venue(openalex_source_id, max_works=max_works)
    else:
        unknowns.append("no OpenAlex source id or corpus fixture supplied")

    manifest = manifest_from_openalex_works(
        target_id=target_id,
        works=works,
        selection_strategy=selection_strategy,
    )
    evidence_refs.extend(a.source_ref for a in manifest.artifacts)
    models = extract_target_models(works, evidence_refs=evidence_refs)

    members = list(editor_members or [])
    if not members and (board_page_url or board_page_html):
        cloud = build_editorial_board_cloud(
            board_page_url=board_page_url,
            board_page_html=board_page_html,
            target_sample=max_editors,
        )
        members = list(cloud.members or [])
        unknowns.extend(list(cloud.unknowns or []))
        if board_page_url:
            evidence_refs.append(board_page_url)

    editor_profiles = acquire_editor_scientific_profiles(
        members,
        max_editors=max_editors,
        fixtures=editor_fixtures,
    ) if members else []
    if members and not editor_profiles:
        unknowns.append("editor members found but no scientific profiles resolved")

    for profile in editor_profiles:
        evidence_refs.extend(profile.source_refs)

    snapshot_id = f"targetworld:{target_id}:{uuid4().hex[:12]}"
    snapshot = TargetWorldSnapshot(
        snapshot_id=snapshot_id,
        target_id=target_id,
        provider_commit=provider_commit,
        venue_profile_ref=venue_profile_ref,
        editor_profiles=editor_profiles,
        corpus_manifest=manifest,
        target_models=models,
        evidence_refs=list(dict.fromkeys(x for x in evidence_refs if x)),
        freshness={
            "snapshot_created_at": _now(),
            "corpus_selection_strategy": selection_strategy,
            "corpus_size": len(manifest.artifacts),
            "editor_profile_count": len(editor_profiles),
            "unknowns": unknowns + list(manifest.unknowns),
        },
    )
    return snapshot
