"""Article Modeler agent (spec §54).

LLM-backed extraction of ArticleModel from manuscript text,
with deterministic fallback to regex heuristics.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..enums import (
    ArticleStage,
    EvidenceStatus,
    Genre,
    InputMode,
    LifecycleStatus,
    MethodStatus,
    NoveltyMode,
)
from ..ids import article_model_id, manuscript_id
from ..llm.attempt_metadata import (
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_REPAIR_FAILED,
    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
    LLMAttemptMetadata,
)
from ..llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
    repair_and_parse,
)
from ..llm.provider import LLMProvider
from ..prompts.article_modeling import (
    ARTICLE_MODELING_FAMILY,
    validate_article_extraction,
)
from ..schema import ArticleModel, ManuscriptModel
from ..services.article_modeling import (
    build_article_model as _deterministic_article,
    build_manuscript_model as _deterministic_manuscript,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class ArticleModelerAgent(AgentRole):
    role_id = "article_modeler"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        text = inp.raw_text or ""
        source_ref = inp.source_refs[0] if inp.source_refs else None

        # Always build deterministic manuscript model (word count, sections, etc.)
        manuscript = _deterministic_manuscript(text, source_ref=source_ref)

        # LLM extraction — apply prompt override if set by pipeline
        family = dict(ARTICLE_MODELING_FAMILY)
        _ovr = getattr(self, "_prompt_family_override", None)
        if _ovr:
            if "system_prompt" in _ovr:
                family["system_prompt"] = _ovr["system_prompt"]
            if "user_prompt_template" in _ovr:
                family["user_prompt_template"] = _ovr["user_prompt_template"]
        user_prompt = family["user_prompt_template"].format(manuscript_text=text)
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.2,
                max_tokens=4096,
                agent_role="article_modeler",
            )
        except Exception as e:
            # Provider call itself failed (network, timeout, API error,
            # empty content guard). This is NOT a JSON-parse failure —
            # the LLM never produced content for us to try to parse.
            # Label honestly so the observability UI can show
            # "provider unavailable" vs "model returned bad JSON".
            logger.warning("LLM call failed for article_modeler, falling back: %s", e)
            err_code = getattr(e, "error_code", None) or e.__class__.__name__
            exc_attempts = getattr(e, "attempts", [])
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                model=None,
                validation_errors=[f"{err_code}: {str(e)[:200]}"],
                parse_status="not_attempted",
                attempts=exc_attempts,
                final_error_code=getattr(e, "error_code", None),
                agent_role="article_modeler",
            )
            return self._deterministic_with_attempt(inp, meta)

        provider_model = response.model
        latency_ms = response.latency_ms
        content_present = bool(response.content)
        parsed = response.parsed

        # First try: provider already gave us parsed JSON
        if isinstance(parsed, dict):
            outcome_status = PARSE_STATUS_PARSED_OK
            outcome_steps: list[str] = []
            outcome_errors: list[str] = []
            repaired = False
        else:
            # Provider parse failed — run our bounded repair pass
            outcome = repair_and_parse(
                response.content, schema=family.get("output_schema"),
            )
            parsed = outcome.parsed
            outcome_status = outcome.status
            outcome_steps = outcome.repair_steps
            outcome_errors = outcome.validation_errors
            repaired = outcome_status == PARSE_STATUS_REPAIRED_OK
            if parsed is None or outcome_status not in (
                PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK,
            ):
                # Decide fallback reason
                reason = (
                    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED
                    if outcome_status == PARSE_STATUS_SCHEMA_VALIDATION_FAILED
                    else (
                        FALLBACK_REASON_REPAIR_FAILED
                        if outcome_steps
                        else FALLBACK_REASON_INVALID_JSON
                    )
                )
                logger.warning(
                    "LLM article_modeler fallback: reason=%s steps=%s errors=%s",
                    reason, outcome_steps, outcome_errors,
                )
                meta = LLMAttemptMetadata.fallback(
                    reason=reason,
                    provider="openai_compatible",
                    model=provider_model,
                    latency_ms=latency_ms,
                    content_present=content_present,
                    repair_attempted=bool(outcome_steps),
                    repair_steps=outcome_steps,
                    validation_errors=outcome_errors,
                    parse_status=outcome_status,
                    requested_model=getattr(response, "requested_model", None),
                    effective_model=getattr(response, "effective_model", None),
                    attempt_count=getattr(response, "attempt_count", 1),
                    attempts=getattr(response, "attempts", []),
                    agent_role="article_modeler",
                )
                return self._deterministic_with_attempt(inp, meta)

        # Validate semantic shape (warnings only — does not gate fallback)
        validation_warnings = validate_article_extraction(parsed)

        # Build ArticleModel from LLM output + deterministic diagnostics
        article = _build_from_llm(parsed, manuscript, text, source_ref)

        # Attach attempt metadata — this is the audit trail that surfaces
        # in API + human view.
        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model=provider_model,
            latency_ms=latency_ms,
            content_present=content_present,
            repaired=repaired,
            repair_steps=outcome_steps,
            requested_model=getattr(response, "requested_model", None),
            effective_model=getattr(response, "effective_model", None),
            attempt_count=getattr(response, "attempt_count", 1),
            attempts=getattr(response, "attempts", []),
            agent_role="article_modeler",
        )
        if getattr(response, "fallback_used", False):
            meta.fallback_used = True
            meta.fallback_reason = "primary_model_failed"
        article.extraction_attempt = meta.to_dict()

        return AgentOutput(
            output_entity_type="ArticleModel",
            output_entity=article.to_dict(),
            evidence_refs=[source_ref] if source_ref else [],
            unknowns=parsed.get("unknowns", []),
            assumptions=parsed.get("assumptions", []),
            confidence=parsed.get("confidence", "medium"),
            warnings=validation_warnings + parsed.get("warnings", []),
            questions_for_user=parsed.get("questions_for_user", []),
            quality_gate_status="preliminary",
            trace_notes=[
                f"LLM model: {response.model}",
                f"Tokens: {response.input_tokens}+{response.output_tokens}",
                f"Latency: {response.latency_ms:.0f}ms",
                f"parse_status: {meta.parse_status}",
                f"repair_steps: {','.join(outcome_steps) if outcome_steps else 'none'}",
            ],
            evidence_status=EvidenceStatus.INFERENCE.value,
            llm_usage={
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "extraction_attempt": meta.to_dict(),
            },
        )

    def _deterministic_with_attempt(
        self, inp: AgentInput, meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        """Run the deterministic fallback AND annotate the result with the
        captured LLM attempt metadata, so the UI can surface the warning.
        """
        out = self.execute_deterministic(inp)
        # Attach attempt metadata onto the ArticleModel dict so the
        # CaseStore persists it and the API surfaces it.
        if isinstance(out.output_entity, dict):
            out.output_entity["extraction_attempt"] = meta.to_dict()
        else:
            try:
                out.output_entity.extraction_attempt = meta.to_dict()
            except Exception:  # noqa: BLE001
                pass
        # Annotate trace + warnings too
        out.trace_notes = list(out.trace_notes or []) + [
            f"fallback_reason: {meta.fallback_reason}",
            f"parse_status: {meta.parse_status}",
        ]
        if meta.warning_for_user:
            out.warnings = list(out.warnings or []) + [meta.warning_for_user]
        return out

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        text = inp.raw_text or ""
        source_ref = inp.source_refs[0] if inp.source_refs else None

        manuscript = _deterministic_manuscript(text, source_ref=source_ref)
        article = _deterministic_article(manuscript, text, source_ref=source_ref)

        return AgentOutput(
            output_entity_type="ArticleModel",
            output_entity=article.to_dict(),
            evidence_refs=[source_ref] if source_ref else [],
            unknowns=article.unknowns,
            assumptions=[],
            confidence=article.confidence or "low",
            warnings=["Deterministic extraction: limited accuracy"],
            questions_for_user=[],
            quality_gate_status="preliminary",
            trace_notes=["Deterministic heuristic extraction (no LLM)"],
            evidence_status="heuristic",
        )


def _build_from_llm(
    parsed: dict[str, Any],
    manuscript: ManuscriptModel,
    text: str,
    source_ref: str | None,
) -> ArticleModel:
    """Merge LLM extraction with deterministic diagnostics."""
    # Deterministic fields that LLM should not compute
    sections = manuscript.sections
    word_count = manuscript.word_count
    ref_count = len(manuscript.bibliography_refs)
    lower_text = text.lower()
    sections_lower = [s.lower() for s in sections]
    has_refs_section = any("reference" in s or "bibliography" in s for s in sections_lower)
    has_methods_section = any("method" in s for s in sections_lower)
    has_data_stmt = "data availability" in lower_text or "data sharing" in lower_text
    ai_patterns = [
        "ai disclosure", "ai was used", "ai tools were used",
        "generated by ai", "assisted by ai", "ai-assisted writing",
        "use of artificial intelligence in the preparation",
        "ai writing tool", "language model was used", "llm was used",
        "chatgpt was used", "used chatgpt",
    ]
    has_ai_disc = any(p in lower_text for p in ai_patterns)
    abstract_text = manuscript.abstract or ""

    def _enum_key(field: str) -> str:
        v = parsed.get(field, "unknown")
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k in ("value", "name", "type", "status", "mode"):
                if isinstance(v.get(k), str):
                    return v[k]
        return "unknown"

    # Map LLM article_stage to our enum
    stage_map = {
        "abstract": ArticleStage.ABSTRACT.value,
        "draft": ArticleStage.DRAFT.value,
        "full_manuscript": ArticleStage.FULL_MANUSCRIPT.value,
        "revision": ArticleStage.FULL_MANUSCRIPT.value,
        "unknown": ArticleStage.UNKNOWN.value,
    }
    stage = stage_map.get(_enum_key("article_stage"), ArticleStage.UNKNOWN.value)

    # Map genre — cover all enum values + common LLM synonyms
    genre_map = {
        "research_article": Genre.RESEARCH_ARTICLE.value,
        "theoretical_essay": Genre.THEORETICAL_ESSAY.value,
        "essay": Genre.THEORETICAL_ESSAY.value,
        "systematic_review": Genre.SYSTEMATIC_REVIEW.value,
        "review": Genre.REVIEW.value,
        "book_review": Genre.REVIEW.value,
        "literature_review": Genre.REVIEW.value,
        "commentary": Genre.COMMENTARY.value,
        "conceptual_article": Genre.CONCEPTUAL_ARTICLE.value,
        "position_paper": Genre.POSITION_PAPER.value,
        "conference_paper": Genre.CONFERENCE_PAPER.value,
        "forum_piece": Genre.FORUM_PIECE.value,
        "book_symposium_piece": Genre.BOOK_SYMPOSIUM_PIECE.value,
        "article": Genre.RESEARCH_ARTICLE.value,
        "unknown": Genre.UNKNOWN.value,
    }
    genre = genre_map.get(_enum_key("genre_current"), Genre.UNKNOWN.value)

    # Map method — cover all enum values + common LLM synonyms
    method_map = {
        "no_method": MethodStatus.NO_METHOD.value,
        "implicit_method": MethodStatus.IMPLICIT_METHOD.value,
        "conceptual_method": MethodStatus.CONCEPTUAL_METHOD.value,
        "conceptual": MethodStatus.CONCEPTUAL_METHOD.value,
        "empirical_method": MethodStatus.EMPIRICAL_METHOD.value,
        "empirical": MethodStatus.EMPIRICAL_METHOD.value,
        "case_based": MethodStatus.CASE_BASED.value,
        "case_study": MethodStatus.CASE_BASED.value,
        "mixed": MethodStatus.MIXED.value,
        "mixed_methods": MethodStatus.MIXED.value,
        "review_method": MethodStatus.REVIEW_METHOD.value,
        "unknown": MethodStatus.UNKNOWN.value,
    }
    method = method_map.get(_enum_key("method_status"), MethodStatus.UNKNOWN.value)

    # Map novelty
    novelty_map = {
        "new_theory": NoveltyMode.NEW_THEORY.value,
        "critique": NoveltyMode.CRITIQUE.value,
        "extension": NoveltyMode.NEW_SYNTHESIS.value,
        "translation_between_fields": NoveltyMode.TRANSLATION_BETWEEN_FIELDS.value,
        "application": NoveltyMode.NEW_APPLICATION.value,
        "synthesis": NoveltyMode.NEW_SYNTHESIS.value,
        "unknown": NoveltyMode.UNKNOWN.value,
    }
    novelty = novelty_map.get(_enum_key("novelty_mode"), NoveltyMode.UNKNOWN.value)

    # Input mode
    has_sections = len(sections) >= 3
    has_substantial = word_count is not None and word_count > 500
    has_full = has_sections and has_substantial
    input_mode = InputMode.FULL_MANUSCRIPT.value if has_full else InputMode.ABSTRACT_ONLY.value

    def _pick(*keys: str, default=None):
        for k in keys:
            v = parsed.get(k)
            if v not in (None, "", []):
                return v
        return default

    def _to_list(v) -> list:
        if v is None or v == "":
            return []
        if isinstance(v, list):
            items = []
            for x in v:
                if isinstance(x, str):
                    items.append(x)
                elif isinstance(x, dict):
                    for k in ("value", "claim", "name", "text", "term"):
                        if isinstance(x.get(k), str):
                            items.append(x[k])
                            break
                    else:
                        items.append(str(x))
                else:
                    items.append(str(x))
            return items
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            for k in ("value", "name", "text"):
                if isinstance(v.get(k), str):
                    return [v[k]]
            return [str(x) for x in v.values()]
        return [str(v)]

    def _coerce_str(v) -> str | None:
        if v is None:
            return None
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) if v else None
        if isinstance(v, dict):
            for k in ("value", "name", "text", "description"):
                if isinstance(v.get(k), str):
                    return v[k]
            return ", ".join(f"{dk}={dv}" for dk, dv in v.items()) if v else None
        return str(v) if v else None

    title_llm = _pick("title", "title_current", "title_ru", "title_en", "title_extracted")
    # Heuristic title extraction: if LLM missed the title, try the first
    # non-empty line of the raw text (common pattern in .md/.txt manuscripts).
    if not _coerce_str(title_llm) and not manuscript.title and text:
        import re as _re
        for line in text.split("\n"):
            candidate = line.strip().lstrip("#").strip()
            # Strip markdown bold markers **...**
            m_bold = _re.match(r"^\*\*(.+?)\*\*$", candidate)
            if m_bold:
                candidate = m_bold.group(1).strip()
            if candidate and 5 <= len(candidate) <= 300:
                title_llm = candidate
                break
    abstract_llm = _pick("abstract_summary", "abstract", "abstract_current", "abstract_ru", "abstract_en")
    pcore_llm = _pick(
        "protected_core_candidate",
        "protected_core",
        "protected_core_candidates",
        "core_protection",
        default=[],
    )
    mut_llm = _pick("mutable_zones", "mutable_zones_candidates", "flexible_zones", default=[])

    return ArticleModel(
        article_model_id=article_model_id(),
        source_refs=[source_ref] if source_ref else [],
        title_current=_coerce_str(title_llm) or manuscript.title,
        abstract_current=_coerce_str(abstract_llm) or manuscript.abstract,
        language=_coerce_str(parsed.get("language")) or manuscript.language,
        input_mode=input_mode,
        article_stage=stage,
        problem_statement=_coerce_str(parsed.get("problem_statement")),
        research_question=_coerce_str(parsed.get("research_question")),
        object_of_inquiry=_coerce_str(parsed.get("object_of_inquiry")),
        core_claims=_to_list(parsed.get("core_claims")),
        genre_current=genre,
        disciplinary_register_current=_coerce_str(parsed.get("disciplinary_register_current")),
        novelty_mode=novelty,
        method_status=method,
        method_description=_coerce_str(parsed.get("method_description")),
        theoretical_shoulders=_to_list(parsed.get("theoretical_shoulders")),
        citation_ecology_current=_coerce_str(parsed.get("citation_ecology_description"))
            or (f"{ref_count} references found" if ref_count else "no bibliography found"),
        protected_core=_to_list(pcore_llm),
        mutable_zones=_to_list(mut_llm),
        unknowns=_to_list(parsed.get("unknowns")),
        confidence=parsed.get("confidence", "medium"),
        evidence_refs=[source_ref] if source_ref else [],
        lifecycle_status=LifecycleStatus.PRELIMINARY.value,
        # Deterministic diagnostic fields
        word_count=word_count,
        section_count=len(sections),
        reference_count=ref_count,
        abstract_length=len(abstract_text.split()) if abstract_text else None,
        has_references_section=has_refs_section,
        has_methods_section=has_methods_section,
        has_data_availability_statement=has_data_stmt,
        has_ai_disclosure=has_ai_disc,
        manuscript_stage=stage,
        extraction_status="llm_assisted",
    )
