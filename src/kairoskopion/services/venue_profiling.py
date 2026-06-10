"""Venue Profiling Service (spec §15.2).

Builds VenueModel and PublicationRegimeModel from venue guidelines text.
MVP: deterministic heuristic extraction — no LLM, no web fetching.
"""

from __future__ import annotations

import re
from typing import Any

from ..enums import (
    LifecycleStatus,
    RegimeType,
    StalenessStatus,
    VenueType,
)
from ..ids import publication_regime_id, venue_model_id
from ..schema import PublicationRegimeModel, VenueModel


def _extract_field(text: str, label: str) -> str | None:
    m = re.search(rf"\*\*{label}:\*\*\s*(.+)", text, re.IGNORECASE)
    if not m:
        m = re.search(rf"^-\s*\*\*{label}:\*\*\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    if not m:
        m = re.search(rf"^{label}:\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_venue_name(text: str) -> str | None:
    """Extract venue name from multiple heading/field formats."""
    name = _extract_field(text, "Journal")
    if name:
        return name
    name = _extract_field(text, "Name")
    if name:
        return name
    m = re.search(r"^#\s+(?:Venue\s+(?:Seed\s+)?Profile:\s*)?(.+)", text.strip())
    if m:
        title = m.group(1).strip()
        for prefix in ("Venue Seed Profile:", "Venue Profile:"):
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        if title:
            return title
    return None


def _text_mentions_as_unknown(text: str, keyword: str) -> bool:
    """Check if a keyword appears in the text only in UNKNOWN/unverified context.

    Returns True if every occurrence of the keyword is inside an UNKNOWN section
    or on a line with explicit unknown/unverified markers.
    """
    lower = text.lower()
    kw = keyword.lower()
    if kw not in lower:
        return False
    in_unknown_section = False
    found_outside_unknown = False
    unknown_markers = [
        "unknown", "not found", "not available",
        "not obtained", "unverified", "requires verification",
        "require verification", "require independent",
        "claims require",
    ]
    for line in text.splitlines():
        stripped = line.strip()
        ll = stripped.lower()
        if re.match(r"^#+\s*UNKNOWN", stripped, re.IGNORECASE) or ll.startswith("unknown"):
            in_unknown_section = True
            continue
        if re.match(r"^#+\s", stripped) and "unknown" not in ll:
            in_unknown_section = False
            continue
        if ll.startswith("## ") and "unknown" not in ll:
            in_unknown_section = False
            continue
        if kw in ll:
            if in_unknown_section:
                continue
            if any(m in ll for m in unknown_markers):
                continue
            found_outside_unknown = True
    return not found_outside_unknown


def _extract_section(text: str, heading: str) -> str | None:
    pattern = rf"##\s*{re.escape(heading)}\s*\n+(.+?)(?=\n##|\Z)"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_article_types(text: str) -> list[str]:
    types: list[str] = []
    for m in re.finditer(r"-\s*\*\*(.+?)\*\*", text):
        name = m.group(1).strip()
        if "article" in name.lower() or "review" in name.lower() or "commentary" in name.lower():
            types.append(name.lower().replace(" ", "_"))
    return types or []


def _detect_review_model(text: str) -> str | None:
    lower = text.lower()
    if "double-blind" in lower or "double blind" in lower:
        return "double_blind"
    if "single-blind" in lower or "single blind" in lower:
        return "single_blind"
    if "open review" in lower:
        return "open_review"
    return None


def _detect_regime(text: str) -> str:
    lower = text.lower()
    if "special issue" in lower:
        return RegimeType.SPECIAL_ISSUE_ARTICLE.value
    if "conference" in lower and "proceedings" in lower:
        return RegimeType.CONFERENCE_PROCEEDINGS.value
    if "mega-journal" in lower or "megajournal" in lower:
        return RegimeType.MEGA_JOURNAL.value
    return RegimeType.CLASSIC_JOURNAL_ARTICLE.value


def _extract_word_limits(text: str) -> dict[str, str]:
    limits: dict[str, str] = {}
    for m in re.finditer(r"(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)\s*words?", text, re.IGNORECASE):
        limits["word_range"] = f"{m.group(1)}–{m.group(2)}"
    abstract_m = re.search(r"abstract.*?(\d+)\s*[-–]\s*(\d+)\s*words?", text, re.IGNORECASE)
    if abstract_m:
        limits["abstract_limit"] = f"{abstract_m.group(1)}–{abstract_m.group(2)}"
    return limits


def build_venue_model(
    text: str,
    *,
    source_ref: str | None = None,
) -> tuple[VenueModel, PublicationRegimeModel]:
    """Parse venue guidelines into VenueModel + PublicationRegimeModel."""
    journal_name = _extract_venue_name(text)
    publisher = _extract_field(text, "Publisher")
    url = _extract_field(text, "URL")
    scope_text = _extract_section(text, "Aims and Scope")
    if not scope_text:
        scope_text = _extract_section(text, "Likely Venue Orientation")
    article_types = _extract_article_types(text)
    review_model = _detect_review_model(text)
    regime_type = _detect_regime(text)
    word_limits = _extract_word_limits(text)

    # Collect explicit UNKNOWN items from seed files
    unknowns: list[str] = []
    unknowns.extend(_extract_explicit_unknowns(text))

    # Detect missing information (inverse logic) only for items NOT already in explicit unknowns
    lower = text.lower()
    if "ai disclosure" not in lower and "ai writing" not in lower:
        unknowns.append("AI disclosure policy not found")
    if "apc" not in lower and "article processing charge" not in lower:
        unknowns.append("APC details not found")
    if "data availability" not in lower:
        unknowns.append("data availability policy not found")
    if "indexing" not in lower and "scopus" not in lower and "web of science" not in lower:
        unknowns.append("indexing information not found")

    # Language
    language = _extract_language_policy(text)

    regime = PublicationRegimeModel(
        publication_regime_id=publication_regime_id(),
        regime_type=regime_type,
        description=f"Peer-reviewed journal, {review_model or 'unknown review model'}",
        review_model=review_model,
        typical_article_forms=article_types,
        evidence_refs=[source_ref] if source_ref else [],
    )

    # Sprint 2: extract enrichment fields (claims, not verified facts)
    # Skip extraction when keywords appear only in UNKNOWN/unverified context
    aims_scope = scope_text
    indexing_claims = _extract_indexing_claims(lower)
    open_access = None if _text_mentions_as_unknown(text, "open access") else _extract_open_access(lower)
    apc_policy = None if _text_mentions_as_unknown(text, "apc") else _extract_apc_policy(lower)
    review_model_safe = None if _text_mentions_as_unknown(text, "peer review") else review_model
    review_claims = review_model_safe or "unknown"
    anonymization = None if _text_mentions_as_unknown(text, "blind") else _extract_anonymization(lower)
    ai_policy = None if _text_mentions_as_unknown(text, "ai") else _extract_ai_policy(lower)
    data_policy = None if _text_mentions_as_unknown(text, "data") else _extract_data_policy(lower)
    ethics_policy = None if _text_mentions_as_unknown(text, "ethics") else _extract_ethics_policy(lower)

    venue = VenueModel(
        venue_model_id=venue_model_id(),
        canonical_name=journal_name,
        venue_type=VenueType.JOURNAL.value,
        official_urls=[url] if url else [],
        scope_summary=scope_text,
        author_guidelines_refs=[source_ref] if source_ref else [],
        article_types_supported=article_types,
        language_policy=language,
        publication_regime_id=regime.publication_regime_id,
        publisher_or_owner=publisher,
        source_refs=[source_ref] if source_ref else [],
        unknowns=unknowns,
        confidence="medium" if scope_text else "low",
        staleness_status=StalenessStatus.FRESH.value,
        lifecycle_status=LifecycleStatus.DRAFT.value,
        # Sprint 2: enrichment fields
        aims_scope_summary=aims_scope,
        indexing_claims=indexing_claims,
        open_access_status=open_access,
        apc_policy=apc_policy,
        review_process_claims=review_claims,
        word_limits=word_limits if word_limits else None,
        anonymization_policy=anonymization,
        ai_policy=ai_policy,
        data_policy=data_policy,
        ethics_policy=ethics_policy,
        freshness_status="fresh",
    )

    return venue, regime


def _extract_language_policy(text: str) -> str | None:
    """Extract article body language from venue guidelines.

    Checks dedicated Language Policy section first, then scope/about text,
    then Submission Requirements as fallback. Distinguishes metadata language
    requirements from article body language.
    """
    lower = text.lower()

    lang_section = _extract_section(text, "Language Policy")
    if lang_section:
        ls = lang_section.lower()
        if "russian-language only" in ls or "russian only" in ls:
            return "Russian"
        if any(m in ls for m in (
            "русскоязычный", "russian-language journal",
            "almost certainly russian", "russian-language only for article body",
        )):
            return "Russian"
        if "english" in ls and "russian" not in ls:
            return "English"
        if "russian" in ls and "english" not in ls:
            return "Russian"
        if "russian" in ls and "english" in ls:
            if "metadata" in ls and "english" in ls:
                return "Russian"
            return "Multilingual"

    scope_section = _extract_section(text, "Aims and Scope") or _extract_section(text, "Scope")
    if scope_section:
        ss = scope_section.lower()
        if "russian-language journal" in ss or "русскоязычный" in ss:
            return "Russian"

    req_section = _extract_section(text, "Submission Requirements")
    if req_section:
        rs = req_section.lower()
        if "metadata" in rs and "english" in rs and "russian" in rs:
            return None
        if "english" in rs:
            return "English"

    return None


def _extract_indexing_claims(lower: str) -> list[str]:
    """Extract indexing claims from text."""
    claims: list[str] = []
    for idx in ("scopus", "web of science", "wos", "pubmed", "medline",
                "doaj", "ebsco", "erih", "ulrich"):
        if idx in lower:
            claims.append(idx)
    return claims


def _extract_open_access(lower: str) -> str | None:
    if "open access" in lower:
        if "gold" in lower:
            return "gold_open_access"
        if "hybrid" in lower:
            return "hybrid"
        return "open_access"
    return None


def _extract_apc_policy(lower: str) -> str | None:
    if "no apc" in lower or "no article processing" in lower or "no publication fee" in lower:
        return "no_apc"
    if "apc" in lower or "article processing charge" in lower:
        return "apc_required"
    return None


def _extract_anonymization(lower: str) -> str | None:
    if "double-blind" in lower or "double blind" in lower:
        return "double_blind"
    if "single-blind" in lower or "single blind" in lower:
        return "single_blind"
    if "open review" in lower:
        return "open_review"
    return None


def _extract_ai_policy(lower: str) -> str | None:
    if "ai disclosure" in lower or "ai writing" in lower or "generative ai" in lower:
        return "ai_policy_present"
    return None


def _extract_data_policy(lower: str) -> str | None:
    if "data availability" in lower or "data sharing" in lower:
        return "data_policy_present"
    return None


def _extract_ethics_policy(lower: str) -> str | None:
    if "ethics approval" in lower or "ethics committee" in lower or "irb" in lower:
        return "ethics_policy_present"
    return None


def _extract_explicit_unknowns(text: str) -> list[str]:
    """Extract items listed under UNKNOWN sections in venue seed files."""
    unknowns: list[str] = []
    in_unknown_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#+\s*UNKNOWN", stripped, re.IGNORECASE) or stripped.startswith("UNKNOWN"):
            in_unknown_section = True
            continue
        if in_unknown_section:
            if re.match(r"^#+\s", stripped) or (stripped and not stripped.startswith("-")):
                if not stripped.startswith("-"):
                    in_unknown_section = False
                    continue
            if stripped.startswith("- "):
                item = stripped[2:].rstrip(";.,")
                if item:
                    unknowns.append(item)
    return unknowns
