"""Tests for venue registry domain model and services."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kairoskopion.enums import VenueClaimStatus, VenueSourceType
from kairoskopion.schema import (
    VenueClaim,
    VenueEvidencePack,
    VenueRecord,
    VenueSource,
)
from kairoskopion.services.venue_registry import (
    ImportResult,
    build_venue_evidence_pack,
    evidence_pack_to_markdown,
    import_venue_seed_corpus,
    persist_import_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEED_CORPUS = Path(__file__).resolve().parent.parent / "examples" / "venue_seed_corpus"


def _make_venue(**overrides: object) -> dict:
    base = {
        "venue_record_id": "vrec_test_001",
        "canonical_name": "Test Venue",
        "aliases": ["TV"],
        "issn": "0000-0001",
        "eissn": None,
        "publisher": "Test Publisher",
        "official_urls": ["https://example.com/tv"],
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_source(venue_record_id: str = "vrec_test_001", **overrides: object) -> dict:
    base = {
        "venue_source_id": "vsrc_test_001",
        "venue_record_id": venue_record_id,
        "source_url": "https://example.com/tv",
        "source_title": "Test Source",
        "source_type": "official_homepage",
        "retrieved_at": "2026-05-15T10:00:00Z",
        "freshness_window_days": 180,
        "extracted_by": "human",
        "extraction_method": "manual_note",
        "notes": None,
        "created_at": "2026-06-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_claim(
    venue_record_id: str = "vrec_test_001",
    venue_source_id: str = "vsrc_test_001",
    **overrides: object,
) -> dict:
    base = {
        "venue_claim_id": "vclm_test_001",
        "venue_record_id": venue_record_id,
        "venue_source_id": venue_source_id,
        "claim_path": "aims_scope",
        "claim_value": "Test scope",
        "evidence_status": "official_fact",
        "confidence": "high",
        "quote_or_summary": "From test source",
        "conflict_group": None,
        "created_at": "2026-06-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _write_corpus(
    tmpdir: Path,
    venues: list[dict],
    sources: list[dict],
    claims: list[dict],
) -> Path:
    for name, records in [("venues", venues), ("sources", sources), ("claims", claims)]:
        path = tmpdir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return tmpdir


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


class TestVenueRecordSerialization:
    def test_roundtrip(self):
        rec = VenueRecord(
            venue_record_id="vrec_abc",
            canonical_name="Test",
            aliases=["T"],
            issn="1234-5678",
        )
        d = rec.to_dict()
        restored = VenueRecord.from_dict(d)
        assert restored.venue_record_id == "vrec_abc"
        assert restored.canonical_name == "Test"
        assert restored.aliases == ["T"]
        assert restored.issn == "1234-5678"

    def test_from_dict_ignores_extra_fields(self):
        d = {"venue_record_id": "vrec_x", "canonical_name": "X", "extra": 42}
        rec = VenueRecord.from_dict(d)
        assert rec.venue_record_id == "vrec_x"


class TestVenueSourceSerialization:
    def test_roundtrip(self):
        src = VenueSource(
            venue_source_id="vsrc_abc",
            venue_record_id="vrec_abc",
            source_type="official_homepage",
        )
        d = src.to_dict()
        restored = VenueSource.from_dict(d)
        assert restored.venue_source_id == "vsrc_abc"
        assert restored.source_type == "official_homepage"


class TestVenueClaimSerialization:
    def test_roundtrip(self):
        claim = VenueClaim(
            venue_claim_id="vclm_abc",
            venue_record_id="vrec_abc",
            venue_source_id="vsrc_abc",
            claim_path="aims_scope",
            claim_value="Test scope",
            evidence_status="official_fact",
            confidence="high",
        )
        d = claim.to_dict()
        restored = VenueClaim.from_dict(d)
        assert restored.venue_claim_id == "vclm_abc"
        assert restored.claim_path == "aims_scope"
        assert restored.claim_value == "Test scope"

    def test_list_claim_value(self):
        claim = VenueClaim(
            venue_claim_id="vclm_list",
            claim_path="accepted_article_types",
            claim_value=["Research Article", "Review"],
            evidence_status="official_fact",
        )
        d = claim.to_dict()
        assert d["claim_value"] == ["Research Article", "Review"]
        restored = VenueClaim.from_dict(d)
        assert restored.claim_value == ["Research Article", "Review"]


class TestVenueEvidencePackSerialization:
    def test_roundtrip(self):
        pack = VenueEvidencePack(
            venue_record_id="vrec_abc",
            profile={"name": "Test"},
            official_facts=["vclm_1"],
            unknowns=["ai_policy"],
            conflicts=[{"claim_path": "apc", "claim_ids": ["vclm_2", "vclm_3"]}],
        )
        d = pack.to_dict()
        restored = VenueEvidencePack.from_dict(d)
        assert restored.venue_record_id == "vrec_abc"
        assert restored.profile["name"] == "Test"
        assert restored.unknowns == ["ai_policy"]
        assert len(restored.conflicts) == 1


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestImportVenueSeedCorpus:
    def test_import_real_seed_corpus(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        assert result.success, f"Import failed: {result.errors}"
        assert len(result.venues) == 5
        assert len(result.sources) >= 10
        assert len(result.claims) >= 20

    def test_import_missing_dir(self):
        result = import_venue_seed_corpus(Path("/nonexistent"))
        assert not result.success
        assert any("not found" in e for e in result.errors)

    def test_import_validates_venues(self, tmp_path):
        _write_corpus(
            tmp_path,
            venues=[{"canonical_name": "No ID"}],
            sources=[],
            claims=[],
        )
        result = import_venue_seed_corpus(tmp_path)
        assert not result.success
        assert any("missing venue_record_id" in e for e in result.errors)

    def test_import_validates_sources(self, tmp_path):
        _write_corpus(
            tmp_path,
            venues=[_make_venue()],
            sources=[{"venue_source_id": "vsrc_x"}],
            claims=[],
        )
        result = import_venue_seed_corpus(tmp_path)
        assert not result.success
        assert any("missing venue_record_id" in e for e in result.errors)

    def test_import_validates_claims(self, tmp_path):
        _write_corpus(
            tmp_path,
            venues=[_make_venue()],
            sources=[_make_source()],
            claims=[{"venue_claim_id": "vclm_x"}],
        )
        result = import_venue_seed_corpus(tmp_path)
        assert not result.success

    def test_import_warns_orphan_source(self, tmp_path):
        _write_corpus(
            tmp_path,
            venues=[_make_venue()],
            sources=[_make_source(venue_record_id="vrec_nonexistent")],
            claims=[],
        )
        result = import_venue_seed_corpus(tmp_path)
        assert result.success
        assert any("not found" in w for w in result.warnings)


class TestPersistImportResult:
    def test_persist_creates_registries(self, tmp_path):
        result = import_venue_seed_corpus(SEED_CORPUS)
        assert result.success
        storage = tmp_path / ".kairoskopion_test"
        written = persist_import_result(result, storage)
        assert "venue_records" in written
        assert "venue_sources" in written
        assert "venue_claims" in written
        assert (storage / "registries" / "venue_records.jsonl").exists()


# ---------------------------------------------------------------------------
# Evidence pack build tests
# ---------------------------------------------------------------------------


class TestBuildVenueEvidencePack:
    def _build_from_seed(self, venue_id: str) -> VenueEvidencePack | None:
        result = import_venue_seed_corpus(SEED_CORPUS)
        return build_venue_evidence_pack(
            venue_id, result.venues, result.sources, result.claims
        )

    def test_build_philo_venue(self):
        pack = self._build_from_seed("vrec_synth_philo")
        assert pack is not None
        assert pack.profile["name"] == "Philosophy & Social Theory Review"
        assert pack.profile.get("accepted_languages") == "English"
        assert len(pack.official_facts) > 0
        assert len(pack.unknowns) > 0

    def test_build_by_alias(self):
        pack = self._build_from_seed("PSTR")
        assert pack is not None
        assert pack.profile["name"] == "Philosophy & Social Theory Review"

    def test_build_by_name(self):
        pack = self._build_from_seed("Philosophy & Social Theory Review")
        assert pack is not None

    def test_build_nonexistent_returns_none(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_nonexistent", result.venues, result.sources, result.claims
        )
        assert pack is None

    def test_build_russian_venue_language(self):
        pack = self._build_from_seed("vrec_synth_russian")
        assert pack is not None
        lang = pack.profile.get("accepted_languages", "")
        assert "Russian" in str(lang)

    def test_build_empirical_venue(self):
        pack = self._build_from_seed("vrec_synth_empirical")
        assert pack is not None
        assert pack.profile.get("data_policy") is not None

    def test_build_incomplete_venue_has_unknowns(self):
        pack = self._build_from_seed("vrec_synth_incomplete")
        assert pack is not None
        assert len(pack.unknowns) > 5

    def test_build_formal_venue_has_conflict(self):
        pack = self._build_from_seed("vrec_synth_formal")
        assert pack is not None
        assert len(pack.conflicts) >= 1
        apc_conflict = [c for c in pack.conflicts if c["claim_path"] == "apc_oa"]
        assert len(apc_conflict) == 1

    def test_build_formal_venue_has_stale_check(self):
        far_future = datetime(2028, 1, 1, tzinfo=timezone.utc)
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_formal", result.venues, result.sources, result.claims,
            now=far_future,
        )
        assert pack is not None
        assert len(pack.stale_warnings) > 0


class TestClaimResolution:
    def test_official_fact_wins_over_external(self, tmp_path):
        venue = _make_venue()
        src_official = _make_source(
            venue_source_id="vsrc_off",
            source_type="official_homepage",
        )
        src_external = _make_source(
            venue_source_id="vsrc_ext",
            source_type="third_party_summary",
        )
        claim_official = _make_claim(
            venue_claim_id="vclm_off",
            venue_source_id="vsrc_off",
            claim_path="apc_oa",
            claim_value="No APC",
            evidence_status="official_fact",
        )
        claim_external = _make_claim(
            venue_claim_id="vclm_ext",
            venue_source_id="vsrc_ext",
            claim_path="apc_oa",
            claim_value="APC $500",
            evidence_status="external_claim",
        )

        _write_corpus(
            tmp_path,
            venues=[venue],
            sources=[src_official, src_external],
            claims=[claim_official, claim_external],
        )
        result = import_venue_seed_corpus(tmp_path)
        pack = build_venue_evidence_pack(
            "vrec_test_001", result.venues, result.sources, result.claims
        )
        assert pack is not None
        assert pack.profile["apc_oa"] == "No APC"
        assert len(pack.conflicts) == 0

    def test_conflicting_official_claims_remain_conflict(self, tmp_path):
        venue = _make_venue()
        src1 = _make_source(
            venue_source_id="vsrc_off1",
            source_type="official_homepage",
        )
        src2 = _make_source(
            venue_source_id="vsrc_off2",
            source_type="official_author_guidelines",
        )
        claim1 = _make_claim(
            venue_claim_id="vclm_off1",
            venue_source_id="vsrc_off1",
            claim_path="review_model",
            claim_value="double-blind",
            evidence_status="official_fact",
        )
        claim2 = _make_claim(
            venue_claim_id="vclm_off2",
            venue_source_id="vsrc_off2",
            claim_path="review_model",
            claim_value="single-blind",
            evidence_status="official_fact",
        )

        _write_corpus(
            tmp_path,
            venues=[venue],
            sources=[src1, src2],
            claims=[claim1, claim2],
        )
        result = import_venue_seed_corpus(tmp_path)
        pack = build_venue_evidence_pack(
            "vrec_test_001", result.venues, result.sources, result.claims
        )
        assert pack is not None
        assert len(pack.conflicts) == 1
        assert pack.conflicts[0]["claim_path"] == "review_model"

    def test_unknowns_preserved(self, tmp_path):
        venue = _make_venue()
        src = _make_source()
        claim = _make_claim(claim_path="aims_scope", claim_value="Test scope")

        _write_corpus(tmp_path, venues=[venue], sources=[src], claims=[claim])
        result = import_venue_seed_corpus(tmp_path)
        pack = build_venue_evidence_pack(
            "vrec_test_001", result.venues, result.sources, result.claims
        )
        assert pack is not None
        assert "ai_policy" in pack.unknowns
        assert "data_policy" in pack.unknowns

    def test_stale_source_flagged(self, tmp_path):
        venue = _make_venue()
        src = _make_source(
            retrieved_at="2020-01-01T00:00:00Z",
            freshness_window_days=90,
        )
        claim = _make_claim()
        _write_corpus(tmp_path, venues=[venue], sources=[src], claims=[claim])
        result = import_venue_seed_corpus(tmp_path)
        pack = build_venue_evidence_pack(
            "vrec_test_001", result.venues, result.sources, result.claims
        )
        assert pack is not None
        assert len(pack.stale_warnings) > 0


# ---------------------------------------------------------------------------
# Markdown rendering tests
# ---------------------------------------------------------------------------


class TestEvidencePackToMarkdown:
    def test_markdown_has_venue_name(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_philo", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "# Philosophy & Social Theory Review" in md

    def test_markdown_has_language_policy(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_philo", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "## Language Policy" in md
        assert "English" in md

    def test_markdown_has_provenance_section(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_philo", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "## Evidence Provenance" in md
        assert "Official facts:" in md

    def test_markdown_has_unknown_fields(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_incomplete", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "## UNKNOWN Fields" in md

    def test_markdown_has_article_types(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_philo", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "## Article Types" in md
        assert "Theoretical Essay" in md

    def test_markdown_conflict_reported(self):
        result = import_venue_seed_corpus(SEED_CORPUS)
        pack = build_venue_evidence_pack(
            "vrec_synth_formal", result.venues, result.sources, result.claims
        )
        md = evidence_pack_to_markdown(pack)
        assert "Conflicts:" in md
        assert "competing claims" in md
