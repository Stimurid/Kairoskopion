"""Canonical prompt family catalog — all 16 families registered.

14 spec-defined (§69.1–§69.14) + 2 UC-1 extensions.
"""

from __future__ import annotations

from ...prompts.article_modeling import ARTICLE_MODELING_FAMILY
from ...prompts.disciplinary_mapping import DISCIPLINARY_MAPPING_FAMILY
from ...prompts.fit_assessment import FIT_ASSESSMENT_FAMILY
from ...prompts.semantic_profiling import SEMANTIC_PROFILING_FAMILY
from ...prompts.venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY
from .citation_ecology import CITATION_ECOLOGY_FAMILY
from .compliance_checklist import COMPLIANCE_CHECKLIST_FAMILY
from .corpus_pattern_mining import CORPUS_PATTERN_MINING_FAMILY
from .evidence_audit import EVIDENCE_AUDIT_FAMILY
from .mismatch_mapping import MISMATCH_MAPPING_FAMILY
from .publication_regime import PUBLICATION_REGIME_FAMILY
from .review_outcome import REVIEW_OUTCOME_FAMILY
from .rewrite_planning import REWRITE_PLANNING_FAMILY
from .risk_reporting import RISK_REPORTING_FAMILY
from .scenario_interview import SCENARIO_INTERVIEW_FAMILY
from .submission_pack import SUBMISSION_PACK_FAMILY

# Canonical 14 spec families + 2 UC-1 extensions
PROMPT_FAMILY_CATALOG: dict[str, dict] = {
    # Spec §69.1 — Article Modeling
    "article_modeling_v2": ARTICLE_MODELING_FAMILY,
    # Spec §69.2 — Scenario Interview
    "scenario_interview_v1": SCENARIO_INTERVIEW_FAMILY,
    # Spec §69.3 — Venue Fact Extraction
    "venue_fact_extraction_v1": VENUE_FACT_EXTRACTION_FAMILY,
    # Spec §69.4 — Publication Regime Classification
    "publication_regime_v1": PUBLICATION_REGIME_FAMILY,
    # Spec §69.5 — Corpus Pattern Mining
    "corpus_pattern_mining_v1": CORPUS_PATTERN_MINING_FAMILY,
    # Spec §69.6 — Citation Ecology
    "citation_ecology_v1": CITATION_ECOLOGY_FAMILY,
    # Spec §69.7 — Fit Assessment
    "fit_assessment_v1": FIT_ASSESSMENT_FAMILY,
    # Spec §69.8 — Mismatch Mapping
    "mismatch_mapping_v1": MISMATCH_MAPPING_FAMILY,
    # Spec §69.9 — Rewrite / Reframe Planning
    "rewrite_planning_v1": REWRITE_PLANNING_FAMILY,
    # Spec §69.10 — Risk Reporting
    "risk_reporting_v1": RISK_REPORTING_FAMILY,
    # Spec §69.11 — Compliance Checklist
    "compliance_checklist_v1": COMPLIANCE_CHECKLIST_FAMILY,
    # Spec §69.12 — Submission Pack
    "submission_pack_v1": SUBMISSION_PACK_FAMILY,
    # Spec §69.13 — Review Outcome
    "review_outcome_v1": REVIEW_OUTCOME_FAMILY,
    # Spec §69.14 — Evidence Audit
    "evidence_audit_v1": EVIDENCE_AUDIT_FAMILY,
    # UC-1 extension — Semantic Profiling
    "semantic_profiling_v2": SEMANTIC_PROFILING_FAMILY,
    # UC-1 extension — Disciplinary Mapping
    "disciplinary_mapping_v1": DISCIPLINARY_MAPPING_FAMILY,
    "disciplinary_mapping_v2": DISCIPLINARY_MAPPING_FAMILY,
}


def get_prompt_family(family_id: str) -> dict | None:
    fam = PROMPT_FAMILY_CATALOG.get(family_id)
    if fam is None and not family_id.endswith(("_v1", "_v2")):
        fam = PROMPT_FAMILY_CATALOG.get(f"{family_id}_v2")
        if fam is None:
            fam = PROMPT_FAMILY_CATALOG.get(f"{family_id}_v1")
    return fam


def list_prompt_families() -> list[str]:
    return sorted(PROMPT_FAMILY_CATALOG.keys())


def get_all_families() -> dict[str, dict]:
    return dict(PROMPT_FAMILY_CATALOG)
