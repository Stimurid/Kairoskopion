"""V2-D minimal ComplianceChecklist builder.

Builds a ComplianceChecklist from already-available chain artefacts
(ArticleModel, VenueModel, SubmissionScenario, RiskReport). Uses ONLY
fields we have honest evidence for:

  - if a venue policy field is None/empty → item status =
    "unknown_not_verified", NEVER "satisfied" or "not required";
  - if ArticleModel lacks title/genre/abstract → checklist item
    surfaces it honestly as "missing" or "needs_user_input";
  - if no bibliography parsed → references item is "needs_user_input";
  - RiskReport contributes warnings/derived items, NEVER invents
    venue requirements.

Does NOT use the legacy services/compliance.py substring matcher
(which has the Z#3 "ai" in gl false-positive bug from V2 audit).
"""

from __future__ import annotations

from typing import Any

from ..schema import (
    ArticleModel,
    BibliographyProfile,
    ComplianceChecklist,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)


# V2-D allowed statuses
ITEM_SATISFIED = "satisfied"
ITEM_MISSING = "missing"
ITEM_NEEDS_USER_INPUT = "needs_user_input"
ITEM_UNKNOWN_NOT_VERIFIED = "unknown_not_verified"
ITEM_NOT_APPLICABLE = "not_applicable"
ITEM_WARNING = "warning"
ITEM_BLOCKED = "blocked"

# source_status taxonomy
SRC_SOURCE_BACKED = "source_backed"
SRC_DERIVED_FROM_ARTICLE = "derived_from_article"
SRC_DERIVED_FROM_VENUE = "derived_from_venue"
SRC_RISK_INFERRED = "risk_inferred"
SRC_UNKNOWN_NOT_VERIFIED = "unknown_not_verified"
SRC_NOT_APPLICABLE = "not_applicable"

# Overall statuses
STATUS_NOT_BUILT = "not_built"
STATUS_DRAFT = "draft"
STATUS_PARTIAL = "partial"
STATUS_READY = "ready"
STATUS_BLOCKED = "blocked"


def _item(
    category: str,
    requirement: str,
    status: str,
    source_status: str,
    notes: str = "",
    user_action_needed: bool | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "item_id": f"cc_{category}",
        "category": category,
        "requirement": requirement,
        "status": status,
        "source_status": source_status,
        "evidence_refs": list(evidence_refs or []),
        "user_action_needed": (
            user_action_needed
            if user_action_needed is not None
            else status in (ITEM_MISSING, ITEM_NEEDS_USER_INPUT,
                            ITEM_UNKNOWN_NOT_VERIFIED, ITEM_BLOCKED)
        ),
        "notes": notes,
    }


def _has(s: str | None) -> bool:
    return bool(s and s.strip())


def build_minimal_compliance_checklist(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario | None,
    risk_report: RiskReport | None,
    bibliography_profile: BibliographyProfile | None = None,
) -> ComplianceChecklist:
    items: list[dict[str, Any]] = []
    missing: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    unknowns: list[str] = []
    created_from: list[str] = ["article_model", "venue_model"]

    # --- Title (derived from article) ---
    if _has(article.title_current):
        items.append(_item(
            "title",
            "Manuscript title present",
            ITEM_SATISFIED,
            SRC_DERIVED_FROM_ARTICLE,
            notes=f"Article modeler extracted: {article.title_current[:60]!r}",
        ))
    else:
        items.append(_item(
            "title",
            "Manuscript title required",
            ITEM_MISSING,
            SRC_DERIVED_FROM_ARTICLE,
            notes="ArticleModeler did not extract a title — verify the "
                  "manuscript has an H1/title heading.",
        ))
        missing.append("manuscript title")

    # --- Article type ---
    if _has(article.genre_current) and article.genre_current != "unknown":
        venue_types = venue.article_types_supported or []
        if venue_types and article.genre_current in venue_types:
            items.append(_item(
                "article_type",
                "Article type compatible with venue's supported types",
                ITEM_SATISFIED,
                SRC_SOURCE_BACKED,
                notes=f"Article: {article.genre_current}; venue accepts "
                      f"{', '.join(venue_types)}.",
            ))
        elif venue_types:
            items.append(_item(
                "article_type",
                "Article type compatible with venue's supported types",
                ITEM_WARNING,
                SRC_SOURCE_BACKED,
                notes=f"Article genre {article.genre_current!r} not in "
                      f"venue's stated types ({', '.join(venue_types)}). "
                      "Verify before submission.",
            ))
            warnings.append("article type may not match venue's supported types")
        else:
            items.append(_item(
                "article_type",
                "Article type compatible with venue",
                ITEM_UNKNOWN_NOT_VERIFIED,
                SRC_UNKNOWN_NOT_VERIFIED,
                notes="Venue model did not extract a list of supported "
                      "article types — check venue page manually.",
            ))
            unknowns.append("venue's supported article types not extracted")
    else:
        items.append(_item(
            "article_type",
            "Article type identified",
            ITEM_NEEDS_USER_INPUT,
            SRC_DERIVED_FROM_ARTICLE,
            notes="ArticleModeler did not identify an article type — "
                  "operator should confirm theoretical-essay vs "
                  "conceptual vs empirical.",
        ))
        missing.append("article type")

    # --- Language ---
    if _has(article.language) and venue.language_policy:
        items.append(_item(
            "language",
            "Language matches venue's language policy",
            (ITEM_SATISFIED if article.language in (venue.language_policy or "")
             else ITEM_WARNING),
            SRC_SOURCE_BACKED,
            notes=f"Article: {article.language}; venue policy: "
                  f"{venue.language_policy}.",
        ))
    elif _has(article.language):
        items.append(_item(
            "language",
            "Language matches venue's policy",
            ITEM_UNKNOWN_NOT_VERIFIED,
            SRC_UNKNOWN_NOT_VERIFIED,
            notes=f"Article in {article.language}; venue's language "
                  "policy not extracted.",
        ))
        unknowns.append("venue language policy unknown")
    else:
        items.append(_item(
            "language",
            "Article language stated",
            ITEM_NEEDS_USER_INPUT,
            SRC_DERIVED_FROM_ARTICLE,
        ))

    # --- Abstract ---
    if _has(article.abstract_current):
        items.append(_item(
            "abstract",
            "Abstract present",
            ITEM_SATISFIED,
            SRC_DERIVED_FROM_ARTICLE,
            notes=f"Length: {article.abstract_length or '?'} chars.",
        ))
    else:
        items.append(_item(
            "abstract",
            "Abstract required",
            ITEM_MISSING,
            SRC_DERIVED_FROM_ARTICLE,
        ))
        missing.append("abstract")

    # --- Word count ---
    if article.word_count:
        items.append(_item(
            "word_count",
            "Word count within venue range",
            ITEM_UNKNOWN_NOT_VERIFIED,
            SRC_UNKNOWN_NOT_VERIFIED,
            notes=f"Article: {article.word_count} words. Venue's explicit "
                  "word range not extracted from venue model in V2-D.",
        ))
        unknowns.append("venue word-count limits not extracted")
    else:
        items.append(_item(
            "word_count",
            "Word count check",
            ITEM_UNKNOWN_NOT_VERIFIED,
            SRC_UNKNOWN_NOT_VERIFIED,
            notes="Article word count not measured by intake.",
        ))

    # --- References (V2-E: bibliography-aware) ---
    bp = bibliography_profile
    if bp is not None:
        created_from.append("bibliography_profile")
        if bp.status == "unknown":
            items.append(_item(
                "references",
                "Manuscript has a parsed bibliography",
                ITEM_UNKNOWN_NOT_VERIFIED,
                SRC_UNKNOWN_NOT_VERIFIED,
                notes="Raw article text unavailable to bibliography "
                      "parser — bibliography state unknown.",
            ))
            unknowns.append("bibliography presence unknown")
        elif bp.status == "not_found":
            items.append(_item(
                "references",
                "Manuscript has a bibliography section",
                ITEM_MISSING,
                SRC_DERIVED_FROM_ARTICLE,
                notes="No recognized bibliography heading detected in "
                      "the supplied article text.",
            ))
            missing.append("bibliography section")
        elif bp.status == "present_unparsed":
            items.append(_item(
                "references",
                "Manuscript has a parseable bibliography",
                ITEM_NEEDS_USER_INPUT,
                SRC_DERIVED_FROM_ARTICLE,
                notes="Bibliography heading found but no references "
                      "could be parsed structurally.",
            ))
            missing.append("parseable bibliography")
        elif bp.status == "malformed":
            items.append(_item(
                "references",
                "Bibliography formatting",
                ITEM_WARNING,
                SRC_DERIVED_FROM_ARTICLE,
                notes=f"{bp.malformed_count}/{bp.reference_count} "
                      "references look malformed.",
            ))
            warnings.append("bibliography contains malformed references")
        elif bp.status in ("parsed_structural", "partial"):
            # Structural parse OK, but external verification not done.
            if bp.verification_status == "verified":
                items.append(_item(
                    "references",
                    "References parsed and externally verified",
                    ITEM_SATISFIED,
                    SRC_SOURCE_BACKED,
                    notes=f"{bp.reference_count} references verified.",
                ))
            else:
                items.append(_item(
                    "references",
                    "References parsed; external verification pending",
                    ITEM_NEEDS_USER_INPUT,
                    SRC_DERIVED_FROM_ARTICLE,
                    notes=f"{bp.reference_count} parsed; "
                          f"{bp.doi_count} have DOI; "
                          "external metadata verification not performed.",
                ))
                missing.append("external reference verification")
        else:
            items.append(_item(
                "references",
                "References present in manuscript",
                ITEM_NEEDS_USER_INPUT,
                SRC_DERIVED_FROM_ARTICLE,
                notes=f"BibliographyProfile.status={bp.status}",
            ))
    elif article.reference_count and article.reference_count > 0:
        items.append(_item(
            "references",
            "References present in manuscript",
            ITEM_NEEDS_USER_INPUT,
            SRC_DERIVED_FROM_ARTICLE,
            notes=f"Self-reported: {article.reference_count} references. "
                  "BibliographyProfile not built — per-reference "
                  "DOI/year verification not performed.",
        ))
        missing.append("structural bibliography parse")
    else:
        items.append(_item(
            "references",
            "Manuscript has a references section",
            ITEM_NEEDS_USER_INPUT,
            SRC_DERIVED_FROM_ARTICLE,
            notes="Reference count not detected — see CitationPlan for "
                  "bibliography parsing task.",
        ))
        missing.append("parsed bibliography")

    # --- AI disclosure (venue policy + article disclosure) ---
    venue_ai = (venue.ai_policy or "").strip()
    article_ai = getattr(article, "has_ai_disclosure", None)
    if venue_ai and venue_ai not in ("unknown", ""):
        # Venue acknowledges an AI policy of some form
        if article_ai is True:
            items.append(_item(
                "ai_disclosure",
                "AI tool disclosure required by venue",
                ITEM_SATISFIED,
                SRC_SOURCE_BACKED,
                notes="Article has AI disclosure statement.",
            ))
        else:
            items.append(_item(
                "ai_disclosure",
                "AI tool disclosure required by venue",
                ITEM_NEEDS_USER_INPUT,
                SRC_SOURCE_BACKED,
                notes=f"Venue AI policy: {venue_ai}. Article does not "
                      "self-report an AI disclosure statement.",
            ))
            missing.append("AI disclosure statement")
    else:
        items.append(_item(
            "ai_disclosure",
            "AI tool disclosure",
            ITEM_UNKNOWN_NOT_VERIFIED,
            SRC_UNKNOWN_NOT_VERIFIED,
            notes="Venue's AI disclosure policy not verified. Do NOT "
                  "assume not-required: check the venue page manually.",
        ))
        unknowns.append("venue AI disclosure policy not verified")

    # --- Data availability ---
    venue_data = (venue.data_policy or "").strip() if hasattr(venue, "data_policy") else ""
    article_data = getattr(article, "has_data_availability_statement", None)
    if venue_data:
        if article.method_status == "no_method" or article.method_status == "conceptual_method":
            items.append(_item(
                "data_availability",
                "Data availability statement (theoretical-only paper)",
                ITEM_NOT_APPLICABLE,
                SRC_DERIVED_FROM_ARTICLE,
                notes=f"Article method status: {article.method_status}.",
            ))
        elif article_data is True:
            items.append(_item(
                "data_availability",
                "Data availability statement required",
                ITEM_SATISFIED, SRC_SOURCE_BACKED,
            ))
        else:
            items.append(_item(
                "data_availability",
                "Data availability statement required",
                ITEM_NEEDS_USER_INPUT, SRC_SOURCE_BACKED,
                notes="Venue requires data availability statement; "
                      "article does not self-report one.",
            ))
            missing.append("data availability statement")
    else:
        items.append(_item(
            "data_availability",
            "Data availability statement",
            ITEM_UNKNOWN_NOT_VERIFIED, SRC_UNKNOWN_NOT_VERIFIED,
            notes="Venue's data availability policy not verified.",
        ))
        unknowns.append("venue data availability policy not verified")

    # --- Ethics / COI / funding / authorship: all unknown-by-default ---
    for cat, label, note in (
        ("ethics", "Ethics statement",
         "Venue's ethics policy not verified; required where applicable."),
        ("coi",   "Conflict of interest declaration",
         "COI declaration commonly required at submission; venue policy not verified."),
        ("funding", "Funding statement",
         "Funding statement commonly required; venue policy not verified."),
        ("authorship", "Authorship & contributor roles",
         "Authorship metadata not extracted by article modeler."),
    ):
        items.append(_item(
            cat, label,
            ITEM_NEEDS_USER_INPUT,
            SRC_UNKNOWN_NOT_VERIFIED,
            notes=note,
        ))

    # --- Formatting / submission system: unknown ---
    items.append(_item(
        "formatting",
        "Manuscript formatting per venue style guide",
        ITEM_UNKNOWN_NOT_VERIFIED, SRC_UNKNOWN_NOT_VERIFIED,
        notes="Venue style guide / template not parsed in V2-D.",
    ))
    items.append(_item(
        "submission_system",
        "Submission system / portal",
        ITEM_UNKNOWN_NOT_VERIFIED, SRC_UNKNOWN_NOT_VERIFIED,
    ))

    # --- RiskReport-derived warnings (do not invent journal rules) ---
    if risk_report is not None:
        created_from.append("risk_report")
        for r in risk_report.risk_items:
            rtype = r.get("risk_type", "") if isinstance(r, dict) else ""
            severity = r.get("severity", "") if isinstance(r, dict) else ""
            if severity == "blocking":
                blocking.append(f"risk: {rtype}")
            elif severity in ("major", "warning"):
                warnings.append(f"risk: {rtype}")

    if scenario is not None:
        created_from.append("submission_scenario")

    # --- Overall status ---
    if blocking:
        status = STATUS_BLOCKED
    elif missing:
        status = STATUS_PARTIAL
    elif unknowns:
        status = STATUS_PARTIAL
    else:
        status = STATUS_READY

    # de-dup
    def _uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return ComplianceChecklist(
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        submission_scenario_id=(
            scenario.submission_scenario_id if scenario else None
        ),
        publication_regime_id=venue.publication_regime_id,
        checklist_items=items,
        guideline_sources=list(getattr(venue, "author_guidelines_refs", []) or []),
        missing_items=_uniq(missing),
        blocking_items=_uniq(blocking),
        warnings=_uniq(warnings),
        unknowns=_uniq(unknowns),
        created_from=_uniq(created_from),
        confidence="low" if unknowns else "medium",
        status=status,
    )
