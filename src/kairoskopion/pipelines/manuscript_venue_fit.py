"""Pipeline 1: One manuscript × one target venue (spec §37).

Supports two execution modes:
- Deterministic (no LLM): heuristic extraction, same as before.
- LLM-assisted: agents extract ArticleModel, VenueModel, FitAssessment
  with semantic understanding. Deterministic diagnostics still computed.
"""

from __future__ import annotations

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


class ManuscriptVenueFitPipeline(PipelineBase):
    """One manuscript × one target venue pipeline."""

    pipeline_type = "manuscript_venue_fit"

    def __init__(
        self,
        *,
        llm_provider: LLMProvider | None = None,
        registry_service: RegistryIntegrationService | None = None,
    ) -> None:
        super().__init__()
        self.llm = llm_provider
        self._registry = registry_service
        self._article_agent = ArticleModelerAgent()
        self._venue_agent = VenueProfilerAgent()
        self._fit_agent = FitAssessorAgent()

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

        # Step 1–3: Build ManuscriptModel and ArticleModel
        self.trace.inputs.append(manuscript_source_ref)

        article_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="article_modeler",
            source_refs=[manuscript_source_ref],
            raw_text=manuscript_text,
        )
        article_output = self._article_agent.run(article_input, self.llm)

        # Reconstruct typed entities from agent output
        ms = build_manuscript_model(manuscript_text, source_ref=manuscript_source_ref)
        result.manuscript = ms
        self.run.created_entity_ids.append(ms.manuscript_id)
        self.trace.entities_created.append(ms.manuscript_id)

        article = ArticleModel.from_dict(article_output.output_entity)
        result.article = article
        self.run.created_entity_ids.append(article.article_model_id)
        self.trace.entities_created.append(article.article_model_id)

        if article_output.llm_usage:
            llm_trace.append({"agent": "article_modeler", **article_output.llm_usage})
        if article_output.trace_notes:
            _append_notes(self.trace, article_output.trace_notes)

        # Step 3b: Build BibliographyProfile (always deterministic)
        bib_profile = build_bibliography_profile(
            manuscript_text,
            manuscript_id=ms.manuscript_id,
            article_model_id=article.article_model_id,
        )
        result.bibliography_profile = bib_profile
        self.run.created_entity_ids.append(bib_profile.bibliography_profile_id)
        self.trace.entities_created.append(bib_profile.bibliography_profile_id)

        # Step 4–6: Build VenueModel and PublicationRegimeModel
        self.trace.inputs.append(venue_source_ref)

        venue_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="venue_profiler",
            source_refs=[venue_source_ref],
            raw_text=venue_guidelines_text,
            user_constraints={
                "source_type": "author_guidelines",
            },
        )
        venue_output = self._venue_agent.run(venue_input, self.llm)

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

        if self._registry:
            try:
                self._registry.store_venue_extraction(
                    venue_dict,
                    source_url=None,
                    source_type="pipeline_venue_profiler",
                )
            except Exception:
                pass

        # Step 7: Build SubmissionScenario
        scenario = build_scenario_from_dict(
            scenario_data,
            article_model_id=article.article_model_id,
            venue_model_id=venue.venue_model_id,
        )
        result.scenario = scenario
        self.run.created_entity_ids.append(scenario.submission_scenario_id)
        self.trace.entities_created.append(scenario.submission_scenario_id)

        # Quality gate: fit prerequisites
        fit_gate = evaluate_fit_gate(
            has_article_source=bool(article.source_refs),
            has_venue_source=bool(venue.source_refs),
            has_scenario=scenario.goal is not None,
            has_evidence_per_axis=False,
            has_context_pack=False,
        )
        result.fit_gate = fit_gate
        self.record_gate(fit_gate)

        # Step 8: FitAssessment
        fit_input = AgentInput(
            operation_id=self.run.pipeline_run_id,
            agent_role_id="fit_assessor",
            entities={
                "article": article.to_dict(),
                "venue": venue.to_dict(),
                "scenario": scenario.to_dict(),
            },
        )
        fit_output = self._fit_agent.run(fit_input, self.llm)
        fit = FitAssessment.from_dict(fit_output.output_entity)
        result.fit = fit
        self.run.created_entity_ids.append(fit.fit_assessment_id)
        self.trace.entities_created.append(fit.fit_assessment_id)

        if fit_output.llm_usage:
            llm_trace.append({"agent": "fit_assessor", **fit_output.llm_usage})
        if fit_output.trace_notes:
            _append_notes(self.trace, fit_output.trace_notes)

        # Step 9: MismatchMap (deterministic from fit)
        mm = build_mismatch_map(fit)
        result.mismatch_map = mm
        fit.mismatch_map_id = mm.mismatch_map_id
        self.run.created_entity_ids.append(mm.mismatch_map_id)
        self.trace.entities_created.append(mm.mismatch_map_id)

        # Step 10: RewritePlan (deterministic from mismatches)
        rw = build_rewrite_plan(
            mm,
            article_model_id=article.article_model_id,
            manuscript_id=ms.manuscript_id,
            venue_model_id=venue.venue_model_id,
        )
        result.rewrite_plan = rw
        self.run.created_entity_ids.append(rw.rewrite_plan_id)
        self.trace.entities_created.append(rw.rewrite_plan_id)

        # Step 12: RiskReport (deterministic)
        risk = build_risk_report(article, venue, scenario, fit, mm)
        result.risk_report = risk
        self.run.created_entity_ids.append(risk.risk_report_id)
        self.trace.entities_created.append(risk.risk_report_id)

        # Step 13: ComplianceChecklist (deterministic)
        cc = build_compliance_checklist(article, ms, venue, venue_guidelines_text)
        result.compliance = cc
        self.run.created_entity_ids.append(cc.compliance_checklist_id)
        self.trace.entities_created.append(cc.compliance_checklist_id)

        # Step 14: Citation ecology report (deterministic)
        cit_eco = build_citation_ecology_report(
            bib_profile, article, venue, venue_guidelines_text,
        )
        result.citation_ecology = cit_eco
        self.run.created_entity_ids.append(cit_eco.citation_ecology_report_id)
        self.trace.entities_created.append(cit_eco.citation_ecology_report_id)

        # Step 15: Evidence audit
        ev_gate = audit_pipeline_evidence(article, venue, fit, mm, risk, cc)
        result.evidence_gate = ev_gate
        self.record_gate(ev_gate)

        # Step 16: Generate artifact
        result.artifact_markdown = _generate_artifact(result)
        result.llm_trace = llm_trace if llm_trace else None

        # Finish
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
