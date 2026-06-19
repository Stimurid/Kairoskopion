"""Tests for the intake-choice-and-routing-seam branch.

Track A — user-choice intake override flow
Track C — minimal per-call routing seam (LLMConfig.for_role +
          _get_llm_provider(role_id))
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest


# ---------------------------------------------------------------------------
# Track C — minimal per-call routing seam
# ---------------------------------------------------------------------------


class TestLLMConfigForRole(unittest.TestCase):
    """``LLMConfig.for_role`` is the env-driven seam Agentum can use to
    route different agents to different model aliases without touching
    agent code."""

    def setUp(self):
        # Save env snapshot — these tests mutate os.environ in-place.
        self._snap = {k: v for k, v in os.environ.items()
                       if k.startswith("KAIROSKOPION_LLM")}

    def tearDown(self):
        for k in list(os.environ):
            if k.startswith("KAIROSKOPION_LLM"):
                del os.environ[k]
        for k, v in self._snap.items():
            os.environ[k] = v

    def test_no_role_returns_global(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "global-model"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role(None)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.model, "global-model")

    def test_role_override_respected(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "global-model"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER"] = "cheap-model"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("input_classifier")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.model, "cheap-model")
        # Different role with no override falls through to global
        cfg2 = LLMConfig.for_role("article_modeler")
        self.assertEqual(cfg2.model, "global-model")

    def test_unknown_role_falls_through(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "global-model"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("brand_new_unrecognized_role")
        self.assertEqual(cfg.model, "global-model")

    def test_no_global_returns_none(self):
        # Preserves the "LLM optional" contract: when no global model is
        # configured, for_role returns None regardless of overrides.
        os.environ.pop("KAIROSKOPION_LLM_MODEL", None)
        os.environ["KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER"] = "ignored"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("input_classifier")
        self.assertIsNone(cfg)

    def test_provider_none_returns_none(self):
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.llm.config import LLMConfig
        self.assertIsNone(LLMConfig.for_role("input_classifier"))

    def test_empty_override_falls_through(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "global-model"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER"] = ""
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("input_classifier")
        self.assertEqual(cfg.model, "global-model")

    def test_hyphenated_role_id_env_uses_underscores(self):
        # role_id "discipline-matcher" (hypothetical) → env var name uses
        # underscores. We use the actual snake_case role ids in code so
        # this is mostly a robustness check.
        os.environ["KAIROSKOPION_LLM_MODEL"] = "global"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_DISCIPLINE_MATCHER"] = "haiku"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("discipline-matcher")
        self.assertEqual(cfg.model, "haiku")


class TestProviderStatusRoutingExposure(unittest.TestCase):
    def setUp(self):
        self._snap = {k: v for k, v in os.environ.items()
                       if k.startswith("KAIROSKOPION_LLM")}

    def tearDown(self):
        for k in list(os.environ):
            if k.startswith("KAIROSKOPION_LLM"):
                del os.environ[k]
        for k, v in self._snap.items():
            os.environ[k] = v

    def test_status_exposes_per_role_map_no_secrets(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "sonnet"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "SECRET_KEY_DO_NOT_LEAK"
        os.environ["KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER"] = "haiku"
        from kairoskopion.llm.config import provider_status
        st = provider_status()
        self.assertEqual(st["model_default"], "sonnet")
        self.assertEqual(st["model_per_role"]["input_classifier"], "haiku")
        self.assertEqual(st["model_per_role"]["article_modeler"], "sonnet")
        self.assertIn("input_classifier", st["overridden_roles"])
        self.assertNotIn("article_modeler", st["overridden_roles"])
        # No key leaked anywhere
        import json
        flat = json.dumps(st, ensure_ascii=False)
        self.assertNotIn("SECRET_KEY_DO_NOT_LEAK", flat)


# ---------------------------------------------------------------------------
# Track A — user-choice intake override flow
# ---------------------------------------------------------------------------


class TestIntakeOverride(unittest.TestCase):
    """Operator overrides classifier's verdict. The pipeline reruns
    using the chosen type; the original classifier verdict is preserved
    on the case for audit."""

    def setUp(self):
        from fastapi.testclient import TestClient

        self._tmpdir = tempfile.mkdtemp(prefix="kairon_override_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        # No LLM provider — exercises the deterministic-fallback path
        # of the classifier (returns input_type=unknown +
        # needs_user_choice=true). The override then picks an explicit
        # type and the article-pipeline path runs against the
        # deterministic article model builder.
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.client = TestClient(app_mod.app)
        resp = self.client.post("/auth/signup", json={
            "display_name": "override_test", "email": None,
        })
        self.token = resp.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        case = self.client.post(
            "/cases", json={"title": "override-test"}, headers=self.headers,
        )
        self.case_id = case.json()["case_id"]

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def _intake_auto(self, text: str):
        return self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={"text": text, "input_type": "auto"},
            headers=self.headers,
        )

    def _override(self, chosen_type: str):
        return self.client.post(
            f"/cases/{self.case_id}/intake/override",
            json={"chosen_type": chosen_type},
            headers=self.headers,
        )

    def test_classifier_to_article_override_runs_pipeline(self):
        # Step 1: intake auto, classifier returns unknown
        r = self._intake_auto("Some long text " * 200)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["input_type"], "unknown")
        self.assertTrue(body["needs_user_choice"])
        self.assertFalse(body["article_model_built"])

        # Step 2: user overrides to article
        r2 = self._override("article")
        self.assertEqual(r2.status_code, 200, r2.text)
        b2 = r2.json()
        self.assertEqual(b2["effective_input_type"], "article")
        self.assertEqual(b2["classifier_input_type"], "unknown")  # preserved
        self.assertEqual(b2["user_selected_input_type"], "article")
        self.assertEqual(b2["override_source"], "user")
        self.assertIsNotNone(b2["override_at"])
        # Pipeline ran
        self.assertTrue(b2["article_model_built"])

    def test_bibliography_classification_no_override_no_pipeline(self):
        # Intake auto → classifier returns unknown (LLM unavailable).
        # Without an override, the pipeline must NOT run silently.
        r = self._intake_auto("ref ref ref " * 100)
        body = r.json()
        self.assertFalse(body["article_model_built"])
        self.assertFalse(body["venue_investigated"])

    def test_mixed_override_to_article_runs(self):
        self._intake_auto("body text " * 100)
        r = self._override("article")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["article_model_built"])

    def test_journal_or_venue_override_runs_venue_path(self):
        self._intake_auto("journal scope " * 50)
        r = self._override("journal_or_venue")
        self.assertEqual(r.status_code, 200)
        # venue investigation deterministic path may produce or skip
        # — we just verify no error and that the routing flag flipped.
        b = r.json()
        self.assertEqual(b["effective_input_type"], "journal_or_venue")

    def test_invalid_override_rejected(self):
        self._intake_auto("text " * 30)
        r = self._override("not_a_real_type")
        self.assertEqual(r.status_code, 400)

    def test_override_before_intake_rejected(self):
        # Fresh case with no input_text yet
        case = self.client.post(
            "/cases", json={"title": "no-intake"}, headers=self.headers,
        ).json()
        r = self.client.post(
            f"/cases/{case['case_id']}/intake/override",
            json={"chosen_type": "article"}, headers=self.headers,
        )
        self.assertEqual(r.status_code, 400)

    def test_override_metadata_persists_through_save_load(self):
        self._intake_auto("body " * 100)
        self._override("article")
        # Reload app to force re-read from disk
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        from kairoskopion.api import auth as auth_mod
        sessions = list(auth_mod._SESSIONS.values()) if hasattr(auth_mod, "_SESSIONS") else []
        user_id = sessions[0].user_id if sessions else None
        case = app_mod.store.get(self.case_id, user_id=user_id)
        self.assertIsNotNone(case)
        self.assertEqual(case.user_selected_input_type, "article")
        self.assertEqual(case.effective_input_type, "article")
        self.assertEqual(case.override_source, "user")
        self.assertIsNotNone(case.override_at)

    def test_anti_leak_in_override_response(self):
        self._intake_auto("body " * 100)
        r = self._override("article")
        body = r.text
        self.assertNotIn("Traceback", body)
        self.assertNotIn("raw_output_ref", body)
        # No real secret should be in the request response anywhere
        self.assertNotIn("KAIROSKOPION_LLM_API_KEY", body)


class TestChipPathSkipsClassifier(unittest.TestCase):
    """When the user picks a chip up front, override_source is 'chip'
    and the classifier is bypassed."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_chip_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from fastapi.testclient import TestClient
        self.client = TestClient(app_mod.app)
        self.token = self.client.post("/auth/signup", json={
            "display_name": "chip_test", "email": None,
        }).json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.case_id = self.client.post(
            "/cases", json={"title": "chip"}, headers=self.headers,
        ).json()["case_id"]

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def test_chip_override_source(self):
        r = self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={"text": "body " * 100, "input_type": "article"},
            headers=self.headers,
        )
        body = r.json()
        self.assertEqual(body["override_source"], "chip")
        self.assertEqual(body["effective_input_type"], "article")


if __name__ == "__main__":
    unittest.main()
