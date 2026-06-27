"""Tests for evidence_pack_harvester (P7.3 Track 4/12)."""

import pytest
from pathlib import Path

from kairoskopion.services.evidence_pack_harvester import (
    harvest_evidence_pack,
    harvest_all_evidence_packs,
    load_harvest_into_hub,
    EvidencePackHarvestResult,
    _extract_section,
    _extract_field,
    _extract_issn,
    _parse_journal_identity,
    _parse_article_sections,
    _parse_metrics,
    _parse_vak_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_EVIDENCE_PACK = """\
# Venue Evidence Pack: Тестовый журнал / Test Journal

## Journal Identity

- **Name:** Тестовый журнал / Test Journal
- **ISSN:** 1234-5678 (print)
- **eISSN:** 2345-6789
- **Publisher:** Test University Press
- **URL:** https://test-journal.example.org/

## Aims and Scope

The journal covers test topics.

## VAK Status

Included in the VAK list. Category: К1.

- **Evidence status:** FACT_FROM_OFFICIAL_SOURCE

## Article Types

1. Research articles / научные статьи
2. Book reviews / рецензии
3. Conference reports / обзоры конференций

## Indexing Claims

- **Scopus subject areas:** Education (Q2), Philosophy (Q3)
- **SJR (2024):** 0.45
- **CiteScore (2024):** 1.23
- **h-index:** 15
- **RSCI 2-year impact factor (core):** 0.678
"""


MINIMAL_NO_ISSN = """\
# Venue Evidence Pack: Журнал без ISSN

## Journal Identity

- **Name:** Журнал без ISSN
- **Publisher:** Без Издателя

## Article Types

1. Статьи

## Indexing Claims

No major indexing.
"""


@pytest.fixture
def evidence_pack_file(tmp_path: Path) -> Path:
    f = tmp_path / "test_evidence_pack.md"
    f.write_text(MINIMAL_EVIDENCE_PACK, encoding="utf-8")
    return f


@pytest.fixture
def evidence_pack_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evidence_packs"
    d.mkdir()
    (d / "journal_a_evidence_pack.md").write_text(
        MINIMAL_EVIDENCE_PACK, encoding="utf-8",
    )
    (d / "journal_b_evidence_pack.md").write_text(
        MINIMAL_NO_ISSN, encoding="utf-8",
    )
    return d


# ---------------------------------------------------------------------------
# Section extraction tests
# ---------------------------------------------------------------------------

class TestSectionExtraction:
    def test_extract_known_section(self):
        result = _extract_section(MINIMAL_EVIDENCE_PACK, "Journal Identity")
        assert result is not None
        assert "ISSN" in result

    def test_extract_missing_section(self):
        result = _extract_section(MINIMAL_EVIDENCE_PACK, "Nonexistent Section")
        assert result is None

    def test_extract_field_name(self):
        section = _extract_section(MINIMAL_EVIDENCE_PACK, "Journal Identity")
        name = _extract_field(section, "Name")
        assert name is not None
        assert "Тестовый журнал" in name

    def test_extract_field_publisher(self):
        section = _extract_section(MINIMAL_EVIDENCE_PACK, "Journal Identity")
        publisher = _extract_field(section, "Publisher")
        assert publisher == "Test University Press"

    def test_extract_issn(self):
        section = _extract_section(MINIMAL_EVIDENCE_PACK, "Journal Identity")
        issn = _extract_issn(section, "ISSN")
        assert issn == "1234-5678"

    def test_extract_eissn(self):
        section = _extract_section(MINIMAL_EVIDENCE_PACK, "Journal Identity")
        eissn = _extract_issn(section, "eISSN")
        assert eissn == "2345-6789"

    def test_extract_issn_missing(self):
        issn = _extract_issn("No ISSN here", "ISSN")
        assert issn is None


# ---------------------------------------------------------------------------
# Identity parsing tests
# ---------------------------------------------------------------------------

class TestIdentityParsing:
    def test_parse_journal_identity(self):
        venue, packet, warnings = _parse_journal_identity(
            MINIMAL_EVIDENCE_PACK, "test.md",
        )
        assert venue is not None
        assert venue.canonical_name == "Тестовый журнал"
        assert "Test Journal" in venue.aliases
        assert venue.issn == "1234-5678"
        assert venue.eissn == "2345-6789"
        assert venue.publisher == "Test University Press"
        assert len(venue.official_urls) == 1
        assert venue.evidence_refs
        assert venue.source_status == "provisional"

    def test_parse_identity_creates_packet(self):
        venue, packet, warnings = _parse_journal_identity(
            MINIMAL_EVIDENCE_PACK, "test.md",
        )
        assert packet is not None
        assert packet.packet_type == "venue_identity"
        assert packet.source_type == "venue_evidence_pack"
        assert packet.confidence == "high"

    def test_parse_identity_no_issn_warns(self):
        venue, packet, warnings = _parse_journal_identity(
            MINIMAL_NO_ISSN, "test.md",
        )
        assert venue is not None
        assert any("ISSN" in w for w in warnings)

    def test_parse_identity_missing_section(self):
        venue, packet, warnings = _parse_journal_identity(
            "# No Identity\n\nJust text.", "test.md",
        )
        assert venue is None
        assert warnings


# ---------------------------------------------------------------------------
# Section parsing tests
# ---------------------------------------------------------------------------

class TestSectionParsing:
    def test_parse_article_sections(self):
        sections, packets, warnings = _parse_article_sections(
            MINIMAL_EVIDENCE_PACK, "venue_123", "test.md",
        )
        assert len(sections) == 3
        assert sections[0].section_name
        assert sections[0].parent_venue_id == "venue_123"
        assert sections[0].section_type == "section"
        assert len(packets) == 3

    def test_section_evidence_refs(self):
        sections, _, _ = _parse_article_sections(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        for sec in sections:
            assert sec.evidence_refs
            assert sec.evidence_refs[0].source_type == "venue_evidence_pack"

    def test_no_sections_warns(self):
        sections, _, warnings = _parse_article_sections(
            "# Title\n\n## Other\n\nNo sections.", "v1", "test.md",
        )
        assert sections == []
        assert warnings


# ---------------------------------------------------------------------------
# Metrics parsing tests
# ---------------------------------------------------------------------------

class TestMetricsParsing:
    def test_parse_sjr(self):
        metrics, packets, _ = _parse_metrics(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        sjr = [m for m in metrics if m.metric_system == "sjr"]
        assert len(sjr) == 1
        assert sjr[0].metric_value == "0.45"
        assert sjr[0].database == "Scopus/Scimago"

    def test_parse_citescore(self):
        metrics, _, _ = _parse_metrics(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        cs = [m for m in metrics if m.metric_system == "citescore"]
        assert len(cs) == 1
        assert cs[0].metric_value == "1.23"

    def test_parse_h_index(self):
        metrics, _, _ = _parse_metrics(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        h = [m for m in metrics if m.metric_system == "h_index"]
        assert len(h) == 1
        assert h[0].metric_value == "15"

    def test_parse_rsci_if(self):
        metrics, _, _ = _parse_metrics(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        rsci = [m for m in metrics if m.metric_system == "rsci_if"]
        assert len(rsci) == 1
        assert rsci[0].metric_value == "0.678"

    def test_parse_scopus_quartiles(self):
        metrics, _, _ = _parse_metrics(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        quartiles = [m for m in metrics if m.metric_system == "scopus_quartile"]
        assert len(quartiles) == 2
        values = {m.metric_value for m in quartiles}
        assert "Q2" in values
        assert "Q3" in values

    def test_no_metrics_warns(self):
        metrics, _, warnings = _parse_metrics(
            "## Indexing Claims\n\nNo data.", "v1", "test.md",
        )
        assert metrics == []
        assert warnings


# ---------------------------------------------------------------------------
# VAK classification tests
# ---------------------------------------------------------------------------

class TestVAKParsing:
    def test_parse_vak_included(self):
        records, packets, _ = _parse_vak_status(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        assert len(records) >= 1
        assert records[0].classification_system_id == "vak_ru"
        assert records[0].venue_id == "v1"

    def test_parse_vak_category(self):
        records, _, _ = _parse_vak_status(
            MINIMAL_EVIDENCE_PACK, "v1", "test.md",
        )
        cat_records = [r for r in records if r.classification_system_id == "vak_ru_category"]
        assert len(cat_records) == 1

    def test_no_vak_section_warns(self):
        records, _, warnings = _parse_vak_status(
            "# Title\n\n## Other\n\nText", "v1", "test.md",
        )
        assert records == []
        assert warnings


# ---------------------------------------------------------------------------
# Full harvest tests
# ---------------------------------------------------------------------------

class TestFullHarvest:
    def test_harvest_evidence_pack(self, evidence_pack_file: Path):
        result = harvest_evidence_pack(evidence_pack_file)
        assert result.venue_record is not None
        assert result.venue_record.canonical_name == "Тестовый журнал"
        assert len(result.section_records) == 3
        assert len(result.metric_records) >= 4
        assert len(result.source_packets) > 0
        assert result.source_file == str(evidence_pack_file)

    def test_harvest_nonexistent_file(self, tmp_path: Path):
        result = harvest_evidence_pack(tmp_path / "missing.md")
        assert result.venue_record is None
        assert result.warnings

    def test_harvest_all_packs(self, evidence_pack_dir: Path):
        results = harvest_all_evidence_packs(evidence_pack_dir)
        assert len(results) == 2
        assert results[0].venue_record is not None
        assert results[1].venue_record is not None

    def test_harvest_all_empty_dir(self, tmp_path: Path):
        results = harvest_all_evidence_packs(tmp_path / "nonexistent")
        assert results == []


# ---------------------------------------------------------------------------
# RegistryHub loading tests
# ---------------------------------------------------------------------------

class TestHubLoading:
    def test_load_into_hub(self, evidence_pack_file: Path, tmp_path: Path):
        from kairoskopion.registry.services import RegistryHub
        hub = RegistryHub(data_dir=tmp_path / "registry")

        result = harvest_evidence_pack(evidence_pack_file)
        counts = load_harvest_into_hub([result], hub)

        assert counts["venues"] == 1
        assert counts["sections"] == 3
        assert counts["metrics"] >= 4
        assert counts["packets"] > 0

        all_venues = hub.venues().list_all()
        assert len(all_venues) == 1
        assert all_venues[0].canonical_name == "Тестовый журнал"

    def test_load_deduplicates_venues(self, evidence_pack_file: Path, tmp_path: Path):
        from kairoskopion.registry.services import RegistryHub
        hub = RegistryHub(data_dir=tmp_path / "registry")

        result = harvest_evidence_pack(evidence_pack_file)
        counts1 = load_harvest_into_hub([result], hub)
        assert counts1["venues"] == 1

        result2 = harvest_evidence_pack(evidence_pack_file)
        counts2 = load_harvest_into_hub([result2], hub)
        assert counts2["venues"] == 0  # duplicate detected

    def test_load_preserves_evidence_refs(self, evidence_pack_file: Path, tmp_path: Path):
        from kairoskopion.registry.services import RegistryHub
        hub = RegistryHub(data_dir=tmp_path / "registry")

        result = harvest_evidence_pack(evidence_pack_file)
        load_harvest_into_hub([result], hub)

        venue = hub.venues().list_all()[0]
        assert venue.evidence_refs
        assert venue.evidence_refs[0].evidence_status == "corpus_grounded"


# ---------------------------------------------------------------------------
# Real evidence pack integration tests
# ---------------------------------------------------------------------------

class TestRealEvidencePacks:
    """Integration tests against real venue evidence packs in the project."""

    @pytest.fixture
    def real_packs_dir(self) -> Path:
        d = Path("data/venue_evidence_packs")
        if not d.exists():
            pytest.skip("No real evidence packs available")
        return d

    def test_harvest_real_voprosy_filosofii(self, real_packs_dir: Path):
        f = real_packs_dir / "voprosy_filosofii_evidence_pack.md"
        if not f.exists():
            pytest.skip("Voprosy filosofii evidence pack not found")
        result = harvest_evidence_pack(f)
        assert result.venue_record is not None
        assert "Вопросы философии" in result.venue_record.canonical_name
        assert result.venue_record.issn == "0042-8744"
        assert len(result.section_records) >= 3
        assert len(result.metric_records) >= 3

    def test_harvest_all_real_packs(self, real_packs_dir: Path):
        results = harvest_all_evidence_packs(real_packs_dir)
        assert len(results) >= 4
        for r in results:
            assert r.venue_record is not None, f"Failed to extract venue from {r.source_file}"

    def test_load_all_real_into_hub(self, real_packs_dir: Path, tmp_path: Path):
        from kairoskopion.registry.services import RegistryHub
        hub = RegistryHub(data_dir=tmp_path / "registry")

        results = harvest_all_evidence_packs(real_packs_dir)
        counts = load_harvest_into_hub(results, hub)
        assert counts["venues"] >= 4
        assert counts["sections"] >= 10
        assert counts["metrics"] >= 5
        assert counts["packets"] >= 20
