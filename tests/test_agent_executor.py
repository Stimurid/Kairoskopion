"""Tests for agent executor."""

from __future__ import annotations

import unittest

from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.executor import execute_agent
from kairoskopion.agents.runtime_models import AgentResult


class TestExecuteAgent(unittest.TestCase):
    def test_execute_status_job(self):
        inp = AgentInput(
            operation_id="test",
            agent_role_id="status_job",
            entities={"article": {"title": "test"}},
        )
        result = execute_agent("status_job", inp)
        self.assertIsInstance(result, AgentResult)
        self.assertIsNone(result.failure)
        self.assertNotEqual(result.confidence, "none")

    def test_execute_intent_classifier(self):
        inp = AgentInput(
            operation_id="test",
            agent_role_id="intent_classifier",
            raw_text="I want to find journals for my paper",
        )
        result = execute_agent("intent_classifier", inp)
        self.assertIsNone(result.failure)
        self.assertEqual(result.agent_role_id, "intent_classifier")

    def test_execute_contract_only_agent(self):
        inp = AgentInput(
            operation_id="test",
            agent_role_id="reviewer_simulation",
            entities={},
        )
        result = execute_agent("reviewer_simulation", inp)
        self.assertIsNone(result.failure)
        self.assertEqual(result.confidence, "none")

    def test_execute_unknown_agent(self):
        inp = AgentInput(operation_id="test", agent_role_id="nonexistent")
        with self.assertRaises(KeyError):
            execute_agent("nonexistent", inp)

    def test_result_has_trace(self):
        inp = AgentInput(
            operation_id="test",
            agent_role_id="status_job",
            entities={},
        )
        result = execute_agent("status_job", inp)
        self.assertTrue(hasattr(result, "_trace"))
        self.assertTrue(hasattr(result, "_run"))
        self.assertTrue(hasattr(result, "_task"))
        self.assertTrue(len(result._trace.steps_log) > 0)


if __name__ == "__main__":
    unittest.main()
