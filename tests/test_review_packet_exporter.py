"""Tests for P9 Review Packet / Dossier Export."""

import json
from pathlib import Path

import pytest

from kairoskopion.registry.models import (
    EvidenceRef,
    SourcePacket,
    SourceAcquisitionTask,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueMetricRecord,
    VenueClassificationRecord,
    DisciplineRecord,
)
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.review_packet_exporter import (
    ReviewPacket,
    build_review_packet,
    export_markdown,
    export_jsonl,
    export_tsv,
    write_review_packet,
)


def _ref(status="corpus_grounded"):
    return EvidenceRef(evidence_status=status, source_type="test")


@pytest.fixture
def hub(tmp_path):
    return RegistryHub(data_dir=tmp_path / "registry")


@pytest.fixture
def populated_hub(hub):
    """Hub with a representative set of records."""
    venues = hub.venues()
    v = VenueRegistryRecord(
        canonical_name="Вопросы философии",
        issn="0042-8744",
        publisher="ИФ РАН",
        evidence_refs=[_ref("corpus_grounded")],
    )
    venues.add_provisional(v)

    sections = hub.venue_sections()
    s = VenueSectionRecord(
        parent_venue_id=v.venue_id,
        section_name="Философия и общество",
        section_type="section",
        evidence_refs=[_ref("corpus_grounded")],
    )
    sections.add_provisional(s)

    metrics = hub.venue_metrics()
    m = VenueMetricRecord(
        venue_id=v.venue_id,
        metric_system="sjr",
        metric_type="quartile",
        metric_value="0.31",
        evidence_status="corpus_grounded",
    )
    metrics.add_provisional(m)

    classifications = hub.venue_classifications()
    c = VenueClassificationRecord(
        venue_id=v.venue_id,
        classification_system_id="vak",
        evidence_status="corpus_grounded",
    )
    classifications.add_provisional(c)

    disciplines = hub.disciplines()
    d = DisciplineRecord(
        display_names={"ru": "Философия", "en": "Philosophy"},
        source_status="provisional",
        provenance="llm_draft from ru_seed.jsonl",
        evidence_refs=[_ref("llm_inference")],
    )
    disciplines.add_provisional(d)

    pkt = SourcePacket(
        packet_type="evidence_pack_harvest",
        source_type="local_file",
        title="Вопросы философии evidence pack",
        evidence_status="corpus_grounded",
    )
    hub.packets.add(pkt)

    task = SourceAcquisitionTask(
        task_type="gap_resolution",
        query="Missing education venue universe",
        status="open",
    )
    hub.tasks.add(task)

    return hub


# ---------------------------------------------------------------------------
# ReviewPacket model
# ---------------------------------------------------------------------------

class TestReviewPacket:
    def test_serializable(self):
        p = ReviewPacket(packet_id="rpkt_test")
        d = p.to_dict()
        assert d["packet_id"] == "rpkt_test"
        json.dumps(d, ensure_ascii=False)

    def test_build_from_empty_hub(self, hub):
        p = build_review_packet(hub)
        assert p.packet_id != ""
        assert len(p.venues) == 0


# ---------------------------------------------------------------------------
# Build review packet
# ---------------------------------------------------------------------------

class TestBuildReviewPacket:
    def test_build_with_records(self, populated_hub):
        p = build_review_packet(populated_hub, gaps=["Missing education venues"])
        assert len(p.venues) == 1
        assert len(p.venue_sections) == 1
        assert len(p.venue_metrics) == 1
        assert len(p.venue_classifications) == 1
        assert len(p.disciplines) == 1
        assert len(p.source_packets) == 1
        assert len(p.acquisition_tasks) == 1
        assert len(p.gaps) == 1
        assert len(p.verification_decisions) >= 1
        assert "verdicts" in p.verification_summary

    def test_provenance_preserved(self, populated_hub):
        p = build_review_packet(populated_hub)
        venue = p.venues[0]
        assert "evidence_refs" in venue
        assert len(venue["evidence_refs"]) >= 1
        assert venue["evidence_refs"][0]["evidence_status"] == "corpus_grounded"

    def test_no_fabricated_records(self, populated_hub):
        p = build_review_packet(populated_hub)
        for v in p.venues:
            assert v.get("canonical_name") is not None
            assert v.get("issn") is not None or v.get("canonical_name") != ""

    def test_separates_verified_provisional_blocked(self, populated_hub):
        p = build_review_packet(populated_hub)
        verdicts = [vd.get("verdict") for vd in p.verification_decisions]
        assert any(v in ("keep_provisional", "promote_local_evidence_supported",
                         "promote_verified") for v in verdicts)

    def test_blocked_items_tracked(self, populated_hub):
        p = build_review_packet(populated_hub)
        assert len(p.blocked_items) >= 1


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

class TestMarkdownExport:
    def test_markdown_generated(self, populated_hub):
        p = build_review_packet(populated_hub, gaps=["Gap 1"])
        md = export_markdown(p)
        assert "# Kairoskopion Review Packet" in md
        assert "## Summary" in md
        assert "## Verification Verdicts" in md
        assert "Вопросы философии" in md

    def test_markdown_has_gaps(self, populated_hub):
        p = build_review_packet(populated_hub, gaps=["Missing data"])
        md = export_markdown(p)
        assert "## Open Gaps" in md
        assert "Missing data" in md

    def test_markdown_has_next_steps(self, populated_hub):
        p = build_review_packet(populated_hub)
        md = export_markdown(p)
        assert "## Next Steps" in md

    def test_markdown_source_packets(self, populated_hub):
        p = build_review_packet(populated_hub)
        md = export_markdown(p)
        assert "## Source Packets" in md


# ---------------------------------------------------------------------------
# JSONL export
# ---------------------------------------------------------------------------

class TestJSONLExport:
    def test_jsonl_valid(self, populated_hub):
        p = build_review_packet(populated_hub)
        jsonl = export_jsonl(p)
        lines = [l for l in jsonl.strip().split("\n") if l.strip()]
        assert len(lines) >= 1
        for line in lines:
            data = json.loads(line)
            assert "record_type" in data

    def test_jsonl_has_header(self, populated_hub):
        p = build_review_packet(populated_hub)
        jsonl = export_jsonl(p)
        first_line = json.loads(jsonl.strip().split("\n")[0])
        assert first_line["record_type"] == "review_packet_header"
        assert first_line["packet_id"] == p.packet_id

    def test_jsonl_contains_all_types(self, populated_hub):
        p = build_review_packet(populated_hub)
        jsonl = export_jsonl(p)
        types = set()
        for line in jsonl.strip().split("\n"):
            data = json.loads(line)
            types.add(data["record_type"])
        assert "venue" in types
        assert "source_packet" in types
        assert "verification_decision" in types


# ---------------------------------------------------------------------------
# TSV export
# ---------------------------------------------------------------------------

class TestTSVExport:
    def test_tsv_valid(self, populated_hub):
        p = build_review_packet(populated_hub)
        tsv = export_tsv(p)
        lines = tsv.strip().split("\n")
        assert len(lines) >= 2
        header = lines[0].split("\t")
        assert "record_type" in header
        assert "record_id" in header

    def test_tsv_has_venues(self, populated_hub):
        p = build_review_packet(populated_hub)
        tsv = export_tsv(p)
        assert "venue" in tsv
        assert "Вопросы философии" in tsv

    def test_tsv_has_metrics(self, populated_hub):
        p = build_review_packet(populated_hub)
        tsv = export_tsv(p)
        assert "venue_metric" in tsv

    def test_tsv_has_needs_action(self, populated_hub):
        p = build_review_packet(populated_hub)
        tsv = export_tsv(p)
        assert "needs_action" in tsv.split("\n")[0]


# ---------------------------------------------------------------------------
# Write to disk
# ---------------------------------------------------------------------------

class TestWriteToDisk:
    def test_writes_all_formats(self, populated_hub, tmp_path):
        p = build_review_packet(populated_hub, gaps=["Gap"])
        out = tmp_path / "output"
        paths = write_review_packet(p, out)
        assert "markdown" in paths
        assert "jsonl" in paths
        assert "tsv" in paths
        assert paths["markdown"].exists()
        assert paths["jsonl"].exists()
        assert paths["tsv"].exists()

    def test_markdown_file_content(self, populated_hub, tmp_path):
        p = build_review_packet(populated_hub)
        out = tmp_path / "output"
        paths = write_review_packet(p, out)
        content = paths["markdown"].read_text(encoding="utf-8")
        assert "# Kairoskopion Review Packet" in content

    def test_jsonl_file_valid(self, populated_hub, tmp_path):
        p = build_review_packet(populated_hub)
        out = tmp_path / "output"
        paths = write_review_packet(p, out)
        content = paths["jsonl"].read_text(encoding="utf-8")
        for line in content.strip().split("\n"):
            json.loads(line)
