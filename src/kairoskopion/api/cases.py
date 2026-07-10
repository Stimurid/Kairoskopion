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
    BibliographyProfile,
    ComplianceChecklist,
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
    SubmissionPack,
    SubmissionScenario,
    VenueCandidatePool,
    VenueModel,
    VenueProfilePackage,
    _now,
)
from ..enums import (
    EvidenceStatus,
    LifecycleStatus,
)
from ..llm.config import LLMConfig
from ..llm.input_limits import LLM_INPUT_CHAR_CAP, cap_llm_input
from ..llm.openai_compat import OpenAICompatProvider
from ..registry.integration import RegistryIntegrationService

import logging

logger = logging.getLogger(__name__)


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


def _get_llm_provider(role_id: str | None = None) -> OpenAICompatProvider | None:
    """Construct a provider for a specific agent role.

    Per-call routing seam (Track C, intake-choice-and-routing-seam):
    when ``KAIROSKOPION_LLM_MODEL_<ROLE>`` env var is set, the per-role
    config supplies a different model alias while reusing the global
    provider/base_url/api_key/timeout/retries. ``role_id=None`` falls
    through to the global model.
    """
    cfg = LLMConfig.for_role(role_id) if role_id else LLMConfig.from_env()
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
        registry_service: RegistryIntegrationService | None = None,
    ):
        self.case_id = case_id or generate_id("case")
        self.title = title or "Новый кейс"
        self.created_at = _now()
        self.stage = CaseStage.EMPTY
        self.user_id: str | None = user_id
        self._registry = registry_service or RegistryIntegrationService()
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
        # V2-D minimal-real lanes
        self.compliance_checklist: ComplianceChecklist | None = None
        self.submission_pack: SubmissionPack | None = None
        # V2-E: BibliographyProfile slot + preserved article raw text
        # so the parser can read the article body after venue intake
        # has clobbered self.input_text.
        self.bibliography_profile: BibliographyProfile | None = None
        self.article_input_text: str = ""
        # Round III-H: upload metadata persisted on the case so the
        # human dossier source header and technical footer can show
        # what file the analysis was built from. Set by the intake/file
        # route; remains None for text-only intakes.
        self.upload_metadata: dict[str, Any] | None = None
        # Round III-J3: cache of Russian surface translations for
        # English upstream semantic fields. Keyed by a stable
        # sha256(field_path + value + prompt_version) hash. Populated
        # by the russian_surface narrator pass; the renderer reads it.
        # No raw LLM body is stored — only the validated Russian text.
        self.russian_surface_cache: dict[str, Any] = {}
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
        # M-8: LLM refinement chat history
        self.refinement_chat: list[dict[str, Any]] = []

        # Phase 1: source acquisition metadata for venue intake
        self.venue_source_metadata: dict[str, Any] | None = None
        # Phase 1: adapter mode override (default = offline_stub)
        self.adapter_mode: str = "offline_stub"
        # Phase 2: aggregated venue profile package
        self.venue_profile_package: VenueProfilePackage | None = None
        # Phase 3: discipline intent (standalone Track A entry)
        self.discipline_intent: dict[str, Any] | None = None
        # Phase 3: venue family context (cross-track)
        self.venue_family_context: dict[str, Any] | None = None
        # Phase 5: depth mode and budget
        self.depth_mode: str = "standard"
        self.budget_constraints: dict[str, Any] | None = None

        # Track A (intake-choice-and-routing-seam): user-choice override
        # state. ``classifier_input_type`` / ``classifier_confidence`` /
        # ``classifier_needs_user_choice`` preserve the AUTO classifier
        # verdict for audit. ``user_selected_input_type`` is what the
        # operator chose via the UI chip flow. ``effective_input_type``
        # is what the pipeline actually used. ``override_source`` is
        # ``"classifier"`` / ``"user"`` / ``"chip"`` (chip = the user
        # picked the chip on first submit and skipped the classifier).
        # ``override_at`` is an ISO timestamp.
        self.classifier_input_type: str | None = None
        self.classifier_confidence: str | None = None
        self.classifier_needs_user_choice: bool = False
        self.user_selected_input_type: str | None = None
        self.effective_input_type: str | None = None
        self.override_source: str = "classifier"
        self.override_at: str | None = None

        # Phase B2: matched disciplines from the registry-driven matcher.
        # Populated by DisciplineMatcherAgent in _build_article_model
        # BEFORE semantic_profile so the profiler gets a narrowed
        # known_disciplines_context instead of the implicit keyword
        # pre-filter fallback.
        self.discipline_matches: dict[str, Any] | None = None
        # Operator hint: region of work — drives matcher slice.
        # Pulled from intake_text(region=...) or defaults to "auto".
        self.region_hint: str = "auto"

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
        if self.discipline_matches:
            matched_count = len(self.discipline_matches.get("matched") or [])
            result["discipline_matches_count"] = matched_count
            result["region_hint"] = self.region_hint
        return result

    # -- Intake --

    def intake_text(
        self,
        text: str,
        input_type: str = "auto",
        search_depth: str = "none",
        region: str = "auto",
    ) -> dict[str, Any]:
        self.input_text = text
        # Operator hint persists for downstream matcher runs in this case
        self.region_hint = (region or "auto").strip() or "auto"
        # Cap the LLM-bound projection once per intake. The original full
        # text stays on self.input_text for deterministic processing and
        # persistence; only the prompt-facing copy is clipped.
        capped, truncation = cap_llm_input(text, LLM_INPUT_CHAR_CAP)
        self._llm_input_text = capped
        self._llm_input_truncation = truncation

        # Classification path: LLM agent if provider available, else
        # ask the user. Explicit override from the UI chip skips the
        # classifier entirely.
        classification_result: dict[str, Any] | None = None
        if input_type != "auto":
            self.input_type = input_type
            self.user_selected_input_type = input_type
            self.override_source = "chip"
            self.override_at = _now()
        else:
            classification_result = self._classify_input_llm(text)
            self.input_type = classification_result["input_type"]
            # Preserve classifier verdict for audit and override resolution.
            self.classifier_input_type = classification_result.get("input_type")
            self.classifier_confidence = classification_result.get("confidence")
            self.classifier_needs_user_choice = bool(
                classification_result.get("needs_user_choice")
            )
            self.override_source = "classifier"

        # ``effective_input_type`` is the routing key. Initially equals
        # the classifier verdict / chip; if the user later POSTs to
        # /intake/override it gets reassigned and the pipeline reruns.
        self.effective_input_type = self.input_type

        self.stage = CaseStage.INTAKE

        enrichment_result: dict[str, Any] = {}

        # Routing centralised in the classifier prompt module so the
        # set of types and their routes stay consistent across LLM
        # output, validator, agent, and intake.
        from ..prompts.input_classification import (
            ARTICLE_PIPELINE_TYPES,
            NEEDS_USER_CHOICE_TYPES,
            VENUE_PIPELINE_TYPES,
        )
        venue_result: dict[str, Any] | None = None
        if self.effective_input_type in ARTICLE_PIPELINE_TYPES:
            # V2-E: preserve raw article text so BibliographyProfile
            # parser can read it after a later venue intake has
            # overwritten self.input_text.
            self.article_input_text = text
            self._build_article_model()
            if search_depth != "none" and self.article_model is not None:
                enrichment_result = self._enrich_article(search_depth)
        elif self.effective_input_type in VENUE_PIPELINE_TYPES:
            try:
                venue_result = self.investigate_venue(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Venue investigation during intake failed: %s", exc)
        elif self.effective_input_type in NEEDS_USER_CHOICE_TYPES:
            # bibliography / field_notes / review_letter / mixed / unknown
            # — no automated pipeline. Save the text on the case so the
            # UI can re-submit after the user picks a chip; do not run
            # ArticleModeler on a thesis dump or a reference list.
            pass

        result: dict[str, Any] = {
            "input_type": self.input_type,
            "effective_input_type": self.effective_input_type,
            "text_length": len(text),
            "article_model_built": self.article_model is not None,
            "venue_investigated": self.investigated_venue is not None,
            "stage": self.stage.value,
            "override_source": self.override_source,
        }
        if classification_result is not None:
            # Surface the LLM classifier verdict to the UI so it can
            # raise a "confirm type" banner instead of silently routing.
            result["classification"] = classification_result
            if classification_result.get("needs_user_choice"):
                result["needs_user_choice"] = True
        if truncation.truncated:
            result["input_truncated_for_llm"] = truncation.to_dict()
        if enrichment_result:
            result["enrichment"] = enrichment_result
        # F3/F5 (venue honesty pass): pass through the venue-investigation
        # outcome so the UI can render the needs_more_venue_text hint,
        # the used_llm fallback badge, and the venue_field_position
        # unknowns. Without this propagation the UI silently saw
        # venue_investigated=False with no hint why.
        if venue_result is not None:
            if venue_result.get("status") == "needs_more_venue_text":
                result["venue_status"] = "needs_more_venue_text"
                result["venue_hint"] = venue_result.get("hint")
                result["venue_min_chars"] = venue_result.get("min_chars")
                result["venue_received_chars"] = venue_result.get("received_chars")
            else:
                result["venue_used_llm"] = venue_result.get("used_llm")
                if venue_result.get("venue_field_position") is not None:
                    fpm = venue_result["venue_field_position"]
                    # Surface only the warning fields, not full FPM —
                    # the UI fetches the full FPM via /investigated-venue.
                    fpm_unknowns = fpm.get("unknowns") if isinstance(fpm, dict) else None
                    if fpm_unknowns:
                        result["venue_field_position_unknowns"] = fpm_unknowns
        return result

    def apply_input_override(self, chosen_type: str) -> dict[str, Any]:
        """Operator picks a different input_type than the classifier did
        (or confirms an ambiguous one). Reruns the pipeline with the
        chosen type. Preserves the original classifier verdict for audit.

        Returns the same result shape as ``intake_text``.
        """
        from ..prompts.input_classification import (
            ARTICLE_PIPELINE_TYPES,
            NEEDS_USER_CHOICE_TYPES,
            VENUE_PIPELINE_TYPES,
        )

        # All known types — accept anything the classifier might return
        # OR a chip the user pressed (chips use the same vocabulary).
        valid_types = (
            ARTICLE_PIPELINE_TYPES | VENUE_PIPELINE_TYPES
            | NEEDS_USER_CHOICE_TYPES
        )
        if chosen_type not in valid_types:
            raise ValueError(f"Unknown input_type: {chosen_type!r}")

        # Clear any prior pipeline output so the override-driven rerun
        # starts from a clean slate. We preserve input_text + classifier
        # audit trail + region_hint; everything semantic gets rebuilt.
        self.article_model = None
        self.semantic_profile = None
        self.discipline_matches = None
        self.investigated_venue = None
        self.publication_regime = None
        self.article_field_position = None

        self.user_selected_input_type = chosen_type
        self.effective_input_type = chosen_type
        self.input_type = chosen_type  # legacy alias kept in sync
        self.override_source = "user"
        self.override_at = _now()

        text = self.input_text or ""
        capped, truncation = cap_llm_input(text, LLM_INPUT_CHAR_CAP)
        self._llm_input_text = capped
        self._llm_input_truncation = truncation

        enrichment_result: dict[str, Any] = {}
        self.stage = CaseStage.INTAKE
        if chosen_type in ARTICLE_PIPELINE_TYPES:
            self._build_article_model()
        elif chosen_type in VENUE_PIPELINE_TYPES:
            try:
                self.investigate_venue(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Venue investigation after user choice failed: %s", exc)
        # NEEDS_USER_CHOICE_TYPES selected by user means the user
        # explicitly chose to NOT run a pipeline (e.g. "treat as
        # field notes, no analysis yet"). Don't run anything.

        result: dict[str, Any] = {
            "input_type": self.input_type,
            "effective_input_type": self.effective_input_type,
            "classifier_input_type": self.classifier_input_type,
            "classifier_confidence": self.classifier_confidence,
            "user_selected_input_type": self.user_selected_input_type,
            "override_source": self.override_source,
            "override_at": self.override_at,
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

    def _classify_input_llm(self, text: str) -> dict[str, Any]:
        """Run InputClassifierAgent — LLM if provider available, else
        deterministic fallback (which returns unknown + needs_user_choice).

        Maps the classifier's output_entity to the legacy input_type
        vocabulary expected by intake_text. Specifically, 'manuscript'
        from the classifier is treated as the legacy 'manuscript' label.
        """
        from ..agents.contract import AgentInput
        from ..agents.input_classifier import InputClassifierAgent

        agent = InputClassifierAgent()
        ag_input = AgentInput(
            operation_id="intake_classify",
            agent_role_id="input_classifier",
            raw_text=text,
        )
        provider = _get_llm_provider("input_classifier")
        try:
            if provider is not None:
                output = agent.execute(ag_input, provider)
            else:
                output = agent.execute_deterministic(ag_input)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Input classifier crashed: %s", exc,
            )
            return {
                "input_type": "unknown",
                "confidence": "low",
                "needs_user_choice": True,
                "language_detected": "unknown",
                "reasoning": "Классификатор не отработал — выберите тип вручную.",
            }
        return output.output_entity or {
            "input_type": "unknown",
            "confidence": "low",
            "needs_user_choice": True,
            "language_detected": "unknown",
            "reasoning": "Классификатор не вернул результат — выберите тип.",
        }

    def _build_article_model(self):

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

        provider = _get_llm_provider("article_modeler")
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
                exc_attempts = getattr(exc, "attempts", [])
                exc_error_code = getattr(exc, "error_code", None)
                case_level_attempt = LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_PROVIDER_ERROR,
                    provider="openai_compatible",
                    validation_errors=[str(exc)[:240]],
                    attempts=exc_attempts,
                    final_error_code=exc_error_code,
                    agent_role="article_modeler",
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
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to attach extraction_attempt metadata: %s", exc)

        # Round-II: structural title fallback. Title is direct
        # source fact; deterministic extraction is allowed
        # when the modeler returned None.
        if self.article_model is not None and not self.article_model.title_current:
            try:
                import re as _re
                src = self.article_input_text or self.input_text or ""
                title_found = None
                # Try markdown heading first
                m = _re.search(r"^\s*#\s+(.+?)\s*$", src, _re.MULTILINE)
                if m:
                    title_found = m.group(1).strip()[:240]
                else:
                    # Try bold title: **Title**
                    m_bold = _re.search(r"^\s*\*\*(.+?)\*\*\s*$", src, _re.MULTILINE)
                    if m_bold:
                        candidate = m_bold.group(1).strip()
                        if 5 <= len(candidate) <= 300:
                            title_found = candidate[:240]
                    else:
                        # Try first non-empty line
                        for line in src.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            if 5 <= len(line) <= 300 and not line.endswith(('.', ',', ';', ':', '!', '?')):
                                title_found = line[:240]
                            break
                if title_found:
                    self.article_model.title_current = title_found
                    self._log_decision("structural_title_extracted", {
                        "length": len(self.article_model.title_current),
                        "origin": "source_fact_direct",
                    })
            except Exception as exc:  # noqa: BLE001
                logger.warning("Title fact tracing failed: %s", exc)

        # Auto-name the case from the article title when it's still default.
        if self.article_model and self.article_model.title_current:
            default_titles = {"Untitled case", "New case", ""}
            if self.title in default_titles:
                self.title = self.article_model.title_current[:80]

        self.stage = CaseStage.ARTICLE_MODEL

        # Phase B2: route through DisciplineMatcherAgent BEFORE
        # semantic_profile so the profiler sees registry-narrowed
        # disciplines instead of falling back to keyword pre-filter
        # implicitly. Honest fallback: if LLM unavailable, matcher
        # still emits keyword candidates marked confidence=low.
        self._run_discipline_matcher()

        # Semantic profile: try LLM agent, fall back to deterministic.
        # known_disciplines_context comes from the matcher output
        # (registry-driven) so the profiler can position the article
        # against ACTUAL discipline cards, not invented Anglo labels.
        provider = _get_llm_provider("article_semantic_profiler")
        if provider is not None:
            from ..agents.semantic_profiler import ArticleSemanticProfilerAgent
            from ..agents.contract import AgentInput as _AI
            sp_agent = ArticleSemanticProfilerAgent()
            sp_entities: dict[str, Any] = {"article": self.article_model.to_dict()}
            disc_ctx = self._build_matched_disciplines_context()
            if disc_ctx:
                sp_entities["known_disciplines_context"] = disc_ctx
            sp_inp = _AI(
                operation_id="semantic_profile",
                agent_role_id="article_semantic_profiler",
                entities=sp_entities,
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

    def _run_discipline_matcher(self) -> None:
        """Phase B2: discipline analysis via LLM when available.

        Registry substring lookup provides seed candidates only.
        When LLM provider is configured, the LLM matcher ALWAYS runs
        to produce the full ranked analysis. Registry-only results are
        used only when no LLM provider is available.
        """
        if self.article_model is None:
            return

        try:
            from ..agents.contract import AgentInput as _AI
            from ..agents.discipline_matcher import DisciplineMatcherAgent
        except Exception as exc:  # noqa: BLE001
            logger.debug("DisciplineMatcherAgent unavailable: %s", exc)
            return

        summary_parts: list[str] = []
        for k in (
            "title", "problem_statement", "object_of_inquiry",
            "core_claims", "key_terms", "disciplinary_register_current",
        ):
            v = getattr(self.article_model, k, None)
            if isinstance(v, list):
                v = "; ".join(str(x) for x in v if x)
            if v:
                summary_parts.append(f"{k}: {v}")
        summary = "\n".join(summary_parts)[:4000]

        agent = DisciplineMatcherAgent()
        inp = _AI(
            operation_id="discipline_match",
            agent_role_id="discipline_matcher",
            raw_text=summary,
            entities={
                "article_summary": summary,
                "region": self.region_hint or "auto",
            },
        )
        provider = _get_llm_provider("discipline_matcher")
        try:
            if provider is not None:
                out = agent.execute(inp, provider)
            else:
                out = agent.execute_deterministic(inp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Discipline matcher crashed: %s", exc)
            out = agent.execute_deterministic(inp)
        if out and out.output_entity:
            self.discipline_matches = out.output_entity
            if provider is not None:
                self.discipline_matches["source"] = "llm"
            logger.info(
                "Discipline matcher emitted %d matches (%s)",
                len(out.output_entity.get("matched", [])),
                out.confidence,
            )

    def rerun_discipline_analysis(self, comment: str | None = None) -> dict[str, Any]:
        """Re-run discipline matcher, optionally incorporating user comment."""
        if self.article_model is None:
            return {"error": "No article model — run intake first"}

        previous = self.discipline_matches

        try:
            from ..agents.contract import AgentInput as _AI
            from ..agents.discipline_matcher import DisciplineMatcherAgent
        except Exception as exc:  # noqa: BLE001
            logger.debug("DisciplineMatcherAgent unavailable: %s", exc)
            return {"error": f"Agent unavailable: {exc}"}

        summary_parts: list[str] = []
        for k in (
            "title", "problem_statement", "object_of_inquiry",
            "core_claims", "key_terms", "disciplinary_register_current",
        ):
            v = getattr(self.article_model, k, None)
            if isinstance(v, list):
                v = "; ".join(str(x) for x in v if x)
            if v:
                summary_parts.append(f"{k}: {v}")
        if comment:
            summary_parts.append(f"user_comment: {comment}")
        summary = "\n".join(summary_parts)[:4000]

        agent = DisciplineMatcherAgent()
        inp = _AI(
            operation_id="discipline_rerun",
            agent_role_id="discipline_matcher",
            raw_text=summary,
            entities={
                "article_summary": summary,
                "region": self.region_hint or "auto",
                "user_comment": comment or "",
            },
        )
        provider = _get_llm_provider("discipline_matcher")
        try:
            if provider is not None:
                out = agent.execute(inp, provider)
            else:
                out = agent.execute_deterministic(inp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Discipline rerun crashed: %s", exc)
            out = agent.execute_deterministic(inp)

        if out and out.output_entity:
            self.discipline_matches = out.output_entity
            logger.info(
                "Discipline rerun emitted %d matches (%s)",
                len(out.output_entity.get("matched", [])),
                out.confidence,
            )
        result = self.discipline_matches or {}
        if previous:
            result["previous_run"] = previous
        return result

    def rerun_article_model(self, comment: str | None = None) -> dict[str, Any]:
        """Re-run article modeler via LLM to resolve UNKNOWN genre/method."""
        if self.article_model is None:
            return {"error": "No article model — run intake first"}
        text = self.article_input_text or self.input_text or ""
        if len(text) < 100:
            return {"error": "Insufficient text for re-analysis"}
        provider = _get_llm_provider("article_modeler")
        if provider is None:
            return {"error": "LLM provider not configured"}
        try:
            from ..agents.article_modeler import ArticleModelerAgent
            from ..agents.contract import AgentInput as _AI
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Agent unavailable: {exc}"}
        if comment:
            text = f"[Комментарий оператора: {comment}]\n\n{text}"
        agent = ArticleModelerAgent()
        inp = _AI(
            operation_id="article_model_rerun",
            agent_role_id="article_modeler",
            raw_text=text,
        )
        try:
            out = agent.execute(inp, provider)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Article model rerun LLM failed: %s", exc)
            return {"error": f"LLM call failed: {exc}"}
        if out and out.output_entity:
            from ..schema import ArticleModel
            new_model = ArticleModel.from_dict(out.output_entity)
            old_genre = getattr(self.article_model, "genre_current", None)
            old_method = getattr(self.article_model, "method_status", None)
            self.article_model.genre_current = new_model.genre_current
            self.article_model.method_status = new_model.method_status
            self.article_model.novelty_mode = new_model.novelty_mode
            if new_model.argument_structure:
                self.article_model.argument_structure = new_model.argument_structure
            return {
                "genre": {"old": old_genre, "new": self.article_model.genre_current},
                "method": {"old": old_method, "new": self.article_model.method_status},
                "novelty_mode": self.article_model.novelty_mode,
                "source": "llm",
            }
        return {"error": "LLM returned no output entity"}

    def _build_matched_disciplines_context(self) -> str | None:
        """Build a compact block summarizing the matcher's verdict for
        downstream prompts (semantic_profiler). Returns None when no
        matches are available — the profiler then falls back to its
        own implicit keyword pre-filter.
        """
        if not self.discipline_matches:
            return None
        matched = self.discipline_matches.get("matched") or []
        if not matched:
            return None
        try:
            from ..services.discipline_registry import load_default_registry
            registry = load_default_registry()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Default discipline registry unavailable: %s", exc)
            registry = None
        lines: list[str] = []
        for m in matched[:6]:
            did = m.get("discipline_id")
            strength = m.get("strength", "unknown")
            why = m.get("why", "")
            card = registry.get(did) if registry else None
            if card is not None:
                lines.append(
                    f"- [{strength}] {card.summary_for_context(500)} — {why}"
                )
            elif did:
                lines.append(f"- [{strength}] {did} — {why}")
        if not lines:
            return None
        return "\n".join(lines)

    def _build_article_field_position(self):
        """Run article_field_positioner. LLM if available, deterministic otherwise."""
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
        provider = _get_llm_provider("article_field_positioner")
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

        # F3: minimum-text guard.
        stripped_len = len(text.strip())
        if stripped_len < 200:
            self._log_decision("investigate_venue_skipped", {
                "reason": "needs_more_venue_text",
                "received_chars": stripped_len,
            })
            return {
                "status": "needs_more_venue_text",
                "received_chars": stripped_len,
                "min_chars": 200,
                "hint": (
                    "Текста слишком мало для разбора площадки. Вставьте "
                    "aims/scope, типы статей и submission policies — "
                    "или приложите ссылку/ISSN."
                ),
            }

        provider = _get_llm_provider("venue_profiler")
        venue = None
        regime = None
        used_llm = False

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
                    used_llm = True
                    logger.info("Venue profiled via LLM")
            except Exception as exc:
                logger.warning("LLM venue profiling failed, falling back: %s", exc)

        if venue is None:
            from ..services.venue_profiling import build_venue_model
            venue, regime = build_venue_model(text)

        self.investigated_venue = venue
        self.publication_regime = regime
        if self.venue_source_metadata is None:
            import hashlib
            self.venue_source_metadata = {
                "source_url": None,
                "source_type": "text_paste",
                "acquisition_timestamp": _now(),
                "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                "char_count": len(text),
            }

        # P6.1 Track 7: store extraction output as provisional records
        source_url = (self.venue_source_metadata or {}).get("source_url")
        source_type = (self.venue_source_metadata or {}).get(
            "source_type", "text_paste",
        )
        registry_result = self._registry.store_venue_extraction(
            venue.to_dict(),
            source_url=source_url,
            source_type=source_type,
        )

        self._build_venue_field_position(venue, guidelines_text=text)

        # P6.1 Track 5: build family context from registry
        self._build_venue_family_from_venue(
            registry_venue_id=registry_result.get("parent_venue_id"),
        )

        self._log_decision("investigate_venue", {
            "venue_name": venue.canonical_name,
            "registry_records_created": registry_result.get("created_count", 0),
        })

        result = {
            "venue": venue.to_dict(),
            "publication_regime": regime.to_dict() if regime else None,
            "venue_field_position": (
                self.venue_field_position.to_dict()
                if self.venue_field_position else None
            ),
            "used_llm": used_llm,
            "registry_records_created": registry_result.get("created_count", 0),
        }

        # P6.1 Track 8: propagate registry status to output
        return self._registry.propagate_status(result)

    def investigate_venue_by_reference(
        self,
        *,
        issn: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a venue evidence pack by ISSN or name, then profile it."""
        from ..services.venue_evidence_pack_resolver import resolve
        pack = resolve(issn=issn, name=name)
        if pack is None:
            return {
                "status": "evidence_pack_not_found",
                "issn": issn,
                "name": name,
                "hint": (
                    "Нет evidence pack для этого журнала. "
                    "Используйте investigate-venue с текстом aims/scope."
                ),
            }
        self._log_decision("investigate_venue_by_reference", {
            "source_file": str(pack.path),
            "issn": pack.issn,
            "canonical_name": pack.canonical_name,
        })
        return self.investigate_venue(pack.text)

    @staticmethod
    def _is_safe_url(url: str) -> tuple[bool, str]:
        """Validate URL against SSRF: scheme, host, private ranges."""
        from urllib.parse import urlparse
        import ipaddress
        import socket

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Scheme '{parsed.scheme}' not allowed; use http or https."
        hostname = parsed.hostname
        if not hostname:
            return False, "No hostname in URL."
        blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
        if hostname.lower() in blocked_hosts:
            return False, "Localhost URLs are blocked."
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for _, _, _, _, addr in resolved:
                ip = ipaddress.ip_address(addr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"Resolved to private/reserved IP {ip}."
                if str(ip) == "169.254.169.254":
                    return False, "Cloud metadata IP blocked."
        except (socket.gaierror, ValueError):
            pass
        return True, ""

    def investigate_venue_by_url(self, url: str) -> dict[str, Any]:
        """Fetch venue page by URL and feed text into investigate_venue."""
        import hashlib
        from ..adapters.http_client import fetch_text_safe

        safe, reason = self._is_safe_url(url)
        if not safe:
            return {
                "status": "invalid_url",
                "hint": reason,
            }

        result = fetch_text_safe(url, timeout=30)
        if not result.ok:
            self._log_decision("investigate_venue_by_url_failed", {
                "url": url, "error": result.error,
            })
            return {
                "status": "fetch_failed",
                "url": url,
                "error": result.error,
            }

        text = result.text
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        self.venue_source_metadata = {
            "source_url": url,
            "source_type": "url_fetch",
            "acquisition_timestamp": _now(),
            "content_hash": content_hash,
            "char_count": len(text),
        }
        self._log_decision("investigate_venue_by_url", {
            "url": url,
            "content_hash": content_hash,
            "char_count": len(text),
        })
        return self.investigate_venue(text)

    def set_adapter_mode(self, mode: str) -> dict[str, Any]:
        """Switch venue adapter mode for this case.

        LIVE_API mode requires KAIROSKOPION_ALLOW_LIVE_API=1 in server env.
        Without this env var, only offline_stub, fixture, and cached are
        allowed — this prevents accidental external API calls in production.
        """
        import os
        from ..adapters.venue.base import VenueAdapterMode
        valid = {m.value for m in VenueAdapterMode}
        if mode not in valid:
            return {"status": "invalid_mode", "valid": sorted(valid)}
        if mode == "live_api" and not os.environ.get("KAIROSKOPION_ALLOW_LIVE_API"):
            return {
                "status": "forbidden",
                "hint": "LIVE_API requires KAIROSKOPION_ALLOW_LIVE_API=1 in server env.",
            }
        self.adapter_mode = mode
        self._log_decision("set_adapter_mode", {"mode": mode})
        return {"status": "ok", "mode": mode}

    def enrich_venue(self) -> dict[str, Any]:
        """Build a VenueProfilePackage from the investigated venue."""
        if not self.investigated_venue:
            return {"status": "no_venue", "hint": "Investigate a venue first."}

        venue = self.investigated_venue
        identity: dict[str, Any] = {
            "canonical_name": venue.canonical_name,
            "issns": [venue.issn] if getattr(venue, "issn", None) else [],
            "publisher": getattr(venue, "publisher", None),
            "homepage_url": getattr(venue, "homepage_url", None),
            "languages": getattr(venue, "languages", None) or [],
            "venue_type": getattr(venue, "venue_type", "journal"),
        }
        use_live = self.adapter_mode == "live_api"
        from ..services.venue_profile_package_builder import build_venue_profile_package
        vpkg = build_venue_profile_package(
            identity=identity,
            fetch_corpus=use_live,
            fetch_editorial_board=False,
        )
        if self.venue_field_position:
            vpkg.venue_field_position_id = self.venue_field_position.field_position_id
            vpkg.completeness["VenueFieldPosition"] = "present"
        if self.publication_regime:
            vpkg.publication_regime_id = self.publication_regime.publication_regime_id
            vpkg.completeness["FormalSubmissionProfile"] = "present"
        if self.source_evidence_packet:
            vpkg.source_evidence_packet_id = self.source_evidence_packet.source_evidence_packet_id

        self.venue_profile_package = vpkg
        self._log_decision("enrich_venue", {
            "venue_name": venue.canonical_name,
            "completeness": vpkg.completeness,
            "confidence": vpkg.confidence,
        })
        return {
            "status": "ok",
            "venue_profile_package": vpkg.to_dict(),
        }

    def get_venue_profile_package(self) -> dict[str, Any]:
        if not self.venue_profile_package:
            return {"status": "not_built", "hint": "Call enrich-venue first."}
        return self.venue_profile_package.to_dict()

    def get_compliance(self) -> dict[str, Any]:
        """Build or return compliance checklist."""
        if self.compliance_checklist and self.compliance_checklist.status != "not_built":
            return self.compliance_checklist.to_dict()
        if not self.investigated_venue or not self.article_model:
            return {"status": "not_ready", "hint": "Need both article and venue."}
        from ..services.compliance_checklist_minimal import build_minimal_compliance_checklist
        checklist = build_minimal_compliance_checklist(
            article=self.article_model,
            venue=self.investigated_venue,
            scenario=self.scenario,
            risk_report=self.risk_report,
            bibliography_profile=self.bibliography_profile,
        )
        self.compliance_checklist = checklist
        return checklist.to_dict()

    def build_submission_pack_api(self) -> dict[str, Any]:
        """Build submission pack via API."""
        if not self.article_model or not self.investigated_venue:
            return {"status": "not_ready", "hint": "Need article and venue."}
        if not self.scenario:
            from ..schema import SubmissionScenario as _SS
            scenario = _SS()
        else:
            scenario = self.scenario
        from ..services.submission_pack import build_submission_pack
        pack = build_submission_pack(
            article=self.article_model,
            venue=self.investigated_venue,
            scenario=scenario,
            fit=self.fit_assessment,
            risk=self.risk_report,
            compliance=self.compliance_checklist,
        )
        self.submission_pack = pack
        return pack.to_dict()

    # -- Phase 3: Track A — Discipline to Venue Funnel --

    def set_discipline_intent(
        self, text: str, region: str = "auto",
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set discipline intent for Track A venue discovery.

        Stores raw text intent. Venue family inference requires LLM —
        if unavailable, returns FUNNEL_BLOCKED_NEEDS_LLM.
        """
        self.discipline_intent = {
            "text": text,
            "region": region,
            "constraints": constraints or [],
            "set_at": _now(),
            "intent_parse_status": "needs_llm",
        }
        self.region_hint = region or "auto"
        self._log_decision("set_discipline_intent", {
            "text_preview": text[:100],
            "region": region,
        })

        if self.semantic_profile:
            self.get_pathways()

        return {
            "status": "ok",
            "discipline_intent": self.discipline_intent,
            "venue_families": [],
            "venue_families_status": "FUNNEL_BLOCKED_NEEDS_LLM",
            "pathways_count": len(self.pathways),
        }

    def _build_venue_family_from_venue(
        self,
        registry_venue_id: str | None = None,
    ) -> None:
        """Build venue family context from registry evidence + venue identity.

        P6.1 Track 5: registry-first family context. If the venue has a
        registry record, builds family from registry evidence (sections,
        parent/child neighbors). Otherwise falls back to the blocked stub.
        """
        if not self.investigated_venue:
            return
        venue = self.investigated_venue
        name = venue.canonical_name or ""

        # P6.1: try registry-first family context
        if registry_venue_id:
            family = self._registry.build_family_context(registry_venue_id)
            self.venue_family_context = {
                "source_venue": name,
                "registry_venue_id": registry_venue_id,
                "families": [],
                "families_status": family.get("status", "incomplete"),
                "registry_family": family,
                "set_at": _now(),
            }
            return

        self.venue_family_context = {
            "source_venue": name,
            "families": [],
            "families_status": "BLOCKED_NEEDS_LLM",
            "set_at": _now(),
        }

    def get_venue_matrix(self) -> dict[str, Any]:
        """Build a venue matrix from the venue pool.

        P6.1 Track 6: enriches candidates with registry provenance.
        Candidates without provenance get warnings. Rejected excluded.
        """
        if not self.venue_pool or not self.venue_pool.candidates:
            return {"candidates": [], "status": "no_pool"}
        matrix_rows = []
        for candidate in self.venue_pool.candidates:
            c = candidate if isinstance(candidate, dict) else (
                candidate.to_dict() if hasattr(candidate, "to_dict") else {}
            )
            matrix_rows.append({
                "venue_candidate_id": c.get("venue_candidate_id", ""),
                "canonical_name": c.get("canonical_name", ""),
                "record_id": c.get("record_id", ""),
                "evidence_level": len(c.get("evidence_refs", [])),
                "sources_count": len(c.get("sources", [])),
                "unknowns_count": len(c.get("unknowns", [])),
                "status": c.get("status", "discovered"),
                "next_action": (
                    "investigate" if c.get("status") == "discovered"
                    else "deepen" if c.get("status") == "light_profiled"
                    else "ready"
                ),
                "preliminary_assessment": "NOT_ASSESSED_NEEDS_LLM",
            })

        # P6.1 Track 6: enrich with registry provenance
        enriched = self._registry.enrich_candidates_with_provenance(matrix_rows)

        result = {"candidates": enriched, "status": "ok"}
        # P6.1 Track 8: propagate status
        return self._registry.propagate_status(result)

    # ------------------------------------------------------------------
    # Phase 5: Depth mode & budget controls
    # ------------------------------------------------------------------

    _DEPTH_MODES = ("quick", "standard", "deep", "exhaustive")

    def set_depth_mode(self, mode: str) -> dict[str, Any]:
        """Set the depth/budget mode for this case."""
        if mode not in self._DEPTH_MODES:
            return {
                "status": "invalid",
                "valid_modes": list(self._DEPTH_MODES),
            }
        self.depth_mode = mode
        self._log_decision("set_depth_mode", {"mode": mode})
        return {"status": "ok", "depth_mode": mode}

    def set_budget_constraints(
        self, max_api_calls: int | None = None, max_tokens: int | None = None,
    ) -> dict[str, Any]:
        self.budget_constraints = {
            "max_api_calls": max_api_calls,
            "max_tokens": max_tokens,
            "set_at": _now(),
        }
        self._log_decision("set_budget_constraints", self.budget_constraints)
        return {"status": "ok", "budget_constraints": self.budget_constraints}

    def get_cost_estimate(self) -> dict[str, Any]:
        """Estimate cost/effort for current depth mode."""
        depth_profiles = {
            "quick": {
                "adapter_calls": 0,
                "llm_calls": 0,
                "estimated_seconds": 5,
                "description": "Local-only, no external calls",
            },
            "standard": {
                "adapter_calls": 3,
                "llm_calls": 1,
                "estimated_seconds": 30,
                "description": "Basic adapter queries + one LLM pass",
            },
            "deep": {
                "adapter_calls": 8,
                "llm_calls": 3,
                "estimated_seconds": 90,
                "description": "Full adapter sweep + multi-pass LLM",
            },
            "exhaustive": {
                "adapter_calls": 15,
                "llm_calls": 5,
                "estimated_seconds": 180,
                "description": "All adapters + corpus analysis + full LLM chain",
            },
        }
        profile = depth_profiles.get(self.depth_mode, depth_profiles["standard"])
        budget = self.budget_constraints or {}
        if budget.get("max_api_calls") is not None:
            profile["adapter_calls"] = min(
                profile["adapter_calls"], budget["max_api_calls"],
            )
        return {
            "depth_mode": self.depth_mode,
            "profile": profile,
            "budget_constraints": self.budget_constraints,
            "status": "ok",
        }

    def _build_venue_field_position(
        self,
        venue: VenueModel,
        *,
        guidelines_text: str = "",
    ):
        """Run venue_field_positioner. LLM if available, deterministic otherwise."""
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
        provider = _get_llm_provider("venue_field_positioner")
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

        # M-7: compute ModelDelta before applying corrections
        model_delta: list[dict[str, Any]] = []
        meta_corrections: dict[str, str] = {}
        text_evidence: dict[str, str] = {}

        if corrections:
            for field, value in corrections.items():
                if field.startswith("_block_rejected_") or field.startswith("_block_comment_"):
                    meta_corrections[field] = value
                elif field.startswith("_text_evidence_"):
                    text_evidence[field] = value
                elif hasattr(self.article_model, field):
                    old_value = getattr(self.article_model, field, None)
                    if old_value != value:
                        model_delta.append({
                            "field": field,
                            "old": old_value,
                            "new": value,
                        })
                    setattr(self.article_model, field, value)

        self.article_model.lifecycle_status = LifecycleStatus.CONFIRMED.value

        decision_details: dict[str, Any] = {
            "protected_core": protected_core,
            "corrections_applied": list(corrections.keys()) if corrections else [],
            "model_delta": model_delta,
        }
        if meta_corrections:
            decision_details["block_decisions"] = meta_corrections
        if text_evidence:
            decision_details["text_evidence"] = text_evidence

        self._log_decision("confirm_article_model", decision_details)
        self._update_quality_gates("confirm_article")

        # M-7: append to CorrectionRegistry
        if model_delta or meta_corrections or text_evidence:
            CorrectionRegistry.append(
                case_id=self.case_id,
                user_id=self.user_id,
                model_delta=model_delta,
                meta_corrections=meta_corrections,
                text_evidence=text_evidence,
            )

        return {
            "confirmed": True,
            "protected_core": self.article_model.protected_core,
            "lifecycle_status": self.article_model.lifecycle_status,
            "model_delta": model_delta,
        }

    # -- M-8: LLM refinement dialog --

    def refine_article_model(self, message: str) -> dict[str, Any]:
        """Send a refinement message to the LLM and return suggestions."""
        import json, logging

        if not self.article_model:
            return {"error": "No article model to refine"}

        provider = _get_llm_provider("article_modeler")
        if provider is None:
            unavail_reply = (
                "LLM не подключён — автоматический диалог недоступен. "
                "Используйте ручную корректировку через типологию и комментарии."
            )
            self.refinement_chat.append({
                "role": "user", "content": message, "timestamp": _now(),
            })
            self.refinement_chat.append({
                "role": "assistant", "content": unavail_reply, "timestamp": _now(),
            })
            self._log_decision("refine_article_model", {
                "user_message": message,
                "suggestions_count": 0,
            })
            return {
                "reply": unavail_reply,
                "suggestions": [],
                "llm_available": False,
            }

        model_summary = {}
        for attr in [
            "title_current", "genre_current", "novelty_mode",
            "method_status", "problem_statement", "discipline",
            "abstract_current", "language",
        ]:
            val = getattr(self.article_model, attr, None)
            if val is not None:
                model_summary[attr] = val

        system_prompt = (
            "You are an article model refinement assistant for the Kairoskopion system. "
            "The user is reviewing a machine-generated article model and wants to correct or clarify specific fields. "
            "Current article model fields:\n"
            f"{json.dumps(model_summary, ensure_ascii=False, indent=2)}\n\n"
            "Respond in JSON with this structure:\n"
            '{"reply": "your explanation in Russian", "suggestions": [{"field": "field_name", "value": "new_value", "reason": "why"}]}\n'
            "Only suggest changes the user explicitly asked for. "
            "Use the exact field names from the model (e.g. genre_current, novelty_mode, method_status). "
            "If the user asks a question without requesting a change, return an empty suggestions list. "
            "Always reply in Russian."
        )

        chat_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        for entry in self.refinement_chat[-10:]:
            chat_messages.append({
                "role": entry["role"],
                "content": entry["content"],
            })
        chat_messages.append({"role": "user", "content": message})

        self.refinement_chat.append({
            "role": "user",
            "content": message,
            "timestamp": _now(),
        })

        attempt_meta: dict[str, Any] = {}
        try:
            response = provider.complete(chat_messages, agent_role="article_model_replay")
            raw_text = response.content or ""
            attempt_meta = {
                "requested_model": getattr(response, "requested_model", None),
                "effective_model": getattr(response, "effective_model", None) or getattr(response, "model", None),
                "fallback_used": getattr(response, "fallback_used", False),
                "attempt_count": getattr(response, "attempt_count", 1),
                "attempts": [
                    a.to_dict() if hasattr(a, "to_dict") else a
                    for a in getattr(response, "attempts", [])
                ],
                "agent_role": "article_model_replay",
                "provider_status": "ok",
                "parse_status": "pending",
                "final_error_code": None,
            }
        except Exception as exc:
            logger.warning("LLM refinement call failed: %s", exc)
            exc_attempts = getattr(exc, "attempts", [])
            attempt_meta = {
                "requested_model": None,
                "effective_model": None,
                "fallback_used": False,
                "attempt_count": len(exc_attempts),
                "attempts": [
                    a.to_dict() if hasattr(a, "to_dict") else a
                    for a in exc_attempts
                ],
                "agent_role": "article_model_replay",
                "provider_status": "error",
                "parse_status": "not_attempted",
                "final_error_code": getattr(exc, "error_code", "UNKNOWN"),
            }
            reply_text = f"Ошибка при обращении к LLM: {type(exc).__name__}"
            self.refinement_chat.append({
                "role": "assistant",
                "content": reply_text,
                "timestamp": _now(),
            })
            return {
                "reply": reply_text,
                "suggestions": [],
                "llm_available": True,
                "attempt_metadata": attempt_meta,
            }

        suggestions: list[dict[str, str]] = []
        reply_text = raw_text

        try:
            from ..llm.json_repair import repair_and_parse
            parsed = repair_and_parse(raw_text)
            if parsed.parsed:
                data = parsed.parsed
                reply_text = data.get("reply", raw_text)
                raw_suggestions = data.get("suggestions", [])
                if isinstance(raw_suggestions, list):
                    for s in raw_suggestions:
                        if isinstance(s, dict) and "field" in s and "value" in s:
                            if hasattr(self.article_model, s["field"]):
                                suggestions.append({
                                    "field": str(s["field"]),
                                    "value": str(s["value"]),
                                    "reason": str(s.get("reason", "")),
                                })
                attempt_meta["parse_status"] = "parsed_ok"
            else:
                attempt_meta["parse_status"] = "parse_failed"
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM suggestion parsing failed: %s", exc)
            attempt_meta["parse_status"] = "parse_error"

        self.refinement_chat.append({
            "role": "assistant",
            "content": reply_text,
            "suggestions": suggestions,
            "timestamp": _now(),
        })

        self._log_decision("refine_article_model", {
            "user_message": message,
            "suggestions_count": len(suggestions),
        })

        return {
            "reply": reply_text,
            "suggestions": suggestions,
            "llm_available": True,
            "attempt_metadata": attempt_meta,
        }

    def get_refinement_chat(self) -> list[dict[str, Any]]:
        return self.refinement_chat

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
            provider = _get_llm_provider("disciplinary_pathway_mapper")
            if provider is not None:
                try:
                    output = agent.execute(inp, provider)
                    logger.info("Pathways mapped via LLM")
                except Exception as exc:
                    logger.warning("LLM pathway mapping failed, falling back: %s", exc)
                    exc_attempts = getattr(exc, "attempts", [])
                    exc_error_code = getattr(exc, "error_code", None)
                    case_level_attempt = LLMAttemptMetadata.fallback(
                        reason=FALLBACK_REASON_PROVIDER_ERROR,
                        provider="openai_compatible",
                        validation_errors=[str(exc)[:240]],
                        attempts=exc_attempts,
                        final_error_code=exc_error_code,
                        agent_role="disciplinary_pathway_mapper",
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
        provider = _get_llm_provider("venue_discovery")
        if provider is not None:
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

        # P6.2 Track 3: store discovered candidates as provisional records
        registry_stored = 0
        if self.venue_pool and self.venue_pool.candidates:
            for cand in self.venue_pool.candidates:
                cand_dict = cand if isinstance(cand, dict) else cand.to_dict()
                cand_name = cand_dict.get("canonical_name")
                if not cand_name:
                    continue
                self._registry.store_venue_extraction(
                    {
                        "canonical_name": cand_name,
                        "issn": cand_dict.get("issn"),
                        "eissn": cand_dict.get("issn_l"),
                    },
                    source_url=None,
                    source_type="venue_discovery",
                )
                registry_stored += 1

        self.stage = CaseStage.VENUE_POOL
        self._log_decision("discover_venues", {
            "candidate_count": len(self.venue_pool.candidates) if self.venue_pool else 0,
            "registry_stored": registry_stored,
        })
        self._update_quality_gates("discover_venues")

        result = self.get_venue_pool()
        return self._registry.propagate_status(result)

    def get_venue_pool(self) -> dict[str, Any]:
        if self.venue_pool:
            return self.venue_pool.to_dict()
        return {"candidates": [], "status": "not_discovered"}

    # -- Select venue & fit --

    def select_venue(self, venue_id: str) -> dict[str, Any]:
        # feature/venue-fit-dossier-slice: support selecting the
        # investigated_venue (user-pasted journal page) directly,
        # without requiring a discovered venue pool. Special tokens:
        #   "investigated" or the investigated_venue.venue_model_id
        # → pick self.investigated_venue.
        is_investigated_token = (
            venue_id == "investigated"
            or (
                self.investigated_venue is not None
                and venue_id == getattr(self.investigated_venue, "venue_model_id", None)
            )
        )
        if is_investigated_token and self.investigated_venue is not None:
            self.selected_venue = self.investigated_venue
        else:
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
        from ..services.fit_assessment import assess_fit
        from ..services.mismatch_mapping import build_mismatch_map
        from ..services.rewrite_planning import build_rewrite_plan

        # If the operator hasn't filled the scenario yet, synthesize a
        # preliminary one so fit can still produce a verdict — but mark
        # it explicitly. The dossier UI shows this as a banner.
        if self.scenario is not None:
            scenario = self.scenario
        else:
            scenario = SubmissionScenario(
                article_model_id=self.article_model.article_model_id
                if self.article_model else "",
                scenario_preliminary=True,
                unknowns=[
                    "Operator has not filled the submission scenario yet — "
                    "fit verdict treats scenario answers as preliminary."
                ],
            )
            # Persist so the dossier card + UI banner surfaces it.
            self.scenario = scenario

        provider = _get_llm_provider("fit_assessor")
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
            except Exception as exc:  # noqa: BLE001
                logger.warning("Deterministic fit assessment failed: %s", exc)
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mismatch map build failed: %s", exc)
            return

        # MismatchNarratorAgent: enrich each mismatch with LLM-authored
        # venue_side / description / possible_actions. The deterministic
        # mismatch builder intentionally leaves venue_side empty and
        # marks an explicit unknown (D2 fix from ee90523); this agent
        # fills the gap in ONE batch call grounded in article + venue
        # evidence. Honest fallback when LLM unavailable: leaves the
        # empty venue_side intact so the UI italic "требуется LLM-
        # комментарий" hint stays truthful.
        try:
            from ..agents.contract import AgentInput as _AI
            from ..agents.mismatch_narrator import (
                MismatchNarratorAgent,
                enrich_mismatch_map_in_place,
            )
            narr_provider = _get_llm_provider("mismatch_narrator")
            narr_agent = MismatchNarratorAgent()
            narr_inp = _AI(
                operation_id="mismatch_narrate",
                agent_role_id="mismatch_narrator",
                entities={
                    "article": self.article_model.to_dict(),
                    "venue": self.selected_venue.to_dict(),
                    "mismatches": [
                        dict(m) if isinstance(m, dict) else m
                        for m in self.mismatch_map.mismatches
                    ],
                },
            )
            if narr_provider is not None:
                narr_out = narr_agent.execute(narr_inp, narr_provider)
            else:
                narr_out = narr_agent.execute_deterministic(narr_inp)
            output_entity = (
                narr_out.output_entity if narr_out else None
            )
            if narr_out and output_entity:
                enriched_count = enrich_mismatch_map_in_place(
                    self.mismatch_map,
                    output_entity.get("narratives") or [],
                )
                # V2-B1: structured coverage diagnostics. Distinguishes
                # empty_llm_output / missing_axes / axis_match_failure /
                # empty_valid_unknown / partial / filled / parse_failed
                # / provider_error so 0-coverage is observable instead
                # of collapsed to one count. No raw LLM output retained.
                from ..services.narrator_coverage import (
                    classify_narrator_coverage,
                    per_axis_status,
                )
                input_axes = [
                    (m.get("axis", "") if isinstance(m, dict)
                     else getattr(m, "axis", ""))
                    for m in self.mismatch_map.mismatches
                ]
                coverage = classify_narrator_coverage(
                    input_axes, output_entity,
                )
                self.mismatch_map.narrator_coverage = coverage
                for m in self.mismatch_map.mismatches:
                    axis = (
                        m.get("axis", "") if isinstance(m, dict)
                        else getattr(m, "axis", "")
                    )
                    new_status = per_axis_status(
                        axis, input_axes, output_entity,
                        coverage["narrator_status"],
                    )
                    if isinstance(m, dict):
                        m["narrative_status"] = new_status
                    else:
                        setattr(m, "narrative_status", new_status)
                self._log_decision("mismatch_narrated", {
                    "enriched_count": enriched_count,
                    "total": len(self.mismatch_map.mismatches),
                    "narrator_status": coverage["narrator_status"],
                    "filled_count": coverage["filled_count"],
                    "missing_axes_count": len(coverage["missing_axes"]),
                    "unmatched_axes_count": len(coverage["unmatched_axes"]),
                })

                # Round III Track E: per-axis rescue when the batch
                # call collapsed. If parse_failed / empty_llm_output /
                # axis_match_failure / missing_axes AND a provider is
                # available, retry one axis at a time. One bad axis
                # then does not collapse the whole case.
                _RESCUE_TRIGGERS = {
                    "parse_failed", "empty_llm_output",
                    "axis_match_failure", "missing_axes",
                }
                if (
                    narr_provider is not None
                    and coverage["narrator_status"] in _RESCUE_TRIGGERS
                    and self.mismatch_map.mismatches
                ):
                    # Round III Track E: cap rescue at first 3 axes so
                    # total chain stays under proxy timeout. Unrescued
                    # axes keep narrative_status=needs_llm honestly.
                    _RESCUE_CAP = 3
                    rescued = 0
                    per_axis_results: list[dict[str, Any]] = []
                    rescued_so_far = 0
                    for m in self.mismatch_map.mismatches:
                        axis = (
                            m.get("axis", "") if isinstance(m, dict)
                            else getattr(m, "axis", "")
                        )
                        if rescued_so_far >= _RESCUE_CAP:
                            per_axis_results.append({
                                "axis": axis,
                                "narrative_status": "needs_llm",
                            })
                            continue
                        rescued_so_far += 1
                        # ONE mismatch per call. If that one fails,
                        # mark this axis needs_llm and continue.
                        single_inp = _AI(
                            operation_id="mismatch_narrate_rescue",
                            agent_role_id="mismatch_narrator",
                            entities={
                                "article": self.article_model.to_dict(),
                                "venue": self.selected_venue.to_dict(),
                                "mismatches": [
                                    dict(m) if isinstance(m, dict) else m
                                ],
                            },
                        )
                        try:
                            single_out = narr_agent.execute(
                                single_inp, narr_provider,
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "Single-mismatch narrator rescue failed: %s", exc,
                            )
                            single_out = None
                        if (single_out is None
                                or not single_out.output_entity):
                            per_axis_results.append({
                                "axis": axis,
                                "narrative_status": "parse_failed",
                            })
                            continue
                        narratives = (
                            single_out.output_entity.get("narratives") or []
                        )
                        # Find the entry for this axis (LLM may rename)
                        n = next(
                            (x for x in narratives
                             if isinstance(x, dict)
                             and x.get("axis") == axis),
                            None,
                        )
                        if n and (n.get("venue_side") or "").strip():
                            per_axis_results.append({
                                "axis": axis,
                                "venue_side": (n.get("venue_side") or "").strip(),
                                "description": (n.get("description") or "").strip(),
                                "possible_actions": list(
                                    n.get("possible_actions") or []),
                                "narrative_status": "llm_filled",
                            })
                            rescued += 1
                        else:
                            per_axis_results.append({
                                "axis": axis,
                                "narrative_status": "needs_llm",
                            })

                    # Re-enrich + reclassify if anything rescued
                    if rescued > 0:
                        enrich_mismatch_map_in_place(
                            self.mismatch_map, per_axis_results,
                        )
                        # Update per-mismatch narrative_status
                        by_axis_resc = {
                            r.get("axis"): r for r in per_axis_results
                        }
                        for m in self.mismatch_map.mismatches:
                            axis = (
                                m.get("axis", "") if isinstance(m, dict)
                                else getattr(m, "axis", "")
                            )
                            r = by_axis_resc.get(axis)
                            if r:
                                new_status = r.get("narrative_status", "needs_llm")
                                if isinstance(m, dict):
                                    m["narrative_status"] = new_status
                                else:
                                    setattr(m, "narrative_status", new_status)
                        # Update coverage
                        total = len(self.mismatch_map.mismatches)
                        cov = self.mismatch_map.narrator_coverage or {}
                        if rescued == total:
                            cov["narrator_status"] = "filled"
                        else:
                            cov["narrator_status"] = "partial"
                        cov["filled_count"] = rescued
                        cov["total_count"] = total
                        cov["empty_reason"] = (
                            f"batch parse failed; per-axis rescue "
                            f"recovered {rescued}/{total}"
                        )
                        self.mismatch_map.narrator_coverage = cov
                        self._log_decision("mismatch_narrator_rescued", {
                            "rescued": rescued,
                            "total": total,
                            "status_after_rescue": cov["narrator_status"],
                        })
        except Exception as exc:
            logger.warning("Mismatch narrator failed (non-fatal): %s", exc)
            # Even on agent exception, mark coverage as provider_error
            # so dossier exposes the failure honestly.
            try:
                from ..services.narrator_coverage import (
                    STATUS_PROVIDER_ERROR,
                )
                input_axes = [
                    (m.get("axis", "") if isinstance(m, dict)
                     else getattr(m, "axis", ""))
                    for m in self.mismatch_map.mismatches
                ]
                self.mismatch_map.narrator_coverage = {
                    "narrator_attempted": True,
                    "narrator_status": STATUS_PROVIDER_ERROR,
                    "filled_count": 0,
                    "total_count": len(input_axes),
                    "missing_axes": list(input_axes),
                    "unmatched_axes": [],
                    "parse_status": None,
                    "used_model": None,
                    "latency_ms": None,
                    "empty_reason": "narrator agent raised exception",
                    "parse_failure_category": None,
                    "parse_failure_reason": None,
                    "schema_failure_path": None,
                    "schema_failure_rule": None,
                    "repair_failure_stage": None,
                    "repair_steps_attempted": [],
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Rewrite plan build failed: %s", exc)

        # Build the risk report alongside the rewrite plan so the
        # dossier has it on the same chain run. (Citation ecology
        # requires a BibliographyProfile which isn't always available
        # at this point — it's built on-demand by /adaptation-plan;
        # skip here to avoid fake data.)
        # Round III: wire LLM risk_officer with needs_llm fallback.
        # On LLM success → semantic_status=llm_grounded with origins=llm.
        # On LLM failure → needs_llm placeholder. Deterministic
        # semantic build_risk_report is NEVER called from the chain.
        try:
            from ..services.llm_semantic_organs import try_llm_risk_officer
            risk_provider = _get_llm_provider("risk_officer")
            self.risk_report = try_llm_risk_officer(
                self.article_model,
                self.selected_venue,
                scenario,
                self.fit_assessment,
                self.mismatch_map,
                risk_provider,
                raw_article_text=getattr(self, "article_input_text", None),
            )
            self._log_decision("risk_report_built", {
                "semantic_status": self.risk_report.semantic_status,
                "risk_count": len(self.risk_report.risk_items),
                "round3_organ": "llm_risk_officer" if (
                    risk_provider is not None
                    and self.risk_report.semantic_status == "llm_grounded"
                ) else "needs_llm_placeholder",
            })
        except Exception as exc:
            logger.warning("Risk report failed (non-fatal): %s", exc)

        if self.mismatch_map.mismatches:
            try:
                # Round III: wire LLM rewrite_planner with needs_llm
                # fallback. Deterministic build_rewrite_plan is NEVER
                # called from the chain. Core-touching changes require
                # user acceptance.
                from ..services.llm_semantic_organs import (
                    try_llm_rewrite_planner,
                )
                rewrite_provider = _get_llm_provider("rewrite_planner")
                self.rewrite_plan = try_llm_rewrite_planner(
                    self.article_model,
                    self.selected_venue,
                    self.fit_assessment,
                    self.mismatch_map,
                    self.risk_report,
                    rewrite_provider,
                    raw_article_text=getattr(self, "article_input_text", None),
                )
                self.stage = CaseStage.ADAPTING
                self._log_decision("rewrite_planned", {
                    "changes_count": len(self.rewrite_plan.changes),
                    "effort": self.rewrite_plan.estimated_effort,
                    "round2b_doctrine": "needs_llm_placeholder",
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
            except Exception as exc:  # noqa: BLE001
                logger.warning("Policy gate wrapper failed: %s", exc)

        # V2-E: BibliographyProfile from preserved raw article text.
        # Pure structural extraction; no external lookups; no invented
        # references. Status=unknown when raw text unavailable.
        try:
            from ..services.bibliography_profile import (
                build_minimal_bibliography_profile,
            )
            raw_article_text = self.article_input_text or None
            self.bibliography_profile = build_minimal_bibliography_profile(
                raw_text=raw_article_text,
                article_model_id=(
                    self.article_model.article_model_id
                    if self.article_model else None
                ),
                source=(
                    "article_input_text" if raw_article_text else None
                ),
            )
            self._log_decision("bibliography_profile_built", {
                "status": self.bibliography_profile.status,
                "reference_count": self.bibliography_profile.reference_count,
                "doi_count": self.bibliography_profile.doi_count,
                "verification_status": self.bibliography_profile.verification_status,
            })
        except Exception as exc:
            logger.warning("BibliographyProfile failed (non-fatal): %s", exc)

        # V2-D + V2-E: minimal-real CitationPlan / ComplianceChecklist /
        # SubmissionPack lanes. Pure deterministic builders, no LLM,
        # no fake content. CitationPlan is now bibliography-aware.
        try:
            from ..services.citation_plan_minimal import (
                build_minimal_citation_plan,
            )
            self.citation_plan = build_minimal_citation_plan(
                self.article_model,
                self.selected_venue,
                self.fit_assessment,
                self.mismatch_map,
                self.risk_report,
                self.rewrite_plan,
                bibliography_profile=self.bibliography_profile,
            )
            # Round III: upgrade with LLM CitationPlanner if provider
            # available. Augments semantic fields (gap_categories /
            # missing_bridges / search_tasks / padding_warnings) and
            # marks origin=llm. Anti-fake filter strips invented DOIs
            # / author-year. Failure: keep structural plan unchanged.
            from ..services.llm_semantic_organs import (
                upgrade_citation_plan_with_llm,
            )
            cit_provider = _get_llm_provider("citation_planner")
            self.citation_plan = upgrade_citation_plan_with_llm(
                self.citation_plan,
                self.article_model,
                self.selected_venue,
                self.bibliography_profile,
                cit_provider,
                raw_article_text=getattr(self, "article_input_text", None),
            )
            self._log_decision("citation_plan_built", {
                "status": self.citation_plan.status,
                "semantic_status": self.citation_plan.semantic_status,
                "gap_categories_count": len(self.citation_plan.citation_gap_categories),
                "search_tasks_count": len(self.citation_plan.recommended_reference_search_tasks),
                "unknowns_count": len(self.citation_plan.unknowns),
                "round3_organ": "llm_citation_planner" if (
                    cit_provider is not None
                    and "llm_citation_planner"
                    in self.citation_plan.created_from
                ) else "structural_minimal_only",
            })
        except Exception as exc:
            logger.warning("CitationPlan minimal failed (non-fatal): %s", exc)

        # Round II-B Track D: ComplianceChecklist must NEVER disappear
        # silently from the dossier. If the builder throws, emit a
        # visible error-placeholder so operator sees the failure
        # instead of an absent section.
        try:
            from ..services.compliance_checklist_minimal import (
                build_minimal_compliance_checklist,
            )
            self.compliance_checklist = build_minimal_compliance_checklist(
                self.article_model,
                self.selected_venue,
                scenario,
                self.risk_report,
                bibliography_profile=self.bibliography_profile,
            )
            self._log_decision("compliance_checklist_built", {
                "status": self.compliance_checklist.status,
                "items_count": len(self.compliance_checklist.checklist_items),
                "missing_count": len(self.compliance_checklist.missing_items),
                "unknowns_count": len(self.compliance_checklist.unknowns),
            })
        except Exception as exc:
            logger.warning(
                "ComplianceChecklist minimal failed — emitting visible "
                "error placeholder (Round II-B Track D): %s", exc,
            )
            # Visible error placeholder so the section is not hidden.
            from ..schema import ComplianceChecklist as _CC
            from ..services.semantic_provenance import (
                ORIGIN_STRUCTURAL_EXTRACTION,
            )
            self.compliance_checklist = _CC(
                article_model_id=(
                    self.article_model.article_model_id
                    if self.article_model else None
                ),
                venue_model_id=(
                    self.selected_venue.venue_model_id
                    if self.selected_venue else None
                ),
                submission_scenario_id=(
                    scenario.submission_scenario_id if scenario else None
                ),
                checklist_items=[],
                missing_items=[],
                blocking_items=[],
                warnings=[
                    "ComplianceChecklist builder raised an exception "
                    "during fit chain. Section preserved as visible "
                    "error placeholder so the operator sees the "
                    "failure instead of a silently absent section."
                ],
                unknowns=[
                    f"builder_exception_type={type(exc).__name__}",
                    "compliance items are not available for this case "
                    "until the builder issue is resolved",
                ],
                status="error",
                created_from=["error_placeholder"],
                confidence="low",
                field_origins={
                    "checklist_items": ORIGIN_STRUCTURAL_EXTRACTION,
                    "status": ORIGIN_STRUCTURAL_EXTRACTION,
                    "warnings": ORIGIN_STRUCTURAL_EXTRACTION,
                    "unknowns": ORIGIN_STRUCTURAL_EXTRACTION,
                },
                semantic_status="error",
            )
            self._log_decision("compliance_checklist_error_placeholder", {
                "exception_type": type(exc).__name__,
            })

        try:
            from ..services.submission_pack_minimal import (
                build_minimal_submission_pack,
            )
            self.submission_pack = build_minimal_submission_pack(
                self.article_model,
                self.selected_venue,
                scenario,
                self.fit_assessment,
                self.risk_report,
                self.rewrite_plan,
                self.citation_plan,
                self.compliance_checklist,
                bibliography_profile=self.bibliography_profile,
            )
            self._log_decision("submission_pack_built", {
                "ready_status": self.submission_pack.ready_status,
                "missing_count": len(self.submission_pack.missing_items),
                "blocking_count": len(self.submission_pack.blocking_issues),
                "next_actions_count": len(self.submission_pack.next_actions),
            })
        except Exception as exc:
            logger.warning("SubmissionPack minimal failed (non-fatal): %s", exc)

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
        # V2-D minimal-real lanes
        if self.compliance_checklist:
            dossier["compliance_checklist"] = self.compliance_checklist.to_dict()
        if self.submission_pack:
            dossier["submission_pack"] = self.submission_pack.to_dict()
        # V2-E BibliographyProfile
        if self.bibliography_profile:
            dossier["bibliography_profile"] = self.bibliography_profile.to_dict()
        if self.upload_metadata:
            dossier["upload_metadata"] = dict(self.upload_metadata)
        if self.russian_surface_cache:
            dossier["russian_surface_cache"] = dict(self.russian_surface_cache)
        # Round III-J: surface enough state for an evidence-based
        # human-dossier renderer. None of these introduce new facts —
        # they expose what is already persisted on the case.
        if self.investigated_venue is not None:
            dossier["investigated_venue"] = self.investigated_venue.to_dict()
        # Operator-supplied venue text lives on self.input_text after a
        # venue-typed intake. Surface a truncated preview + the
        # input_type marker so the renderer can label the venue as
        # "supplied by operator" without LLM-confirmed VenueModel.
        _venue_input_types = (
            "journal_or_venue", "venue", "submission_venue",
        )
        if (
            self.input_text
            and (self.input_type or "").lower() in _venue_input_types
        ):
            dossier["venue_input_text_preview"] = self.input_text[:600]
            dossier["venue_input_type"] = self.input_type
        # First-paragraph preview of the article text — purely
        # structural; renderer uses this only as a TITLE CANDIDATE with
        # explicit source/confidence, never as canonical title.
        if self.article_input_text:
            first_chunk = self.article_input_text.split("\n\n", 1)[0]
            dossier["article_first_paragraph"] = first_chunk[:400]
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


class CorrectionRegistry:
    """JSONL append-only registry of user corrections to article models.

    Each line records one confirm_article_model event with its delta,
    block decisions, and text evidence. Used by M-9 for pattern detection.
    """

    _path = None  # type: ignore[assignment]

    @classmethod
    def _registry_path(cls):
        import os
        from pathlib import Path
        if cls._path is None:
            data_dir = Path(
                os.environ.get("KAIROSKOPION_DATA_DIR", ".kairoskopion")
            )
            data_dir.mkdir(parents=True, exist_ok=True)
            cls._path = data_dir / "correction_registry.jsonl"
        return cls._path

    @classmethod
    def append(
        cls,
        case_id: str,
        user_id: str | None,
        model_delta: list[dict[str, Any]],
        meta_corrections: dict[str, str],
        text_evidence: dict[str, str],
    ) -> None:
        import json, logging
        entry = {
            "case_id": case_id,
            "user_id": user_id,
            "timestamp": _now(),
            "model_delta": model_delta,
            "meta_corrections": meta_corrections,
            "text_evidence": text_evidence,
        }
        try:
            with open(cls._registry_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logger.warning(
                "CorrectionRegistry.append failed: %s", exc,
            )

    @classmethod
    def read_all(cls) -> list[dict[str, Any]]:
        import json
        path = cls._registry_path()
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    @classmethod
    def analyze_signals(cls, min_occurrences: int = 3) -> list[dict[str, Any]]:
        """Detect recurring correction patterns → PromptCorrectionSignals."""
        from collections import Counter
        entries = cls.read_all()
        if not entries:
            return []

        field_change_counter: Counter[str] = Counter()
        field_value_counter: Counter[tuple[str, str]] = Counter()
        rejection_counter: Counter[str] = Counter()

        for entry in entries:
            for delta in entry.get("model_delta", []):
                field = delta.get("field", "")
                new_val = str(delta.get("new", ""))
                if field:
                    field_change_counter[field] += 1
                    field_value_counter[(field, new_val)] += 1
            for key in entry.get("meta_corrections", {}):
                if key.startswith("_block_rejected_"):
                    block_id = key.replace("_block_rejected_", "")
                    rejection_counter[block_id] += 1

        signals: list[dict[str, Any]] = []

        for field, count in field_change_counter.items():
            if count >= min_occurrences:
                top_value = ""
                top_count = 0
                for (f, v), c in field_value_counter.items():
                    if f == field and c > top_count:
                        top_value = v
                        top_count = c
                signals.append({
                    "type": "field_correction_pattern",
                    "field": field,
                    "correction_count": count,
                    "most_common_override": top_value,
                    "override_count": top_count,
                    "severity": "high" if count >= min_occurrences * 2 else "medium",
                    "message": (
                        f"Поле «{field}» исправлялось {count} раз(а). "
                        f"Чаще всего ставят: «{top_value}» ({top_count}x). "
                        "Возможно, промпт систематически ошибается в этом поле."
                    ),
                })

        for block_id, count in rejection_counter.items():
            if count >= min_occurrences:
                signals.append({
                    "type": "block_rejection_pattern",
                    "block_id": block_id,
                    "rejection_count": count,
                    "severity": "medium",
                    "message": (
                        f"Блок «{block_id}» отклонялся {count} раз(а). "
                        "Рассмотрите пересмотр формулировки в промпте для этого блока."
                    ),
                })

        signals.sort(key=lambda s: s.get("correction_count", 0) + s.get("rejection_count", 0), reverse=True)
        return signals


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

    @staticmethod
    def _validate_path_component(value: str, label: str) -> None:
        # Defense-in-depth: ids come from generate_id(), but the storage
        # layer must not trust callers — reject separators/traversal
        if not value or "/" in value or "\\" in value or ".." in value:
            raise ValueError(f"Unsafe {label} for storage path: {value!r}")

    def _case_path(self, case_id: str, user_id: str | None = None):
        self._validate_path_component(case_id, "case_id")
        if user_id:
            self._validate_path_component(user_id, "user_id")
            d = self._users_dir / user_id / "cases"
            d.mkdir(parents=True, exist_ok=True)
            return d / f"{case_id}.json"
        return self._dir / f"{case_id}.json"

    def _load_all(self):
        import json, logging
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
        "article_input_text": case.article_input_text,
        "upload_metadata": case.upload_metadata,
        "russian_surface_cache": (
            dict(case.russian_surface_cache)
            if case.russian_surface_cache else {}
        ),
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
        ("compliance_checklist", "compliance_checklist"),
        ("submission_pack", "submission_pack"),
        ("bibliography_profile", "bibliography_profile"),
        ("publication_regime", "publication_regime"),
        ("investigated_venue", "investigated_venue"),
        ("article_field_position", "article_field_position"),
        ("venue_field_position", "venue_field_position"),
        ("source_evidence_packet", "source_evidence_packet"),
        ("protected_core_policy", "protected_core_policy"),
        ("evidence_policy", "evidence_policy"),
        ("venue_profile_package", "venue_profile_package"),
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

    if case.discipline_matches is not None:
        snap["discipline_matches"] = case.discipline_matches
    if case.region_hint and case.region_hint != "auto":
        snap["region_hint"] = case.region_hint

    # Track A: intake-choice override audit trail.
    if case.classifier_input_type is not None:
        snap["classifier_input_type"] = case.classifier_input_type
    if case.classifier_confidence is not None:
        snap["classifier_confidence"] = case.classifier_confidence
    if case.classifier_needs_user_choice:
        snap["classifier_needs_user_choice"] = True
    if case.user_selected_input_type is not None:
        snap["user_selected_input_type"] = case.user_selected_input_type
    if case.effective_input_type is not None:
        snap["effective_input_type"] = case.effective_input_type
    if case.override_source and case.override_source != "classifier":
        snap["override_source"] = case.override_source
    if case.override_at is not None:
        snap["override_at"] = case.override_at

    if case.refinement_chat:
        snap["refinement_chat"] = case.refinement_chat

    if case.venue_source_metadata is not None:
        snap["venue_source_metadata"] = case.venue_source_metadata
    if case.adapter_mode and case.adapter_mode != "offline_stub":
        snap["adapter_mode"] = case.adapter_mode
    if case.discipline_intent is not None:
        snap["discipline_intent"] = case.discipline_intent
    if case.venue_family_context is not None:
        snap["venue_family_context"] = case.venue_family_context
    if case.depth_mode and case.depth_mode != "standard":
        snap["depth_mode"] = case.depth_mode
    if case.budget_constraints is not None:
        snap["budget_constraints"] = case.budget_constraints

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
    case.article_input_text = data.get("article_input_text", "")
    case.upload_metadata = data.get("upload_metadata") or None
    cache = data.get("russian_surface_cache")
    case.russian_surface_cache = cache if isinstance(cache, dict) else {}
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
        "compliance_checklist": ComplianceChecklist,
        "submission_pack": SubmissionPack,
        "bibliography_profile": BibliographyProfile,
        "publication_regime": PublicationRegimeModel,
        "investigated_venue": VenueModel,
        "article_field_position": FieldPositionModel,
        "venue_field_position": FieldPositionModel,
        "source_evidence_packet": SourceEvidencePacket,
        "protected_core_policy": ProtectedCorePolicy,
        "evidence_policy": EvidencePolicy,
        "venue_profile_package": VenueProfilePackage,
    }
    for key, cls in model_map.items():
        raw = data.get(key)
        if raw is not None and isinstance(raw, dict):
            try:
                setattr(case, key, cls.from_dict(raw))
            except Exception as exc:
                logger.warning(
                    "Snapshot field %s failed to deserialize (dropped): %s",
                    key, exc,
                )

    fpm_fit = data.get("field_position_fit")
    if isinstance(fpm_fit, dict):
        case.field_position_fit = fpm_fit

    pbc = data.get("policy_blocked_changes")
    if isinstance(pbc, list):
        case.policy_blocked_changes = pbc

    dm = data.get("discipline_matches")
    if isinstance(dm, dict):
        case.discipline_matches = dm
    region = data.get("region_hint")
    if isinstance(region, str) and region:
        case.region_hint = region

    # Track A: intake-choice override audit trail.
    if isinstance(data.get("classifier_input_type"), str):
        case.classifier_input_type = data["classifier_input_type"]
    if isinstance(data.get("classifier_confidence"), str):
        case.classifier_confidence = data["classifier_confidence"]
    if data.get("classifier_needs_user_choice"):
        case.classifier_needs_user_choice = True
    if isinstance(data.get("user_selected_input_type"), str):
        case.user_selected_input_type = data["user_selected_input_type"]
    if isinstance(data.get("effective_input_type"), str):
        case.effective_input_type = data["effective_input_type"]
    if isinstance(data.get("override_source"), str):
        case.override_source = data["override_source"]
    if isinstance(data.get("override_at"), str):
        case.override_at = data["override_at"]

    rc = data.get("refinement_chat")
    if isinstance(rc, list):
        case.refinement_chat = rc

    vsm = data.get("venue_source_metadata")
    if isinstance(vsm, dict):
        case.venue_source_metadata = vsm
    am = data.get("adapter_mode")
    if isinstance(am, str) and am:
        case.adapter_mode = am
    di = data.get("discipline_intent")
    if isinstance(di, dict):
        case.discipline_intent = di
    vfc = data.get("venue_family_context")
    if isinstance(vfc, dict):
        case.venue_family_context = vfc
    dm = data.get("depth_mode")
    if isinstance(dm, str) and dm:
        case.depth_mode = dm
    bc = data.get("budget_constraints")
    if isinstance(bc, dict):
        case.budget_constraints = bc

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


# NOTE: the legacy keyword-based ``_classify_input`` was removed in the
# Phase A LLM-classifier migration. Routing now goes through
# ``Case._classify_input_llm`` which dispatches to
# ``InputClassifierAgent``. When the LLM provider is unavailable, the
# agent returns ``input_type=unknown`` with ``needs_user_choice=True``
# rather than guessing — the UI then asks the user to pick a chip.
