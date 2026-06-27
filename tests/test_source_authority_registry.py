"""Tests for P7.2 Source Authority Registry, Sufficiency Evaluator,
External Adapter Registry, and authority-aware seed workflow integration.
"""

import json
from pathlib import Path

import pytest

from kairoskopion.services.source_authority_registry import (
    SourceAuthorityRecord,
    SourceAuthorityDiscoveryTask,
    SourceAuthorityStore,
    SourceAuthorityDiscoveryTaskStore,
    SourceAuthoritySufficiencyEvaluator,
    SufficiencyResult,
    AUTHORITY_TYPES,
    COUNTRY_AUTHORITY_HINTS,
    MINIMUM_AUTHORITY_SET,
)
from kairoskopion.services.external_source_adapters import (
    ExternalAdapterRecord,
    ExternalAdapterRegistry,
)
from kairoskopion.services.seed_workflow import (
    SeedRegistryWorkflow,
    SeedWorkflowConfig,
    SeedWorkflowResult,
)
from kairoskopion.registry.services import RegistryHub


# ===================================================================
# SourceAuthorityRecord
# ===================================================================

class TestSourceAuthorityRecord:
    def test_defaults(self):
        rec = SourceAuthorityRecord()
        assert rec.authority_id.startswith("srcauth_")
        assert rec.authority_type == "other"
        assert rec.source_status == "provisional"
        assert rec.review_status == "pending"

    def test_to_dict_roundtrip(self):
        rec = SourceAuthorityRecord(
            authority_name="VAK nomenclature",
            authority_type="discipline_classification",
            country="RU",
        )
        d = rec.to_dict()
        assert d["authority_name"] == "VAK nomenclature"
        rec2 = SourceAuthorityRecord.from_dict(d)
        assert rec2.authority_name == rec.authority_name
        assert rec2.country == "RU"

    def test_none_fields_excluded_from_dict(self):
        rec = SourceAuthorityRecord(authority_name="X")
        d = rec.to_dict()
        assert "region" not in d
        assert "known_limitations" not in d


# ===================================================================
# SourceAuthorityStore
# ===================================================================

class TestSourceAuthorityStore:
    def test_in_memory_add_and_get(self):
        store = SourceAuthorityStore()
        rec = SourceAuthorityRecord(authority_name="Test")
        store.add(rec)
        assert store.get(rec.authority_id) is rec

    def test_list_all(self):
        store = SourceAuthorityStore()
        for i in range(3):
            store.add(SourceAuthorityRecord(authority_name=f"Auth{i}"))
        assert len(store.list_all()) == 3

    def test_by_country(self):
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(authority_name="RU1", country="RU"))
        store.add(SourceAuthorityRecord(authority_name="AR1", country="AR"))
        store.add(SourceAuthorityRecord(authority_name="RU2", country="RU"))
        assert len(store.by_country("RU")) == 2
        assert len(store.by_country("AR")) == 1

    def test_by_type(self):
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(
            authority_name="X", authority_type="metric_source",
        ))
        store.add(SourceAuthorityRecord(
            authority_name="Y", authority_type="citation_database",
        ))
        assert len(store.by_type("metric_source")) == 1

    def test_search(self):
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(
            authority_name="РИНЦ eLibrary",
            authority_type="national_journal_registry",
            country="RU",
        ))
        assert len(store.search("eLibrary")) == 1
        assert len(store.search("РИНЦ")) == 1
        assert len(store.search("scopus")) == 0

    def test_jsonl_persistence(self, tmp_path):
        path = tmp_path / "authorities.jsonl"
        store = SourceAuthorityStore(path)
        rec = SourceAuthorityRecord(
            authority_name="Crossref",
            authority_type="citation_database",
        )
        store.add(rec)
        assert path.exists()

        store2 = SourceAuthorityStore(path)
        loaded = store2.get(rec.authority_id)
        assert loaded is not None
        assert loaded.authority_name == "Crossref"

    def test_export_snapshot(self):
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(authority_name="A"))
        store.add(SourceAuthorityRecord(authority_name="B"))
        snap = store.export_snapshot()
        assert len(snap) == 2
        assert all(isinstance(s, dict) for s in snap)


# ===================================================================
# SourceAuthorityDiscoveryTask
# ===================================================================

class TestDiscoveryTask:
    def test_defaults(self):
        task = SourceAuthorityDiscoveryTask()
        assert task.task_id.startswith("authtask_")
        assert task.status == "open"

    def test_to_dict_roundtrip(self):
        task = SourceAuthorityDiscoveryTask(
            target_country="AR",
            target_domain="marine_biology",
            missing_authority_type="national_journal_registry",
            reason="No Argentine journal registry",
        )
        d = task.to_dict()
        task2 = SourceAuthorityDiscoveryTask.from_dict(d)
        assert task2.target_country == "AR"
        assert task2.missing_authority_type == "national_journal_registry"


# ===================================================================
# SourceAuthorityDiscoveryTaskStore
# ===================================================================

class TestDiscoveryTaskStore:
    def test_add_and_list(self):
        store = SourceAuthorityDiscoveryTaskStore()
        t1 = SourceAuthorityDiscoveryTask(status="open")
        t2 = SourceAuthorityDiscoveryTask(status="closed")
        store.add(t1)
        store.add(t2)
        assert len(store.list_all()) == 2
        assert len(store.list_open()) == 1

    def test_jsonl_persistence(self, tmp_path):
        path = tmp_path / "tasks.jsonl"
        store = SourceAuthorityDiscoveryTaskStore(path)
        t = SourceAuthorityDiscoveryTask(
            missing_authority_type="metric_source",
        )
        store.add(t)
        store2 = SourceAuthorityDiscoveryTaskStore(path)
        assert store2.get(t.task_id) is not None


# ===================================================================
# SufficiencyEvaluator
# ===================================================================

class TestSufficiencyEvaluator:
    def _populated_store(self, types: list[str], country: str = "RU"):
        store = SourceAuthorityStore()
        for t in types:
            store.add(SourceAuthorityRecord(
                authority_name=f"auth_{t}",
                authority_type=t,
                country=country,
                source_status="accepted",
            ))
        return store

    def test_empty_store_insufficient(self):
        store = SourceAuthorityStore()
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="RU")
        assert not r.sufficient
        assert len(r.missing_authority_types) > 0
        assert len(r.tasks_to_create) > 0

    def test_full_coverage_sufficient(self):
        all_types = [
            "discipline_classification",
            "national_journal_registry",
            "citation_database",
            "metric_source",
            "author_guidelines_source",
            "editorial_board_source",
            "journal_archive_source",
        ]
        store = self._populated_store(all_types)
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(
            target_country="RU",
            publication_task_type="deep_venue_model",
            desired_outputs=["metrics", "deep_model"],
        )
        assert r.sufficient
        assert r.missing_authority_types == []

    def test_partial_coverage(self):
        store = self._populated_store([
            "discipline_classification",
            "national_journal_registry",
        ])
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="RU")
        assert not r.sufficient
        assert "citation_database" in r.missing_authority_types

    def test_argentina_no_russian_hints(self):
        """Argentina must NOT get VAK/РИНЦ in suggestions."""
        store = SourceAuthorityStore()
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(
            target_country="AR",
            target_domain="fishing_clubs",
        )
        for task in r.tasks_to_create:
            for q in task.get("search_queries", []):
                assert "VAK" not in q, f"VAK leaked into Argentina task: {q}"
                assert "РИНЦ" not in q, f"РИНЦ leaked into Argentina task: {q}"

    def test_russian_hints_for_ru(self):
        """Russia should get VAK/РИНЦ in discipline hints."""
        store = SourceAuthorityStore()
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="RU")
        disc_tasks = [
            t for t in r.tasks_to_create
            if t["missing_authority_type"] == "discipline_classification"
        ]
        assert len(disc_tasks) == 1
        queries = disc_tasks[0].get("search_queries", [])
        assert any("VAK" in q for q in queries)

    def test_international_authorities_count(self):
        """Records with country=None or INTERNATIONAL match any target."""
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(
            authority_name="OpenAlex",
            authority_type="citation_database",
            country="INTERNATIONAL",
            source_status="accepted",
        ))
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="AR")
        assert "citation_database" not in r.missing_authority_types

    def test_rejected_authority_not_usable(self):
        """Rejected authorities should not count as coverage."""
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(
            authority_name="Bad Source",
            authority_type="discipline_classification",
            country="RU",
            source_status="rejected",
        ))
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="RU")
        assert "discipline_classification" in r.missing_authority_types

    def test_vak_warning_for_non_russian(self):
        """VAK/РИНЦ present for non-RU target should trigger warning."""
        store = SourceAuthorityStore()
        store.add(SourceAuthorityRecord(
            authority_name="VAK nomenclature",
            authority_type="discipline_classification",
            country="AR",
            source_status="accepted",
        ))
        ev = SourceAuthoritySufficiencyEvaluator(store)
        r = ev.evaluate(target_country="AR")
        assert any("VAK" in w for w in r.warnings)


# ===================================================================
# ExternalAdapterRegistry
# ===================================================================

class TestExternalAdapterRegistry:
    def test_builtin_count(self):
        reg = ExternalAdapterRegistry()
        assert len(reg.list_all()) == 14

    def test_enabled_vs_disabled(self):
        reg = ExternalAdapterRegistry()
        enabled = reg.list_enabled()
        all_adapters = reg.list_all()
        assert len(enabled) < len(all_adapters)
        enabled_ids = {a.adapter_id for a in enabled}
        assert "openalex" in enabled_ids
        assert "crossref" in enabled_ids
        assert "scopus" not in enabled_ids
        assert "wos" not in enabled_ids

    def test_free_adapters(self):
        reg = ExternalAdapterRegistry()
        free = reg.list_free()
        for a in free:
            assert a.cost_class == "free"

    def test_suggest_for_citation_database(self):
        reg = ExternalAdapterRegistry()
        suggested = reg.suggest_for_authority_type("citation_database")
        assert "openalex" in suggested
        assert "crossref" in suggested

    def test_suggest_for_metric_source(self):
        reg = ExternalAdapterRegistry()
        suggested = reg.suggest_for_authority_type("metric_source")
        assert "openalex" in suggested
        assert "scopus" not in suggested  # disabled

    def test_paid_disabled_by_default(self):
        reg = ExternalAdapterRegistry()
        assert not reg.is_available("scopus")
        assert not reg.is_available("wos")

    def test_can_use_for(self):
        reg = ExternalAdapterRegistry()
        assert reg.can_use_for("openalex", require_search=True)
        assert not reg.can_use_for("unpaywall", require_search=True)

    def test_adapter_to_dict(self):
        rec = ExternalAdapterRecord(
            adapter_id="test",
            adapter_name="Test",
        )
        d = rec.to_dict()
        assert d["adapter_id"] == "test"


# ===================================================================
# Constants & Types
# ===================================================================

class TestConstants:
    def test_authority_types_not_empty(self):
        assert len(AUTHORITY_TYPES) >= 14

    def test_minimum_authority_set_keys(self):
        for key in MINIMUM_AUTHORITY_SET:
            assert key in AUTHORITY_TYPES

    def test_country_hints_ru(self):
        assert "RU" in COUNTRY_AUTHORITY_HINTS
        ru = COUNTRY_AUTHORITY_HINTS["RU"]
        assert "discipline_classification" in ru
        assert any("VAK" in s for s in ru["discipline_classification"])

    def test_country_hints_generic(self):
        assert "GENERIC" in COUNTRY_AUTHORITY_HINTS


# ===================================================================
# Authority-aware Seed Workflow Integration
# ===================================================================

MINIMAL_ARTICLE = """
This article investigates the integration of artificial intelligence in
higher education in Russia. We examine pedagogical frameworks, digital
literacy assessment methods, and student performance metrics across
several universities. The study employs mixed methods including survey
analysis and computational modeling of learning outcomes.
""".strip()


class TestAuthorityAwareWorkflow:
    def _make_hub(self, tmp_path):
        return RegistryHub(tmp_path / "registries")

    def test_empty_authority_creates_tasks(self, tmp_path):
        hub = self._make_hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        config = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_country="RU",
            domain_target="education_ai",
            target_zones=["education"],
        )
        result = wf.run(config)
        assert result.authority_coverage is not None
        assert not result.authority_coverage["sufficient"]
        assert len(result.source_authority_tasks) > 0

    def test_full_authority_no_tasks(self, tmp_path):
        hub = self._make_hub(tmp_path)
        store = SourceAuthorityStore()
        for t in [
            "discipline_classification",
            "national_journal_registry",
            "citation_database",
            "metric_source",
            "author_guidelines_source",
            "editorial_board_source",
            "journal_archive_source",
        ]:
            store.add(SourceAuthorityRecord(
                authority_name=f"auth_{t}",
                authority_type=t,
                country="RU",
                source_status="accepted",
            ))
        wf = SeedRegistryWorkflow(hub, authority_store=store)
        config = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_country="RU",
            domain_target="education_ai",
            target_zones=["education"],
        )
        result = wf.run(config)
        assert result.authority_coverage["sufficient"]
        assert len(result.source_authority_tasks) == 0

    def test_available_adapters_populated(self, tmp_path):
        hub = self._make_hub(tmp_path)
        wf = SeedRegistryWorkflow(hub)
        config = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_country="RU",
        )
        result = wf.run(config)
        assert len(result.available_adapters) > 0
        assert "openalex" in result.available_adapters

    def test_blocked_on_authority_reported(self, tmp_path):
        """With no authorities, deep venue tasks should report blocked."""
        hub = self._make_hub(tmp_path)
        # Add a provisional venue so shortlist is non-empty
        from kairoskopion.registry.models import VenueRegistryRecord
        venue = VenueRegistryRecord(
            canonical_name="Test Journal",
            source_status="provisional",
        )
        hub.venues().add_provisional(venue)

        wf = SeedRegistryWorkflow(hub)
        config = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_country="RU",
            target_zones=["Test"],
        )
        result = wf.run(config)
        if result.shortlist:
            assert len(result.blocked_on_authority) > 0
            blocked_types = {b["blocked_on"] for b in result.blocked_on_authority}
            assert "editorial_board_source" in blocked_types or \
                   "journal_archive_source" in blocked_types

    def test_output_persistence(self, tmp_path):
        hub = self._make_hub(tmp_path)
        out_dir = tmp_path / "output"
        wf = SeedRegistryWorkflow(hub)
        config = SeedWorkflowConfig(
            article_text=MINIMAL_ARTICLE,
            target_country="RU",
            output_dir=out_dir,
            target_zones=["education"],
        )
        result = wf.run(config)
        reports = out_dir / "reports"
        assert (reports / "authority_coverage.json").exists()
        assert (reports / "gaps.md").exists()
        if result.source_authority_tasks:
            assert (out_dir / "acquisition_tasks" / "authority_discovery_tasks.json").exists()


# ===================================================================
# Validation hardening
# ===================================================================

class TestValidationHardening:
    def test_sufficiency_result_to_dict(self):
        r = SufficiencyResult(sufficient=True, confidence="high")
        d = r.to_dict()
        assert d["sufficient"] is True
        assert d["confidence"] == "high"

    def test_empty_store_by_country(self):
        store = SourceAuthorityStore()
        assert store.by_country("XX") == []

    def test_empty_store_by_type(self):
        store = SourceAuthorityStore()
        assert store.by_type("other") == []

    def test_discovery_task_store_list_open_filters(self):
        store = SourceAuthorityDiscoveryTaskStore()
        store.add(SourceAuthorityDiscoveryTask(status="open"))
        store.add(SourceAuthorityDiscoveryTask(status="in_progress"))
        store.add(SourceAuthorityDiscoveryTask(status="closed"))
        store.add(SourceAuthorityDiscoveryTask(status="resolved"))
        assert len(store.list_open()) == 2

    def test_adapter_registry_unknown_id(self):
        reg = ExternalAdapterRegistry()
        assert reg.get("nonexistent") is None
        assert not reg.is_available("nonexistent")
        assert not reg.can_use_for("nonexistent")

    def test_suggest_for_unknown_type(self):
        reg = ExternalAdapterRegistry()
        suggested = reg.suggest_for_authority_type("unknown_type_xyz")
        assert isinstance(suggested, list)


# ===================================================================
# P7.2B Recovery Tests — verify recovered authority records
# ===================================================================

class TestRecoveredAuthorities:
    """Tests for P7.2B: recovered source authority records from corpus."""

    @pytest.fixture
    def recovered_store(self, tmp_path):
        """Load recovered records into a tmp store to verify structure."""
        src = Path("data/seed_registry/source_authorities/source_authority_records.jsonl")
        if not src.exists():
            pytest.skip("Recovered authority records not yet generated")
        dst = tmp_path / "recovered.jsonl"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return SourceAuthorityStore(dst)

    def test_record_count(self, recovered_store):
        records = recovered_store.list_all()
        assert len(records) >= 15, f"Expected >= 15 records, got {len(records)}"

    def test_all_records_have_evidence_refs(self, recovered_store):
        for rec in recovered_store.list_all():
            assert rec.evidence_refs, f"{rec.authority_name} has no evidence_refs"
            for ref in rec.evidence_refs:
                assert "source_type" in ref, f"Missing source_type in {rec.authority_name}"
                assert "source_id" in ref, f"Missing source_id in {rec.authority_name}"

    def test_no_model_memory_evidence(self, recovered_store):
        allowed = {"venue_evidence_pack", "adapter_code", "project_data", "project_doc"}
        for rec in recovered_store.list_all():
            for ref in rec.evidence_refs:
                assert ref["source_type"] in allowed, (
                    f"{rec.authority_name} has disallowed source_type: {ref['source_type']}"
                )

    def test_evidence_files_exist(self, recovered_store):
        for rec in recovered_store.list_all():
            for ref in rec.evidence_refs:
                source_id = ref["source_id"]
                if source_id.startswith("data/") or source_id.startswith("src/"):
                    assert Path(source_id).exists(), (
                        f"Evidence file missing: {source_id} "
                        f"(referenced by {rec.authority_name})"
                    )

    def test_ru_authorities_have_country(self, recovered_store):
        ru = recovered_store.by_country("RU")
        assert len(ru) >= 4, f"Expected >= 4 RU authorities, got {len(ru)}"
        for rec in ru:
            assert rec.country == "RU"

    def test_international_authorities(self, recovered_store):
        intl = recovered_store.by_country("INTERNATIONAL")
        assert len(intl) >= 8, f"Expected >= 8 INTERNATIONAL authorities, got {len(intl)}"

    def test_accepted_records_have_curator_confirmed(self, recovered_store):
        for rec in recovered_store.list_all():
            if rec.source_status == "accepted":
                assert rec.review_status == "curator_confirmed", (
                    f"{rec.authority_name} is accepted but review_status={rec.review_status}"
                )

    def test_sufficiency_ru_with_recovered(self, recovered_store):
        evaluator = SourceAuthoritySufficiencyEvaluator(recovered_store)
        result = evaluator.evaluate(target_country="RU", target_domain="education")
        assert result.sufficient is True, (
            f"RU/education should be sufficient, missing: {result.missing_authority_types}"
        )

    def test_sufficiency_ar_no_vak(self, recovered_store):
        evaluator = SourceAuthoritySufficiencyEvaluator(recovered_store)
        result = evaluator.evaluate(target_country="AR", target_domain="fishing")
        for auth in result.usable_authorities:
            name = auth.get("authority_name", "")
            assert "ВАК" not in name and "VAK" not in name.upper() or "INTERNATIONAL" in auth.get("country", ""), (
                f"AR case should not include VAK authority: {name}"
            )

    def test_authority_types_diverse(self, recovered_store):
        types = set()
        for rec in recovered_store.list_all():
            types.add(rec.authority_type)
        assert len(types) >= 5, f"Expected >= 5 authority types, got {len(types)}: {types}"

    def test_all_records_have_access_mode(self, recovered_store):
        for rec in recovered_store.list_all():
            assert rec.access_mode != "unknown", (
                f"{rec.authority_name} has unknown access_mode"
            )
