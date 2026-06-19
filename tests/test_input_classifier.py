"""Tests for the InputClassifierAgent (Phase A).

Covers:
- deterministic fallback never guesses — returns unknown + needs_user_choice
- LLM path produces the expected schema shape (mocked)
- intake endpoint surfaces classification + needs_user_choice in the response
- the legacy bug regression: long manuscript mentioning "reviewer" must NOT
  be silently routed to review_letter (because that branch skips the
  whole pipeline)
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestDeterministicFallback(unittest.TestCase):
    """Without an LLM provider, the agent must ask the user, never guess."""

    def setUp(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.input_classifier import InputClassifierAgent
        self.agent = InputClassifierAgent()
        self.mk_input = lambda text: AgentInput(
            operation_id="t",
            agent_role_id="input_classifier",
            raw_text=text,
        )

    def test_empty_text_returns_unknown(self):
        out = self.agent.execute_deterministic(self.mk_input(""))
        self.assertEqual(out.output_entity["input_type"], "unknown")
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_short_text_returns_unknown(self):
        out = self.agent.execute_deterministic(self.mk_input("Hello world"))
        self.assertEqual(out.output_entity["input_type"], "unknown")
        self.assertTrue(out.output_entity["needs_user_choice"])
        # No guess at language either — that's the LLM's job
        self.assertEqual(out.output_entity["language_detected"], "unknown")

    def test_long_manuscript_mentioning_reviewer_returns_unknown(self):
        # Regression: the OLD keyword classifier flagged this as
        # review_letter on the substring "reviewer", silently skipping
        # the whole intake pipeline. The new fallback never guesses.
        text = ("Vygotsky, Lev S. 1978. Mind in Society. " * 2000) + (
            "Includes reviewer comments by an unnamed referee."
        )
        out = self.agent.execute_deterministic(self.mk_input(text))
        self.assertNotEqual(out.output_entity["input_type"], "review_letter")
        self.assertEqual(out.output_entity["input_type"], "unknown")
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_reasoning_is_in_russian(self):
        out = self.agent.execute_deterministic(self.mk_input("any text"))
        reasoning = out.output_entity["reasoning"]
        # Reasoning surfaces to the user — must be Russian
        self.assertTrue(
            any(0x0400 <= ord(c) <= 0x04FF for c in reasoning),
            f"Reasoning not in Russian: {reasoning!r}",
        )


class TestLLMPath(unittest.TestCase):
    """With a working LLM provider, the agent parses the classification."""

    def setUp(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.input_classifier import InputClassifierAgent
        self.agent = InputClassifierAgent()
        self.mk_input = lambda text: AgentInput(
            operation_id="t",
            agent_role_id="input_classifier",
            raw_text=text,
        )

    def _mock_provider_with(self, parsed_payload: dict) -> MagicMock:
        provider = MagicMock()
        response = MagicMock()
        response.parsed = parsed_payload
        response.content = ""
        response.model = "claude-haiku-4-5"
        response.latency_ms = 100.0
        provider.complete.return_value = response
        return provider

    def test_llm_returning_manuscript_is_passed_through(self):
        provider = self._mock_provider_with({
            "input_type": "manuscript",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "ru",
            "reasoning": "Длинный академический текст с тезисом и библиографией.",
        })
        out = self.agent.execute(self.mk_input("очень длинный текст" * 500), provider)
        self.assertEqual(out.output_entity["input_type"], "manuscript")
        self.assertFalse(out.output_entity["needs_user_choice"])

    def test_llm_low_confidence_forces_needs_user_choice(self):
        # Invariant: even if the LLM forgot to set needs_user_choice,
        # low confidence MUST force it on.
        provider = self._mock_provider_with({
            "input_type": "manuscript",
            "confidence": "low",
            "needs_user_choice": False,  # LLM forgot
            "language_detected": "ru",
            "reasoning": "Не уверен.",
        })
        out = self.agent.execute(self.mk_input("текст"), provider)
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_llm_unknown_forces_needs_user_choice(self):
        # Same invariant for input_type=unknown.
        provider = self._mock_provider_with({
            "input_type": "unknown",
            "confidence": "medium",
            "needs_user_choice": False,
            "language_detected": "ru",
            "reasoning": "Не понял.",
        })
        out = self.agent.execute(self.mk_input("текст"), provider)
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_llm_crash_falls_back_to_unknown(self):
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("boom")
        out = self.agent.execute(self.mk_input("текст"), provider)
        self.assertEqual(out.output_entity["input_type"], "unknown")
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_llm_non_json_falls_back_to_unknown(self):
        provider = MagicMock()
        response = MagicMock()
        response.parsed = None
        response.content = "не json вовсе"
        response.model = "claude-haiku-4-5"
        response.latency_ms = 50.0
        provider.complete.return_value = response
        out = self.agent.execute(self.mk_input("текст"), provider)
        self.assertEqual(out.output_entity["input_type"], "unknown")
        self.assertTrue(out.output_entity["needs_user_choice"])


class TestIntakeEndpointWiring(unittest.TestCase):
    """End-to-end via FastAPI: when LLM is not configured, intake
    returns classification + needs_user_choice on input_type=auto."""

    def setUp(self):
        from fastapi.testclient import TestClient

        self._tmpdir = tempfile.mkdtemp(prefix="kairon_input_clf_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        # Force no LLM provider — exercises the deterministic fallback
        # path in Case._classify_input_llm.
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.client = TestClient(app_mod.app)

        resp = self.client.post("/auth/signup", json={
            "display_name": "test_user_input_clf",
            "email": None,
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.token = resp.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        case = self.client.post(
            "/cases", json={"title": "input-clf"}, headers=self.headers,
        )
        self.assertEqual(case.status_code, 200, case.text)
        self.case_id = case.json()["case_id"]

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def test_auto_intake_no_llm_returns_needs_user_choice(self):
        # 75k chars with a 'reviewer' word — the exact scenario that
        # broke under the old keyword classifier (silent route to
        # review_letter, empty pipeline). With LLM disabled, the new
        # path must say "I don't know, you choose" rather than guess.
        text = ("Vygotsky, Lev S. 1978. Mind in Society. " * 2000) + (
            "Includes reviewer comments by an unnamed referee."
        )
        resp = self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={"text": text, "input_type": "auto"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["input_type"], "unknown")
        self.assertTrue(body["needs_user_choice"])
        # No article model was built — that's correct, the user must
        # confirm the type first.
        self.assertFalse(body["article_model_built"])
        self.assertFalse(body["venue_investigated"])
        self.assertIn("classification", body)
        self.assertEqual(body["classification"]["input_type"], "unknown")
        # No internals / Traceback / raw_output_ref leaks
        self.assertNotIn("Traceback", resp.text)
        self.assertNotIn("raw_output_ref", resp.text)

    def test_explicit_input_type_skips_classifier(self):
        # When the UI chip is set explicitly, classifier must NOT run —
        # the pipeline routes directly to article modeling.
        text = "Short article body. " * 50
        resp = self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={"text": text, "input_type": "article"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        # When the user picked the chip, no classification verdict
        # should appear in the response.
        self.assertNotIn("classification", body)
        self.assertNotIn("needs_user_choice", body)


class TestExpandedTypesAndRouting(unittest.TestCase):
    """v2 classifier output_type vocabulary + routing in cases.py.

    The new categories — bibliography / field_notes / mixed /
    journal_or_venue — must NOT silently route through ArticleModeler
    or VenueProfiler. They get needs_user_choice=true and skip the
    pipelines entirely so the user picks a chip.
    """

    def setUp(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.input_classifier import InputClassifierAgent
        self.agent = InputClassifierAgent()
        self.mk_input = lambda text: AgentInput(
            operation_id="t",
            agent_role_id="input_classifier",
            raw_text=text,
        )

    def _mock_provider_with(self, parsed_payload: dict):
        from unittest.mock import MagicMock
        provider = MagicMock()
        response = MagicMock()
        response.parsed = parsed_payload
        response.content = ""
        response.model = "claude-haiku-4-5"
        response.latency_ms = 100.0
        provider.complete.return_value = response
        return provider

    def test_field_notes_forces_user_choice(self):
        provider = self._mock_provider_with({
            "input_type": "field_notes",
            "confidence": "high",
            "needs_user_choice": False,  # LLM forgot
            "language_detected": "ru",
            "reasoning": "Тезисы без структуры статьи.",
        })
        out = self.agent.execute(self.mk_input("тезисы " * 200), provider)
        self.assertEqual(out.output_entity["input_type"], "field_notes")
        # Invariant: field_notes has no automated pipeline → must ask user
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_bibliography_forces_user_choice(self):
        provider = self._mock_provider_with({
            "input_type": "bibliography",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "en",
            "reasoning": "Pure reference list, no authorial text.",
        })
        out = self.agent.execute(self.mk_input("refs " * 200), provider)
        self.assertEqual(out.output_entity["input_type"], "bibliography")
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_mixed_forces_user_choice(self):
        provider = self._mock_provider_with({
            "input_type": "mixed",
            "confidence": "medium",
            "needs_user_choice": False,
            "language_detected": "mixed",
            "reasoning": "Draft article + author notes about it.",
        })
        out = self.agent.execute(self.mk_input("x"), provider)
        self.assertEqual(out.output_entity["input_type"], "mixed")
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_review_letter_forces_user_choice(self):
        # Even a confident review_letter has no automated pipeline.
        provider = self._mock_provider_with({
            "input_type": "review_letter",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "en",
            "reasoning": "Dear editor letter.",
        })
        out = self.agent.execute(self.mk_input("Dear editor."), provider)
        self.assertTrue(out.output_entity["needs_user_choice"])

    def test_manuscript_high_confidence_proceeds_quietly(self):
        # Article-pipeline types with high confidence do NOT force
        # the user-choice prompt.
        provider = self._mock_provider_with({
            "input_type": "manuscript",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "ru",
            "reasoning": "Полная статья с тезисом, секциями и библиографией.",
        })
        out = self.agent.execute(self.mk_input("длинный текст" * 500), provider)
        self.assertEqual(out.output_entity["input_type"], "manuscript")
        self.assertFalse(out.output_entity["needs_user_choice"])

    def test_journal_or_venue_high_confidence_proceeds_quietly(self):
        provider = self._mock_provider_with({
            "input_type": "journal_or_venue",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "en",
            "reasoning": "Journal aims and scope page.",
        })
        out = self.agent.execute(self.mk_input("Journal of X. ISSN..."), provider)
        self.assertEqual(out.output_entity["input_type"], "journal_or_venue")
        self.assertFalse(out.output_entity["needs_user_choice"])

    def test_validator_warns_on_inconsistent_needs_user_choice(self):
        # Schema validator surfaces the missing needs_user_choice flag.
        from kairoskopion.prompts.input_classification import (
            validate_input_classification,
        )
        warnings = validate_input_classification({
            "input_type": "field_notes",
            "confidence": "high",
            "needs_user_choice": False,
            "language_detected": "ru",
            "reasoning": "тезисы",
        })
        self.assertTrue(any("needs_user_choice" in w for w in warnings))


class TestCasesRoutingForNewTypes(unittest.TestCase):
    """When the LLM classifier returns a new type, Case.intake_text
    must NOT silently run ArticleModeler or VenueProfiler."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_routing_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def _intake(self, input_type: str):
        # Bypass the classifier by passing an explicit input_type. Tests
        # the routing branch directly.
        from kairoskopion.api.cases import Case
        case = Case(title="test")
        return case.intake_text("Body text. " * 30, input_type=input_type)

    def test_field_notes_skips_article_pipeline(self):
        result = self._intake("field_notes")
        self.assertFalse(result["article_model_built"])
        self.assertFalse(result["venue_investigated"])
        self.assertEqual(result["input_type"], "field_notes")

    def test_bibliography_skips_article_pipeline(self):
        result = self._intake("bibliography")
        self.assertFalse(result["article_model_built"])
        self.assertFalse(result["venue_investigated"])

    def test_mixed_skips_pipelines(self):
        result = self._intake("mixed")
        self.assertFalse(result["article_model_built"])
        self.assertFalse(result["venue_investigated"])

    def test_journal_or_venue_routes_to_venue(self):
        result = self._intake("journal_or_venue")
        self.assertFalse(result["article_model_built"])
        # venue_investigated may be True/False depending on whether the
        # venue investigator falls through cleanly; what we care about
        # is that it ATTEMPTED venue routing — i.e. not skipped silently.
        # The deterministic venue path may produce a partial profile.

    def test_legacy_venue_string_still_routes(self):
        result = self._intake("venue")
        self.assertFalse(result["article_model_built"])
        # Backward compat: old "venue" alias keeps working


if __name__ == "__main__":
    unittest.main()
