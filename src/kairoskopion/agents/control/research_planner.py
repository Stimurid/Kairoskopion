"""Research Planner — determines what data needs to be gathered.

Examines available entities and determines which agents need to run
next and what sources are needed.
"""

from __future__ import annotations

from ..base_shell import service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class ResearchPlannerAgent(AgentRole):
    role_id = "research_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        entities = inp.entities
        needs = []
        has = []

        if entities.get("article"):
            has.append("article_model")
        else:
            needs.append({"agent": "article_modeler", "reason": "no ArticleModel available"})

        if entities.get("venue"):
            has.append("venue_model")
        else:
            needs.append({"agent": "venue_profiler", "reason": "no VenueModel available"})

        if entities.get("scenario"):
            has.append("scenario")
        else:
            needs.append({"agent": "scenario_prober", "reason": "no SubmissionScenario"})

        if entities.get("semantic_profile"):
            has.append("semantic_profile")

        if entities.get("disciplinary_pathways"):
            has.append("disciplinary_pathways")
        elif entities.get("article"):
            needs.append({"agent": "article_semantic_profiler", "reason": "semantic profiling not done"})
            needs.append({"agent": "disciplinary_pathway_mapper", "reason": "pathway mapping not done"})

        return service_output(
            "ResearchPlan",
            {
                "available_entities": has,
                "needed_steps": needs,
                "total_needed": len(needs),
            },
            confidence="medium",
            trace_notes=[f"has={len(has)} entities, needs={len(needs)} steps"],
        )
