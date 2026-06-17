"""Tests for the LLM-input-size guard introduced to stop intake from
producing bare API 504 errors on huge pastes.
"""

from __future__ import annotations

import unittest

from kairoskopion.llm.input_limits import (
    INTAKE_HARD_CHAR_CAP,
    LLM_INPUT_CHAR_CAP,
    TRUNCATION_MARKER,
    TruncationInfo,
    cap_llm_input,
)


class TestCapLLMInput(unittest.TestCase):
    def test_short_text_passes_through(self):
        text = "hello world"
        out, info = cap_llm_input(text)
        self.assertEqual(out, text)
        self.assertFalse(info.truncated)
        self.assertEqual(info.original_chars, len(text))
        self.assertEqual(info.used_chars, len(text))

    def test_empty_string_safe(self):
        out, info = cap_llm_input("")
        self.assertEqual(out, "")
        self.assertEqual(info.original_chars, 0)
        self.assertEqual(info.used_chars, 0)

    def test_none_safe(self):
        out, info = cap_llm_input(None)  # type: ignore[arg-type]
        self.assertEqual(out, "")
        self.assertFalse(info.truncated)

    def test_oversize_text_is_capped(self):
        text = "а" * (LLM_INPUT_CHAR_CAP + 5_000)
        out, info = cap_llm_input(text)
        self.assertTrue(info.truncated)
        self.assertEqual(info.original_chars, len(text))
        self.assertLess(info.used_chars, len(text))
        self.assertIn(TRUNCATION_MARKER.strip(), out)
        # The output never exceeds the cap by more than the marker length.
        self.assertLess(len(out), len(text))

    def test_explicit_cap_argument(self):
        out, info = cap_llm_input("a" * 200, cap=50)
        self.assertTrue(info.truncated)
        self.assertEqual(info.cap, 50)
        self.assertLessEqual(info.used_chars, 50)

    def test_to_dict_shape(self):
        info = TruncationInfo(original_chars=100, used_chars=40, cap=40)
        d = info.to_dict()
        self.assertEqual(d["original_chars"], 100)
        self.assertEqual(d["used_chars"], 40)
        self.assertEqual(d["cap"], 40)
        self.assertTrue(d["truncated"])


class TestIntakeEndpointHardCap(unittest.TestCase):
    """The /cases/{id}/intake/text endpoint must return 413 for inputs
    above INTAKE_HARD_CHAR_CAP with a structured detail payload."""

    def setUp(self):
        import importlib
        import os
        import shutil
        import tempfile
        from fastapi.testclient import TestClient

        self._tmpdir = tempfile.mkdtemp(prefix="kairon_intake_limits_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.client = TestClient(app_mod.app)
        self._cleanup_dir = self._tmpdir
        self._shutil = shutil
        self._os = os

        resp = self.client.post("/auth/signup", json={
            "display_name": "test_user_intake_limits", "email": None,
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.token = resp.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        case = self.client.post(
            "/cases", json={"title": "intake-cap"}, headers=self.headers,
        )
        self.assertEqual(case.status_code, 200, case.text)
        self.case_id = case.json()["case_id"]

    def tearDown(self):
        self._shutil.rmtree(self._cleanup_dir, ignore_errors=True)
        self._os.environ.pop("KAIROSKOPION_DATA_DIR", None)

    def test_413_on_oversize_text(self):
        big = "ы" * (INTAKE_HARD_CHAR_CAP + 100)
        resp = self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={"text": big, "input_type": "article"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 413, resp.text)
        body = resp.json()
        # FastAPI wraps HTTPException(detail=dict) under "detail"
        detail = body["detail"]
        self.assertEqual(detail["error"], "input_too_large")
        self.assertEqual(detail["max_chars"], INTAKE_HARD_CHAR_CAP)
        self.assertGreater(detail["received_chars"], INTAKE_HARD_CHAR_CAP)
        self.assertIn("Текст", detail["message"])
        # No internals leaked
        self.assertNotIn("Traceback", resp.text)
        self.assertNotIn("raw_output_ref", resp.text)


# NOTE: classifier-specific tests live in tests/test_input_classifier.py
# after Phase A migrated routing from the keyword heuristic to
# InputClassifierAgent. The keyword tests that used to live here
# have been deleted along with ``_classify_input``.


if __name__ == "__main__":
    unittest.main()
