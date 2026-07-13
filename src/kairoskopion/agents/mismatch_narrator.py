"""MismatchNarratorAgent.

Reads a built MismatchMap + the source ArticleModel + VenueModel, and
asks an LLM to fill ``venue_side`` / ``description`` /
``possible_actions`` for every mismatch. ONE batch call per fit
assessment (not per-axis) — typical Sonnet round-trip on 6-12 axes
fits comfortably in the existing 90s timeout.

Honest deterministic fallback: returns the same input mismatches with
no narrative enrichment (keeping the empty ``venue_side`` + explicit
unknown set by ``services/mismatch_mapping.py`` in commit ee90523).
The fit chain detects "narrative_status: needs_llm" and the dossier
UI shows the existing italic "требуется LLM-комментарий по площадке"
label.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
    LLMAttemptMetadata,
)
from ..llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    repair_and_parse,
)
from ..llm.config import max_tokens_for_role
from ..llm.provider import LLMProvider
from ..prompts.mismatch_narrative import (
    MISMATCH_NARRATIVE_FAMILY,
    validate_mismatch_narrative,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


# Char caps for the compact representations shipped to the LLM. The
# article and venue are already-extracted structured objects — we
# don't need their full text. We only need enough context for the
# LLM to ground each narrative.
_ARTICLE_COMPACT_FIELDS = (
    "title_current", "language", "problem_statement",
    "object_of_inquiry", "core_claims", "key_terms",
    "method_status", "genre_current", "argument_structure_current",
    "novelty_mode", "disciplinary_register_current",
)
_VENUE_COMPACT_FIELDS = (
    "canonical_name", "venue_type", "scope_summary",
    "article_types_supported", "language_policy",
    "open_access_status", "anonymization_policy",
    "review_process_claims",
)


def _compact_article(article: dict[str, Any]) -> str:
    out: list[str] = []
    for f in _ARTICLE_COMPACT_FIELDS:
        v = article.get(f)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v if x)
        if isinstance(v, str) and len(v) > 400:
            v = v[:400] + "…"
        out.append(f"{f}: {v}")
    return "\n".join(out) or "(article fields empty)"


def _compact_venue(venue: dict[str, Any]) -> str:
    out: list[str] = []
    for f in _VENUE_COMPACT_FIELDS:
        v = venue.get(f)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v if x)
        if isinstance(v, str) and len(v) > 400:
            v = v[:400] + "…"
        out.append(f"{f}: {v}")
    return "\n".join(out) or "(venue fields empty)"


def _compact_mismatches(mismatches: list[dict[str, Any]]) -> str:
    """Render one line per mismatch with axis + severity + article side."""
    lines: list[str] = []
    for m in mismatches:
        axis = m.get("axis", "?")
        severity = m.get("severity", "?")
        article_side = (m.get("article_side") or "")[:160]
        lines.append(f"- axis={axis} severity={severity} article_side={article_side!r}")
    return "\n".join(lines) or "(no mismatches)"


class MismatchNarratorAgent(AgentRole):
    role_id = "mismatch_narrator"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        """LLM-driven enrichment. Input entities:

        - ``article``: ArticleModel dict
        - ``venue``: VenueModel dict
        - ``mismatches``: list of mismatch dicts (axis, severity, article_side, ...)

        Output entity:

        - ``narratives``: list of enriched objects, indexed by axis
        - ``extraction_attempt``: attempt metadata dict
        """
        article = inp.entities.get("article", {})
        venue = inp.entities.get("venue", {})
        mismatches = inp.entities.get("mismatches", [])

        if not mismatches:
            # Nothing to narrate. Empty result, parse_status=not_attempted.
            return self._honest_fallback(
                mismatches=[],
                meta=LLMAttemptMetadata.not_attempted(),
            )

        family = MISMATCH_NARRATIVE_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_compact=_compact_article(article),
            venue_compact=_compact_venue(venue),
            mismatches_compact=_compact_mismatches(mismatches),
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.2,
                max_tokens=max_tokens_for_role(self.role_id),
                agent_role="mismatch_narrator",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mismatch narrator LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(mismatches, meta)

        parsed = response.parsed
        if not isinstance(parsed, dict):
            outcome = repair_and_parse(response.content, schema=family["output_schema"])
            if outcome.status not in (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK):
                # Round-II: derive fallback_reason from outcome.status
                # so V2-B2 narrator_coverage surfaces the correct
                # category (invalid_json / repair_failed /
                # schema_validation_failed) instead of always reporting
                # schema_validation_failed.
                from ..llm.attempt_metadata import (
                    FALLBACK_REASON_INVALID_JSON,
                    FALLBACK_REASON_REPAIR_FAILED,
                )
                _reason_map = {
                    "schema_validation_failed": FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
                    "repair_failed": FALLBACK_REASON_REPAIR_FAILED,
                    "invalid_json": FALLBACK_REASON_INVALID_JSON,
                }
                reason = _reason_map.get(
                    outcome.status,
                    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
                )
                meta = LLMAttemptMetadata.fallback(
                    reason=reason,
                    provider="openai_compatible",
                    model=response.model,
                    latency_ms=response.latency_ms,
                    validation_errors=outcome.validation_errors,
                    parse_status=outcome.status,
                    repair_attempted=bool(outcome.repair_steps),
                    repair_steps=outcome.repair_steps,
                )
                return self._honest_fallback(mismatches, meta)
            parsed = outcome.parsed

        warnings = validate_mismatch_narrative(parsed)
        narratives_raw = parsed.get("narratives") or []
        # Validate that every input axis is covered. Missing axes get an
        # empty narrative — operator sees the honest gap.
        by_axis = {n.get("axis"): n for n in narratives_raw if isinstance(n, dict)}
        out_list: list[dict[str, Any]] = []
        for m in mismatches:
            axis = m.get("axis", "")
            n = by_axis.get(axis)
            if n is None:
                out_list.append({
                    "axis": axis,
                    "venue_side": "",
                    "description": "",
                    "possible_actions": [],
                    "narrative_status": "missing_from_llm_output",
                })
            else:
                out_list.append({
                    "axis": axis,
                    "venue_side": (n.get("venue_side") or "").strip(),
                    "description": (n.get("description") or "").strip(),
                    "possible_actions": list(n.get("possible_actions") or []),
                    "narrative_status": "llm_filled",
                })

        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model=response.model,
            latency_ms=response.latency_ms,
            content_present=bool(response.content),
        )
        return AgentOutput(
            output_entity_type="MismatchNarratives",
            output_entity={
                "narratives": out_list,
                "extraction_attempt": meta.to_dict(),
            },
            confidence="medium",
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def _honest_fallback(
        self,
        mismatches: list[dict[str, Any]],
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        """Mirror each mismatch with empty narrative + needs_llm marker.

        The dossier UI already renders empty ``venue_side`` as an italic
        "требуется LLM-комментарий по площадке" hint (UI4 closure in
        commit 25166f3), so this fallback is honest without UI changes.
        """
        narratives = [
            {
                "axis": m.get("axis", ""),
                "venue_side": "",
                "description": "",
                "possible_actions": [],
                "narrative_status": "needs_llm",
            }
            for m in mismatches
        ]
        return AgentOutput(
            output_entity_type="MismatchNarratives",
            output_entity={
                "narratives": narratives,
                "extraction_attempt": meta.to_dict(),
            },
            confidence="low",
            warnings=[
                "LLM mismatch narrator unavailable — venue_side / "
                "description / possible_actions left empty; UI surfaces "
                "the 'requires LLM commentary' hint"
            ],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        mismatches = inp.entities.get("mismatches", [])
        return self._honest_fallback(
            mismatches=mismatches,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )


def enrich_mismatch_map_in_place(
    mismatch_map_obj: Any,
    narratives: list[dict[str, Any]],
) -> int:
    """Apply LLM narratives to an existing MismatchMap dataclass.

    Each ``narratives`` entry is keyed by ``axis`` and supplies
    ``venue_side`` / ``description`` (when non-empty) / ``possible_actions``.
    Empty fields are NOT overwritten — the deterministic empty string
    survives so the UI's italic "requires LLM commentary" hint stays
    truthful when the agent didn't fill the field.

    Returns the count of mismatches actually enriched.
    """
    if mismatch_map_obj is None or not hasattr(mismatch_map_obj, "mismatches"):
        return 0
    by_axis = {n.get("axis"): n for n in narratives if isinstance(n, dict)}
    n_enriched = 0
    for m in mismatch_map_obj.mismatches:
        axis = m.get("axis", "") if isinstance(m, dict) else getattr(m, "axis", "")
        n = by_axis.get(axis)
        if n is None or n.get("narrative_status") not in ("llm_filled",):
            continue
        if isinstance(m, dict):
            target = m
        else:
            target = m  # MismatchItem dataclass; dataclass field assignment works
        # Only overwrite if the LLM produced something meaningful.
        new_venue_side = (n.get("venue_side") or "").strip()
        new_description = (n.get("description") or "").strip()
        new_actions = list(n.get("possible_actions") or [])
        if isinstance(target, dict):
            if new_venue_side:
                target["venue_side"] = new_venue_side
            if new_description:
                target["description"] = new_description
            if new_actions:
                target["possible_actions"] = new_actions
        else:
            if new_venue_side:
                setattr(target, "venue_side", new_venue_side)
            if new_description:
                setattr(target, "description", new_description)
            if new_actions:
                setattr(target, "possible_actions", new_actions)
        n_enriched += 1
    return n_enriched
