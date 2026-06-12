"""Venue Publication Profile Builder — depth-aware profile assembly.

Consumes VenueModel, VenueEvidencePack, VenueDepthCoverage, and optionally
PublishedArticleCorpus, CitationExpectationProfile, EditorialBoardProfile.

Fills known fields, derives corpus/citation/editorial fields only when data
exists, and lists missing L3/L4/L6/L7 as explicit unknowns.
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
        depth_coverage = inp.entities.get("depth_coverage", {})
        corpus = inp.entities.get("corpus", {})
        citation_profile = inp.entities.get("citation_profile", {})
        editorial_board = inp.entities.get("editorial_board", {})

        if not venue and not evidence_pack:
            return missing_input_output("VenuePublicationProfile", "venue or evidence_pack")

        profile = _build_profile(
            venue, evidence_pack, depth_coverage,
            corpus, citation_profile, editorial_board,
        )
        unknowns = _collect_unknowns(profile, depth_coverage, corpus, citation_profile, editorial_board)
        evidence_refs = _extract_evidence_refs(venue, evidence_pack)

        return service_output(
            "VenuePublicationProfile",
            profile.to_dict(),
            unknowns=unknowns,
            evidence_refs=evidence_refs,
            confidence=_compute_confidence(unknowns, corpus, depth_coverage),
            trace_notes=[f"built from venue+evidence_pack, {len(unknowns)} unknowns"],
        )


def _build_profile(
    venue: dict[str, Any],
    evidence_pack: dict[str, Any],
    depth_coverage: dict[str, Any],
    corpus: dict[str, Any],
    citation_profile: dict[str, Any],
    editorial_board: dict[str, Any],
) -> VenuePublicationProfile:
    claims = evidence_pack.get("claims", [])
    claim_map: dict[str, Any] = {}
    for c in claims:
        field = c.get("field_name", "")
        if field and c.get("value"):
            claim_map[field] = c["value"]

    disciplines = venue.get("disciplines", [])
    primary = disciplines[0] if disciplines else venue.get("primary_discipline")

    profile = VenuePublicationProfile(
        venue_model_id=venue.get("venue_model_id"),
        primary_discipline=primary,
        disciplinary_center=disciplines,
        audience_description=venue.get("scope_summary"),
    )

    # L1: method expectations from evidence pack claims
    method_exp = claim_map.get("method_expectations")
    if method_exp:
        profile.method_expectations = [method_exp] if isinstance(method_exp, str) else method_exp

    # Citation from claims
    profile.citation_ecology_expectations = claim_map.get("citation_ecology_expectations")

    # L3: corpus-derived fields — only when corpus data exists
    if corpus and corpus.get("corpus_size"):
        profile.corpus_size = corpus["corpus_size"]
        profile.corpus_period = corpus.get("collection_period")

        if corpus.get("genre_distribution"):
            profile.genre_move_distribution = corpus["genre_distribution"]

        if corpus.get("method_distribution"):
            methods = corpus["method_distribution"]
            profile.method_expectations = [
                m.get("method", m.get("name", "unknown"))
                for m in methods
                if m.get("fraction", 0) >= 0.1 or m.get("count", 0) >= 1
            ]

        if corpus.get("schools_and_traditions"):
            profile.schools_and_traditions_distribution = corpus["schools_and_traditions"]

    # L4: editorial board — only when editorial data exists
    if editorial_board and editorial_board.get("members"):
        if editorial_board.get("disciplinary_center"):
            if not profile.disciplinary_center:
                profile.disciplinary_center = editorial_board["disciplinary_center"]

    # L6: citation ecology — only when citation profile exists
    if citation_profile:
        if citation_profile.get("typical_reference_range"):
            profile.typical_reference_count_range = citation_profile["typical_reference_range"]
        if citation_profile.get("dominant_traditions"):
            profile.dominant_citation_traditions = citation_profile["dominant_traditions"]

    return profile


def _collect_unknowns(
    profile: VenuePublicationProfile,
    depth_coverage: dict[str, Any],
    corpus: dict[str, Any],
    citation_profile: dict[str, Any],
    editorial_board: dict[str, Any],
) -> list[str]:
    unknowns: list[str] = []

    if not profile.primary_discipline:
        unknowns.append("Primary discipline unknown")
    if not profile.genre_move_distribution:
        unknowns.append("Genre/move distribution not available — needs L3 corpus analysis")

    # L3 corpus
    if not corpus or not corpus.get("corpus_size"):
        unknowns.append("L3 corpus sample not available — corpus-derived fields unknown")
    if profile.corpus_size is None:
        unknowns.append("Corpus analysis not available — corpus_size is None")

    # L4 editorial
    if not editorial_board or not editorial_board.get("members"):
        unknowns.append("L4 editorial board data not available — editorial intelligence unknown")

    # L6 citation
    if not citation_profile:
        unknowns.append("L6 citation ecology profile not available — citation expectations unknown")

    # L7 user memory
    unknowns.append("L7 user memory/outcomes not available")

    # Depth coverage notes
    if depth_coverage:
        reached = depth_coverage.get("reached_depth", "")
        purpose = depth_coverage.get("purpose", "")
        if reached and purpose:
            unknowns.append(f"Depth coverage: reached {reached} for purpose '{purpose}'")
        missing = depth_coverage.get("missing_required_sources", [])
        for src in missing:
            unknowns.append(f"Missing required source: {src}")

    return unknowns


def _compute_confidence(
    unknowns: list[str],
    corpus: dict[str, Any],
    depth_coverage: dict[str, Any],
) -> str:
    if len(unknowns) <= 3 and corpus and corpus.get("corpus_size", 0) >= 20:
        return "medium"
    if len(unknowns) <= 5:
        return "low"
    return "low"


def _extract_evidence_refs(venue: dict, pack: dict) -> list[str]:
    refs = []
    if venue.get("venue_model_id"):
        refs.append(venue["venue_model_id"])
    for src in pack.get("sources", []):
        if src.get("venue_source_id"):
            refs.append(src["venue_source_id"])
    return refs
