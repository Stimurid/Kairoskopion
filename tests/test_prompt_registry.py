"""Tests for prompt registry (Track 5)."""
from __future__ import annotations

from pathlib import Path

import pytest

from kairoskopion.services.prompt_registry import (
    PromptFamilyInfo,
    PromptRegistry,
    _hash_text,
)


class TestPromptFamilyInfo:
    def test_to_dict(self):
        info = PromptFamilyInfo(
            prompt_family_id="article_modeling",
            path="/some/path.py",
            source_module="kairoskopion.prompts.article_modeling",
            version_hash="abc123",
            has_schema=True,
            schema_ref="ARTICLE_MODELING_SCHEMA",
        )
        d = info.to_dict()
        assert d["prompt_family_id"] == "article_modeling"
        assert d["has_schema"] is True

    def test_roundtrip(self):
        info = PromptFamilyInfo(
            prompt_family_id="test",
            path="p.py",
            source_module="mod",
            version_hash="h1",
            agent_ref="AgentX",
        )
        d = info.to_dict()
        restored = PromptFamilyInfo.from_dict(d)
        assert restored.prompt_family_id == "test"
        assert restored.agent_ref == "AgentX"


class TestPromptRegistry:
    def test_scan_real_prompts(self):
        registry = PromptRegistry()
        ids = registry.list_ids()
        assert "article_modeling" in ids
        assert "fit_assessment" in ids
        assert "venue_fact_extraction" in ids
        assert len(ids) >= 15

    def test_get_existing(self):
        registry = PromptRegistry()
        info = registry.get("article_modeling")
        assert info is not None
        assert info.prompt_family_id == "article_modeling"
        assert info.agent_ref == "ArticleModelerAgent"
        assert info.version_hash
        assert len(info.version_hash) == 16

    def test_get_nonexistent(self):
        registry = PromptRegistry()
        assert registry.get("nonexistent_prompt") is None

    def test_version_hash_deterministic(self):
        r1 = PromptRegistry()
        r2 = PromptRegistry()
        h1 = r1.get_version_hash("article_modeling")
        h2 = r2.get_version_hash("article_modeling")
        assert h1 == h2

    def test_list_all_returns_infos(self):
        registry = PromptRegistry()
        all_infos = registry.list_all()
        assert len(all_infos) >= 15
        for info in all_infos:
            assert isinstance(info, PromptFamilyInfo)
            assert info.version_hash

    def test_descriptions_extracted(self):
        registry = PromptRegistry()
        info = registry.get("article_modeling")
        assert info.description

    def test_schema_detection(self):
        registry = PromptRegistry()
        for info in registry.list_all():
            if info.has_schema:
                assert info.schema_ref is not None

    def test_empty_dir(self, tmp_path):
        registry = PromptRegistry(prompts_dir=tmp_path)
        assert registry.list_ids() == []

    def test_synthetic_prompt_file(self, tmp_path):
        pf = tmp_path / "test_prompt.py"
        pf.write_text(
            '"""Test prompt family."""\n\n'
            'TEST_PROMPT_SYSTEM = """\nYou are a test agent.\n"""\n\n'
            'TEST_PROMPT_USER = """\nAnalyze: {text}\n"""\n\n'
            'TEST_PROMPT_SCHEMA = {"type": "object"}\n',
            encoding="utf-8",
        )
        registry = PromptRegistry(prompts_dir=tmp_path)
        info = registry.get("test_prompt")
        assert info is not None
        assert info.has_schema is True
        assert "test agent" in info.system_prompt
        assert info.version_hash


class TestHashText:
    def test_consistent(self):
        assert _hash_text("abc") == _hash_text("abc")

    def test_length(self):
        assert len(_hash_text("x")) == 16
