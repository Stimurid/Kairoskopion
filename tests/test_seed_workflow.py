"""Tests for SeedRegistryWorkflow (P7 Bootstrap / Track 13).

Categories covered:
  - Privacy: article text never written to tracked paths
  - Archetype: extraction produces valid archetype dict
  - Registry-first lookup: disciplines searched before tasks created
  - Acquisition tasks: created on miss, persisted in store
  - Source packets: ingest_local_file_as_packet works
  - Venue universe: registry-first search + task fallback
  - Metrics gap: reported when registry empty
  - Shortlist: shortage reported, accepted/provisional sorted
  - Deep venue tasks: created for shortlisted venues
  - Validation: config with missing text fails gracefully
  - No-LLM mode: warning generated
  - Mock fixture E2E: full workflow on minimal text
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.registry.models import (
    DisciplineRecord,
    SourcePacket,
    VenueRegistryRecord,
)
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.seed_workflow import (
    SeedRegistryWorkflow,
    SeedWorkflowConfig,
    SeedWorkflowResult,
    ingest_local_file_as_packet,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_ARTICLE = (
    "Universities After AI: Epistemic Legitimation and Distributed Production. "
    "This article explores the transformation of universities in the age of "
    "artificial intelligence. We argue that AI fundamentally reshapes how "
    "knowledge is produced and legitimized in academic institutions. The "
    "Humboldtian model of the research university faces challenges from "
    "distributed intellectual production facilitated by large language models. "
    "Section 1: Introduction to higher education transformation. "
    "Section 2: Historical models of the university. "
    "Section 3: Epistemic legitimation in the AI era. "
    "Section 4: Distributed intellectual production. "
    "Section 5: Implications for second-tier universities. "
    "References: [1] Clark, B. (1998). Creating Entrepreneurial Universities."
)


def _hub(tmp_path: Path) -> RegistryHub:
    return RegistryHub(data_dir=tmp_path / "registry")


def _seed_discipline(hub: RegistryHub, name: str) -> DisciplineRecord:
    rec = DisciplineRecord(
        display_names={"en": name, "ru": name},
        aliases=[name.lower()],
    )
    hub.disciplines().add_provisional(rec)
    return rec


def _seed_venue(
    hub: RegistryHub,
    name: str,
    *,
    source_status: str = "provisional",
) -> VenueRegistryRecord:
    rec = VenueRegistryRecord(
        canonical_name=name,
    )
    hub.venues().add_provisional(rec)
    if source_status == "accepted":
        hub.venues().accept(rec.venue_id)
    return rec


# ---------------------------------------------------------------------------
# 1. Privacy — article text never in tracked output
# ---------------------------------------------------------------------------

class TestPrivacy:
    def test_raw_article_not_in_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            output_dir=out,
        )
        wf.run(cfg)
        for p in out.rglob("*"):
            if p.is_file():
                content = p.read_text(encoding="utf-8")
                assert MINIMAL_ARTICLE not in content

    def test_no_files_outside_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "seed_out"
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            output_dir=out,
        )
        wf.run(cfg)
        all_new = set(tmp_path.rglob("*")) - {tmp_path}
        registry_or_out = [
            p for p in all_new
            if "registry" not in str(p) and "seed_out" not in str(p)
        ]
        assert not registry_or_out, f"Files outside expected dirs: {registry_or_out}"


# ---------------------------------------------------------------------------
# 2. Article archetype
# ---------------------------------------------------------------------------

class TestArchetype:
    def test_archetype_has_required_keys(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        arch = result.article_archetype
        assert arch is not None
        for key in ("archetype_id", "genre", "provenance", "confidence", "status"):
            assert key in arch, f"Missing key: {key}"
        assert arch["status"] == "draft"
        assert arch["provenance"] == "deterministic_article_modeler"

    def test_archetype_source_ref_preserved(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            article_source_ref="test://luksha_08",
        )
        result = wf.run(cfg)
        assert result.article_archetype["source_article_ref"] == "test://luksha_08"


# ---------------------------------------------------------------------------
# 3. Registry-first discipline lookup
# ---------------------------------------------------------------------------

class TestRegistryFirstLookup:
    def test_existing_discipline_found(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_discipline(hub, "Higher Education")
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Education"],
        )
        result = wf.run(cfg)
        found = [d for d in result.discipline_lookups if d["status"] == "found"]
        assert len(found) >= 1

    def test_missing_discipline_creates_task(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Quantum Chromodynamics"],
        )
        result = wf.run(cfg)
        misses = [d for d in result.discipline_lookups if d["status"] == "miss"]
        assert len(misses) >= 1
        assert any(t["task_type"] == "discipline_lookup" for t in result.acquisition_tasks_created)


# ---------------------------------------------------------------------------
# 4. Acquisition tasks
# ---------------------------------------------------------------------------

class TestAcquisitionTasks:
    def test_tasks_persisted_in_store(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Nonexistent Domain"],
        )
        result = wf.run(cfg)
        stored = hub.tasks.list_all()
        assert len(stored) >= 1
        assert all(t.status in ("open", "pending") for t in stored)

    def test_venue_discovery_task_on_empty_registry(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        venue_tasks = [
            t for t in result.acquisition_tasks_created
            if t["task_type"] == "venue_discovery"
        ]
        assert len(venue_tasks) >= 1


# ---------------------------------------------------------------------------
# 5. Source packets
# ---------------------------------------------------------------------------

class TestSourcePackets:
    def test_ingest_local_file(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        article = tmp_path / "test_article.md"
        article.write_text("Test content for source packet", encoding="utf-8")
        pkt = ingest_local_file_as_packet(hub, article)
        assert pkt.packet_type == "article_text"
        assert pkt.source_type == "local_file"
        assert pkt.evidence_status == "user_provided"
        stored = hub.packets.list_all()
        assert len(stored) == 1
        assert stored[0].packet_id == pkt.packet_id

    def test_excerpt_truncation(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        big = tmp_path / "big.md"
        big.write_text("x" * 5000, encoding="utf-8")
        pkt = ingest_local_file_as_packet(hub, big)
        assert len(pkt.excerpt) == 2000


# ---------------------------------------------------------------------------
# 6. Venue universe
# ---------------------------------------------------------------------------

class TestVenueUniverse:
    def test_registry_venues_included(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_venue(hub, "Education AI Journal", source_status="accepted")
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Education AI"],
        )
        result = wf.run(cfg)
        names = [v["canonical_name"] for v in result.venue_universe]
        assert "Education AI Journal" in names

    def test_empty_registry_creates_tasks(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        assert len(result.venue_universe) == 0
        venue_tasks = [
            t for t in result.acquisition_tasks_created
            if t["task_type"] == "venue_discovery"
        ]
        assert len(venue_tasks) >= 1

    def test_empty_universe_warning(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        assert any("empty" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# 7. Metrics gap
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_empty_metrics_gap_reported(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        assert any("MetricRecord" in g or "metric" in g.lower() for g in result.gaps)


# ---------------------------------------------------------------------------
# 8. Shortlist
# ---------------------------------------------------------------------------

class TestShortlist:
    def test_shortage_reported_when_few_venues(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_venue(hub, "One Journal", source_status="accepted")
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["One"],
        )
        result = wf.run(cfg)
        assert any("shortage" in g.lower() for g in result.gaps)

    def test_accepted_before_provisional(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_venue(hub, "Accepted Venue", source_status="accepted")
        _seed_venue(hub, "Provisional Venue", source_status="provisional")
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Venue"],
        )
        result = wf.run(cfg)
        accepted = [s for s in result.shortlist if s["evidence_strength"] == "registry_accepted"]
        provisional = [s for s in result.shortlist if s["evidence_strength"] == "provisional"]
        assert len(accepted) >= 1
        assert len(provisional) >= 1
        assert provisional[0].get("warning") is not None


# ---------------------------------------------------------------------------
# 9. Deep venue tasks
# ---------------------------------------------------------------------------

class TestDeepVenueTasks:
    def test_tasks_created_for_shortlisted(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_venue(hub, "Deep Target", source_status="accepted")
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Deep"],
        )
        result = wf.run(cfg)
        assert len(result.deep_venue_tasks) >= 1
        assert all(t["task_type"] == "deep_venue_model" for t in result.deep_venue_tasks)


# ---------------------------------------------------------------------------
# 10. Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_empty_text_produces_archetype(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text="")
        result = wf.run(cfg)
        assert result.article_archetype is not None
        assert len(result.gaps) >= 1


# ---------------------------------------------------------------------------
# 11. No-LLM mode
# ---------------------------------------------------------------------------

class TestNoLlmMode:
    def test_no_llm_warning_generated(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE, no_live_llm=True)
        result = wf.run(cfg)
        assert any("no-live-LLM" in w.lower() or "no-live-llm" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# 12. E2E mock fixture
# ---------------------------------------------------------------------------

class TestE2EFixture:
    def test_full_workflow_empty_registry(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        out = tmp_path / "seed_output"
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            output_dir=out,
            no_live_llm=True,
        )
        result = wf.run(cfg)

        assert result.article_archetype is not None
        assert result.run_id
        assert len(result.gaps) >= 1
        assert len(result.warnings) >= 1
        assert len(result.acquisition_tasks_created) >= 1

        # Output files written
        assert (out / "reports" / "gaps.md").exists()
        assert (out / "reports" / "workflow_run_report.json").exists()
        if result.acquisition_tasks_created:
            assert (out / "acquisition_tasks" / "open_tasks.json").exists()

    def test_full_workflow_with_seeded_registry(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        _seed_discipline(hub, "Education Studies")
        _seed_venue(hub, "Education Research Review", source_status="accepted")
        _seed_venue(hub, "AI and Education Journal", source_status="provisional")

        out = tmp_path / "seed_output"
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_zones=["Education"],
            output_dir=out,
        )
        result = wf.run(cfg)

        assert result.article_archetype is not None
        found_disciplines = [d for d in result.discipline_lookups if d["status"] == "found"]
        assert len(found_disciplines) >= 1
        assert len(result.venue_universe) >= 1
        assert len(result.shortlist) >= 1
        assert len(result.deep_venue_tasks) >= 1

    def test_result_to_dict_serializable(self, tmp_path: Path) -> None:
        hub = _hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        cfg = SeedWorkflowConfig(article_text=MINIMAL_ARTICLE)
        result = wf.run(cfg)
        d = result.to_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert len(serialized) > 100
