"""Tests for agentic runtime domain models."""

from __future__ import annotations

import unittest

from kairoskopion.agents.runtime_models import (
    AgentFailure,
    AgentResult,
    AgentRun,
    AgentSpec,
    AgentTask,
    AgentTrace,
    AgentToolCall,
    AgenticWorkflowSpec,
    PromptFamilySpec,
    WorkflowResult,
    WorkflowRun,
    WorkflowStepSpec,
    WorkflowTrace,
)


class TestAgentSpec(unittest.TestCase):
    def test_defaults(self):
        s = AgentSpec(role_id="test_agent")
        self.assertEqual(s.role_id, "test_agent")
        self.assertEqual(s.layer, "")
        self.assertEqual(s.implementation_status, "future")
        self.assertEqual(s.execution_mode, "deterministic")
        self.assertEqual(s.evidence_policy, "preserve_all")

    def test_round_trip(self):
        s = AgentSpec(
            role_id="my_agent",
            display_name="My Agent",
            layer="article",
            implementation_status="operational_now",
            prompt_family_ids=["pf1", "pf2"],
        )
        d = s.to_dict()
        self.assertEqual(d["role_id"], "my_agent")
        self.assertEqual(d["prompt_family_ids"], ["pf1", "pf2"])
        s2 = AgentSpec.from_dict(d)
        self.assertEqual(s2.role_id, "my_agent")
        self.assertEqual(s2.prompt_family_ids, ["pf1", "pf2"])


class TestPromptFamilySpec(unittest.TestCase):
    def test_round_trip(self):
        pf = PromptFamilySpec(
            family_id="pf_test",
            family_name="Test Family",
            purpose="testing",
        )
        d = pf.to_dict()
        pf2 = PromptFamilySpec.from_dict(d)
        self.assertEqual(pf2.family_id, "pf_test")


class TestAgentTask(unittest.TestCase):
    def test_auto_id(self):
        t = AgentTask(agent_role_id="art")
        self.assertTrue(t.task_id.startswith("atask_"))
        self.assertTrue(t.created_at)

    def test_round_trip(self):
        t = AgentTask(agent_role_id="art", raw_text="hello")
        d = t.to_dict()
        self.assertEqual(d["agent_role_id"], "art")
        self.assertEqual(d["raw_text"], "hello")


class TestAgentRun(unittest.TestCase):
    def test_auto_id(self):
        r = AgentRun(agent_role_id="fit")
        self.assertTrue(r.run_id.startswith("arun_"))

    def test_status_default(self):
        r = AgentRun()
        self.assertEqual(r.status, "created")


class TestAgentFailure(unittest.TestCase):
    def test_fields(self):
        f = AgentFailure(error_type="ValueError", error_message="bad input")
        d = f.to_dict()
        self.assertEqual(d["error_type"], "ValueError")
        self.assertEqual(d["error_message"], "bad input")


class TestAgentResult(unittest.TestCase):
    def test_auto_id(self):
        r = AgentResult(agent_role_id="venue")
        self.assertTrue(r.result_id.startswith("ares_"))
        self.assertEqual(r.confidence, "low")

    def test_with_failure(self):
        f = AgentFailure(error_type="IOError", error_message="fail")
        r = AgentResult(agent_role_id="x", failure=f)
        self.assertIsNotNone(r.failure)
        d = r.to_dict()
        self.assertEqual(d["failure"]["error_type"], "IOError")


class TestAgentTrace(unittest.TestCase):
    def test_steps_log(self):
        t = AgentTrace(agent_role_id="test")
        t.steps_log.append("step1")
        self.assertEqual(len(t.steps_log), 1)


class TestAgentToolCall(unittest.TestCase):
    def test_round_trip(self):
        tc = AgentToolCall(tool_name="build_article_model", duration_ms=42.5)
        d = tc.to_dict()
        self.assertEqual(d["tool_name"], "build_article_model")
        self.assertEqual(d["duration_ms"], 42.5)


class TestWorkflowStepSpec(unittest.TestCase):
    def test_round_trip(self):
        s = WorkflowStepSpec(
            step_index=0,
            agent_role_id="article_modeler",
            output_key="article",
            input_keys=["raw_text"],
        )
        d = s.to_dict()
        s2 = WorkflowStepSpec.from_dict(d)
        self.assertEqual(s2.output_key, "article")
        self.assertEqual(s2.input_keys, ["raw_text"])


class TestAgenticWorkflowSpec(unittest.TestCase):
    def test_get_steps(self):
        wf = AgenticWorkflowSpec(
            workflow_id="test_wf",
            steps=[
                {"step_index": 0, "agent_role_id": "a1", "output_key": "out1"},
                {"step_index": 1, "agent_role_id": "a2", "output_key": "out2"},
            ],
        )
        steps = wf.get_steps()
        self.assertEqual(len(steps), 2)
        self.assertIsInstance(steps[0], WorkflowStepSpec)
        self.assertEqual(steps[0].agent_role_id, "a1")
        self.assertEqual(steps[1].output_key, "out2")


class TestWorkflowRun(unittest.TestCase):
    def test_auto_id(self):
        wr = WorkflowRun(workflow_id="wf1")
        self.assertTrue(wr.run_id.startswith("wfrun_"))
        self.assertEqual(wr.status, "created")


class TestWorkflowResult(unittest.TestCase):
    def test_auto_id(self):
        r = WorkflowResult(workflow_id="wf1")
        self.assertTrue(r.result_id.startswith("wfres_"))


class TestWorkflowTrace(unittest.TestCase):
    def test_steps_log(self):
        t = WorkflowTrace(workflow_id="wf1")
        t.steps_log.append("start")
        self.assertEqual(t.steps_log, ["start"])


if __name__ == "__main__":
    unittest.main()
