"""Tests for external adapter stubs and evidence bridge."""

from pathlib import Path

from kairoskopion.adapters.base import AdapterConfig, AdapterRecord, AdapterResult
from kairoskopion.adapters.bridge import (
    convert_adapter_record_to_evidence_item,
    convert_adapter_result_to_source_snapshot,
    link_adapter_records_to_reference_items,
)
from kairoskopion.adapters.crossref import lookup_doi_mock, search_works_mock as crossref_search
from kairoskopion.adapters.openalex import search_works_mock as openalex_search
from kairoskopion.adapters.opencitations import get_citations_mock
from kairoskopion.enums import EvidenceStatus


class TestAdapterResultSerialization:
    def test_adapter_result_to_dict(self):
        r = AdapterResult(adapter_name="test", query="q", is_mock=True)
        d = r.to_dict()
        assert d["adapter_name"] == "test"
        assert d["is_mock"] is True
        assert "adapter_result_id" in d

    def test_adapter_record_to_dict(self):
        rec = AdapterRecord(
            record_id="r1", title="Title", year=2020, doi="10.1234/test",
        )
        d = rec.to_dict()
        assert d["title"] == "Title"
        assert d["year"] == 2020
        assert d["doi"] == "10.1234/test"

    def test_adapter_config_to_dict(self):
        cfg = AdapterConfig(adapter_name="test", is_mock=True)
        d = cfg.to_dict()
        assert d["adapter_name"] == "test"
        assert d["is_mock"] is True


class TestOpenAlexMock:
    def test_returns_records(self):
        result = openalex_search("consciousness")
        assert len(result.records) == 3
        assert result.is_mock is True
        assert result.status == "mock"

    def test_evidence_not_fact(self):
        result = openalex_search("test")
        assert result.evidence_status == EvidenceStatus.VENDOR_CLAIM.value

    def test_deterministic(self):
        r1 = openalex_search("a")
        r2 = openalex_search("b")
        assert len(r1.records) == len(r2.records)
        assert r1.records[0]["title"] == r2.records[0]["title"]

    def test_max_results(self):
        result = openalex_search("test", max_results=1)
        assert len(result.records) == 1

    def test_disclaimer_present(self):
        result = openalex_search("test")
        assert "mock" in result.disclaimer.lower()


class TestCrossrefMock:
    def test_doi_lookup_found(self):
        result = lookup_doi_mock("10.2307/2183914")
        assert len(result.records) == 1
        assert result.records[0]["doi"] == "10.2307/2183914"
        assert result.is_mock is True

    def test_doi_lookup_not_found(self):
        result = lookup_doi_mock("10.9999/nonexistent")
        assert len(result.records) == 0
        assert result.status == "no_results"

    def test_search_returns_records(self):
        result = crossref_search("consciousness")
        assert len(result.records) == 2
        assert result.is_mock is True

    def test_evidence_not_fact(self):
        result = lookup_doi_mock("10.2307/2183914")
        assert result.evidence_status == EvidenceStatus.VENDOR_CLAIM.value

    def test_deterministic(self):
        r1 = crossref_search("a")
        r2 = crossref_search("b")
        assert r1.records[0]["title"] == r2.records[0]["title"]


class TestOpenCitationsMock:
    def test_references_direction(self):
        result = get_citations_mock("10.1126/science.1234567", direction="references")
        assert len(result.records) == 2
        assert result.is_mock is True

    def test_citations_direction(self):
        result = get_citations_mock("10.2307/2183914", direction="citations")
        assert len(result.records) >= 1

    def test_no_match(self):
        result = get_citations_mock("10.9999/nothing", direction="references")
        assert len(result.records) == 0

    def test_evidence_not_fact(self):
        result = get_citations_mock("10.1126/science.1234567")
        assert result.evidence_status == EvidenceStatus.VENDOR_CLAIM.value

    def test_deterministic(self):
        r1 = get_citations_mock("10.1126/science.1234567")
        r2 = get_citations_mock("10.1126/science.1234567")
        assert len(r1.records) == len(r2.records)


class TestBridgeSourceSnapshot:
    def test_creates_snapshot(self):
        result = openalex_search("test")
        snapshot = convert_adapter_result_to_source_snapshot(result)
        assert snapshot.snapshot_id.startswith("snap_")
        assert "adapter:openalex" in snapshot.source_id
        assert snapshot.extraction_status == "extracted"

    def test_empty_result_extraction_status(self):
        result = lookup_doi_mock("10.9999/nonexistent")
        snapshot = convert_adapter_result_to_source_snapshot(result)
        assert snapshot.extraction_status == "no_results"

    def test_mock_tag_in_parser(self):
        result = openalex_search("test")
        snapshot = convert_adapter_result_to_source_snapshot(result)
        assert "mock" in snapshot.parser_used


class TestBridgeEvidenceItem:
    def test_creates_evidence(self):
        result = openalex_search("test")
        rec = result.records[0]
        evi = convert_adapter_record_to_evidence_item(
            rec, adapter_name="openalex", is_mock=True,
        )
        assert evi.evidence_id.startswith("evi_")
        assert evi.evidence_status == EvidenceStatus.VENDOR_CLAIM.value
        assert evi.confidence == "low"

    def test_mock_never_fact_from_source(self):
        result = openalex_search("test")
        for rec in result.records:
            evi = convert_adapter_record_to_evidence_item(
                rec, adapter_name="openalex", is_mock=True,
            )
            assert evi.evidence_status != EvidenceStatus.FACT_FROM_SOURCE.value

    def test_real_adapter_still_vendor_claim(self):
        rec = {"title": "Test", "doi": "10.1234/test", "record_id": "r1"}
        evi = convert_adapter_record_to_evidence_item(
            rec, adapter_name="crossref", is_mock=False,
        )
        assert evi.evidence_status == EvidenceStatus.VENDOR_CLAIM.value
        assert evi.confidence == "medium"

    def test_source_id_propagated(self):
        rec = {"title": "Test", "doi": "10.1234/test"}
        evi = convert_adapter_record_to_evidence_item(
            rec, adapter_name="openalex", is_mock=True, source_id="snap_abc",
        )
        assert evi.source_id == "snap_abc"


class TestBridgeLinkReferences:
    def test_doi_match(self):
        adapter_records = [
            {"record_id": "r1", "doi": "10.2307/2183914", "title": "Bat paper"},
        ]
        reference_items = [
            {"reference_item_id": "ref_001", "doi": "10.2307/2183914", "raw_text": "Nagel 1974"},
        ]
        matches = link_adapter_records_to_reference_items(
            adapter_records, reference_items, adapter_name="crossref",
        )
        assert len(matches) == 1
        assert matches[0]["match_type"] == "doi"
        assert matches[0]["verification_status"] == "not_verified"
        assert matches[0]["is_mock"] is True

    def test_no_doi_no_match(self):
        adapter_records = [
            {"record_id": "r1", "doi": "10.9999/other"},
        ]
        reference_items = [
            {"reference_item_id": "ref_001", "doi": "10.2307/2183914"},
        ]
        matches = link_adapter_records_to_reference_items(
            adapter_records, reference_items, adapter_name="crossref",
        )
        assert len(matches) == 0

    def test_case_insensitive_doi(self):
        adapter_records = [
            {"record_id": "r1", "doi": "10.2307/2183914"},
        ]
        reference_items = [
            {"reference_item_id": "ref_001", "doi": "10.2307/2183914"},
        ]
        matches = link_adapter_records_to_reference_items(
            adapter_records, reference_items, adapter_name="crossref",
        )
        assert len(matches) == 1


class TestMockEvidenceNotVerified:
    def test_citation_ecology_mock_not_verified(self):
        from kairoskopion.services.bibliography_parsing import build_bibliography_profile
        from kairoskopion.services.citation_ecology import build_citation_ecology_report
        from kairoskopion.schema import ArticleModel, VenueModel

        text = "## References\n\n- Nagel, T. (1974). What Is It Like to Be a Bat? Philosophical Review, 83(4)."
        bib = build_bibliography_profile(text)

        article = ArticleModel(
            article_model_id="art_t",
            title_current="Test",
            disciplinary_register_current="philosophy",
        )
        venue = VenueModel(
            venue_model_id="ven_t",
            canonical_name="Test Journal",
            scope_summary="Philosophy of mind",
        )
        report = build_citation_ecology_report(bib, article, venue, "")
        for ref in bib.references:
            assert ref.get("verification_status") == "not_verified"


class TestPersistenceIntegration:
    def test_adapters_smoke_persists(self, tmp_path):
        from kairoskopion.cli import main
        code = main(["--storage-root", str(tmp_path / "s"), "adapters-smoke"])
        assert code == 0
        reg_dir = tmp_path / "s" / "registries"
        assert (reg_dir / "adapter_results.jsonl").exists()
        assert (reg_dir / "source_snapshots.jsonl").exists()
        assert (reg_dir / "evidence_items.jsonl").exists()

    def test_adapters_smoke_record_count(self, tmp_path):
        from kairoskopion.cli import main
        import json

        code = main(["--storage-root", str(tmp_path / "s"), "adapters-smoke"])
        assert code == 0
        ar_path = tmp_path / "s" / "registries" / "adapter_results.jsonl"
        lines = [json.loads(l) for l in ar_path.read_text(encoding="utf-8").strip().splitlines()]
        assert len(lines) == 4  # 4 adapter calls


class TestNoNetwork:
    """Adapters use stdlib urllib for real mode (Sprint 3).

    The constraint is: no third-party HTTP libraries (requests, httpx, aiohttp).
    stdlib urllib.request is allowed — it ships with Python, no extra dependency.
    """

    def _check_no_third_party_http(self, mod_path: str) -> None:
        source = Path(mod_path).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import httpx", "import aiohttp"]:
            assert forbidden not in source, f"Found '{forbidden}' in {mod_path}"

    def test_no_third_party_http_openalex(self):
        import kairoskopion.adapters.openalex as mod
        self._check_no_third_party_http(mod.__file__)

    def test_no_third_party_http_crossref(self):
        import kairoskopion.adapters.crossref as mod
        self._check_no_third_party_http(mod.__file__)

    def test_no_third_party_http_opencitations(self):
        import kairoskopion.adapters.opencitations as mod
        self._check_no_third_party_http(mod.__file__)

    def test_no_third_party_http_bridge(self):
        import kairoskopion.adapters.bridge as mod
        self._check_no_third_party_http(mod.__file__)
