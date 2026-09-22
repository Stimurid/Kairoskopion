"""Evidence reconciliation for target pressure before Kairon sees it."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..schema import ArticleModel, VenueModel
from .models import TargetPressureItem, TargetPressurePack


_STOP = {
    "the","and","for","with","that","this","from","into","between","under","over",
    "article","journal","research","paper","current","new","work","works","using",
    "their","they","its","our","are","is","of","to","in","on","a","an",
}


def _stem(token: str) -> str:
    t = token.lower()
    if t.endswith("ies") and len(t) > 5:
        return t[:-3] + "y"
    if t.endswith("ing") and len(t) > 6:
        return t[:-3]
    if t.endswith("ed") and len(t) > 5:
        return t[:-2]
    if t.endswith("s") and len(t) > 4 and not t.endswith("ss"):
        return t[:-1]
    return t


def _terms(text: str) -> set[str]:
    return {
        _stem(x)
        for x in re.findall(r"[A-Za-z][A-Za-z-]{2,}", text or "")
        if x.lower() not in _STOP
    }


def _article_semantic_text(article: ArticleModel) -> str:
    return " ".join([
        article.title_current or "",
        article.abstract_current or "",
        article.problem_statement or "",
        article.research_question or "",
        article.object_of_inquiry or "",
        article.disciplinary_register_current or "",
        " ".join(article.core_claims or []),
        " ".join(article.theoretical_shoulders or []),
    ])


def _conceptual_share(target_models: dict[str, Any] | None) -> float:
    for row in (target_models or {}).get("genre_patterns") or []:
        if row.get("label") == "conceptual_article":
            try:
                return float(row.get("share") or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _reference_count_from_projection(article: ArticleModel) -> int | None:
    if article.reference_count is not None and article.reference_count > 0:
        return int(article.reference_count)
    text = article.citation_ecology_current or ""
    m = re.search(r"(\d+)\s+(?:bibliography\s+items|references?|sources?)", text, re.I)
    return int(m.group(1)) if m else None


def _formal_fields(formal_profile: dict[str, Any] | None) -> dict[str, Any]:
    if not formal_profile:
        return {}
    return dict(formal_profile.get("fields_present") or formal_profile)


def _drop_dimensions(items: list[TargetPressureItem], dims: set[str]) -> list[TargetPressureItem]:
    return [x for x in items if x.dimension not in dims]


def reconcile_target_pressure_pack(
    *,
    article: ArticleModel,
    venue: VenueModel,
    base_pack: TargetPressurePack,
    target_models: dict[str, Any] | None = None,
    formal_profile: dict[str, Any] | None = None,
) -> TargetPressurePack:
    """Reconcile legacy diagnostics with stronger target-world evidence.

    Conflicting weak heuristics are removed rather than averaged with stronger
    evidence. Every suppression is recorded in conflicts.
    """
    pack = deepcopy(base_pack)
    items = list(pack.items)
    conflicts = list(pack.conflicts)

    article_terms = _terms(_article_semantic_text(article))
    venue_terms = _terms(" ".join([
        venue.scope_summary or "",
        venue.aims_scope_summary or "",
        venue.canonical_name or "",
    ]))
    overlap = sorted(article_terms & venue_terms)
    if len(overlap) >= 3:
        if any(x.dimension == "topic" and x.severity in {"weak","major","bad","critical"} for x in items):
            conflicts.append(
                "legacy topic pressure suppressed: canonical article/official scope "
                f"share semantic terms {overlap[:12]}"
            )
        items = _drop_dimensions(items, {"topic"})

    share = _conceptual_share(target_models)
    official_types = " ".join(venue.article_types_supported or []).lower()
    conceptual = article.genre_current in {"conceptual_article", "theoretical_essay"}
    if conceptual and (
        "original article" in official_types
        or "research article" in official_types
        or share >= 0.15
    ):
        if any(x.dimension == "genre" and x.severity in {"weak","major","bad","critical"} for x in items):
            conflicts.append(
                "legacy genre pressure suppressed: conceptual form is compatible "
                f"with official article container and/or corpus share={share:.3f}"
            )
        items = _drop_dimensions(items, {"genre"})

    refs = _reference_count_from_projection(article)
    if refs and refs > 0:
        citation_items = [x for x in items if x.dimension == "citation_ecology"]
        if citation_items:
            items = _drop_dimensions(items, {"citation_ecology"})
            items.append(TargetPressureItem(
                pressure_id="target:citation_ecology:profile",
                dimension="citation_ecology",
                observation=(
                    f"Article has a verified bibliography baseline ({refs} references); "
                    "target-specific anchor/citation ecology still requires corpus profiling."
                ),
                evidence_refs=list(venue.source_refs or []),
                evidence_status="evidence_need",
                severity="unknown",
                transformation_depth_hint="evidence_needed",
                source_kind="target_world_reconciliation",
            ))

    fields = _formal_fields(formal_profile)

    word_limit = fields.get("word_limit")
    if isinstance(word_limit, dict):
        max_words = word_limit.get("max")
        if max_words and article.word_count:
            items = _drop_dimensions(items, {"formal_compliance"})
            if article.word_count > int(max_words):
                items.append(TargetPressureItem(
                    pressure_id="target:formal:word_limit",
                    dimension="formal_compliance",
                    observation=f"Manuscript {article.word_count} words exceeds target maximum {max_words}.",
                    evidence_refs=list(venue.author_guidelines_refs or venue.source_refs or []),
                    evidence_status="fact_from_source",
                    severity="major",
                    transformation_depth_hint="local_or_structural",
                    source_kind="formal_rule",
                ))

    abstract_limit = fields.get("abstract_word_limit")
    if isinstance(abstract_limit, dict) and article.abstract_current:
        max_abs = abstract_limit.get("max")
        abs_words = len(article.abstract_current.split())
        if max_abs and abs_words > int(max_abs):
            items.append(TargetPressureItem(
                pressure_id="target:formal:abstract_limit",
                dimension="formal_compliance",
                observation=f"Abstract {abs_words} words exceeds target maximum {max_abs}.",
                evidence_refs=list(venue.author_guidelines_refs or venue.source_refs or []),
                evidence_status="fact_from_source",
                severity="minor",
                transformation_depth_hint="local",
                source_kind="formal_rule",
            ))

    ref_style = fields.get("reference_style")
    if isinstance(ref_style, dict) and ref_style.get("value"):
        style = str(ref_style["value"])
        items.append(TargetPressureItem(
            pressure_id="target:formal:reference_style",
            dimension="formal_compliance",
            observation=f"Target requires {style} reference style; formatting conversion must be verified.",
            evidence_refs=list(venue.author_guidelines_refs or venue.source_refs or []),
            evidence_status="fact_from_source",
            severity="minor",
            transformation_depth_hint="local",
            source_kind="formal_rule",
        ))

    ai_policy = fields.get("ai_policy_mentioned")
    if isinstance(ai_policy, dict) and ai_policy.get("value") and not article.has_ai_disclosure:
        items.append(TargetPressureItem(
            pressure_id="target:formal:ai_disclosure",
            dimension="formal_compliance",
            observation="Target explicitly mentions AI-use disclosure; manuscript/submission disclosure state must be completed.",
            evidence_refs=list(venue.author_guidelines_refs or venue.source_refs or []),
            evidence_status="fact_from_source",
            severity="minor",
            transformation_depth_hint="local",
            source_kind="formal_rule",
        ))

    dimensions = {x.dimension for x in items}
    unknowns = [
        u for u in pack.unknowns
        if not (
            (u.startswith("fit:topic") and "topic" not in dimensions)
            or (u.startswith("fit:genre") and "genre" not in dimensions)
        )
    ]
    return TargetPressurePack(
        target_id=pack.target_id,
        snapshot_id=pack.snapshot_id,
        items=items,
        unknowns=unknowns,
        conflicts=list(dict.fromkeys(conflicts)),
    )


def derive_transition_class(pack: TargetPressurePack) -> str:
    """Map reconciled pressure to a Kairon transition class."""
    consequential = [
        x for x in pack.items
        if x.severity not in {"strong", "medium", "informational"}
    ]
    if not consequential:
        return "KEEP"
    depths = {x.transformation_depth_hint for x in consequential}
    if "identity_or_reseed_review" in depths:
        return "REARCHITECT"
    if "structural_or_deeper" in depths:
        return "REARCHITECT"
    if "local_or_structural" in depths:
        return "REFRAME"
    if "local" in depths:
        return "LOCAL_ADAPT"
    if depths <= {"evidence_needed", "unknown"}:
        return "HOLD"
    return "REFRAME"
