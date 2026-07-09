"""DisciplineSourceAcquisitionAgent (Phase B2).

Given a discipline name + region, identifies authoritative classification
entries (ВАК / OECD FORD / ERC / ISCED-F / etc.) and produces 0-3
``DisciplineSourcePacket`` objects with provenance for downstream
seeding.

LLM path uses ``DISCIPLINE_SOURCE_ACQUISITION_FAMILY``.
Deterministic fallback returns a single ``other`` packet marked
``confidence=low`` so the seeder downstream sees clearly that no LLM
was available and the curator must add real sources by hand.

NEVER fabricates classification codes — see prompt anti-rules.
"""

from __future__ import annotations

import datetime
import logging

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
)
from ..llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    repair_and_parse,
)
from ..llm.provider import LLMProvider
from ..prompts.discipline_source_acquisition import (
    DISCIPLINE_SOURCE_ACQUISITION_FAMILY,
    validate_source_acquisition,
)
from ..services.discipline_registry import DisciplineSourcePacket
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _slug(s: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "anon"


def _packets_from_payload(
    payload: dict,
    discipline_name: str,
    region: str,
    retrieved_at: str | None = None,
) -> list[DisciplineSourcePacket]:
    out: list[DisciplineSourcePacket] = []
    for entry in payload.get("packets", []):
        source_type = entry.get("source_type", "other")
        # The packet model requires source_id; if the LLM didn't supply
        # a real code, synthesize a stable placeholder so the curator
        # sees clearly which entry needs verification.
        source_id = entry.get("source_id") or f"{source_type}:unknown:{_slug(discipline_name)}"
        out.append(DisciplineSourcePacket(
            source_type=source_type,
            source_id=source_id,
            candidate_display_name_ru=discipline_name if region == "ru" else None,
            candidate_display_name_en=discipline_name if region != "ru" else None,
            candidate_region=region,
            source_url=entry.get("source_url"),
            retrieved_at=retrieved_at,
            raw_excerpt=entry.get("excerpt") or "",
            raw_facets={"confidence": entry.get("confidence", "low")},
        ))
    return out


class DisciplineSourceAcquisitionAgent(AgentRole):
    role_id = "discipline_source_acquisition"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        discipline_name = (inp.entities.get("discipline_name") or "").strip()
        region = (inp.entities.get("region") or "international").strip() or "international"
        hints = inp.entities.get("hints") or []
        if not discipline_name:
            return self._deterministic_with_attempt(
                discipline_name="",
                region=region,
                meta=LLMAttemptMetadata.not_attempted(),
            )

        family = DISCIPLINE_SOURCE_ACQUISITION_FAMILY
        user_prompt = family["user_prompt_template"].format(
            discipline_name=discipline_name,
            region=region,
            hints=", ".join(hints) if hints else "(none)",
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
                max_tokens=1500,
                agent_role="discipline_source_acquisition",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("source acquisition LLM failed: %s", exc)
            return self._deterministic_with_attempt(
                discipline_name=discipline_name,
                region=region,
                meta=LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_PROVIDER_ERROR,
                    provider="openai_compatible",
                    validation_errors=[str(exc)[:240]],
                ),
            )

        parsed = response.parsed
        if not isinstance(parsed, dict):
            outcome = repair_and_parse(response.content, schema=family["output_schema"])
            if outcome.status not in (PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK) or outcome.parsed is None:
                return self._deterministic_with_attempt(
                    discipline_name=discipline_name,
                    region=region,
                    meta=LLMAttemptMetadata.fallback(
                        reason=FALLBACK_REASON_PROVIDER_ERROR,
                        provider="openai_compatible",
                        model=response.model,
                        latency_ms=response.latency_ms,
                        validation_errors=outcome.validation_errors,
                        parse_status=outcome.status,
                    ),
                )
            parsed = outcome.parsed

        warnings = validate_source_acquisition(parsed)
        packets = _packets_from_payload(parsed, discipline_name, region)
        return AgentOutput(
            output_entity_type="DisciplineSourceAcquisitionResult",
            output_entity={
                "discipline_name": discipline_name,
                "region": region,
                "packets": [p.to_dict() for p in packets],
                "reasoning": parsed.get("reasoning", ""),
                "extraction_attempt": LLMAttemptMetadata.parse_ok(
                    provider="openai_compatible",
                    model=response.model,
                    latency_ms=response.latency_ms,
                    content_present=bool(response.content),
                ).to_dict(),
            },
            confidence="high" if packets else "low",
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def _deterministic_with_attempt(
        self,
        discipline_name: str,
        region: str,
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        # Honest fallback: NO invented codes. Single "other" packet with
        # a clear marker that this is a manual-curator stub.
        slug = _slug(discipline_name) if discipline_name else "anon"
        stub_packet = DisciplineSourcePacket(
            source_type="other",
            source_id=f"manual:curator-stub:{slug}",
            candidate_display_name_ru=discipline_name if region == "ru" else None,
            candidate_display_name_en=discipline_name if region != "ru" else None,
            candidate_region=region,
            raw_excerpt=(
                "LLM unavailable. Curator must supply authoritative source "
                f"for discipline {discipline_name!r} ({region})."
            ),
            raw_facets={"confidence": "low"},
        )
        return AgentOutput(
            output_entity_type="DisciplineSourceAcquisitionResult",
            output_entity={
                "discipline_name": discipline_name,
                "region": region,
                "packets": [stub_packet.to_dict()],
                "reasoning": "LLM unavailable; curator-stub packet emitted.",
                "extraction_attempt": meta.to_dict(),
            },
            confidence="low",
            warnings=["LLM unavailable — curator must complete source identification"],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        discipline_name = (inp.entities.get("discipline_name") or "").strip()
        region = (inp.entities.get("region") or "international").strip() or "international"
        return self._deterministic_with_attempt(
            discipline_name=discipline_name,
            region=region,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
