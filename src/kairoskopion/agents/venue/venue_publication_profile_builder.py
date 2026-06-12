"""Venue Publication Profile Builder (UC-1, Phase 7 mandatory).

Populates VenuePublicationProfile from VenueModel, VenueEvidencePack,
or VenueRecord data. Fills what's available, marks unknowns explicitly.
"""

from __future__ import annotations

from typing import Any

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import VenuePublicationProfile


class VenuePublicationProfileBuilderAgent(AgentRole):
    role_id = "venue_publication_profile_builder"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        evidence_pack = inp.entities.get("evidence_pack", {})

        if not venue and not evidence_pack:
            return missing_input_output("VenuePublicationProfile", "venue or evidence_pack")

        profile = _build_profile(venue, evidence_pack)
        unknowns = _collect_unknowns(profile)

        return service_output(
            "VenuePublicationProfile",
            profile.to_dict(),
            unknowns=unknowns,
            evidence_refs=_extract_evidence_refs(venue, evidence_pack),
            confidence="medium" if len(unknowns) < 5 else "low",
            trace_notes=[f"built from venue+evidence_pack, {len(unknowns)} unknowns"],
        )


def _build_profile(
    venue: dict[str, Any],
    evidence_pack: dict[str, Any],
) -> VenuePublicationProfile:
    """Build VenuePublicationProfile from available data."""
    claims = evidence_pack.get("claims", [])
    claim_map: dict[str, str] = {}
    for c in claims:
        field = c.get("field_name", "")
        if field and c.get("value"):
            claim_map[field] = c["value"]

    disciplines = venue.get("disciplines", [])
    primary = disciplines[0] if disciplines else None
    method_exp = claim_map.get("method_expectations")

    return VenuePublicationProfile(
        venue_model_id=venue.get("venue_model_id"),
        primary_discipline=primary,
        disciplinary_center=disciplines,
        method_expectations=[method_exp] if method_exp else [],
        citation_ecology_expectations=claim_map.get("citation_ecology_expectations"),
        unknowns=_collect_profile_unknowns(venue, evidence_pack),
        evidence_refs=_extract_evidence_refs(venue, evidence_pack),
    )


def _collect_profile_unknowns(venue: dict, pack: dict) -> list[str]:
    unknowns = []
    if not venue.get("disciplines"):
        unknowns.append("No disciplinary center available")
    if not pack.get("claims"):
        unknowns.append("No evidence pack claims available")
    unknowns.append("Corpus/editorial/citation profiles not populated — needs deep profiling")
    return unknowns


def _collect_unknowns(profile: VenuePublicationProfile) -> list[str]:
    unknowns = list(profile.unknowns) if profile.unknowns else []
    if not profile.primary_discipline:
        unknowns.append("Primary discipline unknown")
    if not profile.genre_move_distribution:
        unknowns.append("Genre/move distribution not available")
    if profile.corpus_size is None:
        unknowns.append("Corpus analysis not available")
    return unknowns


def _extract_evidence_refs(venue: dict, pack: dict) -> list[str]:
    refs = []
    if venue.get("venue_model_id"):
        refs.append(venue["venue_model_id"])
    for src in pack.get("sources", []):
        if src.get("venue_source_id"):
            refs.append(src["venue_source_id"])
    return refs
