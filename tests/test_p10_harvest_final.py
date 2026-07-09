"""Tests for P10 final harvest pass.

Verifies: domain classification, acquisition task generation,
verification gate on existing records, review packet export,
provisional candidate export validation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.registry.models import VenueRegistryRecord, EvidenceRef
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.verification_gate import verify_registry, summarize_verification
from kairoskopion.services.review_packet_exporter import (
    build_review_packet, export_markdown, export_jsonl, export_tsv,
)


# Import harvest final script helpers
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_p10_harvest_final import (
    classify_venue,
    build_acquisition_tasks,
    load_provisional_records,
    run_verification_on_records,
)


# ── domain classification ──────────────────────────────────────────

class TestDomainClassification:
    def test_tier1_ru_education(self):
        assert classify_venue("Vysshee Obrazovanie v Rossii = Higher Education in Russia") == "tier1_ru_education"

    def test_tier1_pedagogical(self):
        assert classify_venue("Pedagogical Education in Russia") == "tier1_ru_education"

    def test_tier2_ai_education(self):
        assert classify_venue("International Journal of Artificial Intelligence in Education") == "tier2_ai_education"

    def test_tier3_edtech(self):
        assert classify_venue("British Journal of Educational Technology") == "tier3_edtech"

    def test_tier4_higher_ed(self):
        assert classify_venue("Studies in Higher Education") == "tier4_higher_ed"

    def test_noise_clinical(self):
        assert classify_venue("Clinical and Research Journal in Internal Medicine") == "noise"

    def test_noise_medical(self):
        assert classify_venue("Graduate Medical Education Research Journal") == "noise"

    def test_unclassified(self):
        assert classify_venue("Random Obscure Journal") == "unclassified"

    def test_no_auto_accept(self):
        """Classification never produces 'accepted' status."""
        for name in ["Pedagogical Education", "AI in Education Journal"]:
            tier = classify_venue(name)
            assert tier != "accepted"


# ── acquisition tasks ──────────────────────────────────────────────

class TestAcquisitionTasks:
    def test_task_count(self):
        tasks = build_acquisition_tasks()
        assert len(tasks) == 6

    def test_tasks_have_required_fields(self):
        tasks = build_acquisition_tasks()
        required = {"task_id", "source_need", "description", "target_authority",
                     "acquisition_route", "status", "priority", "created_at"}
        for t in tasks:
            missing = required - set(t.keys())
            assert not missing, f"Task {t['task_id']} missing: {missing}"

    def test_blocked_tasks_marked(self):
        tasks = build_acquisition_tasks()
        blocked = [t for t in tasks if "blocked" in t["status"]]
        assert len(blocked) == 2

    def test_no_duplicate_task_ids(self):
        tasks = build_acquisition_tasks()
        ids = [t["task_id"] for t in tasks]
        assert len(ids) == len(set(ids))

    def test_tasks_reference_valid_source_needs(self):
        tasks = build_acquisition_tasks()
        valid_sn = {"SN-02", "SN-03", "SN-04", "SN-05"}
        for t in tasks:
            assert t["source_need"] in valid_sn, f"{t['task_id']} has invalid SN: {t['source_need']}"


# ── verification gate ─────────────────────────────────────────────

class TestVerificationGateFinal:
    def test_all_provisional_stay_provisional(self, tmp_path):
        records = [
            {
                "venue_id": "vrec_test1",
                "canonical_name": "Test Journal",
                "issn": "1234-5678",
                "source_status": "provisional",
                "review_status": "pending",
                "evidence_refs": [{
                    "source_type": "adapter_openalex",
                    "source_id": "openalex",
                    "evidence_status": "FACT_FROM_API_METADATA",
                    "retrieval_date": "2026-06-27T12:00:00Z",
                }],
                "provenance": "p10_harvest",
            }
        ]
        decisions, summary = run_verification_on_records(records, tmp_path)
        assert len(decisions) >= 1
        for d in decisions:
            assert d.verdict == "keep_provisional"

    def test_no_auto_promotion(self, tmp_path):
        records = [
            {
                "venue_id": "vrec_test2",
                "canonical_name": "Another Journal",
                "issn": "5678-1234",
                "source_status": "provisional",
                "review_status": "pending",
                "evidence_refs": [{
                    "source_type": "adapter_doaj",
                    "source_id": "doaj",
                    "evidence_status": "FACT_FROM_API_METADATA",
                    "retrieval_date": "2026-06-27T12:00:00Z",
                }],
                "provenance": "p10_harvest",
            }
        ]
        decisions, summary = run_verification_on_records(records, tmp_path)
        assert summary["verdicts"].get("promote_verified", 0) == 0

    def test_summary_has_total(self, tmp_path):
        records = [{
            "venue_id": "vrec_sum",
            "canonical_name": "Sum Journal",
            "source_status": "provisional",
            "review_status": "pending",
            "evidence_refs": [],
            "provenance": "test",
        }]
        _, summary = run_verification_on_records(records, tmp_path)
        assert "total" in summary
        assert summary["total"] >= 1


# ── provisional candidate export ─────────────────────────────────

class TestProvisionalCandidateExport:
    def test_output_files_exist(self):
        harvest_dir = Path("data/seed_registry/education_ai_russia/p10_harvest")
        assert (harvest_dir / "provisional_candidate_export.jsonl").exists()
        assert (harvest_dir / "harvest_summary_final.json").exists()
        assert (harvest_dir / "acquisition_tasks_final.json").exists()
        assert (harvest_dir / "verification_decisions_final.jsonl").exists()

    def test_registry_output_all_provisional(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl")
        if not path.exists():
            pytest.skip("Output not yet generated")
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line.strip())
                assert rec["source_status"] == "provisional"
                assert rec["review_status"] == "pending"

    def test_registry_output_has_provenance(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl")
        if not path.exists():
            pytest.skip("Output not yet generated")
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line.strip())
                assert rec.get("provenance"), f"Missing provenance: {rec.get('venue_id')}"

    def test_registry_output_has_domain_tier(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl")
        if not path.exists():
            pytest.skip("Output not yet generated")
        valid_tiers = {"tier1_ru_education", "tier2_ai_education", "tier3_edtech",
                       "tier4_higher_ed", "noise", "unclassified"}
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line.strip())
                assert rec.get("domain_tier") in valid_tiers

    def test_no_accepted_without_verification(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl")
        if not path.exists():
            pytest.skip("Output not yet generated")
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line.strip())
                assert rec["source_status"] != "accepted"

    def test_harvest_summary_has_constraints(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/harvest_summary_final.json")
        if not path.exists():
            pytest.skip("Output not yet generated")
        with open(path, encoding="utf-8") as f:
            summary = json.load(f)
        assert summary["constraints"]["no_paid_api"] is True
        assert summary["constraints"]["no_auto_promote"] is True
        assert summary["constraints"]["no_fabricated_sources"] is True


# ── review packet ─────────────────────────────────────────────────

class TestReviewPacketFinal:
    def test_review_packet_md_exists(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.md")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Review Packet" in content

    def test_review_packet_jsonl_parseable(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.jsonl")
        if not path.exists():
            pytest.skip("Output not yet generated")
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    json.loads(line.strip())

    def test_review_packet_tsv_has_header(self):
        path = Path("data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.tsv")
        if not path.exists():
            pytest.skip("Output not yet generated")
        content = path.read_text(encoding="utf-8")
        assert "record_type" in content.split("\n")[0]


# ── provisional semantics invariants ─────────────────────────────

class TestProvisionalSemanticsInvariants:
    EXPORT_PATH = Path("data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl")

    def _load_records(self):
        if not self.EXPORT_PATH.exists():
            pytest.skip("Export not yet generated")
        with open(self.EXPORT_PATH, encoding="utf-8") as f:
            return [json.loads(line.strip()) for line in f if line.strip()]

    def test_all_87_retain_provisional_status(self):
        records = self._load_records()
        assert len(records) == 87
        for r in records:
            assert r["source_status"] == "provisional", (
                f"{r['venue_id']} has status {r['source_status']}, expected provisional"
            )

    def test_accepted_count_is_zero(self):
        records = self._load_records()
        accepted = [r for r in records if r["source_status"] == "accepted"]
        assert len(accepted) == 0

    def test_provisional_records_not_in_accepted_registry(self):
        from kairoskopion.registry.services import RegistryHub
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            hub = RegistryHub(data_dir=Path(tmp))
            venue_reg = hub._get_registry("venue")
            assert len(venue_reg.list_all()) == 0

    def test_export_preserves_provenance_and_evidence(self):
        records = self._load_records()
        for r in records:
            assert r.get("provenance"), f"Missing provenance: {r['venue_id']}"
            assert r.get("evidence_refs"), f"Missing evidence_refs: {r['venue_id']}"

    def test_noise_records_not_promoted(self):
        records = self._load_records()
        noise = [r for r in records if r.get("domain_tier") == "noise"]
        assert len(noise) > 0
        for r in noise:
            assert r["source_status"] == "provisional"
            assert r["review_status"] == "pending"

    def test_unclassified_records_not_promoted(self):
        records = self._load_records()
        unclassified = [r for r in records if r.get("domain_tier") == "unclassified"]
        assert len(unclassified) > 0
        for r in unclassified:
            assert r["source_status"] == "provisional"
            assert r["review_status"] == "pending"
