"""Tests for Real Source Acquisition v0.

Covers: adapter config/mode, HTTP boundary, all 6 adapters,
real_source_acquisition aggregation, VenueEvidenceStack integration,
EvidenceAuditor authority/conflict tests, CLI commands.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kairoskopion.adapters.venue.base import (
    SourceAcquisitionConfig,
    VenueAdapterConfig,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
)
from kairoskopion.enums import SourceAccessMode


# ========================================================================
# Adapter config / mode tests
# ========================================================================


class TestAdapterConfig(unittest.TestCase):
    def test_default_config_is_offline_safe(self):
        cfg = SourceAcquisitionConfig()
        assert cfg.live_enabled is False
        mode = cfg.effective_mode("openalex_venue")
        assert mode == VenueAdapterMode.OFFLINE_STUB

    def test_live_mode_requires_global_flag(self):
        cfg = SourceAcquisitionConfig(
            live_enabled=False,
            adapters={"openalex_venue": VenueAdapterConfig(mode="live_api")},
        )
        assert cfg.effective_mode("openalex_venue") == VenueAdapterMode.OFFLINE_STUB

    def test_live_mode_with_global_flag(self):
        cfg = SourceAcquisitionConfig(
            live_enabled=True,
            adapters={"openalex_venue": VenueAdapterConfig(mode="live_api")},
        )
        assert cfg.effective_mode("openalex_venue") == VenueAdapterMode.LIVE_API

    def test_disabled_adapter_stays_offline(self):
        cfg = SourceAcquisitionConfig(
            live_enabled=True,
            adapters={"openalex_venue": VenueAdapterConfig(enabled=False, mode="live_api")},
        )
        assert cfg.effective_mode("openalex_venue") == VenueAdapterMode.OFFLINE_STUB

    def test_config_serializes(self):
        cfg = SourceAcquisitionConfig(
            adapters={"test": VenueAdapterConfig(timeout=15)},
        )
        d = cfg.to_dict()
        assert d["live_enabled"] is False
        assert "test" in d["adapters"]

    def test_adapter_result_serializes(self):
        result = VenueAdapterResult(
            adapter_id="test",
            mode="offline_stub",
            status="success",
            source_access_mode="metadata_api",
        )
        d = result.to_dict()
        assert d["adapter_id"] == "test"
        assert d["source_access_mode"] == "metadata_api"
        assert d["prohibited_claims"] == []
        assert d["unsupported_claims"] == []
        assert d["provenance"] == ""

    def test_failure_serializes_not_exception(self):
        result = VenueAdapterResult(
            adapter_id="test",
            mode="live_api",
            status="error",
            error="timeout",
        )
        d = result.to_dict()
        assert d["status"] == "error"
        assert d["error"] == "timeout"
        assert not result.is_available

    def test_venue_adapter_mode_fixture(self):
        assert VenueAdapterMode.FIXTURE.value == "fixture"

    def test_venue_adapter_mode_cached(self):
        assert VenueAdapterMode.CACHED.value == "cached"

    def test_venue_adapter_status_enum(self):
        assert VenueAdapterStatus.RATE_LIMITED.value == "rate_limited"


# ========================================================================
# HTTP boundary tests
# ========================================================================


class TestHttpBoundary(unittest.TestCase):
    def test_http_result_success(self):
        from kairoskopion.adapters.http_client import HttpResult
        r = HttpResult(ok=True, body={"key": "val"}, url="https://test.com")
        assert r.ok
        assert r.body["key"] == "val"

    def test_http_result_error(self):
        from kairoskopion.adapters.http_client import HttpResult
        r = HttpResult(ok=False, error="timeout", url="https://test.com")
        assert not r.ok
        assert r.error == "timeout"

    def test_http_result_from_cache(self):
        from kairoskopion.adapters.http_client import HttpResult
        r = HttpResult(ok=True, body={"cached": True}, from_cache=True, url="x")
        assert r.from_cache

    def test_cache_round_trip(self):
        from kairoskopion.adapters.http_client import read_cache, write_cache
        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td)
            url = "https://test.example.com/api/v1"
            body = {"title": "Test Journal", "issn": "1234-5678"}
            write_cache(url, body, cache_dir=cache_dir)
            cached = read_cache(url, cache_dir=cache_dir)
            assert cached is not None
            assert cached["title"] == "Test Journal"

    def test_cache_miss(self):
        from kairoskopion.adapters.http_client import read_cache
        with tempfile.TemporaryDirectory() as td:
            cached = read_cache("https://no-such.url", cache_dir=Path(td))
            assert cached is None

    def test_fetch_json_safe_with_fixture(self):
        from kairoskopion.adapters.http_client import fetch_json_safe, write_cache
        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td)
            url = "https://mock-api.example.com/journal"
            write_cache(url, {"mock": True}, cache_dir=cache_dir)
            result = fetch_json_safe(url, cache_dir=cache_dir)
            assert result.ok
            assert result.body["mock"] is True
            assert result.from_cache


# ========================================================================
# OpenAlex adapter tests
# ========================================================================


class TestOpenAlexAdapter(unittest.TestCase):
    def test_fixture_lookup_by_name(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(name="Philosophy & Technology")
        assert result.status == "success"
        assert result.source_access_mode == SourceAccessMode.METADATA_API.value
        assert result.authority_assessment is not None
        names = [c.claim_path for c in result.claims]
        assert "canonical_name" in names
        assert "issn" in names

    def test_fixture_lookup_by_issn(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        assert result.status == "success"
        assert len(result.claims) > 0

    def test_authority_prohibits_formal_policy(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(name="test")
        assert result.authority_assessment is not None
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "formal_requirements" in prohibited
        assert "submission_policy" in prohibited
        assert "corpus_pattern" in prohibited

    def test_failure_state_for_no_match(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        adapter = OpenAlexVenueAdapter()
        result = adapter.parse_response({})
        assert result.status == "no_results"

    def test_cached_mode_no_cache_degrades(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        with tempfile.TemporaryDirectory() as td:
            adapter = OpenAlexVenueAdapter(VenueAdapterMode.CACHED, cache_dir=os.path.join(td, "empty"))
            result = adapter.lookup_venue(name="test")
            assert not result.is_available
            assert result.status == "unavailable"

    def test_provenance_set(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(name="test")
        assert result.provenance == "openalex_venue"


# ========================================================================
# Crossref adapter tests
# ========================================================================


class TestCrossrefAdapter(unittest.TestCase):
    def test_fixture_venue_metadata_parse(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter
        adapter = CrossrefVenueAdapter()
        result = adapter.lookup_venue(name="test", issn="2210-5433")
        assert result.status == "success"
        assert result.source_access_mode == SourceAccessMode.METADATA_API.value
        names = [c.claim_path for c in result.claims]
        assert "canonical_name" in names
        assert "publisher_or_owner" in names

    def test_fixture_work_metadata_parse(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter
        adapter = CrossrefVenueAdapter()
        result = adapter.parse_response({
            "title": "Test Journal",
            "ISSN": ["9999-0001"],
            "publisher": "Test Publisher",
            "counts": {"total-dois": 500},
        })
        assert result.status == "success"
        names = [c.claim_path for c in result.claims]
        assert "doi_count" in names

    def test_authority_prohibitions(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter
        adapter = CrossrefVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "formal_requirements" in prohibited
        assert "corpus_pattern" in prohibited

    def test_no_match_failure_state(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter
        adapter = CrossrefVenueAdapter()
        result = adapter.parse_response({})
        assert result.status == "no_results"


# ========================================================================
# DOAJ adapter tests
# ========================================================================


class TestDOAJAdapter(unittest.TestCase):
    def test_fixture_parse(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        adapter = DOAJVenueAdapter()
        result = adapter.lookup_venue(name="test")
        assert result.status == "success"
        assert result.source_access_mode == SourceAccessMode.INDEX_REGISTRY.value
        names = [c.claim_path for c in result.claims]
        assert "doaj_inclusion" in names

    def test_doaj_inclusion_claim_has_limited_authority(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        adapter = DOAJVenueAdapter()
        result = adapter.lookup_venue(name="test")
        # DOAJ as index_registry supports indexing_status but NOT formal_requirements
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "formal_requirements" in prohibited
        assert "submission_policy" in prohibited
        # But it DOES support indexing_status
        supported = result.authority_assessment.get("authority_scopes", [])
        assert "indexing_status" in supported

    def test_no_fake_scopus_wos_inference(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        adapter = DOAJVenueAdapter()
        result = adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        assert "scopus_inclusion" not in claim_paths
        assert "wos_inclusion" not in claim_paths

    def test_missing_fields_become_unknowns(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        adapter = DOAJVenueAdapter()
        result = adapter.parse_response({"bibjson": {}, "admin": {"in_doaj": False}})
        assert "journal title not found in DOAJ" in result.unknowns
        assert "journal not currently in DOAJ" in result.unknowns


# ========================================================================
# Unpaywall adapter tests
# ========================================================================


class TestUnpaywallAdapter(unittest.TestCase):
    def test_fixture_parse(self):
        from kairoskopion.adapters.venue.unpaywall import UnpaywallAdapter
        adapter = UnpaywallAdapter()
        result = adapter.lookup_by_doi("10.1007/s13347-023-00001-x")
        assert result.status == "success"
        names = [c.claim_path for c in result.claims]
        assert "is_oa" in names
        assert "oa_status" in names

    def test_full_text_access_is_not_metadata_authority(self):
        from kairoskopion.adapters.venue.unpaywall import UnpaywallAdapter
        adapter = UnpaywallAdapter()
        result = adapter.lookup_by_doi("10.1007/test")
        # Unpaywall uses metadata_api access mode
        assert result.source_access_mode == SourceAccessMode.METADATA_API.value
        # Metadata API prohibits corpus_pattern and formal_requirements
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "corpus_pattern" in prohibited

    def test_oa_article_access_does_not_become_journal_policy(self):
        from kairoskopion.adapters.venue.unpaywall import UnpaywallAdapter
        adapter = UnpaywallAdapter()
        result = adapter.lookup_by_doi("10.1007/test")
        # Article OA status doesn't imply venue formal_requirements or submission_policy
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "formal_requirements" in prohibited
        assert "submission_policy" in prohibited

    def test_venue_lookup_degrades(self):
        from kairoskopion.adapters.venue.unpaywall import UnpaywallAdapter
        adapter = UnpaywallAdapter()
        result = adapter.lookup_venue(name="test")
        assert not result.is_available


# ========================================================================
# OpenCitations adapter tests
# ========================================================================


class TestOpenCitationsAdapter(unittest.TestCase):
    def test_fixture_parse(self):
        from kairoskopion.adapters.venue.opencitations import OpenCitationsVenueAdapter
        adapter = OpenCitationsVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        assert result.status == "success"
        assert result.source_access_mode == SourceAccessMode.CITATION_GRAPH.value
        names = [c.claim_path for c in result.claims]
        assert "median_citations_per_article" in names

    def test_citation_graph_cannot_authorize_retraction(self):
        from kairoskopion.adapters.venue.opencitations import OpenCitationsVenueAdapter
        adapter = OpenCitationsVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        assert "formal_requirements" in prohibited
        assert "submission_policy" in prohibited
        assert "venue_identity" in prohibited

    def test_failure_state_for_missing_data(self):
        from kairoskopion.adapters.venue.opencitations import OpenCitationsVenueAdapter
        adapter = OpenCitationsVenueAdapter()
        result = adapter.parse_response({})
        assert result.status == "no_results"


# ========================================================================
# Snapshot adapter tests
# ========================================================================


class TestSnapshotAdapter(unittest.TestCase):
    def test_fixture_html_stores(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        crawler = VenueSnapshotCrawler()
        result = crawler.lookup_venue(url="https://example.com/guidelines")
        assert result.status == "success"
        names = [c.claim_path for c in result.claims]
        assert "snapshot_stored" in names
        assert "content_hash" in names

    def test_official_page_has_official_authority(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        crawler = VenueSnapshotCrawler(is_official=True)
        result = crawler.lookup_venue(url="https://journal.example.com")
        assert result.source_access_mode == SourceAccessMode.OFFICIAL_WEBPAGE.value
        supported = result.authority_assessment.get("authority_scopes", [])
        assert "formal_requirements" in supported
        assert "submission_policy" in supported

    def test_non_official_page_has_weaker_authority(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        crawler = VenueSnapshotCrawler(is_official=False)
        result = crawler.lookup_venue(url="https://random.example.com")
        assert result.source_access_mode == SourceAccessMode.MANUAL_NOTE.value

    def test_official_page_not_independent_verification(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        crawler = VenueSnapshotCrawler(is_official=True)
        result = crawler.lookup_venue(url="https://journal.example.com")
        prohibited = result.authority_assessment.get("prohibited_scopes", [])
        # Official webpage cannot independently verify indexing
        assert "indexing_status" in prohibited

    def test_no_broad_crawl(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        crawler = VenueSnapshotCrawler(VenueAdapterMode.LIVE_API)
        result = crawler.lookup_venue(name="test")
        assert not result.is_available
        assert "URL required" in result.error

    def test_vault_storage(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        with tempfile.TemporaryDirectory() as td:
            vault = LocalFsVault(root=td)
            crawler = VenueSnapshotCrawler(vault=vault)
            result = crawler.store_html("<html>test</html>", "https://example.com/test")
            assert result.vault_ref is not None
            assert vault.exists(result.vault_ref)


# ========================================================================
# Real source acquisition aggregation tests
# ========================================================================


class TestRealSourceAcquisition(unittest.TestCase):
    def test_all_fixture_adapters_run(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        result = acquire_venue_sources(venue_name="Test Journal", venue_issn="2210-5433")
        assert result.successful_adapters >= 4
        assert len(result.adapter_results) >= 4
        assert len(result.authority_assessments) >= 4

    def test_conflicting_claims_create_evidence_conflict(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        # OpenAlex says "Springer Nature", Crossref says "Springer Science and Business Media LLC"
        result = acquire_venue_sources(venue_name="Test", venue_issn="2210-5433")
        publisher_conflicts = [
            c for c in result.evidence_conflicts
            if c.get("field_name") == "publisher_or_owner"
        ]
        assert len(publisher_conflicts) > 0

    def test_doaj_inclusion_does_not_imply_scopus(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        result = acquire_venue_sources(venue_name="Test")
        all_claim_paths = [c.get("claim_path") for c in result.all_claims]
        assert "scopus_inclusion" not in all_claim_paths
        assert "wos_inclusion" not in all_claim_paths

    def test_missing_adapter_result_preserved(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        cfg = SourceAcquisitionConfig(
            adapters={"openalex_venue": VenueAdapterConfig(enabled=False)},
        )
        result = acquire_venue_sources(
            venue_name="Test", config=cfg,
            enabled_adapters=["openalex_venue", "crossref_venue"],
        )
        assert "openalex_venue: disabled" in result.degradation_notes

    def test_adapter_results_have_authority(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        result = acquire_venue_sources(venue_name="Test", venue_issn="2210-5433")
        for ar in result.adapter_results:
            if ar.get("status") in ("success", "partial"):
                assert ar.get("source_access_mode"), f"{ar['adapter_id']} missing source_access_mode"
                assert ar.get("authority_assessment") is not None, f"{ar['adapter_id']} missing authority"

    def test_fixture_override(self):
        from kairoskopion.services.real_source_acquisition import acquire_venue_sources
        custom_fixture = {
            "display_name": "Custom Test Journal",
            "issn_l": "0000-0001",
        }
        result = acquire_venue_sources(
            venue_name="Custom",
            adapter_fixtures={"openalex_venue": custom_fixture},
            enabled_adapters=["openalex_venue"],
        )
        has_custom = any(
            c.get("claim_value") == "Custom Test Journal"
            for c in result.all_claims
        )
        assert has_custom


# ========================================================================
# VenueEvidenceStack integration tests
# ========================================================================


class TestVenueEvidenceStackIntegration(unittest.TestCase):
    def test_quick_look_with_fixture_metadata(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(venue_name="Test", venue_issn="2210-5433")
        assert len(result.authority_assessments) >= 1
        assert result.depth_coverage.level_coverage["L0_IDENTITY"].source_count >= 2

    def test_fit_assessment_with_official_webpage(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(
            venue_name="Test",
            venue_issn="2210-5433",
            purpose="fit_assessment",
        )
        l1 = result.depth_coverage.level_coverage.get("L1_OFFICIAL_FORMAL")
        assert l1 is not None
        assert l1.source_count >= 1

    def test_conflict_visible_in_stack(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(venue_name="Test", venue_issn="2210-5433")
        # OpenAlex/Crossref publisher mismatch should produce conflict
        assert len(result.evidence_conflicts) > 0

    def test_unavailable_source_does_not_crash(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(
            venue_name="Test",
            purpose="venue_deep_profile",
        )
        assert result.depth_coverage is not None
        assert len(result.depth_coverage.unavailable_sources) > 0

    def test_use_source_adapters_adds_doaj(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(
            venue_name="Test",
            venue_issn="2210-5433",
            purpose="venue_deep_profile",
            use_source_adapters=True,
        )
        l5 = result.depth_coverage.level_coverage.get("L5_POLICY_AND_INDEXING")
        assert l5 is not None
        assert l5.source_count >= 2  # OpenCitations + DOAJ

    def test_authority_assessments_passed_through(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(venue_name="Test", venue_issn="2210-5433")
        assert len(result.authority_assessments) >= 2
        # Verify they serialize in to_dict
        d = result.to_dict()
        assert "authority_assessments" in d
        assert len(d["authority_assessments"]) >= 2

    def test_existing_tests_still_pass_without_source_adapters(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack
        result = build_venue_evidence_stack(venue_name="Test")
        assert result.depth_coverage is not None
        assert result.evidence_pack is not None


# ========================================================================
# EvidenceAuditor authority/conflict integration tests
# ========================================================================


class TestEvidenceAuditorAuthorityIntegration(unittest.TestCase):
    def _make_minimal_entities(self):
        from kairoskopion.schema import (
            ArticleModel,
            ComplianceChecklist,
            FitAssessment,
            MismatchMap,
            RiskReport,
            VenueModel,
        )
        return dict(
            article=ArticleModel(source_refs=["src1"]),
            venue=VenueModel(source_refs=["src2"]),
            fit=FitAssessment(
                overall_label="strong_candidate",
                axes=[{"axis": "scope", "value": "strong", "evidence_refs": ["e1"]}],
            ),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[{"risk": "test"}]),
            compliance=ComplianceChecklist(checklist_items=[{"item": "test"}]),
        )

    def test_auditor_accepts_authority_assessments(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        from kairoskopion.source_authority import SourceAuthorityAssessment

        entities = self._make_minimal_entities()
        assessment = SourceAuthorityAssessment(
            source_ref="openalex_venue",
            access_modes=["metadata_api"],
        )
        result = audit_pipeline_evidence(
            **entities,
            authority_assessments=[assessment],
        )
        assert result.status in ("passed", "passed_with_warnings")

    def test_auditor_accepts_evidence_conflicts(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        from kairoskopion.source_authority import EvidenceConflict

        entities = self._make_minimal_entities()
        conflict = EvidenceConflict(
            entity_id="venue_001",
            field_name="publisher_or_owner",
            severity="warning",
        )
        result = audit_pipeline_evidence(
            **entities,
            evidence_conflicts=[conflict],
        )
        assert result.status in ("passed", "passed_with_warnings")


# ========================================================================
# CLI tests
# ========================================================================


class TestCLICommands(unittest.TestCase):
    def test_list_source_adapters(self):
        from kairoskopion.cli import main
        rc = main(["list-source-adapters"])
        assert rc == 0

    def test_inspect_adapter_valid(self):
        from kairoskopion.cli import main
        rc = main(["inspect-adapter", "openalex_venue"])
        assert rc == 0

    def test_inspect_adapter_invalid(self):
        from kairoskopion.cli import main
        rc = main(["inspect-adapter", "nonexistent_adapter"])
        assert rc == 1

    def test_acquire_venue_sources_fixture(self):
        from kairoskopion.cli import main
        rc = main(["acquire-venue-sources", "--venue-name", "Test Journal"])
        assert rc == 0

    def test_acquire_venue_sources_with_output(self):
        from kairoskopion.cli import main
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "result.json")
            rc = main(["acquire-venue-sources", "--venue-name", "Test", "--output", out])
            assert rc == 0
            assert os.path.exists(out)
            data = json.loads(Path(out).read_text(encoding="utf-8"))
            assert "adapter_results" in data

    def test_build_venue_evidence_stack_with_source_adapters(self):
        from kairoskopion.cli import main
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "stack.json")
            rc = main([
                "build-venue-evidence-stack",
                "--venue-name", "Test",
                "--purpose", "quick_look",
                "--use-source-adapters",
                "--output", out,
            ])
            assert rc == 0


# ========================================================================
# List/inspect adapters service tests
# ========================================================================


class TestAdapterListInspect(unittest.TestCase):
    def test_list_adapters(self):
        from kairoskopion.services.real_source_acquisition import list_available_adapters
        adapters = list_available_adapters()
        assert len(adapters) == 6
        ids = [a["adapter_id"] for a in adapters]
        assert "openalex_venue" in ids
        assert "doaj_venue" in ids
        assert "unpaywall" in ids

    def test_inspect_known_adapter(self):
        from kairoskopion.services.real_source_acquisition import inspect_adapter
        info = inspect_adapter("doaj_venue")
        assert info is not None
        assert info["source_access_mode"] == "index_registry"

    def test_inspect_unknown_adapter(self):
        from kairoskopion.services.real_source_acquisition import inspect_adapter
        assert inspect_adapter("nonexistent") is None


if __name__ == "__main__":
    unittest.main()
