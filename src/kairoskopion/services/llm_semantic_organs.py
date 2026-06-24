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

from ..agents.base_shell import LLMAttemptOutcome, try_llm_call, try_llm_call_with_outcome
from ..agents.prompt_families.citation_ecology import CITATION_ECOLOGY_FAMILY
from ..agents.prompt_families.rewrite_planning import REWRITE_PLANNING_FAMILY
from ..agents.prompt_families.risk_reporting import RISK_REPORTING_FAMILY
from ..enums import FieldCoreImpact
from ..services.risk_reporting import RISK_TYPES as _CANONICAL_RISK_TYPES
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
    "moderate": "major",
    "severe": "blocking",
    "warning": "minor",
    "info": "informational",
    "minor": "minor",
    "major": "major",
    "blocking": "blocking",
}

_CANONICAL_RISK_TYPE_SET = frozenset(_CANONICAL_RISK_TYPES)


_PROMPT_TO_CANONICAL_RISK_TYPE: dict[str, str] = {
    "desk_rejection": "desk_reject_risk",
    "method_gap": "methodology_mismatch",
    "genre_mismatch": "scope_mismatch",
    "language_barrier": "language_quality",
    "novelty_concern": "scope_mismatch",
    "compliance_gap": "formatting_violation",
    "field_core_destruction": "core_transformation_risk",
    "indexing_risk": "reputational_risk",
    "review_hostility": "reviewer_pool_mismatch",
    "regime_instability": "reputational_risk",
    "evidence_insufficiency": "scope_mismatch",
}


def _normalize_risk_type(raw: str) -> str:
    """Normalize LLM-produced risk_type to canonical enum value.

    Handles: title-case, spaces, hyphens, trailing "_risk" mismatch,
    and prompt-family enum names that differ from canonical service types.
    Unknown values pass through unchanged (honest unknown, not silent drop).
    """
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _CANONICAL_RISK_TYPE_SET:
        return key
    if key in _PROMPT_TO_CANONICAL_RISK_TYPE:
        return _PROMPT_TO_CANONICAL_RISK_TYPE[key]
    without_risk = key.removesuffix("_risk")
    with_risk = key if key.endswith("_risk") else f"{key}_risk"
    if without_risk in _CANONICAL_RISK_TYPE_SET:
        return without_risk
    if with_risk in _CANONICAL_RISK_TYPE_SET:
        return with_risk
    return key or "unknown"

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
    raw_article_text: str | None = None,
) -> RiskReport:
    """Wire LLM risk_officer. On failure → needs_llm with diagnostics."""
    from .llm_attempt_diagnostics import (
        diagnostics_provider_unavailable,
        diagnostics_exception,
        diagnostics_parse_or_schema_failed,
        diagnostics_ok,
        FALLBACK_NO_MISMATCH,
        SEMANTIC_LLM_GROUNDED_PARTIAL,
    )
    from .writing_rubric import (
        rubric_applies_to_article,
        rubric_id,
        render_prompt_block,
    )
    placeholder = build_needs_llm_risk_report(
        article, venue, scenario, fit, mismatch_map,
    )
    if provider is None or article is None or venue is None:
        placeholder.attempt_diagnostics = diagnostics_provider_unavailable(
            "risk_officer", "risk_officer",
        )
        return placeholder

    rubric_block = (
        render_prompt_block() if rubric_applies_to_article(article, raw_article_text=raw_article_text) else ""
    )
    rubric_active = bool(rubric_block)

    # Round III-F: outcome-envelope path.
    try:
        outcome = try_llm_call_with_outcome(
            provider, RISK_REPORTING_FAMILY,
            {
                "article_json": _safe_json(article.to_dict()),
                "venue_json": _safe_json(venue.to_dict()),
                "fit_json": _safe_json(fit.to_dict() if fit else {}),
                "mismatch_json": _safe_json(
                    mismatch_map.to_dict() if mismatch_map else {}),
                "rubric_context": rubric_block,
            },
            strict_schema=False,
            agent_role="risk_officer", model_role="risk_officer",
        )
    except Exception as exc:  # noqa: BLE001
        placeholder.attempt_diagnostics = diagnostics_exception(
            "risk_officer", "risk_officer", exc,
        )
        return placeholder

    if outcome is None:
        placeholder.attempt_diagnostics = diagnostics_parse_or_schema_failed(
            "risk_officer", "risk_officer",
            parse_status="schema_validation_failed", repair_steps=None,
        )
        return placeholder

    parsed = outcome.parsed or outcome.loose_parsed
    if not isinstance(parsed, (dict, list)):
        # Round III-K2: specific failure categories instead of generic
        _fc = outcome.parse_failure_category or outcome.parse_status or "unknown"
        if not outcome.content_present:
            _fc = "no_content_returned"
        elif outcome.parse_status == "repair_failed":
            _fc = "json_repair_exhausted"
        elif outcome.parse_status == "invalid_json":
            _fc = "no_json_found"
        placeholder.attempt_diagnostics = {
            **outcome.to_dict(),
            "semantic_status": "needs_llm",
            "parse_failure_category": _fc,
        }
        logger.warning(
            "RiskOfficer LLM parse failed: category=%s content_length=%d "
            "hash=%s top_keys=%s",
            _fc, outcome.content_length, outcome.content_hash_prefix,
            outcome.redacted_top_level_keys,
        )
        return placeholder
    if isinstance(parsed, list):
        parsed = {"risk_items": parsed}

    # Round III-E: container normalization — Sonnet may put items under
    # alternative top-level keys; adapter finds the list mechanically.
    from .llm_contract_normalizer import (
        find_list_under_aliases, RISK_ITEM_ALIASES, shape_summary,
    )
    raw_items, _match_key = find_list_under_aliases(parsed, RISK_ITEM_ALIASES)
    if raw_items is None:
        raw_items = []
    _risk_shape = shape_summary(parsed)
    risk_items: list[dict[str, Any]] = []
    blocking: list[str] = []
    warnings: list[str] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        rtype = _normalize_risk_type(raw.get("risk_type") or "")
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

    sem = SEMANTIC_STATUS_LLM_GROUNDED if risk_items else SEMANTIC_LLM_GROUNDED_PARTIAL
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
        semantic_status=sem,
        attempt_diagnostics=diagnostics_ok(
            "risk_officer", "risk_officer", semantic_status=sem,
            extra={"items_count": len(risk_items), "rubric_active": rubric_active},
        ),
        rubric_sources=([rubric_id()] if rubric_active and rubric_id() else []),
    )


# ---------- RewritePlanner ----------

def try_llm_rewrite_planner(
    article: ArticleModel | None,
    venue: VenueModel | None,
    fit: FitAssessment | None,
    mismatch_map: MismatchMap | None,
    risk_report: RiskReport | None,
    provider: Any | None,
    raw_article_text: str | None = None,
) -> RewritePlan:
    """Wire LLM rewrite_planner. On failure → needs_llm placeholder.

    Doctrine: any change touching thesis/object/method/disciplinary
    framing → field_core_risk = core_touching/transforming;
    field_core uncertainty → unknown_core_impact (not silently
    core_preserving).
    """
    from .llm_attempt_diagnostics import (
        diagnostics_provider_unavailable,
        diagnostics_exception,
        diagnostics_parse_or_schema_failed,
        diagnostics_ok,
        FALLBACK_NO_MISMATCH,
        SEMANTIC_LLM_GROUNDED_PARTIAL,
    )
    from .writing_rubric import (
        rubric_applies_to_article,
        rubric_id,
        render_prompt_block,
    )
    placeholder = build_needs_llm_rewrite_plan(
        mismatch_map,
        article_model_id=(article.article_model_id if article else None),
        venue_model_id=(venue.venue_model_id if venue else None),
    )
    if (provider is None or article is None or venue is None
            or mismatch_map is None):
        placeholder.attempt_diagnostics = diagnostics_provider_unavailable(
            "rewrite_planner", "rewrite_planner",
        )
        return placeholder

    rubric_block = (
        render_prompt_block() if rubric_applies_to_article(article, raw_article_text=raw_article_text) else ""
    )
    rubric_active = bool(rubric_block)

    # Round III-F: outcome-envelope path
    try:
        outcome = try_llm_call_with_outcome(
            provider, REWRITE_PLANNING_FAMILY,
            {
                "mismatch_json": _safe_json(mismatch_map.to_dict()),
                "article_json": _safe_json(article.to_dict()),
                "venue_json": _safe_json(venue.to_dict()),
                "rubric_context": rubric_block,
            },
            strict_schema=False,
            agent_role="rewrite_planner", model_role="rewrite_planner",
        )
    except Exception as exc:  # noqa: BLE001
        placeholder.attempt_diagnostics = diagnostics_exception(
            "rewrite_planner", "rewrite_planner", exc,
        )
        return placeholder
    if outcome is None:
        placeholder.attempt_diagnostics = diagnostics_parse_or_schema_failed(
            "rewrite_planner", "rewrite_planner",
            parse_status="schema_validation_failed", repair_steps=None,
        )
        return placeholder
    parsed = outcome.parsed or outcome.loose_parsed
    if not isinstance(parsed, (dict, list)):
        placeholder.attempt_diagnostics = {
            **outcome.to_dict(),
            "semantic_status": "needs_llm",
        }
        return placeholder
    if isinstance(parsed, list):
        parsed = {"actions": parsed}

    # Round III-E: accept alternative top-level keys for the actions list.
    from .llm_contract_normalizer import (
        find_list_under_aliases, REWRITE_ITEM_ALIASES, shape_summary,
    )
    actions, _match_key = find_list_under_aliases(parsed, REWRITE_ITEM_ALIASES)
    if actions is None:
        actions = []
    _rewrite_shape = shape_summary(parsed)
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

    sem = (
        SEMANTIC_STATUS_LLM_GROUNDED if changes
        else SEMANTIC_LLM_GROUNDED_PARTIAL
    )
    # If no changes, ensure unknowns contains the reason — never silent.
    if not changes:
        depth_note = (
            depth_raw or "none"
        )
        unknowns.append(
            f"LLM rewrite_planner returned no actions "
            f"(overall_depth={depth_note!r}). Either fit truly needs no "
            "rewrite, or LLM refused to plan changes with provided "
            "evidence. See attempt_diagnostics for confirmation that the "
            "LLM call completed cleanly."
        )
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
        semantic_status=sem,
        attempt_diagnostics=diagnostics_ok(
            "rewrite_planner", "rewrite_planner", semantic_status=sem,
            extra={"changes_count": len(changes), "rubric_active": rubric_active,
                   "core_touching": has_core_touching},
        ),
        rubric_sources=([rubric_id()] if rubric_active and rubric_id() else []),
    )


# ---------- CitationPlanner ----------

def upgrade_citation_plan_with_llm(
    citation_plan: CitationPlan,
    article: ArticleModel | None,
    venue: VenueModel | None,
    bib_profile: BibliographyProfile | None,
    provider: Any | None,
    raw_article_text: str | None = None,
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
    from .llm_attempt_diagnostics import (
        diagnostics_provider_unavailable,
        diagnostics_exception,
        diagnostics_parse_or_schema_failed,
        diagnostics_ok,
        SEMANTIC_LLM_GROUNDED_PARTIAL,
    )
    from .writing_rubric import (
        rubric_applies_to_article,
        rubric_id,
        render_prompt_block,
    )
    import dataclasses as _dc

    def _attach_diag(plan, diag):
        return _dc.replace(plan, attempt_diagnostics=diag)

    if provider is None or article is None or venue is None:
        return _attach_diag(
            citation_plan,
            diagnostics_provider_unavailable(
                "citation_planner", "citation_planner",
            ),
        )

    rubric_block = (
        render_prompt_block() if rubric_applies_to_article(article, raw_article_text=raw_article_text) else ""
    )
    rubric_active = bool(rubric_block)

    # Round III-F: outcome-envelope path
    try:
        outcome = try_llm_call_with_outcome(
            provider, CITATION_ECOLOGY_FAMILY,
            {
                "article_json": _safe_json(article.to_dict()),
                "venue_json": _safe_json(venue.to_dict()),
                "bibliography_json": _safe_json(
                    bib_profile.to_dict() if bib_profile else {}),
                "rubric_context": rubric_block,
            },
            strict_schema=False,
            agent_role="citation_planner", model_role="citation_planner",
        )
    except Exception as exc:  # noqa: BLE001
        return _attach_diag(citation_plan, diagnostics_exception(
            "citation_planner", "citation_planner", exc,
        ))
    if outcome is None:
        return _attach_diag(citation_plan, diagnostics_parse_or_schema_failed(
            "citation_planner", "citation_planner",
            parse_status="schema_validation_failed", repair_steps=None,
        ))
    parsed = outcome.parsed or outcome.loose_parsed
    if not isinstance(parsed, (dict, list)):
        return _attach_diag(citation_plan, {
            **outcome.to_dict(),
            "semantic_status": "needs_llm",
        })
    if isinstance(parsed, list):
        parsed = {"source_work_tasks": parsed}

    # Round III-E: accept alternative top-level keys
    from .llm_contract_normalizer import (
        find_list_under_aliases, CITATION_BRIDGE_ALIASES,
        CITATION_GAP_ALIASES, CITATION_TASK_ALIASES, CITATION_RISK_ALIASES,
    )
    _br, _ = find_list_under_aliases(parsed, CITATION_BRIDGE_ALIASES)
    _gp, _ = find_list_under_aliases(parsed, CITATION_GAP_ALIASES)
    _tk, _ = find_list_under_aliases(parsed, CITATION_TASK_ALIASES)
    _rk, _ = find_list_under_aliases(parsed, CITATION_RISK_ALIASES)
    bridges = [b for b in (_br or [])
               if isinstance(b, str) and b.strip()]
    gaps = [g for g in (_gp or [])
            if isinstance(g, str) and g.strip()]
    risks = [r for r in (_rk or [])
             if isinstance(r, str) and r.strip()]
    # Allow LLM-emitted source-work tasks as search_tasks even when
    # bibliography is absent (Track E: missing bibliography → safe
    # source-work tasks are allowed, concrete refs forbidden).
    llm_search_tasks = [t for t in (_tk or [])
                        if isinstance(t, str) and t.strip()]
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
    # Round III-E: include LLM-emitted source-work tasks too (anti-fake
    # filter already stripped fake refs above).
    _safe_llm_tasks = [t for t in llm_search_tasks if _safe(t)]
    new_search_tasks = list(citation_plan.recommended_reference_search_tasks) + [
        f"Search for references that bridge: {b}" for b in bridges
    ] + [
        f"Address tradition gap: {g}" for g in gaps
    ] + _safe_llm_tasks
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

    has_semantic = bool(gaps or bridges or new_search_tasks
                        != list(citation_plan.recommended_reference_search_tasks))
    sem = (
        new_semantic_status if has_semantic
        else SEMANTIC_LLM_GROUNDED_PARTIAL
    )
    # If LLM produced nothing usable (empty after anti-fake filter),
    # add an explicit unknown so the operator sees the reason.
    if not has_semantic:
        new_unknowns.append(
            "LLM citation_planner returned no usable bridges/gaps after "
            "anti-fake filter. Either bibliography evidence was too "
            "sparse or LLM refused to invent references (correct "
            "doctrine behaviour). See attempt_diagnostics."
        )
    diag = diagnostics_ok(
        "citation_planner", "citation_planner", semantic_status=sem,
        extra={
            "bridges_count": len(bridges),
            "gaps_count": len(gaps),
            "rubric_active": rubric_active,
        },
    )
    return _dc.replace(
        citation_plan,
        citation_gap_categories=new_gap_categories,
        missing_bridge_categories=new_missing_bridges,
        recommended_reference_search_tasks=new_search_tasks,
        dangerous_padding_warnings=padding_warnings,
        unknowns=new_unknowns,
        risk_flags=list(citation_plan.risk_flags) + risks,
        field_origins=new_origins,
        semantic_status=sem,
        attempt_diagnostics=diag,
        rubric_sources=([rubric_id()] if rubric_active and rubric_id() else []),
        created_from=list(citation_plan.created_from) + ["llm_citation_planner"],
    )
