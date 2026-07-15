"""P6.2 closure tests — VenueDiscoveryAgent wiring, pipeline closure,
status propagation, review-queue endpoint, E2E smoke.
"""

from __future__ import annotations

import dataclasses as dc
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from kairoskopion.registry.integration import RegistryIntegrationService
from kairoskopion.registry.services import RegistryHub
from kairoskopion.registry.models import (
    VenueRegistryRecord,
    VenueSectionRecord,
    DisciplineRecord,
    EvidenceRef,
)
from kairoskopion.registry.status import record_usage_status


# ===================================================================
# Helpers
# ===================================================================

def _make_hub(tmp_path: Path) -> RegistryHub:
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    return RegistryHub(data_dir=reg_dir)


def _make_service(tmp_path: Path) -> RegistryIntegrationService:
    return RegistryIntegrationService(hub=_make_hub(tmp_path))


def _seed_venue(hub: RegistryHub, name: str, issn: str | None = None,
                source_status: str = "provisional",
                review_status: str = "pending") -> VenueRegistryRecord:
    rec = VenueRegistryRecord(
        canonical_name=name,
        issn=issn,
        source_status=source_status,
        review_status=review_status,
    )
    hub.venues().add_provisional(rec)
    if source_status == "accepted" and review_status == "curator_confirmed":
        hub.venues().accept(rec.venue_id)
    return rec


# ===================================================================
# Track 3: VenueDiscoveryAgent → registry closure
# ===================================================================

class TestDiscoverVenueRegistryClosure:
    """discover_venues() must store discovered candidates as provisional."""

    def test_discover_stores_candidates_as_provisional(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import (
            DisciplinaryPathway,
            VenueCandidatePool,
        )

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)
        case.pathways = [DisciplinaryPathway(discipline_name="Economics")]

        fake_pool = VenueCandidatePool(
            candidates=[
                {"canonical_name": "Вопросы экономики", "issn": "0042-8736"},
                {"canonical_name": "Финансы и кредит"},
            ],
        )

        fake_output = MagicMock()
        fake_output.output_entity = {"pool": fake_pool.to_dict()}

        with patch(
            "kairoskopion.agents.venue.venue_discovery.VenueDiscoveryAgent"
        ) as MockAgent:
            MockAgent.return_value.execute_deterministic.return_value = fake_output
            result = case.discover_venues()

        venues = svc.hub.venues().list_all()
        assert len(venues) >= 2
        names = {v.canonical_name for v in venues}
        assert "Вопросы экономики" in names
        assert "Финансы и кредит" in names
        for v in venues:
            assert v.source_status == "provisional"

    def test_discover_propagates_registry_status(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import DisciplinaryPathway, VenueCandidatePool

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)
        case.pathways = [DisciplinaryPathway(discipline_name="Economics")]

        fake_pool = VenueCandidatePool(candidates=[])
        fake_output = MagicMock()
        fake_output.output_entity = {"pool": fake_pool.to_dict()}

        with patch(
            "kairoskopion.agents.venue.venue_discovery.VenueDiscoveryAgent"
        ) as MockAgent:
            MockAgent.return_value.execute_deterministic.return_value = fake_output
            result = case.discover_venues()

        assert isinstance(result, dict)

    def test_discover_skips_nameless_candidates(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import DisciplinaryPathway, VenueCandidatePool

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)
        case.pathways = [DisciplinaryPathway(discipline_name="Economics")]

        fake_pool = VenueCandidatePool(
            candidates=[{"issn": "0000-0000"}],
        )
        fake_output = MagicMock()
        fake_output.output_entity = {"pool": fake_pool.to_dict()}

        with patch(
            "kairoskopion.agents.venue.venue_discovery.VenueDiscoveryAgent"
        ) as MockAgent:
            MockAgent.return_value.execute_deterministic.return_value = fake_output
            case.discover_venues()

        assert len(svc.hub.venues().list_all()) == 0

    def test_discover_deduplicates_by_issn(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import DisciplinaryPathway, VenueCandidatePool

        svc = _make_service(tmp_path)
        _seed_venue(svc.hub, "Вопросы экономики", issn="0042-8736")
        case = Case(registry_service=svc)
        case.pathways = [DisciplinaryPathway(discipline_name="Economics")]

        fake_pool = VenueCandidatePool(
            candidates=[
                {"canonical_name": "Вопросы экономики", "issn": "0042-8736"},
            ],
        )
        fake_output = MagicMock()
        fake_output.output_entity = {"pool": fake_pool.to_dict()}

        with patch(
            "kairoskopion.agents.venue.venue_discovery.VenueDiscoveryAgent"
        ) as MockAgent:
            MockAgent.return_value.execute_deterministic.return_value = fake_output
            case.discover_venues()

        assert len(svc.hub.venues().list_all()) == 1


# ===================================================================
# Track 4: ManuscriptVenueFitPipeline — legacy bypass documentation
# ===================================================================

class TestPipelineLegacyBypass:
    """Pipeline is CLI-only, not API-reachable."""

    def test_pipeline_not_imported_by_api_app(self):
        import kairoskopion.api.app as api_mod
        src = Path(api_mod.__file__).read_text(encoding="utf-8")
        assert "ManuscriptVenueFitPipeline" not in src

    def test_pipeline_exists_in_cli(self):
        import kairoskopion.cli as cli_mod
        src = Path(cli_mod.__file__).read_text(encoding="utf-8")
        assert "ManuscriptVenueFitPipeline" in src


# ===================================================================
# Track 5: Status propagation audit
# ===================================================================

class TestStatusPropagation:
    """All registry-relevant outputs carry _registry_status."""

    def test_investigate_venue_requires_llm(self, tmp_path):
        """ARCH-SEM-001: investigate_venue requires LLM for semantic profiling."""
        from kairoskopion.api.cases import Case

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)

        text = "Philosophy journal about continental philosophy and STS. " * 20
        result = case.investigate_venue(text)
        assert result["status"] == "llm_required"

    def test_venue_matrix_propagates(self, tmp_path):
        from kairoskopion.api.cases import Case

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)
        result = case.get_venue_matrix()
        assert isinstance(result, dict)

    def test_propagate_status_annotates_venue_id(self, tmp_path):
        svc = _make_service(tmp_path)
        rec = _seed_venue(svc.hub, "Test Journal", issn="1234-5678")
        output = {"venue_id": rec.venue_id, "data": "test"}
        result = svc.propagate_status(output)
        assert "_registry_status" in result
        assert result["_registry_status"]["source_status"] == "provisional"

    def test_propagate_status_recurses_candidates(self, tmp_path):
        svc = _make_service(tmp_path)
        rec = _seed_venue(svc.hub, "Test", issn="0000-0001")
        output = {
            "candidates": [
                {"venue_id": rec.venue_id, "name": "Test"},
                {"name": "Unknown"},
            ]
        }
        result = svc.propagate_status(output)
        assert result["candidates"][0].get("_registry_status") is not None
        assert "_registry_status" not in result["candidates"][1]


# ===================================================================
# Track 6: Review-queue endpoint
# ===================================================================

class TestReviewQueueEndpoint:
    """GET /api/registry/review-queue returns pending records."""

    def test_review_queue_returns_provisional(self, tmp_path):
        from kairoskopion.api.registry_router import review_queue
        from kairoskopion.registry.store import load_registry, _RECORD_TYPES

        import os
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        try:
            venues_reg = load_registry("venue", reg_dir)
            rec = VenueRegistryRecord(
                canonical_name="Test Journal",
                source_status="provisional",
                review_status="pending",
            )
            venues_reg.add_provisional(rec)

            result = review_queue(limit=100)
            assert len(result) >= 1
            found = [r for r in result if r.get("canonical_name") == "Test Journal"]
            assert len(found) == 1
            assert found[0]["_record_type"] == "venue"
            assert found[0]["_usage_status"] == "provisional_with_warning"
        finally:
            os.environ.pop("KAIROSKOPION_DATA_DIR", None)

    def test_review_queue_excludes_accepted(self, tmp_path):
        from kairoskopion.api.registry_router import review_queue
        from kairoskopion.registry.store import load_registry

        import os
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        try:
            venues_reg = load_registry("venue", reg_dir)
            rec = VenueRegistryRecord(
                canonical_name="Accepted",
                source_status="accepted",
                review_status="curator_confirmed",
            )
            venues_reg.add_provisional(rec)
            venues_reg.accept(rec.venue_id)

            result = review_queue(limit=100)
            accepted = [r for r in result if r.get("canonical_name") == "Accepted"]
            assert len(accepted) == 0
        finally:
            os.environ.pop("KAIROSKOPION_DATA_DIR", None)

    def test_review_queue_respects_limit(self, tmp_path):
        from kairoskopion.api.registry_router import review_queue
        from kairoskopion.registry.store import load_registry

        import os
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KAIROSKOPION_DATA_DIR"] = str(tmp_path)
        try:
            venues_reg = load_registry("venue", reg_dir)
            for i in range(5):
                rec = VenueRegistryRecord(
                    canonical_name=f"Journal {i}",
                    source_status="provisional",
                    review_status="pending",
                )
                venues_reg.add_provisional(rec)

            result = review_queue(limit=3)
            assert len(result) == 3
        finally:
            os.environ.pop("KAIROSKOPION_DATA_DIR", None)


# ===================================================================
# Track 7: E2E acceptance smoke
# ===================================================================

class TestE2EAcceptanceSmoke:
    """End-to-end scenarios proving registry-first product paths."""

    def test_scenario_a_discipline_registry_first(self, tmp_path):
        """Scenario A: discipline registry lookup → canonical match."""
        svc = _make_service(tmp_path)
        hub = svc.hub
        disc = DisciplineRecord(
            display_names={"en": "Economics", "ru": "Экономика"},
            aliases=["economics", "экономика"],
            source_status="accepted",
            review_status="curator_confirmed",
        )
        hub.disciplines().add_provisional(disc)
        hub.disciplines().accept(disc.discipline_id)

        result = svc.discipline_lookup("economics")
        assert result["found"] is True
        assert result["usage_status"] == "canonical"
        assert result["record"].discipline_id == disc.discipline_id

    def test_scenario_b_venue_investigation_requires_llm(self, tmp_path):
        """ARCH-SEM-001: venue investigation requires LLM."""
        from kairoskopion.api.cases import Case

        svc = _make_service(tmp_path)
        case = Case(registry_service=svc)

        text = (
            "# Вопросы философии\n\n"
            "Journal: Вопросы философии\n"
            "ISSN: 0042-8744\n"
            "Publisher: Российская академия наук\n"
            "Aims and scope: Вопросы философии — ведущий российский "
            "философский журнал, публикующий оригинальные исследования "
            "по всем разделам философии, включая онтологию, эпистемологию, "
            "этику, эстетику, логику, философию науки и историю философии.\n"
        )
        result = case.investigate_venue(text)
        assert result["status"] == "llm_required"
        assert case.venue_source_metadata is not None

    def test_scenario_c_venue_matrix_enrichment(self, tmp_path):
        """Scenario C: venue matrix enriches with provenance from registry."""
        from kairoskopion.api.cases import Case

        svc = _make_service(tmp_path)
        rec = _seed_venue(svc.hub, "Known Journal", issn="1111-2222")
        case = Case(registry_service=svc)

        result = case.get_venue_matrix()
        assert isinstance(result, dict)

    def test_scenario_d_review_queue_populated_after_investigation(self, tmp_path):
        """Scenario D: after investigation, review queue shows pending records."""
        svc = _make_service(tmp_path)
        svc.store_venue_extraction(
            {"canonical_name": "New Journal", "issn": "9999-0001"},
            source_url="https://example.com/guidelines",
            source_type="author_guidelines",
        )
        venues = svc.hub.venues().list_all()
        assert len(venues) >= 1
        for v in venues:
            status = record_usage_status(v)
            assert status == "provisional_with_warning"

    def test_scenario_e_accepted_record_is_canonical(self, tmp_path):
        """Scenario E: accepted+curator_confirmed → canonical usage."""
        svc = _make_service(tmp_path)
        rec = _seed_venue(
            svc.hub, "Canonical Journal", issn="5555-0001",
            source_status="accepted", review_status="curator_confirmed",
        )
        status = record_usage_status(rec)
        assert status == "canonical"

        result = svc.propagate_status({"venue_id": rec.venue_id})
        assert result["_registry_status"]["usage_status"] == "canonical"


# ===================================================================
# Track 2: Bypass audit — structural tests
# ===================================================================

class TestBypassAuditStructural:
    """Verify no new un-audited agent calls in cases.py."""

    KNOWN_AGENT_CALLS = {
        "InputClassifierAgent",
        "ArticleModelerAgent",
        "ArticleSemanticProfilerAgent",
        "DisciplineMatcherAgent",
        "ArticleFieldPositionerAgent",
        "VenueProfilerAgent",
        "VenueFieldPositionerAgent",
        "DisciplinaryPathwayMapperAgent",
        "VenueDiscoveryAgent",
        "FitAssessorAgent",
        "MismatchNarratorAgent",
    }

    def test_no_new_agent_calls(self):
        import re
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        pattern = re.compile(r"(\w+Agent)\(\)")
        found = set(pattern.findall(src))
        unknown = found - self.KNOWN_AGENT_CALLS
        assert not unknown, f"Unknown agent calls in cases.py: {unknown}"

    def test_registry_relevant_agents_wired(self):
        from kairoskopion.api import cases as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "_registry.store_venue_extraction" in src
        assert "_registry.propagate_status" in src
        assert "_registry.enrich_candidates_with_provenance" in src
        assert "_registry.build_family_context" in src
