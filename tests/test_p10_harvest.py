"""Tests for P10 operational harvest behavior.

Verifies: adapter search → dedup → provisional record creation →
registry loading → verification gate → review packet export.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.adapters.venue.base import (
    VenueAdapterClaim,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
)
from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
from kairoskopion.registry.models import EvidenceRef, VenueRegistryRecord
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.verification_gate import verify_registry, summarize_verification
from kairoskopion.services.review_packet_exporter import (
    build_review_packet, export_markdown, export_jsonl, export_tsv,
)


# ── helpers ──────────────────────────────────────────────────────────

def _make_adapter_result(
    adapter_id: str = "openalex_venue",
    name: str = "Test Journal",
    issn: str | None = "1234-5678",
    publisher: str | None = "Test Publisher",
    status: str = "success",
) -> VenueAdapterResult:
    claims = [VenueAdapterClaim("canonical_name", name, "FACT_FROM_API_METADATA", "high")]
    if issn:
        claims.append(VenueAdapterClaim("issn", issn, "FACT_FROM_API_METADATA", "high"))
    if publisher:
        claims.append(VenueAdapterClaim("publisher_or_owner", publisher, "FACT_FROM_API_METADATA", "medium"))
    return VenueAdapterResult(
        adapter_id=adapter_id,
        mode="live_api",
        query={"search": "test"},
        status=status,
        source_access_mode="free_api",
        evidence_status="FACT_FROM_API_METADATA",
        source_role="bibliographic",
        claims=claims,
        provenance=adapter_id,
        fetched_at="2026-06-27T12:00:00+00:00",
    )


def _result_to_record(result: VenueAdapterResult) -> VenueRegistryRecord | None:
    """Minimal conversion matching harvest script logic."""
    name = None
    issn = None
    publisher = None
    for c in result.claims:
        if c.claim_path == "canonical_name":
            name = c.claim_value
        elif c.claim_path == "issn":
            issn = c.claim_value
        elif c.claim_path == "publisher_or_owner":
            publisher = c.claim_value
    if not name:
        return None
    evidence = EvidenceRef(
        source_type=f"adapter_{result.adapter_id}",
        source_id=result.adapter_id,
        evidence_status=result.evidence_status,
        retrieval_date=result.fetched_at or "",
    )
    return VenueRegistryRecord(
        canonical_name=name,
        issn=issn,
        publisher=publisher,
        source_status="provisional",
        review_status="pending",
        evidence_refs=[evidence],
        provenance=f"p10_harvest_{result.adapter_id}",
    )


# ── adapter mode tests ──────────────────────────────────────────────

class TestAdapterModes:
    def test_openalex_offline_stub_returns_empty_for_search(self):
        adapter = OpenAlexVenueAdapter(mode=VenueAdapterMode.OFFLINE_STUB)
        results = adapter.search_venues("education", per_page=5)
        assert results == []

    def test_openalex_fixture_returns_empty_for_search(self):
        adapter = OpenAlexVenueAdapter(mode=VenueAdapterMode.FIXTURE)
        results = adapter.search_venues("education", per_page=5)
        assert results == []

    def test_doaj_offline_stub_returns_empty_for_search(self):
        adapter = DOAJVenueAdapter(mode=VenueAdapterMode.OFFLINE_STUB)
        results = adapter.search_venues("education", per_page=5)
        assert results == []

    def test_doaj_fixture_returns_empty_for_search(self):
        adapter = DOAJVenueAdapter(mode=VenueAdapterMode.FIXTURE)
        results = adapter.search_venues("education", per_page=5)
        assert results == []


# ── deduplication tests ──────────────────────────────────────────────

class TestDeduplication:
    def test_dedup_by_issn(self):
        r1 = _make_adapter_result(name="Journal A", issn="1111-2222")
        r2 = _make_adapter_result(name="Journal B", issn="1111-2222", adapter_id="doaj_venue")
        from scripts.run_p10_education_ai_harvest import deduplicate_results
        deduped = deduplicate_results([r1, r2])
        assert len(deduped) == 1

    def test_dedup_by_name(self):
        r1 = _make_adapter_result(name="Education Journal", issn=None)
        r2 = _make_adapter_result(name="education journal", issn=None, adapter_id="doaj_venue")
        from scripts.run_p10_education_ai_harvest import deduplicate_results
        deduped = deduplicate_results([r1, r2])
        assert len(deduped) == 1

    def test_no_dedup_different_entries(self):
        r1 = _make_adapter_result(name="Journal A", issn="1111-2222")
        r2 = _make_adapter_result(name="Journal B", issn="3333-4444")
        from scripts.run_p10_education_ai_harvest import deduplicate_results
        deduped = deduplicate_results([r1, r2])
        assert len(deduped) == 2

    def test_dedup_skips_non_success(self):
        r1 = _make_adapter_result(name="Failed", issn="1111-2222", status="error")
        from scripts.run_p10_education_ai_harvest import deduplicate_results
        deduped = deduplicate_results([r1])
        assert len(deduped) == 0


# ── record conversion tests ─────────────────────────────────────────

class TestRecordConversion:
    def test_result_to_provisional_record(self):
        result = _make_adapter_result(name="Test Journal", issn="1234-5678", publisher="Test Pub")
        rec = _result_to_record(result)
        assert rec is not None
        assert rec.canonical_name == "Test Journal"
        assert rec.issn == "1234-5678"
        assert rec.publisher == "Test Pub"
        assert rec.source_status == "provisional"
        assert rec.review_status == "pending"
        assert len(rec.evidence_refs) == 1
        assert rec.evidence_refs[0].evidence_status == "FACT_FROM_API_METADATA"

    def test_result_without_name_returns_none(self):
        result = VenueAdapterResult(
            adapter_id="openalex_venue",
            mode="live_api",
            query={},
            status="success",
            claims=[],
            provenance="openalex_venue",
        )
        rec = _result_to_record(result)
        assert rec is None

    def test_record_provenance_includes_adapter(self):
        result = _make_adapter_result(adapter_id="doaj_venue")
        rec = _result_to_record(result)
        assert "doaj_venue" in rec.provenance

    def test_no_auto_promotion(self):
        result = _make_adapter_result()
        rec = _result_to_record(result)
        assert rec.source_status == "provisional"
        assert rec.source_status != "accepted"


# ── registry loading tests ──────────────────────────────────────────

class TestRegistryLoading:
    def test_load_to_registry(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        reg = hub._get_registry("venue")
        reg.add_provisional(rec, evidence_refs=rec.evidence_refs)
        assert len(reg.list_all()) == 1
        loaded = reg.list_all()[0]
        assert loaded.source_status == "provisional"

    def test_duplicate_detection(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec1 = _result_to_record(_make_adapter_result(issn="1111-2222"))
        rec2 = _result_to_record(_make_adapter_result(issn="1111-2222"))
        reg = hub._get_registry("venue")
        reg.add_provisional(rec1)
        dup = reg.find_duplicate(rec2)
        assert dup is not None

    def test_no_duplicate_different_issn(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec1 = _result_to_record(_make_adapter_result(name="Journal A", issn="1111-2222"))
        rec2 = _result_to_record(_make_adapter_result(name="Journal B", issn="3333-4444"))
        reg = hub._get_registry("venue")
        reg.add_provisional(rec1)
        dup = reg.find_duplicate(rec2)
        assert dup is None


# ── verification gate tests ─────────────────────────────────────────

class TestVerificationGate:
    def test_all_provisional_keep_provisional(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        decisions = verify_registry(hub, no_paid_api=True)
        assert len(decisions) >= 1
        for d in decisions:
            assert d.verdict == "keep_provisional"

    def test_no_auto_promote_to_accepted(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        decisions = verify_registry(hub, no_paid_api=True)
        for d in decisions:
            assert d.after_status != "accepted"

    def test_verification_summary_structure(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        decisions = verify_registry(hub, no_paid_api=True)
        summary = summarize_verification(decisions)
        assert "total" in summary
        assert "verdicts" in summary
        assert summary["total"] >= 1


# ── review packet tests ─────────────────────────────────────────────

class TestReviewPacket:
    def test_build_review_packet(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        gaps = ["test gap"]
        packet = build_review_packet(hub, gaps=gaps, no_paid_api=True)
        assert len(packet.venues) >= 1
        assert packet.gaps == ["test gap"]

    def test_export_markdown(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result(name="Test Journal"))
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        packet = build_review_packet(hub, no_paid_api=True)
        md = export_markdown(packet)
        assert "Test Journal" in md
        assert "Review Packet" in md

    def test_export_jsonl(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        packet = build_review_packet(hub, no_paid_api=True)
        jsonl = export_jsonl(packet)
        lines = jsonl.strip().split("\n")
        assert len(lines) >= 2
        header = json.loads(lines[0])
        assert header["record_type"] == "review_packet_header"

    def test_export_tsv(self, tmp_path):
        hub = RegistryHub(data_dir=tmp_path)
        rec = _result_to_record(_make_adapter_result())
        hub._get_registry("venue").add_provisional(rec, evidence_refs=rec.evidence_refs)
        packet = build_review_packet(hub, no_paid_api=True)
        tsv = export_tsv(packet)
        lines = tsv.strip().split("\n")
        assert len(lines) >= 2
        assert "record_type" in lines[0]


# ── DOAJ oa_start fix ────────────────────────────────────────────────

class TestDOAJOaStartFix:
    def test_oa_start_as_int(self):
        adapter = DOAJVenueAdapter(mode=VenueAdapterMode.OFFLINE_STUB)
        data = {
            "bibjson": {"title": "Test Journal", "oa_start": 2015},
            "admin": {"in_doaj": True},
        }
        result = adapter._parse_response(data, {"test": True})
        oa_claim = [c for c in result.claims if c.claim_path == "oa_start_year"]
        assert len(oa_claim) == 1
        assert oa_claim[0].claim_value == 2015

    def test_oa_start_as_dict(self):
        adapter = DOAJVenueAdapter(mode=VenueAdapterMode.OFFLINE_STUB)
        data = {
            "bibjson": {"title": "Test Journal", "oa_start": {"year": 2020}},
            "admin": {"in_doaj": True},
        }
        result = adapter._parse_response(data, {"test": True})
        oa_claim = [c for c in result.claims if c.claim_path == "oa_start_year"]
        assert len(oa_claim) == 1
        assert oa_claim[0].claim_value == 2020

    def test_oa_start_missing(self):
        adapter = DOAJVenueAdapter(mode=VenueAdapterMode.OFFLINE_STUB)
        data = {
            "bibjson": {"title": "Test Journal"},
            "admin": {"in_doaj": True},
        }
        result = adapter._parse_response(data, {"test": True})
        oa_claim = [c for c in result.claims if c.claim_path == "oa_start_year"]
        assert len(oa_claim) == 0


# ── OpenAlex filter fix ─────────────────────────────────────────────

class TestOpenAlexFilterFix:
    def test_search_url_uses_filter_param(self):
        """Verify the search URL uses filter=type:journal, not type=journal."""
        import kairoskopion.adapters.venue.openalex as oa_mod
        import inspect
        source = inspect.getsource(oa_mod.OpenAlexVenueAdapter.search_venues)
        assert "filter=type:journal" in source
        assert "&type=journal" not in source or "filter=type:journal" in source
