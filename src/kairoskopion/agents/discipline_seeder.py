"""DisciplineSeederAgent (Phase B2).

Consumes one or more ``DisciplineSourcePacket`` objects and produces a
draft ``DisciplineModel`` card with provenance back to the packets.
Output ships as ``source_status="llm_draft"`` — curator promotes
later. The agent must NOT auto-promote.

The seeder is the only path from a packet to a registry row. There is
no shortcut from raw web search → discipline card.
"""

from __future__ import annotations

import datetime
import json
import logging
import re

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
from ..prompts.discipline_seeding import (
    DISCIPLINE_SEEDING_FAMILY,
    validate_seeding,
)
from ..services.discipline_registry import DisciplineModel, DisciplineSourcePacket
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "anon"


def _default_id(discipline_name: str, region: str) -> str:
    prefix = "ru" if region == "ru" else "intl"
    return f"{prefix}-{_slug(discipline_name)}"


def _evidence_refs_from_packets(packets: list[DisciplineSourcePacket]) -> list[dict]:
    out: list[dict] = []
    for p in packets:
        # The DisciplineModel evidence_ref shape uses 'excerpt', not 'raw_excerpt'.
        ref = {"source_type": p.source_type}
        if p.source_id:
            ref["source_id"] = p.source_id
        if p.source_url:
            ref["source_url"] = p.source_url
        if p.retrieved_at:
            ref["retrieved_at"] = p.retrieved_at
        if p.raw_excerpt:
            ref["excerpt"] = p.raw_excerpt[:600]
        out.append(ref)
    return out


class DisciplineSeederAgent(AgentRole):
    role_id = "discipline_seeder"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        discipline_name = (inp.entities.get("discipline_name") or "").strip()
        region = (inp.entities.get("region") or "international").strip() or "international"
        raw_packets = inp.entities.get("packets") or []
        packets: list[DisciplineSourcePacket] = []
        for p in raw_packets:
            if isinstance(p, DisciplineSourcePacket):
                packets.append(p)
            elif isinstance(p, dict):
                packets.append(DisciplineSourcePacket.from_dict(p))

        if not discipline_name or not packets:
            return self._deterministic_with_attempt(
                discipline_name=discipline_name,
                region=region,
                packets=packets,
                meta=LLMAttemptMetadata.not_attempted(),
            )

        family = DISCIPLINE_SEEDING_FAMILY
        user_prompt = family["user_prompt_template"].format(
            discipline_name=discipline_name,
            region=region,
            packets_json=json.dumps(
                [p.to_dict() for p in packets], ensure_ascii=False, indent=2,
            )[:8000],
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.3,
                max_tokens=max_tokens_for_role(self.role_id),
                agent_role="discipline_seeder",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("seeder LLM call failed: %s", exc)
            return self._deterministic_with_attempt(
                discipline_name=discipline_name,
                region=region,
                packets=packets,
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
                    packets=packets,
                    meta=LLMAttemptMetadata.fallback(
                        reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
                        provider="openai_compatible",
                        model=response.model,
                        latency_ms=response.latency_ms,
                        validation_errors=outcome.validation_errors,
                        parse_status=outcome.status,
                    ),
                )
            parsed = outcome.parsed

        warnings = validate_seeding(parsed)

        # Defensive normalization
        parsed.setdefault("discipline_id", _default_id(discipline_name, region))
        parsed.setdefault("display_names", {})
        if region == "ru" and "ru" not in parsed["display_names"]:
            parsed["display_names"]["ru"] = discipline_name
        elif region != "ru" and "en" not in parsed["display_names"]:
            parsed["display_names"]["en"] = discipline_name
        parsed["region"] = region
        parsed["source_status"] = "llm_draft"
        # Always anchor evidence_refs in the input packets — no fabricated provenance.
        parsed["evidence_refs"] = _evidence_refs_from_packets(packets)
        parsed.setdefault("last_updated", datetime.date.today().isoformat())
        parsed.setdefault("schema_version", "1.0.0")
        parsed.setdefault("model_version", "0.1.0")

        try:
            card = DisciplineModel.from_dict(parsed)
        except Exception as exc:  # noqa: BLE001
            return self._deterministic_with_attempt(
                discipline_name=discipline_name,
                region=region,
                packets=packets,
                meta=LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
                    provider="openai_compatible",
                    model=response.model,
                    latency_ms=response.latency_ms,
                    validation_errors=[str(exc)[:240]],
                ),
            )

        return AgentOutput(
            output_entity_type="DisciplineModel",
            output_entity={
                "card": card.to_dict(),
                "extraction_attempt": LLMAttemptMetadata.parse_ok(
                    provider="openai_compatible",
                    model=response.model,
                    latency_ms=response.latency_ms,
                    content_present=bool(response.content),
                ).to_dict(),
            },
            confidence="medium",
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def _deterministic_with_attempt(
        self,
        discipline_name: str,
        region: str,
        packets: list[DisciplineSourcePacket],
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        # Honest minimal card: identity only + provenance from packets +
        # all working-tool fields empty + unknowns list filled. The card
        # is explicitly not useful as a working tool yet; that's the
        # signal to the curator that LLM seeding is required.
        slug = _slug(discipline_name) if discipline_name else "anon"
        card = DisciplineModel(
            discipline_id=_default_id(discipline_name, region) if discipline_name else f"intl-stub-{slug}",
            display_names={"ru" if region == "ru" else "en": discipline_name or "(unnamed)"},
            region=region or "international",
            source_status="llm_draft",
            last_updated=datetime.date.today().isoformat(),
            unknowns=[
                "paradigm", "epistemic_regime", "forms_of_evidence",
                "canonical_questions", "legitimate_objects",
                "illegitimate_or_borderline_objects", "argument_styles",
                "publication_genres", "institutional_forms",
            ],
        )
        # Anchor evidence_refs in input packets if any.
        if packets:
            from ..services.discipline_registry.model import EvidenceRef
            card.evidence_refs = [
                EvidenceRef(
                    source_type=p.source_type,
                    source_id=p.source_id,
                    source_url=p.source_url,
                    retrieved_at=p.retrieved_at,
                    excerpt=(p.raw_excerpt or "")[:600] or None,
                )
                for p in packets
            ]
        return AgentOutput(
            output_entity_type="DisciplineModel",
            output_entity={
                "card": card.to_dict(),
                "extraction_attempt": meta.to_dict(),
            },
            confidence="low",
            warnings=[
                "LLM seeder unavailable — card is identity-only stub; "
                "curator must complete working-tool fields"
            ],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        discipline_name = (inp.entities.get("discipline_name") or "").strip()
        region = (inp.entities.get("region") or "international").strip() or "international"
        raw_packets = inp.entities.get("packets") or []
        packets: list[DisciplineSourcePacket] = []
        for p in raw_packets:
            if isinstance(p, DisciplineSourcePacket):
                packets.append(p)
            elif isinstance(p, dict):
                packets.append(DisciplineSourcePacket.from_dict(p))
        return self._deterministic_with_attempt(
            discipline_name=discipline_name,
            region=region,
            packets=packets,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
