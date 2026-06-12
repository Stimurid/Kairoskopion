"""Tests for LLM provider module."""

from __future__ import annotations

import os
import unittest

from kairoskopion.llm.config import LLMConfig
from kairoskopion.llm.response import LLMResponse


class TestLLMConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = LLMConfig()
        self.assertEqual(cfg.model, "")
        self.assertEqual(cfg.base_url, "")
        self.assertEqual(cfg.api_key_env, "KAIROSKOPION_LLM_API_KEY")
        self.assertAlmostEqual(cfg.temperature, 0.2)
        self.assertEqual(cfg.max_tokens, 4096)
        self.assertEqual(cfg.max_retries, 3)

    def test_from_env_returns_none_when_no_model(self):
        old = os.environ.pop("KAIROSKOPION_LLM_MODEL", None)
        try:
            cfg = LLMConfig.from_env()
            self.assertIsNone(cfg)
        finally:
            if old is not None:
                os.environ["KAIROSKOPION_LLM_MODEL"] = old

    def test_from_env_returns_config_when_model_set(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "test-model"
        os.environ["KAIROSKOPION_LLM_BASE_URL"] = "http://localhost:8080/v1"
        try:
            cfg = LLMConfig.from_env()
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg.model, "test-model")
            self.assertEqual(cfg.base_url, "http://localhost:8080/v1")
        finally:
            os.environ.pop("KAIROSKOPION_LLM_MODEL", None)
            os.environ.pop("KAIROSKOPION_LLM_BASE_URL", None)

    def test_api_key_from_env(self):
        os.environ["MY_KEY"] = "secret123"
        try:
            cfg = LLMConfig(api_key_env="MY_KEY")
            self.assertEqual(cfg.api_key, "secret123")
        finally:
            os.environ.pop("MY_KEY", None)

    def test_api_key_missing_returns_empty(self):
        cfg = LLMConfig(api_key_env="DEFINITELY_NOT_SET_12345")
        self.assertEqual(cfg.api_key, "")


class TestLLMResponse(unittest.TestCase):
    def test_fields(self):
        r = LLMResponse(
            content='{"a":1}',
            parsed={"a": 1},
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1234.5,
            finish_reason="stop",
        )
        self.assertEqual(r.content, '{"a":1}')
        self.assertEqual(r.parsed, {"a": 1})
        self.assertEqual(r.model, "gpt-4o")
        self.assertEqual(r.input_tokens, 100)
        self.assertEqual(r.output_tokens, 50)
        self.assertAlmostEqual(r.latency_ms, 1234.5)

    def test_defaults(self):
        r = LLMResponse(content="hi")
        self.assertIsNone(r.parsed)
        self.assertIsNone(r.model)
        self.assertEqual(r.input_tokens, 0)
        self.assertEqual(r.output_tokens, 0)


if __name__ == "__main__":
    unittest.main()
