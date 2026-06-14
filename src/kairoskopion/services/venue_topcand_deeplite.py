"""Top-candidate deep-lite: discover URLs, extract formal profile,
build corpus pattern light summary.

Operates ONLY on the venues the caller passes in. NOT a broad
discovery pass. Caps fetches per venue.

Steps for each VPKG:

  1. Controlled homepage -> {guidelines, board, scope, OA/APC} URL hop
     via `adapters.venue.venue_url_hop`.
  2. If a guidelines URL was discovered AND it opens, call
     `adapters.venue.guidelines_extractor` to populate a minimal
     FormalSubmissionProfile.
  3. If the VPKG has an OpenAlex source id, re-mine up to 25 latest
     works and build a PublishedArticlePattern-shaped light summary.

NO LLM. All extracted facts carry evidence_status. All absent facts
remain UNKNOWN_NOT_FOUND or INACCESSIBLE; never inferred as 'NO'.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


# Stopwords for corpus title bag analysis
_STOPS_EN = {
    "the", "a", "an", "of", "and", "in", "on", "to", "for", "with",
    "from", "by", "at", "is", "are", "as", "or", "be", "this", "that",
    "between", "through", "into", "within", "across", "about",
    "study", "studies", "analysis", "case", "review",
}


def discover_for_vpkg(vpkg) -> dict[str, Any]:
    """C/D step: URL hop + guidelines extraction.

    Returns a dossier with discovered URLs and formal_submission_profile.
    Does NOT mutate the VPKG.
    """
    from ..adapters.venue.venue_url_hop import discover_urls_from_homepage
    from ..adapters.venue.guidelines_extractor import (
        extract_formal_submission_profile,
    )

    dossier: dict[str, Any] = {
        "vpkg_id": vpkg.venue_profile_package_id,
        "canonical_name": vpkg.canonical_name,
        "homepage_url": vpkg.homepage_url,
        "url_hop": None,
        "formal_submission_profile": None,
        "warnings": [],
    }

    if not vpkg.homepage_url:
        dossier["warnings"].append(
            "no homepage_url on VPKG — URL hop skipped"
        )
        return dossier

    hop = discover_urls_from_homepage(vpkg.homepage_url)
    dossier["url_hop"] = hop

    guidelines_urls = hop.get("discovered", {}).get("guidelines") or []
    if guidelines_urls:
        fsp = extract_formal_submission_profile(
            guidelines_url=guidelines_urls[0]
        )
        # Tag confidence: this came from a homepage-hopped link
        fsp["discovery_method"] = "homepage_link_hop"
        fsp["source_url"] = guidelines_urls[0]
        # Each extracted field already carries `evidence` and the doc
        # carries `access_status`; add an overall extraction_confidence:
        if fsp.get("access_status") == "opened" and fsp.get("fields_present"):
            fsp["extraction_confidence"] = (
                "medium" if len(fsp["fields_present"]) >= 3 else "low"
            )
        else:
            fsp["extraction_confidence"] = "low"
        dossier["formal_submission_profile"] = fsp
    else:
        dossier["warnings"].append(
            "no guidelines URL discovered on homepage — FormalSubmissionProfile "
            "remains UNKNOWN_NOT_FOUND"
        )

    return dossier


def corpus_pattern_light_summary(
    vpkg, *, max_works: int = 25,
) -> dict[str, Any]:
    """Re-mine venue corpus and produce a PublishedArticlePattern-light dict.

    Returns:
      {
        "vpkg_id", "canonical_name", "openalex_source_id",
        "works_sampled", "abstracts_available",
        "year_range", "common_terms", "dominant_concepts",
        "method_token_density", "article_type_hints",
        "novelty_claim_hints", "reference_count_stats",
        "evidence_status": "openalex_corpus_observation",
        "warnings": [...],
        "_lifecycle_status": "PRELIMINARY" | "INSUFFICIENT_CORPUS_FOR_PATTERN"
      }
    """
    summary: dict[str, Any] = {
        "vpkg_id": vpkg.venue_profile_package_id,
        "canonical_name": vpkg.canonical_name,
        "openalex_source_id": vpkg.openalex_source_id,
        "works_sampled": 0,
        "abstracts_available": 0,
        "year_range": [None, None],
        "common_terms": [],
        "dominant_concepts": [],
        "method_token_density": 0.0,
        "article_type_hints": [],
        "novelty_claim_hints": [],
        "reference_count_stats": {"min": None, "max": None,
                                    "median": None, "available_in": 0},
        "evidence_status": "openalex_corpus_observation",
        "warnings": [],
        "_lifecycle_status": "PRELIMINARY",
    }
    if not vpkg.openalex_source_id:
        summary["warnings"].append("no openalex_source_id; pattern skipped")
        summary["_lifecycle_status"] = "INSUFFICIENT_CORPUS_FOR_PATTERN"
        return summary

    # Lazy import to preserve services-no-urllib invariant
    from ..adapters.venue.openalex_works import (
        fetch_works_for_venue,
        reconstruct_abstract,
    )

    works = fetch_works_for_venue(vpkg.openalex_source_id, max_works=max_works)
    if not works:
        summary["warnings"].append("no works fetched")
        summary["_lifecycle_status"] = "INSUFFICIENT_CORPUS_FOR_PATTERN"
        return summary

    titles: list[str] = []
    years: list[int] = []
    concept_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    ref_counts: list[int] = []
    abstracts_n = 0
    method_hits = 0
    novelty_hits = 0
    for w in works:
        t = (w.get("title") or w.get("display_name") or "").strip()
        if t:
            titles.append(t)
        y = w.get("publication_year")
        if isinstance(y, int):
            years.append(y)
        ab = reconstruct_abstract(w.get("abstract_inverted_index"))
        if ab:
            abstracts_n += 1
            low = ab.lower()
            if any(tok in low for tok in (
                "we conducted", "we collected", "interviews",
                "we surveyed", "questionnaire", "experiment", "method",
            )):
                method_hits += 1
            if any(tok in low for tok in (
                "we propose", "we introduce", "we argue",
                "novel", "first to", "new framework",
            )):
                novelty_hits += 1
        for c in (w.get("concepts") or [])[:5]:
            name = c.get("display_name")
            if name:
                concept_counter[name] += 1
        wt = (w.get("type") or "").strip()
        if wt:
            type_counter[wt] += 1
        if "referenced_works_count" in w:
            v = w.get("referenced_works_count")
            if isinstance(v, int):
                ref_counts.append(v)
        elif "referenced_works" in w and isinstance(
            w.get("referenced_works"), list
        ):
            ref_counts.append(len(w["referenced_works"]))

    summary["works_sampled"] = len(works)
    summary["abstracts_available"] = abstracts_n
    if years:
        summary["year_range"] = [min(years), max(years)]
    # Common terms from titles
    tokens: Counter[str] = Counter()
    for t in titles:
        for w in re.findall(r"[A-Za-zА-Яа-яёЁ]{4,}", t):
            wl = w.lower()
            if wl in _STOPS_EN:
                continue
            tokens[wl] += 1
    summary["common_terms"] = [
        {"term": k, "count": v} for k, v in tokens.most_common(10)
    ]
    summary["dominant_concepts"] = [
        {"name": k, "count": v} for k, v in concept_counter.most_common(8)
    ]
    summary["article_type_hints"] = [
        {"type": k, "count": v} for k, v in type_counter.most_common(5)
    ]
    if abstracts_n > 0:
        summary["method_token_density"] = round(method_hits / abstracts_n, 3)
        summary["novelty_claim_hints"] = [
            {"hint": "novelty_phrase_density",
             "value": round(novelty_hits / abstracts_n, 3),
             "evidence": "openalex_abstract_corpus_observation"},
        ]
    if ref_counts:
        ref_counts.sort()
        med = ref_counts[len(ref_counts) // 2]
        summary["reference_count_stats"] = {
            "min": ref_counts[0],
            "max": ref_counts[-1],
            "median": med,
            "available_in": len(ref_counts),
        }
    if summary["works_sampled"] < 3:
        summary["_lifecycle_status"] = "INSUFFICIENT_CORPUS_FOR_PATTERN"
        summary["warnings"].append(
            f"only {summary['works_sampled']} works — insufficient for pattern"
        )
    return summary


def enrich_board_for_vpkg(
    vpkg, board_page_url: str | None,
) -> dict[str, Any]:
    """Wire the existing editorial_board adapter onto a discovered URL.

    Returns a dossier dict with:
      - vpkg_id, canonical_name
      - board_page_url (the URL tried)
      - extraction_status: one of
          EXTRACTED_FROM_OFFICIAL_HTML | EXTRACTED_UNVERIFIED |
          INACCESSIBLE | JS_ONLY | NOT_FOUND_AFTER_SEARCH | UNKNOWN
      - editorial_board_cloud: the EBC dict (when extraction succeeded),
        else None
      - members_sampled: int
      - notes: [...]

    Does NOT mutate the VPKG. Caller does the safe upsert. Honors:
      - empty extraction NEVER overwrites an existing non-empty board
        cloud (caller must NOT overwrite if extraction_status is
        anything other than EXTRACTED_FROM_OFFICIAL_HTML or
        EXTRACTED_UNVERIFIED with members > 0);
      - JS-only and INACCESSIBLE cases are honest, not fabricated.
    """
    from ..adapters.venue.editorial_board import (
        build_editorial_board_cloud,
    )

    out: dict[str, Any] = {
        "vpkg_id": vpkg.venue_profile_package_id,
        "canonical_name": vpkg.canonical_name,
        "board_page_url": board_page_url,
        "extraction_status": "UNKNOWN",
        "editorial_board_cloud": None,
        "members_sampled": 0,
        "notes": [],
    }

    if not board_page_url:
        out["extraction_status"] = "NOT_FOUND_AFTER_SEARCH"
        out["notes"].append(
            "no board URL was discovered for this VPKG — board enrichment skipped"
        )
        return out

    try:
        cloud = build_editorial_board_cloud(
            board_page_url=board_page_url,
            venue_profile_package_id=vpkg.venue_profile_package_id,
            target_sample=30,
        )
    except Exception as exc:  # noqa: BLE001
        out["extraction_status"] = "INACCESSIBLE"
        out["notes"].append(f"adapter raised: {type(exc).__name__}: {exc}")
        return out

    members = getattr(cloud, "members", []) or []
    members_n = getattr(cloud, "members_sampled", 0) or len(members)
    out["members_sampled"] = members_n

    # Inspect the unknowns/warnings the adapter produced
    unks_joined = " | ".join(getattr(cloud, "unknowns", []) or [])
    warns_joined = " | ".join(getattr(cloud, "warnings", []) or [])
    if members_n == 0:
        if "JS-only" in warns_joined or "JS-only" in unks_joined:
            out["extraction_status"] = "JS_ONLY"
        elif "fetch failed" in unks_joined:
            out["extraction_status"] = "INACCESSIBLE"
        elif "no editor name/affiliation" in unks_joined:
            out["extraction_status"] = "NOT_FOUND_AFTER_SEARCH"
        else:
            out["extraction_status"] = "UNKNOWN"
        out["notes"].append("0 members extracted — VPKG board not updated")
        out["editorial_board_cloud"] = cloud.to_dict()
        return out

    # We have members. Check whether at least one carried OpenAlex
    # identity resolution (that flips status from UNVERIFIED to verified).
    any_verified = any(
        (m or {}).get("evidence_status") == "metadata_api_openalex"
        for m in members
    )
    out["extraction_status"] = (
        "EXTRACTED_FROM_OFFICIAL_HTML" if any_verified
        else "EXTRACTED_UNVERIFIED"
    )
    out["editorial_board_cloud"] = cloud.to_dict()
    return out


# Late import of re (kept at bottom to be obvious that pattern
# uses regex inside the function only)
import re  # noqa: E402
