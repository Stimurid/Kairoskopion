"""Tests for agent contract (AgentInput, AgentOutput, AgentRole)."""

from __future__ import annotations

import unittest

from kairoskopion.agents.contract import AgentInput, AgentOutput, AgentRole
from kairoskopion.llm.provider import LLMProvider


class TestAgentInput(unittest.TestCase):
    def test_defaults(self):
        inp = AgentInput(operation_id="op1", agent_role_id="test")
        self.assertEqual(inp.operation_id, "op1")
        self.assertEqual(inp.agent_role_id, "test")
        self.assertEqual(inp.input_entity_refs, [])
        self.assertEqual(inp.source_refs, [])
        self.assertIsNone(inp.raw_text)
        self.assertEqual(inp.entities, {})
        self.assertEqual(inp.user_constraints, {})

    def test_with_data(self):
        inp = AgentInput(
            operation_id="op2",
            agent_role_id="modeler",
            raw_text="some text",
            source_refs=["src1"],
            entities={"k": "v"},
        )
        self.assertEqual(inp.raw_text, "some text")
        self.assertEqual(inp.source_refs, ["src1"])
        self.assertEqual(inp.entities["k"], "v")


class TestAgentOutput(unittest.TestCase):
    def test_defaults(self):
        out = AgentOutput(output_entity_type="ArticleModel")
        self.assertEqual(out.output_entity_type, "ArticleModel")
        self.assertEqual(out.output_entity, {})
        self.assertEqual(out.confidence, "low")
        self.assertEqual(out.evidence_status, "INFERENCE")
        self.assertIsNone(out.llm_usage)

    def test_with_data(self):
        out = AgentOutput(
            output_entity_type="VenueModel",
            output_entity={"name": "test"},
            confidence="high",
            unknowns=["scope unclear"],
        )
        self.assertEqual(out.output_entity["name"], "test")
        self.assertEqual(out.confidence, "high")
        self.assertEqual(len(out.unknowns), 1)


class _DummyAgent(AgentRole):
    role_id = "dummy"

    def execute(self, inp, provider):
        return AgentOutput(
            output_entity_type="Test",
            output_entity={"mode": "llm"},
            evidence_status="INFERENCE",
        )

    def execute_deterministic(self, inp):
        return AgentOutput(
            output_entity_type="Test",
            output_entity={"mode": "deterministic"},
            evidence_status="heuristic",
        )


class TestAgentRole(unittest.TestCase):
    def test_run_dispatches_to_deterministic_when_no_provider(self):
        agent = _DummyAgent()
        inp = AgentInput(operation_id="t1", agent_role_id="dummy")
        out = agent.run(inp, provider=None)
        self.assertEqual(out.output_entity["mode"], "deterministic")

    def test_run_dispatches_to_llm_when_provider_given(self):
        agent = _DummyAgent()
        inp = AgentInput(operation_id="t2", agent_role_id="dummy")

        class FakeProvider:
            def complete(self, messages, **kw):
                pass
        out = agent.run(inp, provider=FakeProvider())
        self.assertEqual(out.output_entity["mode"], "llm")


if __name__ == "__main__":
    unittest.main()
