"""Tests for P6 registry-first acquisition pipeline.

Covers:
- Record model serialization (to_dict/from_dict round-trip)
- BaseRegistry CRUD (add_provisional, accept, reject, search, dedup)
- JSONL persistence (write, reload)
- SourcePacket → EvidenceRef bridge
- AcquisitionTask lifecycle
- record_usage_status() downstream rules
- VenueSectionRecord independence from parent
- VenueMetricRecord per-database/year/category
- VenueClassificationRecord lacks source_status (uses evidence_status)
"""

import json
from pathlib import Path

import pytest

from kairoskopion.registry import (
    EvidenceRef,
    SourcePacket,
    DisciplineRecord,
    EpistemicFrameworkRecord,
    VenueRegistryRecord,
    VenueSectionRecord,
    ClassificationSystemRecord,
    SubjectCategoryRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    SourceAcquisitionTask,
    SOURCE_STATUSES,
    REVIEW_STATUSES,
    TASK_STATUSES,
    BaseRegistry,
    load_registry,
    record_usage_status,
)
from kairoskopion.registry.store import (
    SourcePacketStore,
    AcquisitionTaskStore,
    _read_jsonl,
    _append_jsonl,
)


# =====================================================================
# 1. EvidenceRef
# =====================================================================

class TestEvidenceRef:
    def test_round_trip(self):
        ref = EvidenceRef(
            source_type="openalex",
            source_id="W12345",
            source_url="https://openalex.org/W12345",
            evidence_status="source_grounded",
        )
        d = ref.to_dict()
        restored = EvidenceRef.from_dict(d)
        assert restored.source_type == "openalex"
        assert restored.source_id == "W12345"
        assert restored.evidence_status == "source_grounded"

    def test_none_fields_excluded_from_dict(self):
        ref = EvidenceRef(source_type="manual")
        d = ref.to_dict()
        assert "source_url" not in d
        assert "source_type" in d

    def test_auto_generated_id(self):
        ref = EvidenceRef()
        assert ref.evidence_id.startswith("evref_")


# =====================================================================
# 2. SourcePacket
# =====================================================================

class TestSourcePacket:
    def test_round_trip(self):
        pkt = SourcePacket(
            packet_type="venue_search",
            query="Вопросы философии",
            source_type="openalex",
            adapter_name="openalex_venue",
        )
        d = pkt.to_dict()
        restored = SourcePacket.from_dict(d)
        assert restored.packet_type == "venue_search"
        assert restored.query == "Вопросы философии"

    def test_to_evidence_ref(self):
        pkt = SourcePacket(
            source_type="crossref",
            source_id="ISSN:0042-8744",
            source_url="https://api.crossref.org/journals/0042-8744",
            evidence_status="adapter_result",
            confidence="high",
        )
        ref = pkt.to_evidence_ref()
        assert ref.source_type == "crossref"
        assert ref.source_id == "ISSN:0042-8744"
        assert ref.evidence_status == "adapter_result"
        assert ref.confidence == "high"

    def test_auto_generated_id(self):
        pkt = SourcePacket()
        assert pkt.packet_id


# =====================================================================
# 3. SourceAcquisitionTask
# =====================================================================

class TestSourceAcquisitionTask:
    def test_round_trip(self):
        task = SourceAcquisitionTask(
            task_type="venue_issn_lookup",
            query="0042-8744",
            reason="Need canonical venue record for VF",
            target_sources=["crossref", "openalex"],
            created_by_agent="venue_profiler",
        )
        d = task.to_dict()
        restored = SourceAcquisitionTask.from_dict(d)
        assert restored.task_type == "venue_issn_lookup"
        assert restored.target_sources == ["crossref", "openalex"]
        assert restored.status == "open"

    def test_auto_generated_id(self):
        task = SourceAcquisitionTask()
        assert task.task_id.startswith("acqtask_")


# =====================================================================
# 4. Registry record models — serialization
# =====================================================================

class TestDisciplineRecord:
    def test_round_trip(self):
        rec = DisciplineRecord(
            display_names={"ru": "Философия", "en": "Philosophy"},
            aliases=["филос."],
            source_status="accepted",
            review_status="curator_confirmed",
            legitimate_objects=["бытие", "сознание"],
        )
        d = rec.to_dict()
        restored = DisciplineRecord.from_dict(d)
        assert restored.display_names["ru"] == "Философия"
        assert restored.legitimate_objects == ["бытие", "сознание"]
        assert restored.source_status == "accepted"

    def test_record_id_alias(self):
        rec = DisciplineRecord()
        assert rec.record_id == rec.discipline_id

    def test_evidence_refs_round_trip(self):
        ref = EvidenceRef(source_type="manual", evidence_status="user_provided")
        rec = DisciplineRecord(evidence_refs=[ref])
        d = rec.to_dict()
        restored = DisciplineRecord.from_dict(d)
        assert len(restored.evidence_refs) == 1
        assert restored.evidence_refs[0].source_type == "manual"


class TestEpistemicFrameworkRecord:
    def test_round_trip(self):
        rec = EpistemicFrameworkRecord(
            label="Phenomenology",
            framework_kind="tradition",
            related_disciplines=["disc-001"],
        )
        d = rec.to_dict()
        restored = EpistemicFrameworkRecord.from_dict(d)
        assert restored.label == "Phenomenology"
        assert restored.framework_kind == "tradition"

    def test_record_id_alias(self):
        rec = EpistemicFrameworkRecord()
        assert rec.record_id == rec.framework_id


class TestVenueRegistryRecord:
    def test_round_trip(self):
        rec = VenueRegistryRecord(
            canonical_name="Вопросы философии",
            issn="0042-8744",
            publisher="РАН",
        )
        d = rec.to_dict()
        restored = VenueRegistryRecord.from_dict(d)
        assert restored.canonical_name == "Вопросы философии"
        assert restored.issn == "0042-8744"

    def test_record_id_alias(self):
        rec = VenueRegistryRecord()
        assert rec.record_id == rec.venue_id


class TestVenueSectionRecord:
    def test_round_trip(self):
        rec = VenueSectionRecord(
            parent_venue_id="venue-001",
            section_name="Этика",
            section_type="section",
            scope="Applied ethics and metaethics",
        )
        d = rec.to_dict()
        restored = VenueSectionRecord.from_dict(d)
        assert restored.parent_venue_id == "venue-001"
        assert restored.section_name == "Этика"
        assert restored.section_type == "section"

    def test_independent_from_parent(self):
        """Section scope != parent scope — first-class record."""
        sec = VenueSectionRecord(
            parent_venue_id="venue-001",
            section_name="Логика",
            scope="Formal and non-formal logic",
        )
        assert sec.section_id != sec.parent_venue_id
        assert sec.scope is not None

    def test_record_id_alias(self):
        rec = VenueSectionRecord()
        assert rec.record_id == rec.section_id


class TestClassificationSystemRecord:
    def test_round_trip(self):
        rec = ClassificationSystemRecord(
            name="ВАК",
            region="RU",
            version_or_year="2024",
        )
        d = rec.to_dict()
        restored = ClassificationSystemRecord.from_dict(d)
        assert restored.name == "ВАК"
        assert restored.region == "RU"

    def test_record_id_alias(self):
        rec = ClassificationSystemRecord()
        assert rec.record_id == rec.system_id


class TestSubjectCategoryRecord:
    def test_round_trip(self):
        rec = SubjectCategoryRecord(
            classification_system_id="sys-001",
            code="09.00.00",
            label="Философские науки",
        )
        d = rec.to_dict()
        restored = SubjectCategoryRecord.from_dict(d)
        assert restored.code == "09.00.00"
        assert restored.label == "Философские науки"

    def test_record_id_alias(self):
        rec = SubjectCategoryRecord()
        assert rec.record_id == rec.category_id


class TestVenueClassificationRecord:
    def test_round_trip(self):
        rec = VenueClassificationRecord(
            venue_id="venue-001",
            classification_system_id="sys-001",
            subject_category_id="cat-001",
            year_or_version="2024",
            evidence_status="source_grounded",
        )
        d = rec.to_dict()
        restored = VenueClassificationRecord.from_dict(d)
        assert restored.venue_id == "venue-001"
        assert restored.evidence_status == "source_grounded"

    def test_no_source_status_field(self):
        """VenueClassificationRecord uses evidence_status, not source_status."""
        rec = VenueClassificationRecord()
        assert not hasattr(rec, "source_status")
        assert hasattr(rec, "evidence_status")


class TestVenueMetricRecord:
    def test_round_trip(self):
        rec = VenueMetricRecord(
            venue_id="venue-001",
            database="Scopus",
            subject_category_id="cat-001",
            year="2023",
            metric_type="quartile",
            metric_value="Q2",
            evidence_status="adapter_result",
        )
        d = rec.to_dict()
        restored = VenueMetricRecord.from_dict(d)
        assert restored.database == "Scopus"
        assert restored.metric_value == "Q2"
        assert restored.year == "2023"

    def test_per_database_year_category(self):
        """Never collapse to journal.quartile = Q1. Each metric is its own record."""
        m1 = VenueMetricRecord(
            venue_id="venue-001", database="Scopus",
            subject_category_id="cat-001", year="2023",
            metric_type="quartile", metric_value="Q1",
        )
        m2 = VenueMetricRecord(
            venue_id="venue-001", database="WoS",
            subject_category_id="cat-002", year="2023",
            metric_type="quartile", metric_value="Q3",
        )
        assert m1.metric_id != m2.metric_id
        assert m1.database != m2.database
        assert m1.metric_value != m2.metric_value


# =====================================================================
# 5. Constants
# =====================================================================

class TestConstants:
    def test_source_statuses(self):
        assert "provisional" in SOURCE_STATUSES
        assert "accepted" in SOURCE_STATUSES
        assert "rejected" in SOURCE_STATUSES
        assert "unknown" in SOURCE_STATUSES

    def test_review_statuses(self):
        assert "pending" in REVIEW_STATUSES
        assert "curator_confirmed" in REVIEW_STATUSES
        assert "rejected" in REVIEW_STATUSES

    def test_task_statuses(self):
        assert "open" in TASK_STATUSES
        assert "completed" in TASK_STATUSES
        assert "blocked" in TASK_STATUSES


# =====================================================================
# 6. record_usage_status()
# =====================================================================

class TestRecordUsageStatus:
    def test_canonical(self):
        rec = DisciplineRecord(source_status="accepted", review_status="curator_confirmed")
        assert record_usage_status(rec) == "canonical"

    def test_provisional_with_warning(self):
        rec = DisciplineRecord(source_status="provisional", review_status="pending")
        assert record_usage_status(rec) == "provisional_with_warning"

    def test_provisional_reviewed(self):
        rec = DisciplineRecord(source_status="provisional", review_status="reviewed")
        assert record_usage_status(rec) == "provisional_with_warning"

    def test_rejected_by_source(self):
        rec = DisciplineRecord(source_status="rejected", review_status="pending")
        assert record_usage_status(rec) == "rejected_unusable"

    def test_rejected_by_review(self):
        rec = DisciplineRecord(source_status="provisional", review_status="rejected")
        assert record_usage_status(rec) == "rejected_unusable"

    def test_unknown(self):
        rec = DisciplineRecord(source_status="unknown", review_status="pending")
        assert record_usage_status(rec) == "unknown"

    def test_accepted_but_not_confirmed(self):
        rec = DisciplineRecord(source_status="accepted", review_status="pending")
        assert record_usage_status(rec) == "unknown"


# =====================================================================
# 7. JSONL I/O helpers
# =====================================================================

class TestJSONLIO:
    def test_read_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert _read_jsonl(p) == []

    def test_read_nonexistent(self, tmp_path: Path):
        p = tmp_path / "missing.jsonl"
        assert _read_jsonl(p) == []

    def test_append_and_read(self, tmp_path: Path):
        p = tmp_path / "test.jsonl"
        _append_jsonl(p, {"a": 1})
        _append_jsonl(p, {"b": 2})
        records = _read_jsonl(p)
        assert len(records) == 2
        assert records[0]["a"] == 1
        assert records[1]["b"] == 2

    def test_creates_parent_dirs(self, tmp_path: Path):
        p = tmp_path / "sub" / "dir" / "test.jsonl"
        _append_jsonl(p, {"x": 1})
        assert p.exists()

    def test_skips_invalid_lines(self, tmp_path: Path):
        p = tmp_path / "bad.jsonl"
        p.write_text('{"ok": 1}\nnot json\n{"ok": 2}\n')
        records = _read_jsonl(p)
        assert len(records) == 2


# =====================================================================
# 8. BaseRegistry — in-memory (no JSONL)
# =====================================================================

class TestBaseRegistryInMemory:
    def test_add_provisional(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(display_names={"en": "Philosophy"})
        result = reg.add_provisional(rec)
        assert result.source_status == "provisional"
        assert result.review_status == "pending"
        assert len(reg) == 1

    def test_get(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(display_names={"en": "Philosophy"})
        reg.add_provisional(rec)
        fetched = reg.get(rec.discipline_id)
        assert fetched is not None
        assert fetched.display_names["en"] == "Philosophy"

    def test_get_missing(self):
        reg = BaseRegistry("discipline")
        assert reg.get("nonexistent") is None

    def test_list_all(self):
        reg = BaseRegistry("discipline")
        reg.add_provisional(DisciplineRecord(display_names={"en": "A"}))
        reg.add_provisional(DisciplineRecord(display_names={"en": "B"}))
        assert len(reg.list_all()) == 2

    def test_search_by_name(self):
        reg = BaseRegistry("venue")
        reg.add_provisional(VenueRegistryRecord(canonical_name="Вопросы философии"))
        reg.add_provisional(VenueRegistryRecord(canonical_name="Этнографическое обозрение"))
        results = reg.search("философ")
        assert len(results) == 1
        assert results[0].canonical_name == "Вопросы философии"

    def test_search_by_alias(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(display_names={"en": "Philosophy"}, aliases=["филос.", "phil"])
        reg.add_provisional(rec)
        results = reg.search("филос")
        assert len(results) == 1

    def test_search_empty_query(self):
        reg = BaseRegistry("discipline")
        reg.add_provisional(DisciplineRecord(display_names={"en": "A"}))
        reg.add_provisional(DisciplineRecord(display_names={"en": "B"}))
        assert len(reg.search("")) == 2

    def test_accept(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(display_names={"en": "Philosophy"})
        reg.add_provisional(rec)
        accepted = reg.accept(rec.discipline_id, reviewer_note="Verified")
        assert accepted.source_status == "accepted"
        assert accepted.review_status == "curator_confirmed"

    def test_reject(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(display_names={"en": "Fake"})
        reg.add_provisional(rec)
        rejected = reg.reject(rec.discipline_id, reviewer_note="Not real")
        assert rejected.source_status == "rejected"
        assert rejected.review_status == "rejected"

    def test_accept_missing(self):
        reg = BaseRegistry("discipline")
        assert reg.accept("nonexistent") is None

    def test_reject_missing(self):
        reg = BaseRegistry("discipline")
        assert reg.reject("nonexistent") is None

    def test_update_review_status(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord()
        reg.add_provisional(rec)
        updated = reg.update_review_status(rec.discipline_id, "reviewed")
        assert updated.review_status == "reviewed"

    def test_update_review_status_invalid(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord()
        reg.add_provisional(rec)
        with pytest.raises(ValueError, match="Invalid review_status"):
            reg.update_review_status(rec.discipline_id, "bogus")

    def test_append_evidence_ref(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord()
        reg.add_provisional(rec)
        ref = EvidenceRef(source_type="manual")
        result = reg.append_evidence_ref(rec.discipline_id, ref)
        assert len(result.evidence_refs) == 1

    def test_find_duplicate_by_id(self):
        reg = BaseRegistry("discipline")
        rec = DisciplineRecord(discipline_id="disc-dup")
        reg.add_provisional(rec)
        dup = DisciplineRecord(discipline_id="disc-dup")
        assert reg.find_duplicate(dup) is not None

    def test_find_duplicate_by_name(self):
        reg = BaseRegistry("venue")
        rec = VenueRegistryRecord(canonical_name="Вопросы философии")
        reg.add_provisional(rec)
        dup = VenueRegistryRecord(canonical_name="Вопросы философии")
        found = reg.find_duplicate(dup)
        assert found is not None
        assert found.venue_id == rec.venue_id

    def test_find_duplicate_by_issn(self):
        reg = BaseRegistry("venue")
        rec = VenueRegistryRecord(issn="0042-8744")
        reg.add_provisional(rec)
        dup = VenueRegistryRecord(issn="0042-8744")
        assert reg.find_duplicate(dup) is not None

    def test_find_no_duplicate(self):
        reg = BaseRegistry("venue")
        rec = VenueRegistryRecord(canonical_name="А")
        reg.add_provisional(rec)
        other = VenueRegistryRecord(canonical_name="Б")
        assert reg.find_duplicate(other) is None

    def test_export_snapshot(self):
        reg = BaseRegistry("discipline")
        reg.add_provisional(DisciplineRecord(display_names={"en": "A"}))
        snapshot = reg.export_snapshot()
        assert len(snapshot) == 1
        assert isinstance(snapshot[0], dict)

    def test_unknown_record_type(self):
        with pytest.raises(ValueError, match="Unknown record_type"):
            BaseRegistry("bogus_type")


# =====================================================================
# 9. BaseRegistry — JSONL persistence
# =====================================================================

class TestBaseRegistryJSONL:
    def test_persist_and_reload(self, tmp_path: Path):
        p = tmp_path / "disciplines.jsonl"
        reg = BaseRegistry("discipline", p)
        rec = DisciplineRecord(display_names={"en": "Philosophy"})
        reg.add_provisional(rec)
        reg.accept(rec.discipline_id)

        reg2 = BaseRegistry("discipline", p)
        assert len(reg2) == 1
        loaded = reg2.get(rec.discipline_id)
        assert loaded.source_status == "accepted"

    def test_jsonl_append_on_accept(self, tmp_path: Path):
        p = tmp_path / "venues.jsonl"
        reg = BaseRegistry("venue", p)
        rec = VenueRegistryRecord(canonical_name="Test")
        reg.add_provisional(rec)
        reg.accept(rec.venue_id)
        lines = p.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_reload_deduplicates(self, tmp_path: Path):
        """JSONL has two entries for same ID — last wins on reload."""
        p = tmp_path / "disciplines.jsonl"
        reg = BaseRegistry("discipline", p)
        rec = DisciplineRecord(
            discipline_id="disc-fixed",
            display_names={"en": "V1"},
        )
        reg.add_provisional(rec)
        reg.accept("disc-fixed")

        reg2 = BaseRegistry("discipline", p)
        assert len(reg2) == 1
        assert reg2.get("disc-fixed").source_status == "accepted"


# =====================================================================
# 10. All record types loadable in BaseRegistry
# =====================================================================

class TestAllRecordTypes:
    @pytest.mark.parametrize("rtype,cls", [
        ("discipline", DisciplineRecord),
        ("epistemic_framework", EpistemicFrameworkRecord),
        ("venue", VenueRegistryRecord),
        ("venue_section", VenueSectionRecord),
        ("classification_system", ClassificationSystemRecord),
        ("subject_category", SubjectCategoryRecord),
    ])
    def test_add_and_get(self, rtype, cls):
        reg = BaseRegistry(rtype)
        rec = cls()
        reg.add_provisional(rec)
        assert len(reg) == 1
        fetched = reg.list_all()[0]
        assert fetched.source_status == "provisional"


# =====================================================================
# 11. SourcePacketStore
# =====================================================================

class TestSourcePacketStore:
    def test_add_and_get(self):
        store = SourcePacketStore()
        pkt = SourcePacket(packet_type="test")
        store.add(pkt)
        assert store.get(pkt.packet_id) is not None
        assert len(store) == 1

    def test_persist_and_reload(self, tmp_path: Path):
        p = tmp_path / "packets.jsonl"
        store = SourcePacketStore(p)
        pkt = SourcePacket(packet_type="test", query="q")
        store.add(pkt)

        store2 = SourcePacketStore(p)
        assert len(store2) == 1
        assert store2.get(pkt.packet_id).query == "q"

    def test_export_snapshot(self):
        store = SourcePacketStore()
        store.add(SourcePacket(packet_type="a"))
        store.add(SourcePacket(packet_type="b"))
        snap = store.export_snapshot()
        assert len(snap) == 2


# =====================================================================
# 12. AcquisitionTaskStore
# =====================================================================

class TestAcquisitionTaskStore:
    def test_add_and_list_open(self):
        store = AcquisitionTaskStore()
        t1 = SourceAcquisitionTask(task_type="lookup", status="open")
        t2 = SourceAcquisitionTask(task_type="crawl", status="completed")
        store.add(t1)
        store.add(t2)
        assert len(store) == 2
        assert len(store.list_open()) == 1

    def test_update_status(self):
        store = AcquisitionTaskStore()
        task = SourceAcquisitionTask(task_type="lookup")
        store.add(task)
        updated = store.update_status(task.task_id, "completed", ["pkt-001"])
        assert updated.status == "completed"
        assert "pkt-001" in updated.result_packet_ids

    def test_update_missing(self):
        store = AcquisitionTaskStore()
        assert store.update_status("nonexistent", "completed") is None

    def test_persist_and_reload(self, tmp_path: Path):
        p = tmp_path / "tasks.jsonl"
        store = AcquisitionTaskStore(p)
        task = SourceAcquisitionTask(task_type="lookup")
        store.add(task)
        store.update_status(task.task_id, "completed")

        store2 = AcquisitionTaskStore(p)
        assert len(store2) == 1
        assert store2.get(task.task_id).status == "completed"


# =====================================================================
# 13. load_registry convenience
# =====================================================================

class TestLoadRegistry:
    def test_load_from_empty_dir(self, tmp_path: Path):
        reg = load_registry("discipline", tmp_path)
        assert len(reg) == 0

    def test_load_with_seed_data(self, tmp_path: Path):
        p = tmp_path / "venues.jsonl"
        rec = VenueRegistryRecord(canonical_name="Test Journal")
        _append_jsonl(p, rec.to_dict())
        reg = load_registry("venue", tmp_path)
        assert len(reg) == 1
        assert reg.list_all()[0].canonical_name == "Test Journal"


# =====================================================================
# 14. Search with code field (SubjectCategoryRecord)
# =====================================================================

class TestSearchByCode:
    def test_search_by_code(self):
        reg = BaseRegistry("subject_category")
        rec = SubjectCategoryRecord(code="09.00.00", label="Философские науки")
        reg.add_provisional(rec)
        results = reg.search("09.00")
        assert len(results) == 1

    def test_search_by_label(self):
        reg = BaseRegistry("subject_category")
        rec = SubjectCategoryRecord(code="09.00.00", label="Философские науки")
        reg.add_provisional(rec)
        results = reg.search("философ")
        assert len(results) == 1


# =====================================================================
# 15. VenueMetricRecord — no collapse
# =====================================================================

class TestVenueMetricNoCollapse:
    def test_separate_metrics_different_dbs(self):
        reg = BaseRegistry("venue_metric")
        m1 = VenueMetricRecord(
            venue_id="v1", database="Scopus",
            year="2023", metric_type="quartile", metric_value="Q1",
        )
        m2 = VenueMetricRecord(
            venue_id="v1", database="WoS",
            year="2023", metric_type="quartile", metric_value="Q2",
        )
        reg.add_provisional(m1)
        reg.add_provisional(m2)
        assert len(reg) == 2

    def test_separate_metrics_different_years(self):
        reg = BaseRegistry("venue_metric")
        m1 = VenueMetricRecord(
            venue_id="v1", database="Scopus", year="2022", metric_value="Q2",
        )
        m2 = VenueMetricRecord(
            venue_id="v1", database="Scopus", year="2023", metric_value="Q1",
        )
        reg.add_provisional(m1)
        reg.add_provisional(m2)
        assert len(reg) == 2


# =====================================================================
# 16. Edge cases
# =====================================================================

class TestEdgeCases:
    def test_add_provisional_with_evidence_refs(self):
        reg = BaseRegistry("discipline")
        ref = EvidenceRef(source_type="manual")
        rec = DisciplineRecord()
        reg.add_provisional(rec, evidence_refs=[ref])
        fetched = reg.get(rec.discipline_id)
        assert len(fetched.evidence_refs) == 1

    def test_append_evidence_ref_missing_record(self):
        reg = BaseRegistry("discipline")
        ref = EvidenceRef(source_type="manual")
        assert reg.append_evidence_ref("nonexistent", ref) is None

    def test_venue_classification_add_and_get(self):
        """VenueClassificationRecord uses record_id as primary key."""
        reg = BaseRegistry("venue_classification")
        rec = VenueClassificationRecord(
            venue_id="v1",
            classification_system_id="sys-1",
            subject_category_id="cat-1",
        )
        reg.add_provisional(rec)
        assert len(reg) == 1

    def test_venue_metric_add_and_get(self):
        reg = BaseRegistry("venue_metric")
        rec = VenueMetricRecord(venue_id="v1", metric_value="Q1")
        reg.add_provisional(rec)
        assert len(reg) == 1


# =====================================================================
# 17. RegistryHub — registry-first lookups
# =====================================================================

from kairoskopion.registry.services import RegistryHub


class TestRegistryHub:
    def test_discipline_lookup_found(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        rec = DisciplineRecord(display_names={"en": "Philosophy"})
        hub.disciplines().add_provisional(rec)
        result = hub.lookup_discipline("Philosophy")
        assert result["found"] is True
        assert result["task"] is None
        assert result["usage_status"] == "provisional_with_warning"

    def test_discipline_lookup_not_found(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        result = hub.lookup_discipline("Nonexistent discipline")
        assert result["found"] is False
        assert result["task"] is not None
        assert result["task"].task_type == "discipline_lookup"
        assert len(hub.tasks) == 1

    def test_venue_lookup_by_issn(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        rec = VenueRegistryRecord(
            canonical_name="Вопросы философии",
            issn="0042-8744",
        )
        hub.venues().add_provisional(rec)
        result = hub.lookup_venue("anything", issn="0042-8744")
        assert result["found"] is True

    def test_venue_lookup_not_found_creates_task(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        result = hub.lookup_venue("Unknown Journal", issn="9999-9999")
        assert result["found"] is False
        assert result["task"].task_type == "venue_lookup"

    def test_venue_sections_lookup(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        s1 = VenueSectionRecord(parent_venue_id="v1", section_name="Ethics")
        s2 = VenueSectionRecord(parent_venue_id="v1", section_name="Logic")
        s3 = VenueSectionRecord(parent_venue_id="v2", section_name="Other")
        reg = hub.venue_sections()
        reg.add_provisional(s1)
        reg.add_provisional(s2)
        reg.add_provisional(s3)
        sections = hub.lookup_venue_sections("v1")
        assert len(sections) == 2

    def test_venue_metrics_lookup_filtered(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        m1 = VenueMetricRecord(venue_id="v1", database="Scopus", year="2023")
        m2 = VenueMetricRecord(venue_id="v1", database="WoS", year="2023")
        m3 = VenueMetricRecord(venue_id="v1", database="Scopus", year="2022")
        reg = hub.venue_metrics()
        reg.add_provisional(m1)
        reg.add_provisional(m2)
        reg.add_provisional(m3)
        results = hub.lookup_venue_metrics("v1", database="Scopus")
        assert len(results) == 2
        results = hub.lookup_venue_metrics("v1", year="2023")
        assert len(results) == 2
        results = hub.lookup_venue_metrics("v1", database="Scopus", year="2023")
        assert len(results) == 1

    def test_ingest_source_packet(self, tmp_path: Path):
        hub = RegistryHub(tmp_path)
        pkt = SourcePacket(packet_type="test", query="q")
        hub.ingest_source_packet(pkt)
        assert len(hub.packets) == 1


# =====================================================================
# 18. Registry API Router
# =====================================================================

from fastapi.testclient import TestClient
from kairoskopion.api.app import app


class TestRegistryAPI:
    @pytest.fixture(autouse=True)
    def _set_data_dir(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("KAIROSKOPION_DATA_DIR", str(tmp_path))

    def test_list_types(self):
        client = TestClient(app)
        resp = client.get("/api/registry/types")
        assert resp.status_code == 200
        types = resp.json()
        assert "discipline" in types
        assert "venue" in types

    def test_list_empty_registry(self):
        client = TestClient(app)
        resp = client.get("/api/registry/discipline")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_and_get(self):
        client = TestClient(app)
        resp = client.post(
            "/api/registry/discipline",
            json={"data": {"display_names": {"en": "TestDisc"}}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "created"
        rid = body["record"]["discipline_id"]

        resp2 = client.get(f"/api/registry/discipline/{rid}")
        assert resp2.status_code == 200
        assert resp2.json()["display_names"]["en"] == "TestDisc"

    def test_get_not_found(self):
        client = TestClient(app)
        resp = client.get("/api/registry/discipline/nonexistent")
        assert resp.status_code == 404

    def test_invalid_type(self):
        client = TestClient(app)
        resp = client.get("/api/registry/bogus_type")
        assert resp.status_code == 400

    def test_accept_and_reject(self):
        client = TestClient(app)
        resp = client.post(
            "/api/registry/venue",
            json={"data": {"canonical_name": "Test Journal"}},
        )
        rid = resp.json()["record"]["venue_id"]

        resp_accept = client.post(
            f"/api/registry/venue/{rid}/accept",
            json={"note": "verified"},
        )
        assert resp_accept.status_code == 200
        assert resp_accept.json()["source_status"] == "accepted"
        assert resp_accept.json()["_usage_status"] == "canonical"
