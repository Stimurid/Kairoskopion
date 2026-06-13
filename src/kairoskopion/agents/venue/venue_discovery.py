"""Venue Discovery Agent (UC-1 step 5).

Takes DisciplinaryPathway set + constraints and produces VenueCandidatePool
via the venue pool discovery pipeline. Supports fixture/offline and live modes.

No live web by default. No fake journal lists. No final recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...services.venue_pool_discovery import discover_venue_pool
from ...services.venue_candidate_identity import dedupe_candidates
from ...services.venue_candidate_screening import (
    build_candidate_evidence_matrix,
    screen_candidates,
)

logger = logging.getLogger(__name__)


class VenueDiscoveryAgent(AgentRole):
    role_id = "venue_discovery"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        pathways_raw = (
            inp.entities.get("disciplinary_pathways")
            or inp.entities.get("pathways")
            or []
        )
        scenario = inp.entities.get("scenario", {})
        seed_venues = inp.entities.get("seed_venues", []) or inp.entities.get("venue_pool", [])
        semantic_profile = inp.entities.get("semantic_profile", {})

        if isinstance(pathways_raw, dict):
            pathways = pathways_raw.get("pathways", [])
        else:
            pathways = pathways_raw

        if not pathways:
            return missing_input_output("VenueCandidatePool", "disciplinary_pathways")

        pool = discover_venue_pool(
            semantic_profile=semantic_profile,
            pathways=pathways,
            scenario=scenario,
            seed_venues=seed_venues,
        )

        pool_dict = pool.to_dict()
        candidates = pool_dict.get("candidates", [])

        # Deduplicate
        deduped, dedupe_notes, conflicts = dedupe_candidates(candidates)
        pool_dict["candidates"] = deduped
        pool_dict["dedupe_notes"] = dedupe_notes
        for cf in conflicts:
            pool_dict.setdefault("rejected_candidates", [])

        # Screen
        screening_results = screen_candidates(
            candidates=deduped,
            semantic_profile=semantic_profile,
            pathways=pathways,
            scenario=scenario,
        )

        matrix = build_candidate_evidence_matrix(
            pool=pool_dict,
            screening_results=screening_results,
        )

        unknowns = list(pool_dict.get("unknowns", []))
        unknowns.append("Venue discovery is preliminary — candidates are not recommendations")
        if not deduped:
            unknowns.append("No candidates discovered — search plan generated only")

        entity = {
            "pool": pool_dict,
            "screening_results": [sr.to_dict() for sr in screening_results],
            "evidence_matrix": matrix.to_dict(),
            "candidate_count": len(deduped),
            "screened_in_count": sum(
                1 for sr in screening_results
                if sr.status == "screened_in"
            ),
            "search_task_count": len(pool_dict.get("queries", [])),
        }

        confidence = "medium" if deduped else "low"

        return service_output(
            "VenueCandidatePool",
            entity,
            unknowns=unknowns,
            confidence=confidence,
            trace_notes=[
                f"pathways={len(pathways)}, seed_venues={len(seed_venues)}",
                f"candidates={len(deduped)}, queries={len(pool_dict.get('queries', []))}",
                f"dedupe_notes={len(dedupe_notes)}, conflicts={len(conflicts)}",
            ],
        )
