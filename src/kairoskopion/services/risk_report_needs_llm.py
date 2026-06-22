"""Round II-B: needs_llm RiskReport placeholder.

Per Round II-B doctrine, deterministic code MUST NOT emit semantic
risk diagnoses. The legacy ``services/risk_reporting.py::build_risk_report``
remains available for unit tests and as the LLM agent's deterministic
fallback target, but the production chain now routes through THIS
builder instead, which returns a structural placeholder with
``semantic_status=needs_llm`` and empty risk_items.

When ``agents/submission/risk_officer.py`` is wired as the production
LLM organ, the chain will use its output instead and this placeholder
will be obsolete.
"""

from __future__ import annotations

from ..schema import (
    ArticleModel,
    FitAssessment,
    MismatchMap,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from .semantic_provenance import (
    ORIGIN_NEEDS_LLM,
    ORIGIN_STRUCTURAL_EXTRACTION,
    SEMANTIC_STATUS_NEEDS_LLM,
)


def build_needs_llm_risk_report(
    article: ArticleModel | None,
    venue: VenueModel | None,
    scenario: SubmissionScenario | None,
    fit: FitAssessment | None,
    mismatch_map: MismatchMap | None,
) -> RiskReport:
    """Return a structural-only RiskReport marked needs_llm.

    Doctrine: no deterministic risk diagnosis. Empty risk_items,
    empty blocking_risks/warnings. Surface that an LLM risk_officer
    organ is required.
    """
    unknowns = [
        "Risk diagnosis requires LLM risk_officer organ (Round II-B). "
        "Agent class exists at agents/submission/risk_officer.py but "
        "is not wired in the production chain in this pass; semantic "
        "risk items, scope-mismatch / method / citation / field-core "
        "risk claims must come from that organ."
    ]
    field_origins = {
        "risk_items": ORIGIN_NEEDS_LLM,
        "blocking_risks": ORIGIN_NEEDS_LLM,
        "warnings": ORIGIN_NEEDS_LLM,
        "overall_risk_label": ORIGIN_NEEDS_LLM,
        "unknowns": ORIGIN_STRUCTURAL_EXTRACTION,
    }
    return RiskReport(
        article_model_id=(article.article_model_id if article else None),
        venue_model_id=(venue.venue_model_id if venue else None),
        submission_scenario_id=(
            scenario.submission_scenario_id if scenario else None
        ),
        risk_items=[],
        overall_risk_label=None,
        blocking_risks=[],
        warnings=[],
        unknowns=unknowns,
        field_origins=field_origins,
        semantic_status=SEMANTIC_STATUS_NEEDS_LLM,
    )
