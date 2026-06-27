"""Pipeline 1: One manuscript × one target venue (spec §37).

Supports two execution modes:
- Deterministic (no LLM): heuristic extraction, same as before.
- LLM-assisted: agents extract ArticleModel, VenueModel, FitAssessment
  with semantic understanding. Deterministic diagnostics still computed.

P11 instrumentation: every stage creates a PipelineNode with status,
producer_type, artifacts, prompt metadata, and override tracking.
LLM-capable stages emit PromptRunRecord with rendered prompts.
"""

from __future__ import annotations

import json
from typing import Any

from ..agents.article_modeler import ArticleModelerAgent
from ..agents.contract import AgentInput
from ..agents.fit_assessor import FitAssessorAgent
from ..agents.venue_profiler import VenueProfilerAgent
from ..cards import (
    article_model_card,
    fit_assessment_card,
    risk_report_card,
    venue_model_card,
)
from ..enums import OutputLevel, PipelineRunStatus
from ..ids import pipeline_run_id as _new_run_id
from ..llm.provider import LLMProvider
from ..prompts.article_modeling import ARTICLE_MODELING_FAMILY
from ..prompts.fit_assessment import FIT_ASSESSMENT_FAMILY
from ..prompts.venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY
from ..quality import QualityGateResult, evaluate_fit_gate
from ..registry.integration import RegistryIntegrationService
from ..schema import (
    ArticleModel,
    BibliographyProfile,
    CitationEcologyReport,
    ComplianceChecklist,
    FitAssessment,
    ManuscriptModel,
    MismatchMap,
    PublicationRegimeModel,
    RewritePlan,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)
from ..services.article_modeling import build_article_model, build_manuscript_model
from ..services.bibliography_parsing import build_bibliography_profile
from ..services.citation_ecology import build_citation_ecology_report
from ..services.compliance import build_compliance_checklist
from ..services.evidence_audit import audit_pipeline_evidence
from ..services.fit_assessment import assess_fit
from ..services.mismatch_mapping import build_mismatch_map
from ..services.pipeline_trace import (
    PipelineNode,
    PipelineTraceStore,
    PromptRunRecord,
    _hash_text,
    _now,
)
from ..services.pipeline_trace import PipelineRun as TraceRun
from ..services.prompt_override import PromptOverrideStore
from ..services.rewrite_planning import build_rewrite_plan
from ..services.risk_reporting import build_risk_report
from ..services.scenario import build_scenario_from_dict
from ..services.venue_profiling import build_venue_model
from ..traces import finish_trace, start_trace
from .base import PipelineBase


class ManuscriptVenueFitResult:
    """Container for all entities produced by the pipeline."""

    def __init__(self) -> None:
        self.manuscript: ManuscriptModel | None = None
        self.article: ArticleModel | None = None
        self.venue: VenueModel | None = None
        self.regime: PublicationRegimeModel | None = None
        self.scenario: SubmissionScenario | None = None
        self.fit: FitAssessment | None = None
        self.mismatch_map: MismatchMap | None = None
        self.rewrite_plan: RewritePlan | None = None
        self.risk_report: RiskReport | None = None
        self.compliance: ComplianceChecklist | None = None
        self.bibliography_profile: BibliographyProfile | None = None
        self.citation_ecology: CitationEcologyReport | None = None
        self.fit_gate: QualityGateResult | None = None
        self.evidence_gate: QualityGateResult | None = None
        self.artifact_markdown: str | None = None
        self.llm_trace: list[dict[str, Any]] | None = None
        self.trace_run: Any | None = None


_NOT_APPLICABLE_STAGES = frozenset([
    "input_classification", "semantic_profile",
    "discipline_mapping", "discipline_matching",
    "venue_discovery", "venue_family_context", "venue_matrix",
])

_STAGE_META: dict[str, dict[str, Any]] = {
    "intake":               {"label": "Source Intake",        "order": 0,  "producer": "deterministic", "service": "build_manuscript_model"},
    "input_classification": {"label": "Input Classification", "order": 1,  "producer": "llm_agent",     "service": "InputClassifierAgent",          "prompt_family": "input_classification"},
    "article_model":        {"label": "Article Modeling",     "order": 2,  "producer": "llm_agent",     "service": "ArticleModelerAgent",           "prompt_family": "article_modeling"},
    "semantic_profile":     {"label": "Semantic Profiling",   "order": 3,  "producer": "llm_agent",     "service": "SemanticProfilerAgent",         "prompt_family": "semantic_profiling"},
    "bibliography_parse":   {"label": "Bibliography Parsing", "order": 4,  "producer": "deterministic", "service": "build_bibliography_profile"},
    "discipline_mapping":   {"label": "Disciplinary Mapping", "order": 5,  "producer": "llm_agent",     "service": "DisciplinaryMapperAgent",       "prompt_family": "disciplinary_mapping"},
    "discipline_matching":  {"label": "Discipline Matching",  "order": 6,  "producer": "llm_agent",     "service": "DisciplineMatcherAgent",        "prompt_family": "discipline_matching"},
    "venue_investigation":  {"label": "Venue Investigation",  "order": 7,  "producer": "llm_agent",     "service": "VenueProfilerAgent",            "prompt_family": "venue_fact_extraction"},
    "venue_discovery":      {"label": "Venue Discovery",      "order": 8,  "producer": "llm_agent",     "service": "VenueFunnelPlannerAgent",       "prompt_family": "venue_funnel_planning"},
    "venue_family_context": {"label": "Venue Family Context", "order": 9,  "producer": "llm_agent",     "service": "VenueFamilyContextBuilderAgent","prompt_family": "venue_family_context"},
    "venue_matrix":         {"label": "Venue Matrix",         "order": 10, "producer": "llm_agent",     "service": "VenueMatrixAssessorAgent",      "prompt_family": "venue_matrix_assessment"},
    "fit_gate":             {"label": "Fit Gate",             "order": 11, "producer": "deterministic", "service": "evaluate_fit_gate"},
    "fit_assessment":       {"label": "Fit Assessment",       "order": 12, "producer": "llm_agent",     "service": "FitAssessorAgent",              "prompt_family": "fit_assessment"},
    "mismatch_map":         {"label": "Mismatch Mapping",    "order": 13, "producer": "deterministic", "service": "build_mismatch_map"},
    "rewrite_plan":         {"label": "Rewrite Planning",    "order": 14, "producer": "deterministic", "service": "build_rewrite_plan"},
    "risk_report":          {"label": "Risk Reporting",      "order": 15, "producer": "deterministic", "service": "build_risk_report"},
    "compliance_check":     {"label": "Compliance Check",    "order": 16, "producer": "deterministic", "service": "build_compliance_checklist"},
    "evidence_audit":       {"label": "Evidence Audit",      "order": 17, "producer": "deterministic", "service": "audit_pipeline_evidence"},
}


class ManuscriptVenueFitPipeline(PipelineBase):
    """One manuscript × one target venue pipeline."""

    pipeline_type = "manuscript_venue_fit"

    def __init__(
        self,
        *,
        llm_provider: LLMProvider | None = None,
        registry_service: RegistryIntegrationService | None = None,
        trace_store: PipelineTraceStore | None = None,
        override_store: PromptOverrideStore | None = None,
        case_id: str | None = None,
    ) -> None:
        super().__init__()
        self.llm = llm_provider
        self._registry = registry_service
        self._trace_store = trace_store
        self._override_store = override_store
        self._case_id = case_id
        self._article_agent = ArticleModelerAgent()
        self._venue_agent = VenueProfilerAgent()
        self._fit_agent = FitAssessorAgent()

    # -- trace helpers --------------------------------------------------------

    def _make_node(self, trace_run: TraceRun, stage_id: str, **extra: Any) -> PipelineNode:
        meta = _STAGE_META.get(stage_id, {})
        node = PipelineNode(
            run_id=trace_run.run_id,
            stage_id=stage_id,
            stage_label=meta.get("label", stage_id),
            order_index=meta.get("order", 0),
            producer_type=meta.get("producer", "deterministic"),
            service_or_agent=meta.get("service", ""),
            prompt_family_id=meta.get("prompt_family"),
            status="running",
            started_at=_now(),
            **extra,
        )
        trace_run.node_ids.append(node.node_id)
        return node

    def _finish_node(
        self, node: PipelineNode, *,
        output_refs: list[str] | None = None,
        output_hash: str | None = None,
        diagnostics: list[str] | None = None,
        status: str = "completed",
    ) -> None:
        node.status = status
        node.completed_at = _now()
        if output_refs:
            node.output_artifact_refs = output_refs
        if output_hash:
            node.output_hash = output_hash
        if diagnostics:
            node.diagnostics = diagnostics
        if self._trace_store:
            self._trace_store.save_node(node)

    def _skip_node(self, trace_run: TraceRun, stage_id: str, reason: str) -> None:
        meta = _STAGE_META.get(stage_id, {})
        node = PipelineNode(
            run_id=trace_run.run_id,
            stage_id=stage_id,
            stage_label=meta.get("label", stage_id),
            order_index=meta.get("order", 0),
            producer_type=meta.get("producer", "deterministic"),
            service_or_agent=meta.get("service", ""),
            prompt_family_id=meta.get("prompt_family"),
            status="not_applicable",
            diagnostics=[reason],
        )
        trace_run.node_ids.append(node.node_id)
        if self._trace_store:
            self._trace_store.save_node(node)

    def _get_override_for(self, prompt_family_id: str) -> tuple[dict[str, str] | None, str | None]:
        if not self._override_store or not self._case_id:
            return None, None
        ovr = self._override_store.get_active_override(self._case_id, prompt_family_id)
        if not ovr:
            return None, None
        override_dict: dict[str, str] = {}
        if ovr.edited_system_prompt:
            override_dict["system_prompt"] = ovr.edited_system_prompt
        if ovr.edited_user_template:
            override_dict["user_prompt_template"] = ovr.edited_user_template
        return override_dict, ovr.override_id

    def _record_prompt(
        self,
        node: PipelineNode,
        family: dict[str, Any],
        rendered_user: str,
        agent_output: Any,
        override_id: str | None = None,
    ) -> None:
        if not self._trace_store:
            return
        is_llm = agent_output.llm_usage is not None
        notes = agent_output.trace_notes or []
        is_fallback = any(
            "deterministic" in n.lower() or "fallback" in n.lower()
            for n in notes
        )

        provider_status = "success" if is_llm else (
            "deterministic_fallback" if is_fallback else "not_called"
        )
        response_status = "parsed" if is_llm else "deterministic"

        rec = PromptRunRecord(
            node_id=node.node_id,
            prompt_family_id=node.prompt_family_id or "",
            prompt_version_hash=_hash_text(family.get("system_prompt", "")),
            prompt_override_id=override_id,
            rendered_system_prompt=family.get("system_prompt", ""),
            rendered_user_prompt=rendered_user,
            provider_status=provider_status,
            response_status=response_status,
            diagnostics=[n for n in notes if "parse" in n.lower() or "fallback" in n.lower()],
        )
        self._trace_store.save_prompt_record(rec)

        node.prompt_version_hash = rec.prompt_version_hash
        node.prompt_override_id = override_id
        node.provider_status = provider_status
        node.parse_status = response_status
        if is_fallback:
            node.producer_type = "deterministic_fallback"

    # -- main execution -------------------------------------------------------

    def execute(
        self,
        *,
        manuscript_text: str,
        venue_guidelines_text: str,
        scenario_data: dict[str, Any],
        manuscript_source_ref: str = "fixture:manuscript_sample",
        venue_source_ref: str = "fixture:venue_guidelines_sample",
    ) -> ManuscriptVenueFitResult:
        """Run the full pipeline.  Returns all created entities."""
        self.mark_running()
        result = ManuscriptVenueFitResult()
        llm_trace: list[dict[str, Any]] = []

        # -- Create trace run --
        trace_run = TraceRun(case_id=self._case_id, trigger="pipeline_execute")
        if self._trace_store:
            self._trace_store.save_run(trace_run)

        # -- Emit not-applicable nodes for stages this pipeline doesn't run --
        for sid in _NOT_APPLICABLE_STAGES:
            self._skip_node(trace_run, sid, "not_executed_in_manuscript_venue_fit")

        # ===== Stage: intake (order 0) =====
        n_intake = self._make_node(trace_run, "intake")
        self.trace.inputs.append(manuscript_source_ref)

        ms = build_manuscript_model(manuscript_text, source_ref=manuscript_source_ref)
        result.manuscript = ms
        self.run.created_entity_ids.append(ms.manuscript_id)
        self.trace.entities_created.append(ms.manuscript_id)

        self._finish_node(n_intake, output_refs=[ms.manuscript_id],
                          output_hash=_hash_text(str(ms.to_dict())))

        # ===== Stage: article_model (order 2) =====
        n_art = self._make_node(trace_run, "article_model")
        override_dict, override_id = self._get_override_for("article_modeling")

        article_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="article_modeler",
            source_refs=[manuscript_source_ref],
            raw_text=manuscript_text,
        )
        article_output = self._article_agent.run(
            article_input, self.llm,
            prompt_family_override=override_dict,
        )

        article = ArticleModel.from_dict(article_output.output_entity)
        result.article = article
        self.run.created_entity_ids.append(article.article_model_id)
        self.trace.entities_created.append(article.article_model_id)

        if article_output.llm_usage:
            llm_trace.append({"agent": "article_modeler", **article_output.llm_usage})
        if article_output.trace_notes:
            _append_notes(self.trace, article_output.trace_notes)

        eff_art_family = dict(ARTICLE_MODELING_FAMILY)
        if override_dict:
            eff_art_family.update(override_dict)
        rendered_art_user = eff_art_family["user_prompt_template"].format(
            manuscript_text=manuscript_text,
        )
        self._record_prompt(n_art, eff_art_family, rendered_art_user,
                            article_output, override_id)
        n_art.input_artifact_refs = [manuscript_source_ref]
        self._finish_node(n_art, output_refs=[article.article_model_id],
                          output_hash=_hash_text(str(article_output.output_entity)))

        # ===== Stage: bibliography_parse (order 4) =====
        n_bib = self._make_node(trace_run, "bibliography_parse")

        bib_profile = build_bibliography_profile(
            manuscript_text,
            manuscript_id=ms.manuscript_id,
            article_model_id=article.article_model_id,
        )
        result.bibliography_profile = bib_profile
        self.run.created_entity_ids.append(bib_profile.bibliography_profile_id)
        self.trace.entities_created.append(bib_profile.bibliography_profile_id)

        n_bib.input_artifact_refs = [ms.manuscript_id, article.article_model_id]
        self._finish_node(n_bib, output_refs=[bib_profile.bibliography_profile_id],
                          output_hash=_hash_text(str(bib_profile.to_dict())))

        # ===== Stage: venue_investigation (order 7) =====
        n_venue = self._make_node(trace_run, "venue_investigation")
        self.trace.inputs.append(venue_source_ref)
        override_dict_v, override_id_v = self._get_override_for("venue_fact_extraction")

        venue_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="venue_profiler",
            source_refs=[venue_source_ref],
            raw_text=venue_guidelines_text,
            user_constraints={"source_type": "author_guidelines"},
        )
        venue_output = self._venue_agent.run(
            venue_input, self.llm,
            prompt_family_override=override_dict_v,
        )

        venue_dict = venue_output.output_entity
        regime_dict = venue_dict.pop("_regime", {})
        venue = VenueModel.from_dict(venue_dict)
        regime = PublicationRegimeModel.from_dict(regime_dict) if regime_dict else PublicationRegimeModel()
        result.venue = venue
        result.regime = regime
        self.run.created_entity_ids.append(venue.venue_model_id)
        self.run.created_entity_ids.append(regime.publication_regime_id)
        self.trace.entities_created.extend([venue.venue_model_id, regime.publication_regime_id])

        if venue_output.llm_usage:
            llm_trace.append({"agent": "venue_profiler", **venue_output.llm_usage})
        if venue_output.trace_notes:
            _append_notes(self.trace, venue_output.trace_notes)

        eff_venue_family = dict(VENUE_FACT_EXTRACTION_FAMILY)
        if override_dict_v:
            eff_venue_family.update(override_dict_v)
        rendered_venue_user = eff_venue_family["user_prompt_template"].format(
            venue_text=venue_guidelines_text,
            source_type="author_guidelines",
            source_url="unknown",
        )
        self._record_prompt(n_venue, eff_venue_family, rendered_venue_user,
                            venue_output, override_id_v)
        n_venue.input_artifact_refs = [venue_source_ref]
        self._finish_node(n_venue, output_refs=[venue.venue_model_id, regime.publication_regime_id],
                          output_hash=_hash_text(str(venue_output.output_entity)))

        if self._registry:
            try:
                self._registry.store_venue_extraction(
                    venue_dict, source_url=None, source_type="pipeline_venue_profiler",
                )
            except Exception:
                pass

        # ===== Stage: fit_gate (order 11) — includes scenario build =====
        n_gate = self._make_node(trace_run, "fit_gate")

        scenario = build_scenario_from_dict(
            scenario_data,
            article_model_id=article.article_model_id,
            venue_model_id=venue.venue_model_id,
        )
        result.scenario = scenario
        self.run.created_entity_ids.append(scenario.submission_scenario_id)
        self.trace.entities_created.append(scenario.submission_scenario_id)

        fit_gate = evaluate_fit_gate(
            has_article_source=bool(article.source_refs),
            has_venue_source=bool(venue.source_refs),
            has_scenario=scenario.goal is not None,
            has_evidence_per_axis=False,
            has_context_pack=False,
        )
        result.fit_gate = fit_gate
        self.record_gate(fit_gate)

        n_gate.input_artifact_refs = [article.article_model_id, venue.venue_model_id]
        n_gate.gate_results = {"fit_gate": fit_gate.status}
        self._finish_node(n_gate,
                          output_refs=[scenario.submission_scenario_id],
                          output_hash=_hash_text(fit_gate.status),
                          diagnostics=[f"gate={fit_gate.status}"])

        # ===== Stage: fit_assessment (order 12) =====
        n_fit = self._make_node(trace_run, "fit_assessment")
        override_dict_f, override_id_f = self._get_override_for("fit_assessment")

        fit_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="fit_assessor",
            entities={
                "article": article.to_dict(),
                "venue": venue.to_dict(),
                "scenario": scenario.to_dict(),
            },
        )
        fit_output = self._fit_agent.run(
            fit_input, self.llm,
            prompt_family_override=override_dict_f,
        )
        fit = FitAssessment.from_dict(fit_output.output_entity)
        result.fit = fit
        self.run.created_entity_ids.append(fit.fit_assessment_id)
        self.trace.entities_created.append(fit.fit_assessment_id)

        if fit_output.llm_usage:
            llm_trace.append({"agent": "fit_assessor", **fit_output.llm_usage})
        if fit_output.trace_notes:
            _append_notes(self.trace, fit_output.trace_notes)

        eff_fit_family = dict(FIT_ASSESSMENT_FAMILY)
        if override_dict_f:
            eff_fit_family.update(override_dict_f)
        rendered_fit_user = eff_fit_family["user_prompt_template"].format(
            article_json=json.dumps(article.to_dict(), ensure_ascii=False, indent=2),
            venue_json=json.dumps(venue.to_dict(), ensure_ascii=False, indent=2),
            scenario_json=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2),
        )
        self._record_prompt(n_fit, eff_fit_family, rendered_fit_user,
                            fit_output, override_id_f)
        n_fit.input_artifact_refs = [article.article_model_id, venue.venue_model_id,
                                     scenario.submission_scenario_id]
        self._finish_node(n_fit, output_refs=[fit.fit_assessment_id],
                          output_hash=_hash_text(str(fit_output.output_entity)))

        # ===== Stage: mismatch_map (order 13) =====
        n_mm = self._make_node(trace_run, "mismatch_map")

        mm = build_mismatch_map(fit)
        result.mismatch_map = mm
        fit.mismatch_map_id = mm.mismatch_map_id
        self.run.created_entity_ids.append(mm.mismatch_map_id)
        self.trace.entities_created.append(mm.mismatch_map_id)

        n_mm.input_artifact_refs = [fit.fit_assessment_id]
        self._finish_node(n_mm, output_refs=[mm.mismatch_map_id],
                          output_hash=_hash_text(str(mm.to_dict())))

        # ===== Stage: rewrite_plan (order 14) =====
        n_rw = self._make_node(trace_run, "rewrite_plan")

        rw = build_rewrite_plan(
            mm,
            article_model_id=article.article_model_id,
            manuscript_id=ms.manuscript_id,
            venue_model_id=venue.venue_model_id,
        )
        result.rewrite_plan = rw
        self.run.created_entity_ids.append(rw.rewrite_plan_id)
        self.trace.entities_created.append(rw.rewrite_plan_id)

        n_rw.input_artifact_refs = [mm.mismatch_map_id, article.article_model_id]
        self._finish_node(n_rw, output_refs=[rw.rewrite_plan_id],
                          output_hash=_hash_text(str(rw.to_dict())))

        # ===== Stage: risk_report (order 15) =====
        n_risk = self._make_node(trace_run, "risk_report")

        risk = build_risk_report(article, venue, scenario, fit, mm)
        result.risk_report = risk
        self.run.created_entity_ids.append(risk.risk_report_id)
        self.trace.entities_created.append(risk.risk_report_id)

        n_risk.input_artifact_refs = [article.article_model_id, venue.venue_model_id,
                                      fit.fit_assessment_id, mm.mismatch_map_id]
        self._finish_node(n_risk, output_refs=[risk.risk_report_id],
                          output_hash=_hash_text(str(risk.to_dict())))

        # ===== Stage: compliance_check (order 16) =====
        n_cc = self._make_node(trace_run, "compliance_check")

        cc = build_compliance_checklist(article, ms, venue, venue_guidelines_text)
        result.compliance = cc
        self.run.created_entity_ids.append(cc.compliance_checklist_id)
        self.trace.entities_created.append(cc.compliance_checklist_id)

        n_cc.input_artifact_refs = [article.article_model_id, ms.manuscript_id,
                                    venue.venue_model_id]
        self._finish_node(n_cc, output_refs=[cc.compliance_checklist_id],
                          output_hash=_hash_text(str(cc.to_dict())))

        # ===== Stage: evidence_audit (order 17) — includes citation ecology =====
        n_ev = self._make_node(trace_run, "evidence_audit")

        cit_eco = build_citation_ecology_report(
            bib_profile, article, venue, venue_guidelines_text,
        )
        result.citation_ecology = cit_eco
        self.run.created_entity_ids.append(cit_eco.citation_ecology_report_id)
        self.trace.entities_created.append(cit_eco.citation_ecology_report_id)

        ev_gate = audit_pipeline_evidence(article, venue, fit, mm, risk, cc)
        result.evidence_gate = ev_gate
        self.record_gate(ev_gate)

        n_ev.input_artifact_refs = [article.article_model_id, venue.venue_model_id,
                                    fit.fit_assessment_id, mm.mismatch_map_id,
                                    risk.risk_report_id, cc.compliance_checklist_id]
        n_ev.gate_results = {"evidence_audit": ev_gate.status}
        self._finish_node(n_ev,
                          output_refs=[cit_eco.citation_ecology_report_id],
                          output_hash=_hash_text(ev_gate.status),
                          diagnostics=[f"gate={ev_gate.status}"])

        # -- Finalize --
        result.artifact_markdown = _generate_artifact(result)
        result.llm_trace = llm_trace if llm_trace else None

        trace_run.status = "completed"
        trace_run.completed_at = _now()
        trace_run.gates_summary = {
            "fit_gate": fit_gate.status,
            "evidence_audit": ev_gate.status,
        }
        if self._trace_store:
            self._trace_store.save_run(trace_run)

        result.trace_run = trace_run  # expose for API / tests

        self.trace.sources_accessed = [manuscript_source_ref, venue_source_ref]
        self.finish(output_level=OutputLevel.PRELIMINARY)
        return result


def _append_notes(trace, notes: list[str]) -> None:
    joined = "; ".join(notes)
    if trace.notes:
        trace.notes = trace.notes + "; " + joined
    else:
        trace.notes = joined


def _generate_artifact(r: ManuscriptVenueFitResult) -> str:
    """Generate human-readable markdown artifact from pipeline result."""
    parts: list[str] = ["# Kairoskopion Fit Report\n"]

    if r.article:
        parts.append(article_model_card(r.article.to_dict()))
        parts.append("")

    if r.venue:
        parts.append(venue_model_card(r.venue.to_dict()))
        parts.append("")

    if r.fit:
        parts.append(fit_assessment_card(r.fit.to_dict()))
        parts.append("")

    if r.mismatch_map and r.mismatch_map.mismatches:
        parts.append("## Mismatch Map\n")
        parts.append(f"**Summary:** {r.mismatch_map.summary}\n")
        for mm in r.mismatch_map.mismatches:
            parts.append(
                f"- **{mm.get('axis', '?')}** [{mm.get('severity', '?')}]: "
                f"{mm.get('description', '')} "
                f"(core: {mm.get('field_core_risk', '?')})"
            )
        parts.append("")

    if r.rewrite_plan and r.rewrite_plan.changes:
        parts.append("## Rewrite Plan\n")
        parts.append(f"**Summary:** {r.rewrite_plan.summary}\n")
        parts.append(f"**Estimated effort:** {r.rewrite_plan.estimated_effort}\n")
        parts.append(f"**Field core risk:** {r.rewrite_plan.field_core_risk}\n")
        for ch in r.rewrite_plan.changes:
            parts.append(
                f"- [{ch.get('change_type', '?')}] {ch.get('desired_state', '')} "
                f"(linked to: {ch.get('related_mismatch_id', '?')})"
            )
        parts.append("")

    if r.risk_report:
        parts.append(risk_report_card(r.risk_report.to_dict()))
        parts.append("")

    if r.compliance:
        parts.append("## Compliance Checklist\n")
        for item in r.compliance.checklist_items:
            status = item.get("status", "?")
            marker = {"present": "+", "missing": "!", "unknown": "?",
                      "non_compliant": "X", "not_applicable": "-"}.get(status, "?")
            parts.append(
                f"- [{marker}] **{item.get('category', '?')}**: "
                f"{item.get('requirement', '')} — {status}"
            )
        if r.compliance.missing_items:
            parts.append(f"\n**Missing:** {', '.join(r.compliance.missing_items)}")
        parts.append("")

    # Citation ecology
    if r.citation_ecology:
        parts.append("## Citation Ecology\n")
        parts.append(f"> {r.citation_ecology.disclaimer}\n")
        if r.citation_ecology.summary:
            parts.append(f"**Summary:** {r.citation_ecology.summary}\n")
        if r.citation_ecology.gaps:
            for g in r.citation_ecology.gaps:
                parts.append(
                    f"- [{g.get('severity', '?')}] **{g.get('gap_type', '?')}**: "
                    f"{g.get('description', '')}"
                )
        if r.citation_ecology.warning_signals:
            parts.append("\n**Warnings:**")
            for w in r.citation_ecology.warning_signals:
                parts.append(f"- {w}")
        parts.append("")

    # Evidence & unknowns summary
    parts.append("## Evidence & Unknowns\n")
    all_unknowns: list[str] = []
    for entity_name, entity in [
        ("ArticleModel", r.article),
        ("VenueModel", r.venue),
        ("FitAssessment", r.fit),
        ("MismatchMap", r.mismatch_map),
        ("RiskReport", r.risk_report),
        ("CitationEcology", r.citation_ecology),
    ]:
        if entity and hasattr(entity, "unknowns") and entity.unknowns:
            for u in entity.unknowns:
                all_unknowns.append(f"- **{entity_name}**: {u}")
    if all_unknowns:
        parts.extend(all_unknowns)
    else:
        parts.append("No unknowns recorded.")

    parts.append("")

    # Quality gates
    if r.fit_gate:
        parts.append(f"## Quality Gates\n")
        parts.append(f"**Fit gate:** {r.fit_gate.status}")
        if r.fit_gate.warnings:
            for w in r.fit_gate.warnings:
                parts.append(f"  - {w}")
    if r.evidence_gate:
        parts.append(f"**Evidence audit:** {r.evidence_gate.status}")
        if r.evidence_gate.warnings:
            for w in r.evidence_gate.warnings:
                parts.append(f"  - {w}")

    # LLM usage summary
    if r.llm_trace:
        parts.append("\n## LLM Usage\n")
        for entry in r.llm_trace:
            parts.append(
                f"- **{entry.get('agent', '?')}**: model={entry.get('model', '?')}, "
                f"tokens={entry.get('input_tokens', 0)}+{entry.get('output_tokens', 0)}, "
                f"latency={entry.get('latency_ms', 0):.0f}ms"
            )

    return "\n".join(parts)
