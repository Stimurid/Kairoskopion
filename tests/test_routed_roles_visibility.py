"""V2-A: routed_roles tuple completion.

Audit V2 §5 + §10 Pass A found 3 production-live LLM roles called
from cases.py but absent from `provider_status().model_per_role`,
so their per-role env override (KAIROSKOPION_LLM_MODEL_<ROLE>) was
silently ignored:

    - article_field_positioner  (cases.py:644)
    - venue_field_positioner    (cases.py:809)
    - venue_discovery           (cases.py:973)

This test guards the visibility fix. No behaviour change beyond
/health surface — model defaults still inherit the global.
"""

from __future__ import annotations

import os
import unittest


class TestRoutedRolesVisibility(unittest.TestCase):
    def setUp(self):
        self._snap = {
            k: v for k, v in os.environ.items()
            if k.startswith("KAIROSKOPION_LLM")
        }

    def tearDown(self):
        for k in list(os.environ):
            if k.startswith("KAIROSKOPION_LLM"):
                del os.environ[k]
        for k, v in self._snap.items():
            os.environ[k] = v

    def test_three_field_roles_visible_in_health(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "sonnet"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        from kairoskopion.llm.config import provider_status
        st = provider_status()
        for role in (
            "article_field_positioner",
            "venue_field_positioner",
            "venue_discovery",
        ):
            self.assertIn(role, st["model_per_role"])
            self.assertEqual(st["model_per_role"][role], "sonnet")
        self.assertEqual(st["overridden_roles"], [])

    def test_env_override_respected_for_new_roles(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "sonnet"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_VENUE_DISCOVERY"] = "haiku"
        from kairoskopion.llm.config import LLMConfig, provider_status
        cfg = LLMConfig.for_role("venue_discovery")
        self.assertEqual(cfg.model, "haiku")
        st = provider_status()
        self.assertEqual(st["model_per_role"]["venue_discovery"], "haiku")
        self.assertIn("venue_discovery", st["overridden_roles"])

    def test_classifier_only_override_unchanged(self):
        """Mirrors current prod env: only input_classifier is overridden."""
        os.environ["KAIROSKOPION_LLM_MODEL"] = "claude-sonnet-4-5-20250929"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER"] = "gpt-4o-mini"
        from kairoskopion.llm.config import provider_status
        st = provider_status()
        self.assertEqual(st["overridden_roles"], ["input_classifier"])
        self.assertEqual(
            st["model_per_role"]["article_field_positioner"],
            "claude-sonnet-4-5-20250929",
        )
        self.assertEqual(
            st["model_per_role"]["venue_field_positioner"],
            "claude-sonnet-4-5-20250929",
        )
        self.assertEqual(
            st["model_per_role"]["venue_discovery"],
            "claude-sonnet-4-5-20250929",
        )


if __name__ == "__main__":
    unittest.main()
