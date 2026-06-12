"""Corpus Sampler Agent — thin wrapper around services.corpus_sampler.

Wraps sample_venue_corpus() as an AgentRole so the orchestrator can
invoke it as a workflow step.
"""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class CorpusSamplerAgent(AgentRole):
    role_id = "corpus_sampler"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        if not venue:
            return missing_input_output("CorpusSample", "venue")

        from ...services.corpus_sampler import (
            CorpusSampleConfig,
            sample_venue_corpus,
        )

        venue_model_id = venue.get("venue_model_id") or venue.get("name", "unknown")
        fixtures = inp.entities.get("article_fixtures", [])

        config = CorpusSampleConfig()
        result = sample_venue_corpus(
            venue_model_id=venue_model_id,
            article_fixtures=fixtures or None,
            config=config,
        )

        corpus_dict = result.corpus.to_dict()

        unknowns = []
        if result.fixture_source:
            unknowns.append("Corpus from fixtures only — not live API data")
        unknowns.extend(result.representativeness_notes)
        unknowns.extend(result.bias_notes)

        return service_output(
            "CorpusSample",
            corpus_dict,
            unknowns=unknowns,
            confidence="low" if result.fixture_source else "medium",
            trace_notes=[
                f"sampled {result.corpus.corpus_size} articles for '{venue_model_id}'",
                f"strategy={result.selection_strategy_used}",
            ],
        )
