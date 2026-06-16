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
    EvidencePolicy,
    FieldPositionModel,
    FitAssessment,
    MismatchMap,
    ProtectedCorePolicy,
    PublicationRegimeModel,
    RewritePlan,
    CitationPlan,
    RiskReport,
    SourceEvidencePacket,
    SubmissionScenario,
    VenueCandidatePool,
    VenueModel,
    _now,
)
from ..enums import (
    EvidenceStatus,
    LifecycleStatus,
)
from ..llm.config import LLMConfig
from ..llm.input_limits import LLM_INPUT_CHAR_CAP, cap_llm_input
from ..llm.openai_compat import OpenAICompatProvider


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


def _get_llm_provider() -> OpenAICompatProvider | None:
    cfg = LLMConfig.from_env()
    if cfg is None:
        return None
    if not cfg.api_key:
        return None
    return OpenAICompatProvider(cfg)


class Case:
    """In-memory case state.  One case = one publication situation.

    `user_id` is None for legacy/demo/system cases (pre-auth, tests).
    User-scoped cases carry the owner's user_id; the store partitions
    on-disk storage and read access by it.
    """

    def __init__(
        self, case_id: str | None = None, title: str = "",
        user_id: str | None = None,
    ):
        self.case_id = case_id or generate_id("case")
        self.title = title or "Untitled case"
        self.created_at = _now()
        self.stage = CaseStage.EMPTY
        self.user_id: str | None = user_id
        self.input_text: str = ""
        self.input_type: str = ""
        # LLM-bound projection of input_text (clipped via input_limits).
        # Recomputed each intake_text() call.
        self._llm_input_text: str = ""
        self._llm_input_truncation = None

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
        self.publication_regime: PublicationRegimeModel | None = None
        self.investigated_venue: VenueModel | None = None
        self.article_field_position: FieldPositionModel | None = None
        self.venue_field_position: FieldPositionModel | None = None
        self.field_position_fit: dict[str, Any] | None = None
        self.source_evidence_packet: SourceEvidencePacket | None = None
        self.protected_core_policy: ProtectedCorePolicy | None = None
        self.evidence_policy: EvidencePolicy | None = None
        self.policy_blocked_changes: list[dict[str, Any]] = []

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

    def intake_text(
        self,
        text: str,
        input_type: str = "auto",
        search_depth: str = "none",
    ) -> dict[str, Any]:
        self.input_text = text
        # Cap the LLM-bound projection once per intake. The original full
        # text stays on self.input_text for deterministic processing and
        # persistence; only the prompt-facing copy is clipped.
        capped, truncation = cap_llm_input(text, LLM_INPUT_CHAR_CAP)
        self._llm_input_text = capped
        self._llm_input_truncation = truncation
        self.input_type = input_type if input_type != "auto" else _classify_input(text)
        self.stage = CaseStage.INTAKE

        enrichment_result: dict[str, Any] = {}

        if self.input_type in ("article", "abstract", "manuscript"):
            self._build_article_model()
            # Web enrichment pass
            if search_depth != "none" and self.article_model is not None:
                enrichment_result = self._enrich_article(search_depth)
        elif self.input_type == "venue":
            try:
                self.investigate_venue(text)
            except Exception:
                pass

        result: dict[str, Any] = {
            "input_type": self.input_type,
            "text_length": len(text),
            "article_model_built": self.article_model is not None,
            "venue_investigated": self.investigated_venue is not None,
            "stage": self.stage.value,
        }
        if truncation.truncated:
            result["input_truncated_for_llm"] = truncation.to_dict()
        if enrichment_result:
            result["enrichment"] = enrichment_result
        return result

    def _build_article_model(self):
        import logging
        logger = logging.getLogger(__name__)

        # Track LLM attempt explicitly so case-level fallbacks (not just
        # agent-level) carry the visible warning that the human view
        # surfaces. Without this, a deeper crash silently falls to the
        # deterministic service path with no audit trail.
        from ..llm.attempt_metadata import (
            FALLBACK_REASON_LLM_UNAVAILABLE,
            FALLBACK_REASON_PROVIDER_ERROR,
            LLMAttemptMetadata,
        )

        case_level_attempt: LLMAttemptMetadata | None = None

        provider = _get_llm_provider()
        if provider is not None:
            from ..agents.article_modeler import ArticleModelerAgent
            from ..agents.contract import AgentInput
            agent = ArticleModelerAgent()
            inp = AgentInput(
                operation_id="intake_article",
                agent_role_id="article_modeler",
                raw_text=self._llm_input_text or self.input_text,
            )
            try:
                output = agent.execute(inp, provider)
                if output.output_entity:
                    self.article_model = ArticleModel.from_dict(output.output_entity)
                    logger.info("Article model built via LLM (%s)", output.confidence)
            except Exception as exc:
                logger.warning("LLM article modeling failed, falling back: %s", exc)
                case_level_attempt = LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_PROVIDER_ERROR,
                    provider="openai_compatible",
                    validation_errors=[str(exc)[:240]],
                )
                provider = None
        else:
            # No provider configured at all.
            case_level_attempt = LLMAttemptMetadata.not_attempted()

        if self.article_model is None:
            from ..services.article_modeling import (
                build_manuscript_model,
                build_article_model,
            )
            manuscript = build_manuscript_model(self.input_text)
            self.article_model = build_article_model(manuscript, self.input_text)
            logger.info("Article model built via deterministic fallback")
            # If we got here via a case-level crash, attach metadata so the
            # human view warns the author honestly.
            if case_level_attempt is not None and self.article_model is not None:
                try:
                    self.article_model.extraction_attempt = case_level_attempt.to_dict()
                except Exception:  # noqa: BLE001
                    pass

        self.stage = CaseStage.ARTICLE_MODEL

        # Semantic profile: try LLM agent, fall back to deterministic
        provider = _get_llm_provider()
        if provider is not None:
            from ..agents.semantic_profiler import ArticleSemanticProfilerAgent
            from ..agents.contract import AgentInput as _AI
            sp_agent = ArticleSemanticProfilerAgent()
            sp_inp = _AI(
                operation_id="semantic_profile",
                agent_role_id="article_semantic_profiler",
                entities={"article": self.article_model.to_dict()},
            )
            try:
                sp_out = sp_agent.execute(sp_inp, provider)
                if sp_out.output_entity:
                    self.semantic_profile = ArticleSemanticProfile.from_dict(sp_out.output_entity)
                    logger.info("Semantic profile built via LLM")
            except Exception as exc:
                logger.warning("LLM semantic profiling failed, falling back: %s", exc)

        if self.semantic_profile is None:
            from ..services.article_enrichment import build_article_semantic_profile
            self.semantic_profile = build_article_semantic_profile(self.article_model)

        self._build_article_field_position()

    def _build_article_field_position(self):
        """Run article_field_positioner. LLM if available, deterministic otherwise."""
        import logging
        logger = logging.getLogger(__name__)
        if self.article_model is None:
            return

        from ..agents.article_field_positioner import ArticleFieldPositionerAgent
        from ..agents.contract import AgentInput as _AI

        agent = ArticleFieldPositionerAgent()
        entities: dict[str, Any] = {"article": self.article_model.to_dict()}
        if self.semantic_profile is not None:
            entities["semantic_profile"] = self.semantic_profile.to_dict()
        inp = _AI(
            operation_id="article_field_position",
            agent_role_id="article_field_positioner",
            entities=entities,
            raw_text=getattr(self, "_llm_input_text", None) or self.input_text,
        )
        provider = _get_llm_provider()
        try:
            if provider is not None:
                out = agent.execute(inp, provider)
            else:
                out = agent.execute_deterministic(inp)
        except Exception as exc:
            logger.warning("Article field positioning failed: %s", exc)
            return
        if out.output_entity:
            try:
                self.article_field_position = FieldPositionModel.from_dict(out.output_entity)
                logger.info("Article FPM built (%s)", out.confidence)
            except Exception as exc:
                logger.warning("Failed to deserialize article FPM: %s", exc)

    def _enrich_article(self, search_depth: str) -> dict[str, Any]:
        """Run web enrichment on article_model. Returns enrichment metadata."""
        import logging
        logger = logging.getLogger(__name__)

        from ..search.provider import SearchDepth
        try:
            depth = SearchDepth(search_depth)
        except ValueError:
            logger.warning("Invalid search_depth '%s', skipping enrichment", search_depth)
            return {}

        if depth == SearchDepth.NONE:
            return {}

        provider = _get_llm_provider()
        if provider is None:
            logger.warning("Web enrichment requires LLM provider, skipping")
            return {"status": "skipped", "reason": "no_llm_provider"}

        from ..search.duckduckgo import get_search_provider
        from ..services.web_enrichment import enrich_article_model

        search = get_search_provider()
        article_dict = self.article_model.to_dict()

        try:
            enriched = enrich_article_model(article_dict, search, provider, depth)
        except Exception as exc:
            logger.warning("Web enrichment failed: %s", exc)
            return {"status": "failed", "reason": str(exc)}

        # Apply enrichment back to ArticleModel
        enrichment_meta = enriched.pop("_enrichment", {})
        updated_fields = enrichment_meta.get("fields_updated", [])
        if updated_fields:
            self.article_model = ArticleModel.from_dict(enriched)
            logger.info("Article enriched via web search: %s", updated_fields)

        return {
            "status": "done",
            "depth": search_depth,
            "fields_updated": updated_fields,
            "unknowns_resolved": enrichment_meta.get("unknowns_resolved", []),
            "verification_notes": enrichment_meta.get("verification_notes", []),
        }

    # -- Venue investigation --

    def investigate_venue(self, text: str) -> dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)

        provider = _get_llm_provider()
        venue = None
        regime = None

        if provider is not None:
            from ..agents.venue_profiler import VenueProfilerAgent
            from ..agents.contract import AgentInput
            agent = VenueProfilerAgent()
            inp = AgentInput(
                operation_id="investigate_venue",
                agent_role_id="venue_profiler",
                raw_text=text,
            )
            try:
                output = agent.execute(inp, provider)
                if output.output_entity:
                    entity = output.output_entity
                    regime_dict = entity.pop("_regime", None)
                    venue = VenueModel.from_dict(entity)
                    if regime_dict:
                        regime = PublicationRegimeModel.from_dict(regime_dict)
                    logger.info("Venue profiled via LLM")
            except Exception as exc:
                logger.warning("LLM venue profiling failed, falling back: %s", exc)

        if venue is None:
            from ..services.venue_profiling import build_venue_model
            venue, regime = build_venue_model(text)

        self.investigated_venue = venue
        self.publication_regime = regime
        self._build_venue_field_position(venue, guidelines_text=text)
        self._log_decision("investigate_venue", {
            "venue_name": venue.canonical_name,
        })
        return {
            "venue": venue.to_dict(),
            "publication_regime": regime.to_dict(),
        }

    def _build_venue_field_position(
        self,
        venue: VenueModel,
        *,
        guidelines_text: str = "",
    ):
        """Run venue_field_positioner. LLM if available, deterministic otherwise."""
        import logging
        logger = logging.getLogger(__name__)
        from ..agents.venue_field_positioner import VenueFieldPositionerAgent
        from ..agents.contract import AgentInput as _AI

        agent = VenueFieldPositionerAgent()
        entities: dict[str, Any] = {
            "venue": venue.to_dict(),
            "venue_guidelines_text": guidelines_text,
        }
        inp = _AI(
            operation_id="venue_field_position",
            agent_role_id="venue_field_positioner",
            entities=entities,
            raw_text=guidelines_text,
        )
        provider = _get_llm_provider()
        try:
            if provider is not None:
                out = agent.execute(inp, provider)
            else:
                out = agent.execute_deterministic(inp)
        except Exception as exc:
            logger.warning("Venue field positioning failed: %s", exc)
            return
        if out.output_entity:
            try:
                self.venue_field_position = FieldPositionModel.from_dict(out.output_entity)
                logger.info("Venue FPM built (%s)", out.confidence)
            except Exception as exc:
                logger.warning("Failed to deserialize venue FPM: %s", exc)

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
        self._update_quality_gates("confirm_article")

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
        self._update_quality_gates("set_scenario")

        return self.scenario.to_dict()

    # -- Pathways --

    def get_pathways(self) -> list[dict[str, Any]]:
        if not self.pathways and self.semantic_profile:
            import logging
            logger = logging.getLogger(__name__)
            from ..agents.disciplinary_mapper import DisciplinaryPathwayMapperAgent
            from ..agents.contract import AgentInput
            from ..llm.attempt_metadata import (
                FALLBACK_REASON_PROVIDER_ERROR,
                LLMAttemptMetadata,
            )
            agent = DisciplinaryPathwayMapperAgent()
            am_dict = self.article_model.to_dict() if self.article_model else {}
            inp = AgentInput(
                operation_id="pathway_map",
                agent_role_id="disciplinary_pathway_mapper",
                entities={
                    "article": am_dict,
                    "semantic_profile": self.semantic_profile.to_dict(),
                },
            )
            case_level_attempt: LLMAttemptMetadata | None = None
            provider = _get_llm_provider()
            if provider is not None:
                try:
                    output = agent.execute(inp, provider)
                    logger.info("Pathways mapped via LLM")
                except Exception as exc:
                    logger.warning("LLM pathway mapping failed, falling back: %s", exc)
                    case_level_attempt = LLMAttemptMetadata.fallback(
                        reason=FALLBACK_REASON_PROVIDER_ERROR,
                        provider="openai_compatible",
                        validation_errors=[str(exc)[:240]],
                    )
                    output = agent.execute_deterministic(inp)
            else:
                case_level_attempt = LLMAttemptMetadata.not_attempted()
                output = agent.execute_deterministic(inp)

            if output.output_entity:
                raw = output.output_entity.get("pathways", [])
                # If we hit a case-level fallback that the agent didn't
                # know about, stamp every pathway with the metadata.
                if case_level_attempt is not None:
                    meta_dict = case_level_attempt.to_dict()
                    for p in raw:
                        if isinstance(p, dict) and not p.get("extraction_attempt"):
                            p["extraction_attempt"] = meta_dict
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

    def discover_venues(self) -> dict[str, Any]:
        if not self.pathways:
            return {"candidates": [], "status": "no_pathways"}

        from ..agents.venue.venue_discovery import VenueDiscoveryAgent
        from ..agents.contract import AgentInput

        seed_venues: list[str] = []
        scenario_dict = self.scenario.to_dict() if self.scenario else {}

        agent = VenueDiscoveryAgent()
        inp = AgentInput(
            operation_id="discover_venues",
            agent_role_id="venue_discovery",
            entities={
                "disciplinary_pathways": [
                    p.to_dict() if hasattr(p, "to_dict") else p
                    for p in self.pathways
                ],
                "scenario": scenario_dict,
                "seed_venues": seed_venues,
            },
        )
        provider = _get_llm_provider()
        if provider is not None:
            import logging
            logger = logging.getLogger(__name__)
            try:
                output = agent.execute(inp, provider)
                logger.info("Venues discovered via LLM")
            except Exception:
                logger.warning("LLM venue discovery failed, falling back")
                output = agent.execute_deterministic(inp)
        else:
            output = agent.execute_deterministic(inp)
        if output.output_entity:
            raw = output.output_entity
            pool_data = raw.get("pool", raw) if isinstance(raw, dict) else raw
            if isinstance(pool_data, dict):
                known_keys = {f.name for f in __import__("dataclasses").fields(VenueCandidatePool)}
                filtered = {k: v for k, v in pool_data.items() if k in known_keys}
                self.venue_pool = VenueCandidatePool(**filtered)
            else:
                self.venue_pool = pool_data

        self.stage = CaseStage.VENUE_POOL
        self._log_decision("discover_venues", {
            "candidate_count": len(self.venue_pool.candidates) if self.venue_pool else 0,
        })
        self._update_quality_gates("discover_venues")

        return self.get_venue_pool()

    def get_venue_pool(self) -> dict[str, Any]:
        if self.venue_pool:
            return self.venue_pool.to_dict()
        return {"candidates": [], "status": "not_discovered"}

    # -- Select venue & fit --

    def select_venue(self, venue_id: str) -> dict[str, Any]:
        # Resolve candidate from pool
        candidate_dict = self._resolve_candidate(venue_id)
        if candidate_dict:
            self.selected_venue = self._venue_model_from_candidate(candidate_dict)
        self.stage = CaseStage.VENUE_SELECTED
        self._log_decision("select_venue", {"venue_id": venue_id})

        # Build venue FPM for the selected venue (if not already produced)
        if self.selected_venue is not None and self.venue_field_position is None:
            self._build_venue_field_position(self.selected_venue)

        # Auto-run fit → mismatch → rewrite chain
        if self.selected_venue and self.article_model:
            self._run_fit_chain()

        self._update_quality_gates("venue_selected")

        return {
            "selected_venue_id": venue_id,
            "stage": self.stage.value,
            "fit_available": self.fit_assessment is not None,
            "mismatch_count": (
                len(self.mismatch_map.mismatches)
                if self.mismatch_map and hasattr(self.mismatch_map, "mismatches")
                else 0
            ),
            "rewrite_plan_available": self.rewrite_plan is not None,
        }

    def _resolve_candidate(self, venue_id: str) -> dict[str, Any] | None:
        if not self.venue_pool:
            return None
        candidates = (
            self.venue_pool.candidates
            if hasattr(self.venue_pool, "candidates")
            else []
        )
        for c in candidates:
            cid = c.get("venue_candidate_id", "") if isinstance(c, dict) else getattr(c, "venue_candidate_id", "")
            if cid == venue_id:
                return c if isinstance(c, dict) else c.to_dict()
        # Fallback: take first candidate if ID not found
        if candidates:
            first = candidates[0]
            return first if isinstance(first, dict) else first.to_dict()
        return None

    def _venue_model_from_candidate(self, candidate: dict[str, Any]) -> VenueModel:
        raw = candidate.get("raw_adapter_data", {})
        first_source = next(iter(raw.values()), {}) if raw else {}
        topics = first_source.get("topics", [])
        scope = ", ".join(topics) if topics else None
        return VenueModel(
            canonical_name=candidate.get("canonical_name", ""),
            venue_type=first_source.get("type", "journal"),
            official_urls=candidate.get("urls", []),
            scope_summary=scope,
            publisher_or_owner=first_source.get("publisher"),
            confidence=candidate.get("confidence", "low"),
            unknowns=candidate.get("unknowns", []),
            source_refs=candidate.get("sources", []),
        )

    def _run_fit_chain(self):
        import logging
        logger = logging.getLogger(__name__)
        from ..services.fit_assessment import assess_fit
        from ..services.mismatch_mapping import build_mismatch_map
        from ..services.rewrite_planning import build_rewrite_plan

        scenario = self.scenario or SubmissionScenario(
            article_model_id=self.article_model.article_model_id
            if self.article_model else "",
        )

        provider = _get_llm_provider()
        fit_via_llm = False

        if provider is not None:
            from ..agents.fit_assessor import FitAssessorAgent
            from ..agents.contract import AgentInput
            agent = FitAssessorAgent()
            inp = AgentInput(
                operation_id="fit_assess",
                agent_role_id="fit_assessor",
                entities={
                    "article": self.article_model.to_dict(),
                    "venue": self.selected_venue.to_dict(),
                    "scenario": scenario.to_dict(),
                },
            )
            try:
                output = agent.execute(inp, provider)
                if output.output_entity:
                    self.fit_assessment = FitAssessment.from_dict(output.output_entity)
                    fit_via_llm = True
                    logger.info("Fit assessed via LLM")
            except Exception as exc:
                logger.warning("LLM fit assessment failed, falling back: %s", exc)

        if not fit_via_llm:
            try:
                self.fit_assessment = assess_fit(
                    self.article_model, self.selected_venue, scenario,
                )
            except Exception:
                return

        self.stage = CaseStage.FIT_ASSESSED
        self._log_decision("fit_assessed", {
            "overall_label": self.fit_assessment.overall_label,
            "axes_count": len(self.fit_assessment.axes),
        })

        # FPM-based fit, parallel to legacy fit. Computed when both FPMs present.
        if (
            self.article_field_position is not None
            and self.venue_field_position is not None
        ):
            try:
                from ..logic.field_position_fit import compute_field_position_fit
                self.field_position_fit = compute_field_position_fit(
                    self.article_field_position.to_dict(),
                    self.venue_field_position.to_dict(),
                )
                logger.info(
                    "FPM fit computed (%s)",
                    self.field_position_fit.get("overall_label"),
                )
                self._log_decision("fpm_fit_computed", {
                    "overall_label": self.field_position_fit.get("overall_label"),
                    "summary": self.field_position_fit.get("summary"),
                })
            except Exception as exc:
                logger.warning("FPM fit computation failed: %s", exc)

        try:
            self.mismatch_map = build_mismatch_map(self.fit_assessment)
            self._log_decision("mismatch_mapped", {
                "mismatch_count": len(self.mismatch_map.mismatches),
                "summary": self.mismatch_map.summary,
            })
        except Exception:
            return

        if self.mismatch_map.mismatches:
            try:
                self.rewrite_plan = build_rewrite_plan(
                    self.mismatch_map,
                    article_model_id=(
                        self.article_model.article_model_id
                        if self.article_model else None
                    ),
                    venue_model_id=(
                        self.selected_venue.venue_model_id
                        if self.selected_venue else None
                    ),
                )
                self.stage = CaseStage.ADAPTING
                self._log_decision("rewrite_planned", {
                    "changes_count": len(self.rewrite_plan.changes),
                    "effort": self.rewrite_plan.estimated_effort,
                })
                # Sprint α B3: pass the plan through the policy gate
                try:
                    from ..services.protected_core import apply_policy_gate
                    policy = self.ensure_protected_core_policy()
                    if policy.forbidden_moves:
                        gated, blocked = apply_policy_gate(self.rewrite_plan, policy)
                        self.rewrite_plan = gated
                        self.policy_blocked_changes = blocked
                        if blocked:
                            self._log_decision("policy_gate_blocked", {
                                "blocked_count": len(blocked),
                                "moves": sorted({m for b in blocked for m in b.get("matched_moves", [])}),
                            })
                except Exception as exc:
                    logger.warning("Policy gate failed (non-fatal): %s", exc)
            except Exception:
                pass

        self._update_quality_gates("fit_chain")

    def get_fit(self) -> dict[str, Any]:
        if self.fit_assessment:
            result = self.fit_assessment.to_dict()
            if self.field_position_fit is not None:
                result["field_position_fit"] = self.field_position_fit
            return result
        return {"status": "not_assessed"}

    def get_source_evidence_packet(self) -> dict[str, Any]:
        """Build (or rebuild) the SourceEvidencePacket from current case state.

        Lazy: rebuilds every call so the packet always reflects the latest
        input_text / investigated_venue / selected_venue. Deterministic, no LLM.
        """
        from ..services.source_evidence_packet import build_packet_from_case
        self.source_evidence_packet = build_packet_from_case(self)
        return self.source_evidence_packet.to_dict()

    def ensure_protected_core_policy(self) -> ProtectedCorePolicy:
        """Return a ProtectedCorePolicy, deriving one from ArticleModel if missing."""
        if self.protected_core_policy is not None:
            return self.protected_core_policy
        from ..services.protected_core import policy_from_article
        article = self.article_model
        self.protected_core_policy = policy_from_article(
            article_model_id=article.article_model_id if article else None,
            protected_core=article.protected_core if article else [],
            mutable_zones=article.mutable_zones if article else [],
        )
        return self.protected_core_policy

    def get_protected_core_policy(self) -> dict[str, Any]:
        return self.ensure_protected_core_policy().to_dict()

    def set_protected_core_policy(self, data: dict[str, Any]) -> dict[str, Any]:
        """Author or update the ProtectedCorePolicy from operator input."""
        existing = self.ensure_protected_core_policy().to_dict()
        existing.update({k: v for k, v in data.items() if v is not None})
        self.protected_core_policy = ProtectedCorePolicy.from_dict(existing)
        return self.protected_core_policy.to_dict()

    def get_evidence_policy(self) -> dict[str, Any]:
        if self.evidence_policy is None:
            self.evidence_policy = EvidencePolicy(case_id=self.case_id)
        return self.evidence_policy.to_dict()

    def get_field_positions(self) -> dict[str, Any]:
        return {
            "article_field_position": (
                self.article_field_position.to_dict()
                if self.article_field_position else None
            ),
            "venue_field_position": (
                self.venue_field_position.to_dict()
                if self.venue_field_position else None
            ),
            "field_position_fit": self.field_position_fit,
        }

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
        if self.article_field_position:
            dossier["article_field_position"] = self.article_field_position.to_dict()
        if self.venue_field_position:
            dossier["venue_field_position"] = self.venue_field_position.to_dict()
        if self.field_position_fit is not None:
            dossier["field_position_fit"] = self.field_position_fit

        dossier["decision_log"] = self.decision_log
        dossier["quality_gates"] = self.quality_gates

        return dossier

    # -- Decision log --

    def _update_quality_gates(self, trigger: str = ""):
        gates: dict[str, dict[str, Any]] = {}

        if self.article_model:
            has_core = bool(self.article_model.protected_core)
            gates["article_model"] = {
                "gate_name": "Article Model",
                "status": "pass" if has_core else "warning",
                "message": (
                    "Confirmed with protected core"
                    if has_core else "No protected core defined"
                ),
            }

        if self.scenario:
            gates["scenario"] = {
                "gate_name": "Submission Scenario",
                "status": "pass",
                "message": f"Goal: {self.scenario.goal or 'set'}",
            }

        if self.venue_pool:
            n = len(self.venue_pool.candidates) if hasattr(self.venue_pool, "candidates") else 0
            gates["venue_pool"] = {
                "gate_name": "Venue Pool",
                "status": "pass" if n > 0 else "fail",
                "message": f"{n} candidate(s) discovered",
            }

        if self.fit_assessment:
            label = self.fit_assessment.overall_label
            gates["fit_assessment"] = {
                "gate_name": "Fit Assessment",
                "status": "pass" if label != "poor" else "warning",
                "message": f"Overall: {label}",
            }

        if self.mismatch_map:
            n_blocking = sum(
                1 for m in self.mismatch_map.mismatches
                if m.get("severity") == "blocking"
            )
            gates["mismatch_map"] = {
                "gate_name": "Mismatch Map",
                "status": "fail" if n_blocking > 0 else "pass",
                "message": (
                    f"{n_blocking} blocking mismatch(es)"
                    if n_blocking else "No blocking mismatches"
                ),
            }

        if self.rewrite_plan:
            n_changes = len(self.rewrite_plan.changes)
            gates["rewrite_plan"] = {
                "gate_name": "Rewrite Plan",
                "status": "pass" if n_changes > 0 else "warning",
                "message": f"{n_changes} change(s), effort: {self.rewrite_plan.estimated_effort}",
            }

        self.quality_gates = gates

    def _log_decision(self, action: str, details: dict[str, Any]):
        self.decision_log.append({
            "action": action,
            "details": details,
            "timestamp": _now(),
        })


class CaseStore:
    """File-backed case store with user partitioning.

    Layout:
      ${data_dir}/cases/<case_id>.json
          legacy / system / demo cases (user_id = None)
      ${data_dir}/users/<user_id>/cases/<case_id>.json
          user-owned cases (user_id != None)

    Read API supports optional `user_id` scoping:
      - `user_id=None` (legacy mode): all cases, unrestricted. Used by
        existing tests and CLI tooling.
      - `user_id='user_xxx'`: only cases owned by that user. Used by
        the auth-protected HTTP endpoints.
    """

    def __init__(self, data_dir: str | None = None):
        import os
        from pathlib import Path
        raw = data_dir or os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion"
        self._root = Path(raw)
        self._dir = self._root / "cases"  # legacy/system cases live here
        self._users_dir = self._root / "users"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._users_dir.mkdir(parents=True, exist_ok=True)
        self._cases: dict[str, Case] = {}
        self._load_all()

    def _case_path(self, case_id: str, user_id: str | None = None):
        from pathlib import Path
        if user_id:
            d = self._users_dir / user_id / "cases"
            d.mkdir(parents=True, exist_ok=True)
            return d / f"{case_id}.json"
        return self._dir / f"{case_id}.json"

    def _load_all(self):
        import json, logging
        logger = logging.getLogger(__name__)
        # Legacy/system cases (no user_id)
        for p in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                case = _case_from_snapshot(data)
                self._cases[case.case_id] = case
            except Exception as exc:
                logger.warning("Failed to load case %s: %s", p.name, exc)
        # User-scoped cases — walk users/<user_id>/cases/
        if self._users_dir.exists():
            for udir in sorted(self._users_dir.glob("*/cases")):
                for p in sorted(udir.glob("*.json")):
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        case = _case_from_snapshot(data)
                        # Defensive: ensure user_id reflects directory location
                        if not case.user_id:
                            case.user_id = udir.parent.name
                        self._cases[case.case_id] = case
                    except Exception as exc:
                        logger.warning(
                            "Failed to load user case %s: %s", p.name, exc,
                        )

    def create(self, title: str = "", user_id: str | None = None) -> Case:
        case = Case(title=title, user_id=user_id)
        self._cases[case.case_id] = case
        self._persist(case)
        return case

    def get(self, case_id: str, user_id: str | None = None) -> Case | None:
        """Return the case if accessible to caller.

        Scoping rules:
          - `user_id=None` (legacy): return whatever is in the store.
          - `user_id='user_xxx'`: return only if the case's user_id
            matches. Cross-tenant access is silently None.
        """
        c = self._cases.get(case_id)
        if c is None:
            return None
        if user_id is None:
            return c
        if c.user_id == user_id:
            return c
        return None

    def all(self, user_id: str | None = None) -> list[Case]:
        if user_id is None:
            return list(self._cases.values())
        return [c for c in self._cases.values() if c.user_id == user_id]

    def delete(self, case_id: str, user_id: str | None = None) -> bool:
        c = self._cases.get(case_id)
        if c is None:
            return False
        # Scope check on delete: callers with a user_id may only delete
        # their own.
        if user_id is not None and c.user_id != user_id:
            return False
        path = self._case_path(case_id, c.user_id)
        self._cases.pop(case_id, None)
        path.unlink(missing_ok=True)
        return True

    def save(self, case: Case):
        self._cases[case.case_id] = case
        self._persist(case)

    def _persist(self, case: Case):
        import json, logging
        logger = logging.getLogger(__name__)
        path = self._case_path(case.case_id, case.user_id)
        snapshot = _case_to_snapshot(case)
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(snapshot, ensure_ascii=False, default=str, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception as exc:
            logger.error("Failed to persist case %s: %s", case.case_id, exc)


def _case_to_snapshot(case: Case) -> dict[str, Any]:
    """Serialize full Case state to a JSON-safe dict."""
    snap: dict[str, Any] = {
        "case_id": case.case_id,
        "title": case.title,
        "created_at": case.created_at,
        "stage": case.stage.value if isinstance(case.stage, CaseStage) else case.stage,
        "user_id": case.user_id,
        "input_text": case.input_text,
        "input_type": case.input_type,
        "decision_log": case.decision_log,
        "quality_gates": case.quality_gates,
    }
    for attr, key in [
        ("article_model", "article_model"),
        ("semantic_profile", "semantic_profile"),
        ("scenario", "scenario"),
        ("venue_pool", "venue_pool"),
        ("selected_venue", "selected_venue"),
        ("fit_assessment", "fit_assessment"),
        ("mismatch_map", "mismatch_map"),
        ("rewrite_plan", "rewrite_plan"),
        ("citation_plan", "citation_plan"),
        ("risk_report", "risk_report"),
        ("publication_regime", "publication_regime"),
        ("investigated_venue", "investigated_venue"),
        ("article_field_position", "article_field_position"),
        ("venue_field_position", "venue_field_position"),
        ("source_evidence_packet", "source_evidence_packet"),
        ("protected_core_policy", "protected_core_policy"),
        ("evidence_policy", "evidence_policy"),
    ]:
        obj = getattr(case, attr, None)
        if obj is not None:
            snap[key] = obj.to_dict() if hasattr(obj, "to_dict") else obj

    if case.pathways:
        snap["pathways"] = [
            p.to_dict() if hasattr(p, "to_dict") else p
            for p in case.pathways
        ]

    if case.field_position_fit is not None:
        snap["field_position_fit"] = case.field_position_fit

    if case.policy_blocked_changes:
        snap["policy_blocked_changes"] = case.policy_blocked_changes

    return snap


def _case_from_snapshot(data: dict[str, Any]) -> Case:
    """Deserialize a snapshot dict back into a Case object."""
    case = Case(
        case_id=data["case_id"],
        title=data.get("title", ""),
        user_id=data.get("user_id"),
    )
    case.created_at = data.get("created_at", case.created_at)
    stage_val = data.get("stage", "empty")
    try:
        case.stage = CaseStage(stage_val)
    except ValueError:
        case.stage = CaseStage.EMPTY
    case.input_text = data.get("input_text", "")
    case.input_type = data.get("input_type", "")
    case.decision_log = data.get("decision_log", [])
    case.quality_gates = data.get("quality_gates", {})

    model_map = {
        "article_model": ArticleModel,
        "semantic_profile": ArticleSemanticProfile,
        "scenario": SubmissionScenario,
        "venue_pool": VenueCandidatePool,
        "selected_venue": VenueModel,
        "fit_assessment": FitAssessment,
        "mismatch_map": MismatchMap,
        "rewrite_plan": RewritePlan,
        "citation_plan": CitationPlan,
        "risk_report": RiskReport,
        "publication_regime": PublicationRegimeModel,
        "investigated_venue": VenueModel,
        "article_field_position": FieldPositionModel,
        "venue_field_position": FieldPositionModel,
        "source_evidence_packet": SourceEvidencePacket,
        "protected_core_policy": ProtectedCorePolicy,
        "evidence_policy": EvidencePolicy,
    }
    for key, cls in model_map.items():
        raw = data.get(key)
        if raw is not None and isinstance(raw, dict):
            try:
                setattr(case, key, cls.from_dict(raw))
            except Exception:
                pass

    fpm_fit = data.get("field_position_fit")
    if isinstance(fpm_fit, dict):
        case.field_position_fit = fpm_fit

    pbc = data.get("policy_blocked_changes")
    if isinstance(pbc, list):
        case.policy_blocked_changes = pbc

    raw_pathways = data.get("pathways", [])
    for p in raw_pathways:
        if isinstance(p, dict):
            try:
                case.pathways.append(DisciplinaryPathway(**p))
            except Exception:
                case.pathways.append(p)
        else:
            case.pathways.append(p)

    return case


def _classify_input(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["reviewer", "revision", "reject", "resubmit", "referee"]):
        return "review_letter"
    if any(k in lower for k in ["issn", "author guidelines", "scope of the journal"]):
        return "venue"
    if len(text) < 500:
        return "abstract"
    return "manuscript"
