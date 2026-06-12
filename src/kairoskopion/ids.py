"""Deterministic and random ID generation for Kairoskopion entities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_id(prefix: str) -> str:
    """Generate a prefixed UUID-based entity ID.

    Format: ``{prefix}_{uuid4_hex[:12]}``
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_timestamp_id(prefix: str) -> str:
    """Generate a prefixed ID with embedded UTC timestamp.

    Format: ``{prefix}_{YYYYMMDD_HHMMSSffffff}_{uuid4_hex[:8]}``
    """
    ts = _utcnow().strftime("%Y%m%d_%H%M%S%f")
    return f"{prefix}_{ts}_{uuid.uuid4().hex[:8]}"


# Convenience helpers per entity type

def article_model_id() -> str:
    return generate_id("art")

def manuscript_id() -> str:
    return generate_id("ms")

def venue_model_id() -> str:
    return generate_id("ven")

def publication_regime_id() -> str:
    return generate_id("reg")

def submission_scenario_id() -> str:
    return generate_id("scn")

def evidence_item_id() -> str:
    return generate_id("evi")

def source_snapshot_id() -> str:
    return generate_id("snap")

def fit_assessment_id() -> str:
    return generate_id("fit")

def mismatch_map_id() -> str:
    return generate_id("mm")

def rewrite_plan_id() -> str:
    return generate_id("rw")

def citation_plan_id() -> str:
    return generate_id("cit")

def risk_report_id() -> str:
    return generate_id("risk")

def compliance_checklist_id() -> str:
    return generate_id("cc")

def submission_pack_id() -> str:
    return generate_id("sp")

def pipeline_run_id() -> str:
    return generate_timestamp_id("run")

def operation_trace_id() -> str:
    return generate_timestamp_id("trace")

def quality_gate_id() -> str:
    return generate_id("gate")

def decision_id() -> str:
    return generate_id("dec")

def reference_item_id() -> str:
    return generate_id("ref")

def bibliography_profile_id() -> str:
    return generate_id("bib")

def citation_ecology_report_id() -> str:
    return generate_id("citeco")

def adapter_result_id() -> str:
    return generate_timestamp_id("adpt")

def trajectory_report_id() -> str:
    return generate_id("ptr")

def venue_record_id() -> str:
    return generate_id("vrec")

def venue_source_id() -> str:
    return generate_id("vsrc")

def venue_claim_id() -> str:
    return generate_id("vclm")

def venue_evidence_pack_id() -> str:
    return generate_id("vpack")

def article_semantic_profile_id() -> str:
    return generate_id("asp")

def disciplinary_pathway_id() -> str:
    return generate_id("dpath")

def article_variant_id() -> str:
    return generate_id("avar")

def editorial_board_profile_id() -> str:
    return generate_id("ebp")

def published_article_corpus_id() -> str:
    return generate_id("pac")

def citation_expectation_profile_id() -> str:
    return generate_id("cexp")

def venue_publication_profile_id() -> str:
    return generate_id("vpp")


# --- Agentic contour IDs ---

def agent_task_id() -> str:
    return generate_timestamp_id("atask")

def agent_run_id() -> str:
    return generate_timestamp_id("arun")

def agent_result_id() -> str:
    return generate_id("ares")

def agent_trace_id() -> str:
    return generate_timestamp_id("atrc")

def workflow_run_id() -> str:
    return generate_timestamp_id("wfrun")

def workflow_result_id() -> str:
    return generate_id("wfres")

def workflow_trace_id() -> str:
    return generate_timestamp_id("wftrc")


# --- Source authority / integrity IDs ---

def source_authority_claim_id() -> str:
    return generate_id("sacl")

def source_authority_assessment_id() -> str:
    return generate_id("saas")

def evidence_conflict_id() -> str:
    return generate_id("econ")

def evidence_reconciliation_id() -> str:
    return generate_id("erec")

def publication_history_id() -> str:
    return generate_id("phist")

def citation_integrity_check_id() -> str:
    return generate_id("cint")

def reporting_guideline_selection_id() -> str:
    return generate_id("rgsel")
