"""P7.3 — Pipeline ↔ Registry wiring tests.

Verifies that ManuscriptVenueFitPipeline stores venue extractions as
provisional registry records when a RegistryIntegrationService is provided,
and that the CLI helper _resolve_registry_service creates a working service.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ────────────────────────────────────────────────────────

MANUSCRIPT_SAMPLE = (
    "Исследование влияния цифровой трансформации на управление знаниями "
    "в российских университетах. Методология основана на анализе 50 вузов. "
    "Ключевые слова: цифровизация, управление знаниями, высшее образование. "
    "Результаты показывают, что цифровая трансформация повышает эффективность. "
    "Введение. Современные университеты сталкиваются с необходимостью "
    "цифровизации всех процессов управления знаниями."
)

VENUE_GUIDELINES_SAMPLE = (
    "# Journal: Вестник Образования\n\n"
    "Тематика: педагогика, управление образованием, цифровизация.\n"
    "Формат: научные статьи от 20000 до 40000 знаков.\n"
    "Язык: русский.\n"
    "Рецензирование: двойное слепое.\n"
    "Требования к оформлению: ГОСТ Р 7.0.5-2008.\n"
    "Publisher: Издательский дом «Образование».\n"
    "ISSN: 1234-5678.\n"
    "Периодичность: 4 раза в год.\n"
)

SCENARIO_SAMPLE = {
    "goal": "publication",
    "timeline": "6 months",
    "constraints": [],
}


# ── Pipeline + Registry integration ────────────────────────────────


class TestPipelineRegistryWiring:
    """Pipeline stores venue extractions as provisional when registry is set."""

    def test_pipeline_calls_store_venue_extraction(self, tmp_path: Path):
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )

        mock_registry = MagicMock()
        mock_registry.store_venue_extraction.return_value = {"stored": True}

        pipeline = ManuscriptVenueFitPipeline(
            llm_provider=None,
            registry_service=mock_registry,
        )
        result = pipeline.execute(
            manuscript_text=MANUSCRIPT_SAMPLE,
            venue_guidelines_text=VENUE_GUIDELINES_SAMPLE,
            scenario_data=SCENARIO_SAMPLE,
        )

        mock_registry.store_venue_extraction.assert_called_once()
        call_kwargs = mock_registry.store_venue_extraction.call_args
        venue_dict = call_kwargs[0][0]
        assert isinstance(venue_dict, dict)
        assert call_kwargs[1]["source_type"] == "pipeline_venue_profiler"

    def test_pipeline_works_without_registry(self, tmp_path: Path):
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )

        pipeline = ManuscriptVenueFitPipeline(llm_provider=None)
        result = pipeline.execute(
            manuscript_text=MANUSCRIPT_SAMPLE,
            venue_guidelines_text=VENUE_GUIDELINES_SAMPLE,
            scenario_data=SCENARIO_SAMPLE,
        )
        assert result.venue is not None
        assert result.article is not None

    def test_pipeline_registry_receives_canonical_name(self, tmp_path: Path):
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )

        mock_registry = MagicMock()
        mock_registry.store_venue_extraction.return_value = {}

        pipeline = ManuscriptVenueFitPipeline(
            llm_provider=None,
            registry_service=mock_registry,
        )
        result = pipeline.execute(
            manuscript_text=MANUSCRIPT_SAMPLE,
            venue_guidelines_text=VENUE_GUIDELINES_SAMPLE,
            scenario_data=SCENARIO_SAMPLE,
        )

        venue_dict = mock_registry.store_venue_extraction.call_args[0][0]
        assert "canonical_name" in venue_dict

    def test_registry_error_does_not_break_pipeline(self, tmp_path: Path):
        """Registry failure should not crash the pipeline."""
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )

        mock_registry = MagicMock()
        mock_registry.store_venue_extraction.side_effect = RuntimeError("registry down")

        pipeline = ManuscriptVenueFitPipeline(
            llm_provider=None,
            registry_service=mock_registry,
        )
        result = pipeline.execute(
            manuscript_text=MANUSCRIPT_SAMPLE,
            venue_guidelines_text=VENUE_GUIDELINES_SAMPLE,
            scenario_data=SCENARIO_SAMPLE,
        )
        assert result.venue is not None


class TestPipelineWithRealRegistry:
    """End-to-end: pipeline + real RegistryHub on disk."""

    def test_venue_stored_as_provisional(self, tmp_path: Path):
        from kairoskopion.pipelines.manuscript_venue_fit import (
            ManuscriptVenueFitPipeline,
        )
        from kairoskopion.registry.services import RegistryHub
        from kairoskopion.registry.integration import RegistryIntegrationService

        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        hub = RegistryHub(data_dir=reg_dir)
        registry = RegistryIntegrationService(hub=hub)

        pipeline = ManuscriptVenueFitPipeline(
            llm_provider=None,
            registry_service=registry,
        )
        result = pipeline.execute(
            manuscript_text=MANUSCRIPT_SAMPLE,
            venue_guidelines_text=VENUE_GUIDELINES_SAMPLE,
            scenario_data=SCENARIO_SAMPLE,
        )

        venue_reg = hub._get_registry("venue")
        records = venue_reg.list_all()
        assert len(records) >= 1
        rec = records[0]
        assert rec.source_status in ("provisional", "provisional_with_warning")


class TestCLIRegistryHelper:
    """_resolve_registry_service creates a valid service."""

    def test_creates_registry_service(self, tmp_path: Path):
        from kairoskopion.cli import _resolve_registry_service
        from kairoskopion.registry.integration import RegistryIntegrationService

        svc = _resolve_registry_service(tmp_path)
        assert isinstance(svc, RegistryIntegrationService)

    def test_creates_registry_dir(self, tmp_path: Path):
        from kairoskopion.cli import _resolve_registry_service

        root = tmp_path / "fresh"
        root.mkdir()
        svc = _resolve_registry_service(root)
        assert (root / "registry").is_dir()
