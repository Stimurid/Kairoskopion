"""Round III: thin LLM wiring for the three semantic organs.

Each helper calls ``try_llm_call`` directly (bypassing the agent's
deterministic fallback, which would call the forbidden legacy
``build_risk_report`` / ``build_rewrite_plan`` / ``build_citation_ecology_report``
services). On LLM failure: returns the corresponding ``needs_llm``
placeholder, NOT deterministic semantic prose.

Adapter responsibilities (LLM output schema → Kairoskopion dataclass):
  - RiskOfficer:    {risk_items[{risk_type, severity ∈ critical/high/medium/low/informational, description, evidence, mitigation}], ...}
                    → RiskReport (severity normalized to blocking/major/minor/informational)
  - RewritePlanner: {overall_depth, actions[{action_id, target_mismatch, action_type, description, effort, field_core_impact, ...}], unknowns, confidence}
                    → RewritePlan
  - CitationPlanner: CitationEcologyResult {tradition_match, canonical_coverage, bridge_references_needed[], tradition_gaps[], risk_items[], unknowns}
                     → CitationPlan semantic fields (gap_categories, missing_bridges, search_tasks)

All outputs carry `semantic_status="llm"` + `field_origins` all=`llm` on
success. NO raw LLM output retained anywhere.
"""

from __future__ import annotations

import logging
from typing import Any

from ..agents.base_shell import try_llm_call
from ..agents.prompt_families.citation_ecology import CITATION_ECOLOGY_FAMILY
from ..agents.prompt_families.rewrite_planning import REWRITE_PLANNING_FAMILY
from ..agents.prompt_families.risk_reporting import RISK_REPORTING_FAMILY
from ..enums import FieldCoreImpact
from ..ids import generate_id


def risk_item_id() -> str:
    return generate_id("ri")


def rewrite_change_id() -> str:
    return generate_id("rc")
from ..schema import (
    ArticleModel,
    BibliographyProfile,
    CitationPlan,
    FitAssessment,
    MismatchMap,
    RewritePlan,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from .semantic_provenance import (
    ORIGIN_LLM,
    ORIGIN_STRUCTURAL_EXTRACTION,
    SEMANTIC_STATUS_LLM_GROUNDED,
    SEMANTIC_STATUS_NEEDS_LLM,
)
from .risk_report_needs_llm import build_needs_llm_risk_report
from .rewrite_plan_needs_llm import build_needs_llm_rewrite_plan

logger = logging.getLogger(__name__)


# ---------- severity / field-core mapping ----------

_RISK_SEVERITY_MAP = {
    "critical": "blocking",
    "high": "major",
    "medium": "major",
    "low": "minor",
    "informational": "informational",
}

_FIELD_CORE_NORMALIZE = {
    "core_preserving": FieldCoreImpact.CORE_PRESERVING.value,
    "core_touching": FieldCoreImpact.CORE_TOUCHING.value,
    "core_transforming": FieldCoreImpact.CORE_TRANSFORMING.value,
    "core_destroying_risk": FieldCoreImpact.CORE_DESTROYING_RISK.value,
    "unknown": FieldCoreImpact.UNKNOWN_CORE_IMPACT.value,
    "unknown_core_impact": FieldCoreImpact.UNKNOWN_CORE_IMPACT.value,
}


def _safe_json(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return "{}"


# ---------- RiskOfficer ----------

def try_llm_risk_officer(
    article: ArticleModel | None,
    venue: VenueModel | None,
    scenario: SubmissionScenario | None,
    fit: FitAssessment | None,
    mismatch_map: MismatchMap | None,
    provider: Any | None,
) -> RiskReport:
    """Wire LLM risk_officer. On failure → needs_llm placeholder."""
    placeholder = build_needs_llm_risk_report(
        article, venue, scenario, fit, mismatch_map,
    )
    if provider is None or article is None or venue is None:
        return placeholder

    try:
        result = try_llm_call(provider, RISK_REPORTING_FAMILY, {
            "article_json": _safe_json(article.to_dict()),
            "venue_json": _safe_json(venue.to_dict()),
            "fit_json": _safe_json(fit.to_dict() if fit else {}),
            "mismatch_json": _safe_json(
                mismatch_map.to_dict() if mismatch_map else {}),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("RiskOfficer LLM call failed: %s", exc)
        return placeholder

    if result is None:
        return placeholder

    parsed, _meta = result
    if not isinstance(parsed, dict):
        return placeholder

    raw_items = parsed.get("risk_items") or []
    risk_items: list[dict[str, Any]] = []
    blocking: list[str] = []
    warnings: list[str] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        rtype = (raw.get("risk_type") or "").strip() or "unknown"
        sev_raw = (raw.get("severity") or "").lower().strip()
        sev = _RISK_SEVERITY_MAP.get(sev_raw, sev_raw or "informational")
        desc = (raw.get("description") or "").strip()
        mit = raw.get("mitigation")
        item = {
            "risk_id": risk_item_id(),
            "risk_type": rtype,
            "severity": sev,
            "description": desc,
            "likelihood": None,
            "evidence_refs": [],
            "mitigation": (mit if isinstance(mit, str) else None),
            "requires_user_action": sev == "blocking",
        }
        risk_items.append(item)
        if sev == "blocking":
            blocking.append(f"{rtype}: {desc[:120]}")
        elif sev == "major":
            warnings.append(f"{rtype}: {desc[:120]}")

    unknowns = [u for u in (parsed.get("unknowns") or []) if isinstance(u, str)]
    overall = parsed.get("overall_risk_label") or parsed.get("overall") or None

    field_origins = {
        "risk_items": ORIGIN_LLM,
        "blocking_risks": ORIGIN_LLM,
        "warnings": ORIGIN_LLM,
        "overall_risk_label": ORIGIN_LLM,
        "unknowns": ORIGIN_LLM,
    }

    return RiskReport(
        article_model_id=(article.article_model_id if article else None),
        venue_model_id=(venue.venue_model_id if venue else None),
        submission_scenario_id=(
            scenario.submission_scenario_id if scenario else None
        ),
        risk_items=risk_items,
        overall_risk_label=overall if isinstance(overall, str) else None,
        blocking_risks=blocking,
        warnings=warnings,
        unknowns=unknowns,
        field_origins=field_origins,
        semantic_status=SEMANTIC_STATUS_LLM_GROUNDED,
    )


# ---------- RewritePlanner ----------

def try_llm_rewrite_planner(
    article: ArticleModel | None,
    venue: VenueModel | None,
    fit: FitAssessment | None,
    mismatch_map: MismatchMap | None,
    risk_report: RiskReport | None,
    provider: Any | None,
) -> RewritePlan:
    """Wire LLM rewrite_planner. On failure → needs_llm placeholder.

    Doctrine: any change touching thesis/object/method/disciplinary
    framing → field_core_risk = core_touching/transforming;
    field_core uncertainty → unknown_core_impact (not silently
    core_preserving).
    """
    placeholder = build_needs_llm_rewrite_plan(
        mismatch_map,
        article_model_id=(article.article_model_id if article else None),
        venue_model_id=(venue.venue_model_id if venue else None),
    )
    if (provider is None or article is None or venue is None
            or mismatch_map is None):
        return placeholder

    try:
        result = try_llm_call(provider, REWRITE_PLANNING_FAMILY, {
            "mismatch_json": _safe_json(mismatch_map.to_dict()),
            "article_json": _safe_json(article.to_dict()),
            "venue_json": _safe_json(venue.to_dict()),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("RewritePlanner LLM call failed: %s", exc)
        return placeholder

    if result is None:
        return placeholder

    parsed, _meta = result
    if not isinstance(parsed, dict):
        return placeholder

    actions = parsed.get("actions") or []
    changes: list[dict[str, Any]] = []
    has_core_touching = False
    for a in actions:
        if not isinstance(a, dict):
            continue
        target = (a.get("target_mismatch") or "").strip()
        desc = (a.get("description") or "").strip()
        effort = (a.get("effort") or "").strip() or None
        fci_raw = (a.get("field_core_impact") or "").lower().strip()
        fci = _FIELD_CORE_NORMALIZE.get(
            fci_raw, FieldCoreImpact.UNKNOWN_CORE_IMPACT.value,
        )
        if fci in (
            FieldCoreImpact.CORE_TOUCHING.value,
            FieldCoreImpact.CORE_TRANSFORMING.value,
            FieldCoreImpact.CORE_DESTROYING_RISK.value,
        ):
            has_core_touching = True
        changes.append({
            "change_id": rewrite_change_id(),
            "target_block": target or "?",
            "desired_state": desc,
            "reason": (a.get("notes") or "")[:400] or "",
            "status": "proposed",
            "field_core_risk": fci,
        })

    depth_raw = (parsed.get("overall_depth") or "").lower().strip()
    depth_map = {"none": "none", "light": "low",
                 "medium": "medium", "major": "major"}
    estimated_effort = depth_map.get(depth_raw, depth_raw or None)

    # Object-level field_core_risk = strongest among per-change values
    if has_core_touching:
        overall_fci = FieldCoreImpact.CORE_TOUCHING.value
    elif changes:
        # Mixed unknown / preserving
        overall_fci = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    else:
        overall_fci = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value

    unknowns = [u for u in (parsed.get("unknowns") or []) if isinstance(u, str)]
    if has_core_touching:
        unknowns.append(
            "Core-touching changes proposed — user acceptance required "
            "before applying."
        )

    summary = None
    if parsed.get("recommend_against_venue"):
        reason = parsed.get("recommend_against_reason") or ""
        summary = f"LLM recommends against this venue: {reason}"[:600]

    field_origins = {
        "changes": ORIGIN_LLM,
        "summary": ORIGIN_LLM,
        "estimated_effort": ORIGIN_LLM,
        "field_core_risk": ORIGIN_LLM,
        "unknowns": ORIGIN_LLM,
    }

    return RewritePlan(
        article_model_id=(article.article_model_id if article else None),
        target_venue_id=(venue.venue_model_id if venue else None),
        fit_assessment_id=(mismatch_map.fit_assessment_id if mismatch_map else None),
        changes=changes,
        summary=summary,
        estimated_effort=estimated_effort,
        field_core_risk=overall_fci,
        requires_user_acceptance=has_core_touching,
        unknowns=unknowns,
        field_origins=field_origins,
        semantic_status=SEMANTIC_STATUS_LLM_GROUNDED,
    )


# ---------- CitationPlanner ----------

def upgrade_citation_plan_with_llm(
    citation_plan: CitationPlan,
    article: ArticleModel | None,
    venue: VenueModel | None,
    bib_profile: BibliographyProfile | None,
    provider: Any | None,
) -> CitationPlan:
    """Augment the structural CitationPlan with LLM semantic fields.

    On failure: return the original plan unchanged (semantic fields
    stay empty with origin=needs_llm). On success: populate
    citation_gap_categories / missing_bridge_categories /
    recommended_reference_search_tasks / dangerous_padding_warnings
    with semantic_status=mixed and per-field origin=llm.

    NEVER produces concrete reference titles, DOIs, or author names —
    the prompt forbids it and we additionally filter for them.
    """
    if provider is None or article is None or venue is None:
        return citation_plan

    try:
        result = try_llm_call(provider, CITATION_ECOLOGY_FAMILY, {
            "article_json": _safe_json(article.to_dict()),
            "venue_json": _safe_json(venue.to_dict()),
            "bibliography_json": _safe_json(
                bib_profile.to_dict() if bib_profile else {}),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("CitationPlanner LLM call failed: %s", exc)
        return citation_plan

    if result is None:
        return citation_plan

    parsed, _meta = result
    if not isinstance(parsed, dict):
        return citation_plan

    bridges = [b for b in (parsed.get("bridge_references_needed") or [])
               if isinstance(b, str) and b.strip()]
    gaps = [g for g in (parsed.get("tradition_gaps") or [])
            if isinstance(g, str) and g.strip()]
    risks = [r for r in (parsed.get("risk_items") or [])
             if isinstance(r, str) and r.strip()]
    unknowns_llm = [u for u in (parsed.get("unknowns") or [])
                    if isinstance(u, str) and u.strip()]

    # Anti-fake filter: drop any string containing an apparent DOI or
    # author-year pattern. Bridges/gaps must be categories, not refs.
    import re as _re
    _DOI_RE = _re.compile(r"10\.\d{4,}/\S+")
    _AY_RE = _re.compile(r"\b[A-Z][a-z]+\s+\d{4}\b")
    def _safe(s: str) -> bool:
        return not _DOI_RE.search(s) and not _AY_RE.search(s)

    bridges = [b for b in bridges if _safe(b)]
    gaps = [g for g in gaps if _safe(g)]
    risks = [r for r in risks if _safe(r)]

    # Map LLM ecology fields → CitationPlan semantic fields
    new_gap_categories = list(citation_plan.citation_gap_categories) + gaps
    new_missing_bridges = list(citation_plan.missing_bridge_categories) + bridges
    # Search tasks: LLM produces tradition_gaps + bridge_references_needed
    # implicitly imply search work; we surface them as search tasks here.
    new_search_tasks = list(citation_plan.recommended_reference_search_tasks) + [
        f"Search for references that bridge: {b}" for b in bridges
    ] + [
        f"Address tradition gap: {g}" for g in gaps
    ]
    # Padding warning is always added when expansion is recommended;
    # this is editorial advice that the LLM agent's prompt produces.
    padding_warnings = list(citation_plan.dangerous_padding_warnings)
    if bridges or gaps:
        padding_warnings.append(
            "LLM citation_planner: only add references that support real "
            "argumentative bridges. Cosmetic padding to imitate venue "
            "metrics is a desk-reject risk."
        )

    new_unknowns = list(citation_plan.unknowns) + unknowns_llm

    # Update origins for the now-populated semantic fields
    new_origins = dict(citation_plan.field_origins or {})
    if gaps:
        new_origins["citation_gap_categories"] = ORIGIN_LLM
    if bridges:
        new_origins["missing_bridge_categories"] = ORIGIN_LLM
    if bridges or gaps:
        new_origins["recommended_reference_search_tasks"] = ORIGIN_LLM
        new_origins["dangerous_padding_warnings"] = ORIGIN_LLM

    # Object-level: mixed structural + LLM
    from .semantic_provenance import (
        SEMANTIC_STATUS_MIXED, aggregate_semantic_status,
    )
    new_semantic_status = aggregate_semantic_status(new_origins)

    # Return a new CitationPlan with augmented fields
    import dataclasses as _dc
    return _dc.replace(
        citation_plan,
        citation_gap_categories=new_gap_categories,
        missing_bridge_categories=new_missing_bridges,
        recommended_reference_search_tasks=new_search_tasks,
        dangerous_padding_warnings=padding_warnings,
        unknowns=new_unknowns,
        risk_flags=list(citation_plan.risk_flags) + risks,
        field_origins=new_origins,
        semantic_status=new_semantic_status,
        created_from=list(citation_plan.created_from) + ["llm_citation_planner"],
    )
