"""Tests for Kairoskopion JSONL registry."""

import json
import tempfile
from pathlib import Path

from kairoskopion import registry


class TestRegistry:
    def test_append_and_read(self, tmp_path):
        record = {"id": "art_001", "title": "Test Article"}
        registry.append("test_articles", record, base_dir=tmp_path)

        records = registry.read_all("test_articles", base_dir=tmp_path)
        assert len(records) == 1
        assert records[0]["id"] == "art_001"
        assert records[0]["title"] == "Test Article"

    def test_append_multiple(self, tmp_path):
        for i in range(5):
            registry.append("items", {"id": f"item_{i}", "n": i}, base_dir=tmp_path)

        records = registry.read_all("items", base_dir=tmp_path)
        assert len(records) == 5
        assert records[4]["n"] == 4

    def test_list_ids(self, tmp_path):
        registry.append("articles", {"id": "a1"}, base_dir=tmp_path)
        registry.append("articles", {"id": "a2"}, base_dir=tmp_path)

        ids = registry.list_ids("articles", base_dir=tmp_path)
        assert ids == ["a1", "a2"]

    def test_list_ids_with_entity_prefix(self, tmp_path):
        registry.append("venue_models", {"venue_models_id": "v1"}, base_dir=tmp_path)
        registry.append("venue_models", {"venue_models_id": "v2"}, base_dir=tmp_path)

        ids = registry.list_ids("venue_models", base_dir=tmp_path)
        assert ids == ["v1", "v2"]

    def test_find_by_id(self, tmp_path):
        registry.append("items", {"id": "x1", "data": "hello"}, base_dir=tmp_path)
        registry.append("items", {"id": "x2", "data": "world"}, base_dir=tmp_path)

        found = registry.find_by_id("items", "x2", base_dir=tmp_path)
        assert found is not None
        assert found["data"] == "world"

        not_found = registry.find_by_id("items", "x99", base_dir=tmp_path)
        assert not_found is None

    def test_read_empty_registry(self, tmp_path):
        records = registry.read_all("nonexistent", base_dir=tmp_path)
        assert records == []

    def test_registry_exists(self, tmp_path):
        assert not registry.registry_exists("test", base_dir=tmp_path)
        registry.append("test", {"id": "1"}, base_dir=tmp_path)
        assert registry.registry_exists("test", base_dir=tmp_path)

    def test_jsonl_format(self, tmp_path):
        registry.append("fmt", {"id": "1", "name": "тест"}, base_dir=tmp_path)
        path = tmp_path / "fmt.jsonl"
        line = path.read_text(encoding="utf-8").strip()
        parsed = json.loads(line)
        assert parsed["name"] == "тест"

    def test_schema_model_roundtrip(self, tmp_path):
        from kairoskopion.schema import ArticleModel

        am = ArticleModel(title_current="Test Paper")
        registry.append("articles", am.to_dict(), base_dir=tmp_path)

        records = registry.read_all("articles", base_dir=tmp_path)
        assert len(records) == 1
        restored = ArticleModel.from_dict(records[0])
        assert restored.title_current == "Test Paper"
        assert restored.article_model_id == am.article_model_id
