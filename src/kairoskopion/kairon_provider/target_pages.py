"""Bounded target-page discovery and snapshotting for publication worlds."""

from __future__ import annotations

from typing import Any

from ..adapters.venue.base import VenueAdapterMode
from ..adapters.venue.guidelines_extractor import extract_formal_submission_profile
from ..adapters.venue.snapshot_crawler import VenueSnapshotCrawler
from ..adapters.venue.venue_url_hop import discover_urls_from_homepage
from .models import TargetPageBundle, TargetPageSnapshot


def _claim(result: Any, path: str) -> Any:
    for claim in getattr(result, "claims", []) or []:
        if getattr(claim, "claim_path", None) == path:
            return getattr(claim, "claim_value", None)
    return None


def build_target_page_bundle(
    *,
    homepage_url: str,
    discovered: dict[str, list[str]] | None = None,
    provided_html: dict[str, str] | None = None,
) -> TargetPageBundle:
    """Discover and snapshot a bounded set of journal target pages.

    provided_html maps URL -> HTML for deterministic tests/offline replay.
    Live mode fetches only explicit URLs discovered by the existing bounded
    same-domain hop.
    """
    provided_html = provided_html or {}
    hop = None
    if discovered is None:
        hop = discover_urls_from_homepage(homepage_url)
        discovered = dict(hop.get("discovered") or {})
    warnings = list((hop or {}).get("warnings") or [])

    pages: list[TargetPageSnapshot] = []
    for role, urls in discovered.items():
        for url in list(urls or [])[:1]:
            html = provided_html.get(url)
            crawler = VenueSnapshotCrawler(
                VenueAdapterMode.FIXTURE if html is not None else VenueAdapterMode.LIVE_API
            )
            result = (
                crawler.store_provided_html(html, url)
                if html is not None
                else crawler.lookup_venue(url=url)
            )
            extracted: dict[str, Any] = {}
            if role == "guidelines":
                extracted["formal_submission_profile"] = extract_formal_submission_profile(
                    guidelines_url=url if html is None else None,
                    guidelines_html=html,
                )
            pages.append(
                TargetPageSnapshot(
                    role=role,
                    url=url,
                    access_status=(
                        "opened" if getattr(result, "is_available", False)
                        else str(getattr(result, "status", "unknown"))
                    ),
                    content_hash=_claim(result, "content_hash"),
                    evidence_status=str(getattr(result, "evidence_status", "unknown")),
                    extracted=extracted,
                    unknowns=list(getattr(result, "unknowns", []) or []),
                )
            )

    return TargetPageBundle(
        homepage_url=homepage_url,
        pages=pages,
        discovered_urls=discovered,
        warnings=warnings,
    )
