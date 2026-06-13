"""Case state management for the cockpit API.

A Case is a publication positioning session: one article through one or
more venue evaluations.  It wraps domain objects (ArticleModel, VenueModel,
FitAssessment, etc.) and tracks user decisions.
"""

from __future__ import annotations

import enum
from typing import Any

from ..ids import generate_id
from ..schema import (
    ArticleModel,
    ArticleSemanticProfile,
    DisciplinaryPathway,
    FitAssessment,
    MismatchMap,
    RewritePlan,
    CitationPlan,
    RiskReport,
    SubmissionScenario,
    VenueCandidatePool,
    VenueModel,
    _now,
)
from ..enums import (
    EvidenceStatus,
    LifecycleStatus,
)


class CaseStage(str, enum.Enum):
    EMPTY = "empty"
    INTAKE = "intake"
    ARTICLE_MODEL = "article_model"
    SCENARIO = "scenario"
    PATHWAYS = "pathways"
    VENUE_POOL = "venue_pool"
    VENUE_SELECTED = "venue_selected"
    FIT_ASSESSED = "fit_assessed"
    ADAPTING = "adapting"
    SUBMISSION_PACK = "submission_pack"
    DOSSIER = "dossier"


class Case:
    """In-memory case state.  One case = one publication situation."""

    def __init__(self, case_id: str | None = None, title: str = ""):
        self.case_id = case_id or generate_id("case")
        self.title = title or "Untitled case"
        self.created_at = _now()
        self.stage = CaseStage.EMPTY
        self.input_text: str = ""
        self.input_type: str = ""

        self.article_model: ArticleModel | None = None
        self.semantic_profile: ArticleSemanticProfile | None = None
        self.scenario: SubmissionScenario | None = None
        self.pathways: list[DisciplinaryPathway] = []
        self.venue_pool: VenueCandidatePool | None = None
        self.selected_venue: VenueModel | None = None
        self.fit_assessment: FitAssessment | None = None
        self.mismatch_map: MismatchMap | None = None
        self.rewrite_plan: RewritePlan | None = None
        self.citation_plan: CitationPlan | None = None
        self.risk_report: RiskReport | None = None

        self.decision_log: list[dict[str, Any]] = []
        self.quality_gates: dict[str, dict[str, Any]] = {}

    # -- Stage tracking --

    def _objects_present(self) -> dict[str, bool]:
        return {
            "intake": bool(self.input_text),
            "article_model": self.article_model is not None,
            "scenario": self.scenario is not None,
            "pathways": len(self.pathways) > 0,
            "venue_pool": self.venue_pool is not None,
            "venue_selected": self.selected_venue is not None,
            "fit_assessed": self.fit_assessment is not None,
            "adaptation_plan": self.rewrite_plan is not None,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "stage": self.stage.value,
            "created_at": self.created_at,
            "objects_present": self._objects_present(),
        }

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "case_id": self.case_id,
            "title": self.title,
            "stage": self.stage.value,
            "created_at": self.created_at,
            "objects_present": self._objects_present(),
            "input_text_length": len(self.input_text),
            "input_type": self.input_type,
            "decision_log_count": len(self.decision_log),
            "quality_gates": self.quality_gates,
        }
        if self.article_model:
            result["article_model_id"] = self.article_model.article_model_id
        if self.scenario:
            result["scenario_id"] = self.scenario.submission_scenario_id
        if self.selected_venue:
            result["selected_venue_id"] = self.selected_venue.venue_model_id
        if self.fit_assessment:
            result["fit_label"] = self.fit_assessment.overall_label
        return result

    # -- Intake --

    def intake_text(self, text: str, input_type: str = "auto") -> dict[str, Any]:
        self.input_text = text
        self.input_type = input_type if input_type != "auto" else _classify_input(text)
        self.stage = CaseStage.INTAKE

        if self.input_type in ("article", "abstract", "manuscript"):
            self._build_article_model()

        return {
            "input_type": self.input_type,
            "text_length": len(text),
            "article_model_built": self.article_model is not None,
            "stage": self.stage.value,
        }

    def _build_article_model(self):
        from ..services.article_modeling import (
            build_manuscript_model,
            build_article_model,
        )
        manuscript = build_manuscript_model(self.input_text)
        self.article_model = build_article_model(manuscript, self.input_text)
        self.stage = CaseStage.ARTICLE_MODEL

        from ..services.article_enrichment import build_article_semantic_profile
        self.semantic_profile = build_article_semantic_profile(self.article_model)

    # -- Confirm article model --

    def confirm_article_model(
        self,
        protected_core: list[str] | None = None,
        corrections: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.article_model:
            return {"error": "No article model to confirm"}

        if protected_core is not None:
            self.article_model.protected_core = protected_core

        if corrections:
            for field, value in corrections.items():
                if hasattr(self.article_model, field):
                    setattr(self.article_model, field, value)

        self.article_model.lifecycle_status = LifecycleStatus.CONFIRMED.value

        self._log_decision("confirm_article_model", {
            "protected_core": protected_core,
            "corrections_applied": list(corrections.keys()) if corrections else [],
        })

        return {
            "confirmed": True,
            "protected_core": self.article_model.protected_core,
            "lifecycle_status": self.article_model.lifecycle_status,
        }

    # -- Scenario --

    def set_scenario(self, data: dict[str, Any]) -> dict[str, Any]:
        field_map = {
            "language": "language_constraints",
            "apc_max": "APC_constraints",
            "target_indexing": "target_indexing",
        }
        mapped: dict[str, Any] = {}
        valid_fields = {f.name for f in __import__("dataclasses").fields(SubmissionScenario)}
        for k, v in data.items():
            target = field_map.get(k, k)
            if target in valid_fields and v is not None:
                mapped[target] = str(v) if target == "APC_constraints" else v

        self.scenario = SubmissionScenario(
            article_model_id=(
                self.article_model.article_model_id
                if self.article_model else ""
            ),
            **mapped,
        )
        self.stage = CaseStage.SCENARIO

        self._log_decision("set_scenario", {
            "goal": data.get("goal", ""),
            "rewrite_depth": data.get("rewrite_depth_allowed", ""),
        })

        return self.scenario.to_dict()

    # -- Pathways --

    def get_pathways(self) -> list[dict[str, Any]]:
        if not self.pathways and self.semantic_profile:
            from ..agents.article.pathway_mapper import DisciplinaryPathwayMapperAgent
            agent = DisciplinaryPathwayMapperAgent()
            output = agent.execute_deterministic(
                entities={"article_semantic_profile": self.semantic_profile.to_dict()},
            )
            if output.output_entity:
                raw = output.output_entity.get("pathways", [])
                self.pathways = [
                    DisciplinaryPathway(**p) if isinstance(p, dict) else p
                    for p in raw
                ]
            self.stage = CaseStage.PATHWAYS
        return [
            p.to_dict() if hasattr(p, "to_dict") else p
            for p in self.pathways
        ]

    # -- Venue pool --

    def get_venue_pool(self) -> dict[str, Any]:
        if self.venue_pool:
            return self.venue_pool.to_dict()
        return {"candidates": [], "status": "not_discovered"}

    # -- Select venue & fit --

    def select_venue(self, venue_id: str) -> dict[str, Any]:
        self.stage = CaseStage.VENUE_SELECTED

        self._log_decision("select_venue", {"venue_id": venue_id})

        return {
            "selected_venue_id": venue_id,
            "stage": self.stage.value,
            "fit_available": self.fit_assessment is not None,
        }

    def get_fit(self) -> dict[str, Any]:
        if self.fit_assessment:
            return self.fit_assessment.to_dict()
        return {"status": "not_assessed"}

    def get_mismatch_map(self) -> dict[str, Any]:
        if self.mismatch_map:
            return self.mismatch_map.to_dict()
        return {"mismatches": [], "status": "not_assessed"}

    # -- Adaptation --

    def get_adaptation_plan(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.rewrite_plan:
            result["rewrite_plan"] = self.rewrite_plan.to_dict()
        if self.citation_plan:
            result["citation_plan"] = self.citation_plan.to_dict()
        if self.risk_report:
            result["risk_report"] = self.risk_report.to_dict()
        if not result:
            result["status"] = "no_plan"
        return result

    def apply_decisions(
        self, decisions_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.rewrite_plan:
            return {"error": "No rewrite plan to apply decisions to"}

        from ..services.review_loop import (
            UserDecision,
            apply_user_decisions,
        )

        decisions = [
            UserDecision(
                change_id=d["change_id"],
                action=d["action"],
                reason=d.get("reason", ""),
            )
            for d in decisions_data
        ]

        protected_core = (
            self.article_model.protected_core
            if self.article_model else []
        )

        self.rewrite_plan, iteration = apply_user_decisions(
            self.rewrite_plan, decisions, protected_core,
        )
        self.stage = CaseStage.ADAPTING

        for d in decisions_data:
            self._log_decision(f"decision_{d['action']}", {
                "change_id": d["change_id"],
                "reason": d.get("reason", ""),
            })

        return iteration.to_dict()

    # -- Evidence --

    def get_evidence(
        self, entity_type: str, field_path: str,
    ) -> dict[str, Any]:
        return {
            "entity_type": entity_type,
            "field_path": field_path,
            "evidence_status": EvidenceStatus.UNKNOWN.value,
            "source": None,
            "confidence": "low",
            "note": "Evidence drill-down not yet connected to adapters",
        }

    # -- Quality gates --

    def get_quality_gates(self) -> dict[str, dict[str, Any]]:
        return self.quality_gates

    # -- Dossier --

    def build_dossier(self) -> dict[str, Any]:
        dossier: dict[str, Any] = {
            "case_id": self.case_id,
            "title": self.title,
            "stage": self.stage.value,
            "created_at": self.created_at,
            "generated_at": _now(),
        }

        if self.article_model:
            dossier["article_model"] = self.article_model.to_dict()
        if self.semantic_profile:
            dossier["semantic_profile"] = self.semantic_profile.to_dict()
        if self.scenario:
            dossier["scenario"] = self.scenario.to_dict()
        if self.pathways:
            dossier["pathways"] = [
                p.to_dict() if hasattr(p, "to_dict") else p
                for p in self.pathways
            ]
        if self.venue_pool:
            dossier["venue_pool"] = self.venue_pool.to_dict()
        if self.selected_venue:
            dossier["selected_venue"] = self.selected_venue.to_dict()
        if self.fit_assessment:
            dossier["fit_assessment"] = self.fit_assessment.to_dict()
        if self.mismatch_map:
            dossier["mismatch_map"] = self.mismatch_map.to_dict()
        if self.rewrite_plan:
            dossier["rewrite_plan"] = self.rewrite_plan.to_dict()
        if self.citation_plan:
            dossier["citation_plan"] = self.citation_plan.to_dict()
        if self.risk_report:
            dossier["risk_report"] = self.risk_report.to_dict()

        dossier["decision_log"] = self.decision_log
        dossier["quality_gates"] = self.quality_gates

        return dossier

    # -- Decision log --

    def _log_decision(self, action: str, details: dict[str, Any]):
        self.decision_log.append({
            "action": action,
            "details": details,
            "timestamp": _now(),
        })


class CaseStore:
    """In-memory case store.  Will migrate to file-based persistence later."""

    def __init__(self):
        self._cases: dict[str, Case] = {}

    def create(self, title: str = "") -> Case:
        case = Case(title=title)
        self._cases[case.case_id] = case
        return case

    def get(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def all(self) -> list[Case]:
        return list(self._cases.values())

    def delete(self, case_id: str) -> bool:
        return self._cases.pop(case_id, None) is not None

    def save(self, case: Case):
        self._cases[case.case_id] = case


def _classify_input(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["reviewer", "revision", "reject", "resubmit", "referee"]):
        return "review_letter"
    if any(k in lower for k in ["issn", "author guidelines", "scope of the journal"]):
        return "venue"
    if len(text) < 500:
        return "abstract"
    return "manuscript"
