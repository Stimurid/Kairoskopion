"""Corpus acquisition manifest for Kairon target-world snapshots."""

from __future__ import annotations

from typing import Any

from ..adapters.venue.openalex_works import fetch_works_for_venue, reconstruct_abstract
from .models import CorpusArtifact, CorpusArtifactManifest


def _authors(work: dict[str, Any]) -> list[str]:
    out = []
    for a in work.get("authorships") or []:
        name = ((a or {}).get("author") or {}).get("display_name")
        if name:
            out.append(name)
    return out


def _best_content_ref(work: dict[str, Any]) -> tuple[str | None, str]:
    """Return (locator, kind) where kind is fulltext or landing.

    DOI/article landing pages are evidence locators but are not automatically
    full text. This distinction is required before download/validation.
    """
    oa = work.get("open_access") or {}
    if oa.get("oa_url"):
        return oa.get("oa_url"), "fulltext"
    for loc_key in ("best_oa_location", "primary_location"):
        loc = work.get(loc_key) or {}
        if loc.get("pdf_url"):
            return loc.get("pdf_url"), "fulltext"
    for loc in work.get("locations") or []:
        if isinstance(loc, dict) and loc.get("pdf_url"):
            return loc.get("pdf_url"), "fulltext"
    for loc_key in ("best_oa_location", "primary_location"):
        loc = work.get(loc_key) or {}
        if loc.get("landing_page_url"):
            return loc.get("landing_page_url"), "landing"
    for loc in work.get("locations") or []:
        if isinstance(loc, dict) and loc.get("landing_page_url"):
            return loc.get("landing_page_url"), "landing"
    if work.get("doi"):
        return str(work.get("doi")), "landing"
    return None, "none"


def manifest_from_openalex_works(
    *,
    target_id: str,
    works: list[dict[str, Any]],
    selection_strategy: str = "recent_articles",
) -> CorpusArtifactManifest:
    artifacts: list[CorpusArtifact] = []
    years: list[int] = []
    for w in works:
        year = w.get("publication_year")
        if isinstance(year, int):
            years.append(year)
        abstract = w.get("_reconstructed_abstract")
        if abstract is None:
            abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
        locator, locator_kind = _best_content_ref(w)
        state = (
            "fulltext_locator" if locator_kind == "fulltext"
            else "landing_locator" if locator_kind == "landing"
            else "abstract" if abstract
            else "metadata_only"
        )
        refs = w.get("id") or w.get("doi") or f"openalex:unknown:{len(artifacts)}"
        notes = []
        if abstract:
            notes.append("abstract_available")
        if locator:
            notes.append(f"{locator_kind}_locator:{locator}")
        artifacts.append(
            CorpusArtifact(
                source_ref=str(refs),
                title=w.get("title"),
                authors=_authors(w),
                year=year if isinstance(year, int) else None,
                doi=w.get("doi"),
                acquisition_state=state,
                local_ref=None,
                evidence_status="metadata_api_openalex",
                notes=notes,
            )
        )
    return CorpusArtifactManifest(
        target_id=target_id,
        selection_strategy=selection_strategy,
        artifacts=artifacts,
        time_range=f"{min(years)}-{max(years)}" if years else None,
        bias_notes=[
            "OpenAlex source coverage and ranking are not guaranteed representative of the full venue corpus"
        ],
        unknowns=[] if artifacts else ["no works acquired for target"],
    )


def acquire_corpus_manifest(
    *,
    target_id: str,
    openalex_source_id: str,
    max_works: int = 30,
    selection_strategy: str = "recent_articles",
    fixture_works: list[dict[str, Any]] | None = None,
) -> CorpusArtifactManifest:
    works = fixture_works if fixture_works is not None else fetch_works_for_venue(
        openalex_source_id, max_works=max_works
    )
    return manifest_from_openalex_works(
        target_id=target_id,
        works=list(works),
        selection_strategy=selection_strategy,
    )
