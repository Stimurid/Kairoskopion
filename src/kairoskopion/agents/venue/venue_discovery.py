"""Venue Discovery Agent (UC-1 step 5, Phase 7 mandatory).

Takes DisciplinaryPathway set + constraints and produces candidate
venue search tasks and/or matches from local seed corpus.

No live web by default. No fake journal lists.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class VenueDiscoveryAgent(AgentRole):
    role_id = "venue_discovery"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        pathways = inp.entities.get("disciplinary_pathways", [])
        scenario = inp.entities.get("scenario", {})
        seed_venues = inp.entities.get("seed_venues", [])

        if not pathways:
            return missing_input_output("VenueDiscoveryResult", "disciplinary_pathways")

        candidates = []
        search_tasks = []

        if isinstance(pathways, dict):
            pathways = pathways.get("pathways", [])

        language_constraint = scenario.get("language_constraint")

        for pw in pathways:
            discipline = pw.get("discipline_name", "unknown")
            strength = pw.get("fit_strength", "unknown")

            matched = _match_seed_venues(discipline, seed_venues, language_constraint)
            candidates.extend(matched)

            search_tasks.append({
                "discipline": discipline,
                "fit_strength": strength,
                "search_query_hints": [
                    f"{discipline} journals",
                    f"{discipline} peer-reviewed venues",
                ],
                "venue_type_hints": pw.get("venue_type_hints", []),
                "language_options": pw.get("language_options", []),
                "evidence_requirements": [
                    "Official venue homepage required",
                    "Author guidelines required",
                    "Indexing status verification required",
                ],
            })

        return service_output(
            "VenueDiscoveryResult",
            {
                "candidates": candidates,
                "search_tasks": search_tasks,
                "candidate_count": len(candidates),
                "search_task_count": len(search_tasks),
                "source": "seed_corpus_match" if candidates else "search_plan_only",
            },
            unknowns=_build_unknowns(candidates, search_tasks),
            confidence="medium" if candidates else "low",
            trace_notes=[
                f"pathways={len(pathways)}, seed_venues={len(seed_venues)}",
                f"candidates={len(candidates)}, search_tasks={len(search_tasks)}",
            ],
        )


def _match_seed_venues(
    discipline: str,
    seed_venues: list[dict[str, Any]],
    language_constraint: str | None,
) -> list[dict[str, Any]]:
    """Match seed venues against a discipline name."""
    if not seed_venues:
        return []

    discipline_lower = discipline.lower()
    candidates = []

    for venue in seed_venues:
        venue_disciplines = [
            d.lower() for d in (
                venue.get("disciplines", []) +
                [venue.get("scope_description", "")]
            )
        ]
        venue_name = venue.get("name", "").lower()

        score = 0
        for vd in venue_disciplines:
            if discipline_lower in vd or vd in discipline_lower:
                score += 2
            elif any(w in vd for w in discipline_lower.split()):
                score += 1

        if any(w in venue_name for w in discipline_lower.split() if len(w) > 3):
            score += 1

        if language_constraint:
            venue_langs = venue.get("languages", [])
            if venue_langs and language_constraint.lower() not in [l.lower() for l in venue_langs]:
                score -= 2

        if score > 0:
            candidates.append({
                "venue_name": venue.get("name", "unknown"),
                "venue_id": venue.get("venue_record_id") or venue.get("venue_model_id"),
                "match_score": score,
                "match_discipline": discipline,
                "evidence_status": "seed_corpus",
            })

    candidates.sort(key=lambda c: c["match_score"], reverse=True)
    return candidates


def _build_unknowns(candidates: list, search_tasks: list) -> list[str]:
    unknowns = []
    if not candidates:
        unknowns.append("No local venue corpus matches — search tasks generated instead")
    unknowns.append("Venue discovery does not query external databases in this version")
    if search_tasks:
        unknowns.append(f"{len(search_tasks)} search tasks need manual or adapter execution")
    return unknowns
