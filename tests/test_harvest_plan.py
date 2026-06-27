"""Tests for harvest_plan (P7.3 Track 3/12)."""

import json
import pytest
from pathlib import Path

from kairoskopion.services.harvest_plan import (
    HarvestTask,
    HarvestPlan,
    build_authority_harvest_plan,
    persist_harvest_plan,
    HARVEST_TASK_TYPES,
    HARVEST_TASK_STATUSES,
)


# ---------------------------------------------------------------------------
# HarvestTask model tests
# ---------------------------------------------------------------------------

class TestHarvestTaskModel:
    def test_create_default(self):
        task = HarvestTask()
        assert task.task_id.startswith("htask_")
        assert task.status == "planned"
        assert task.task_type == "manual_web_lookup"

    def test_create_with_fields(self):
        task = HarvestTask(
            task_type="fetch_venue_by_issn",
            authority_id="srcauth_123",
            authority_name="OpenAlex",
            adapter_hint="openalex",
            query="ISSN 1234-5678",
            status="ready",
        )
        assert task.task_type == "fetch_venue_by_issn"
        assert task.authority_name == "OpenAlex"
        assert task.status == "ready"

    def test_to_dict_roundtrip(self):
        task = HarvestTask(
            task_type="ingest_local_evidence_pack",
            expected_outputs=["venue_records", "metrics"],
            warnings=["test warning"],
        )
        d = task.to_dict()
        assert isinstance(d, dict)
        restored = HarvestTask.from_dict(d)
        assert restored.task_type == task.task_type
        assert restored.expected_outputs == task.expected_outputs
        assert restored.warnings == task.warnings

    def test_to_dict_omits_none(self):
        task = HarvestTask()
        d = task.to_dict()
        assert "authority_id" not in d
        assert "blocked_reason" not in d

    def test_all_task_types_valid(self):
        for tt in HARVEST_TASK_TYPES:
            task = HarvestTask(task_type=tt)
            assert task.task_type == tt

    def test_all_statuses_valid(self):
        for s in HARVEST_TASK_STATUSES:
            task = HarvestTask(status=s)
            assert task.status == s


# ---------------------------------------------------------------------------
# HarvestPlan model tests
# ---------------------------------------------------------------------------

class TestHarvestPlanModel:
    def test_create_empty(self):
        plan = HarvestPlan()
        assert plan.tasks == []
        assert plan.ready_count == 0

    def test_to_dict(self):
        plan = HarvestPlan(
            plan_id="plan_abc",
            target_country="RU",
            tasks=[HarvestTask(task_type="ingest_discipline_seed")],
        )
        d = plan.to_dict()
        assert d["plan_id"] == "plan_abc"
        assert len(d["tasks"]) == 1


# ---------------------------------------------------------------------------
# Plan builder tests
# ---------------------------------------------------------------------------

SAMPLE_AUTHORITIES = [
    {
        "authority_id": "srcauth_001",
        "authority_name": "OpenAlex",
        "authority_type": "citation_database",
        "country": "INTERNATIONAL",
        "adapter_hint": "openalex",
    },
    {
        "authority_id": "srcauth_002",
        "authority_name": "VAK journal list",
        "authority_type": "national_journal_registry",
        "country": "RU",
        "adapter_hint": "manual_url",
    },
    {
        "authority_id": "srcauth_003",
        "authority_name": "Scopus",
        "authority_type": "metric_source",
        "country": "INTERNATIONAL",
        "adapter_hint": "scopus",
    },
    {
        "authority_id": "srcauth_004",
        "authority_name": "DOAJ",
        "authority_type": "national_journal_registry",
        "country": "INTERNATIONAL",
        "adapter_hint": "doaj",
    },
    {
        "authority_id": "srcauth_005",
        "authority_name": "Argentine CONICET",
        "authority_type": "national_journal_registry",
        "country": "AR",
        "adapter_hint": "manual_url",
    },
]


class TestBuildHarvestPlan:
    def test_builds_plan(self):
        plan = build_authority_harvest_plan(
            SAMPLE_AUTHORITIES,
            target_country="RU",
        )
        assert plan.plan_id.startswith("plan_")
        assert len(plan.tasks) > 0

    def test_free_adapters_ready(self):
        plan = build_authority_harvest_plan(SAMPLE_AUTHORITIES)
        openalex_tasks = [
            t for t in plan.tasks if t.authority_name == "OpenAlex"
        ]
        assert all(t.status == "ready" for t in openalex_tasks)

    def test_paid_adapters_blocked_when_no_paid(self):
        plan = build_authority_harvest_plan(
            SAMPLE_AUTHORITIES,
            no_paid_api=True,
        )
        scopus_tasks = [
            t for t in plan.tasks if t.authority_name == "Scopus"
        ]
        assert all(t.status == "blocked" for t in scopus_tasks)

    def test_paid_adapters_ready_when_paid_allowed(self):
        plan = build_authority_harvest_plan(
            SAMPLE_AUTHORITIES,
            no_paid_api=False,
        )
        scopus_tasks = [
            t for t in plan.tasks if t.authority_name == "Scopus"
        ]
        assert all(t.status == "ready" for t in scopus_tasks)

    def test_manual_url_planned(self):
        plan = build_authority_harvest_plan(SAMPLE_AUTHORITIES)
        vak_tasks = [
            t for t in plan.tasks if t.authority_name == "VAK journal list"
        ]
        assert all(t.status == "planned" for t in vak_tasks)

    def test_filters_by_country(self):
        plan = build_authority_harvest_plan(
            SAMPLE_AUTHORITIES,
            target_country="RU",
        )
        # Argentine authority should NOT appear in RU plan
        ar_tasks = [
            t for t in plan.tasks
            if t.authority_name == "Argentine CONICET"
        ]
        assert ar_tasks == []

    def test_local_evidence_packs_highest_priority(self, tmp_path: Path):
        d = tmp_path / "packs"
        d.mkdir()
        (d / "test_evidence_pack.md").write_text("# Test", encoding="utf-8")

        plan = build_authority_harvest_plan(
            SAMPLE_AUTHORITIES,
            evidence_pack_dir=d,
        )
        local_tasks = [
            t for t in plan.tasks
            if t.task_type == "ingest_local_evidence_pack"
        ]
        assert len(local_tasks) == 1
        assert local_tasks[0].priority == "high"
        assert local_tasks[0].status == "ready"
        # Should be first in sorted list
        assert plan.tasks[0].task_type == "ingest_local_evidence_pack"

    def test_discipline_seed_task(self, tmp_path: Path):
        seed = tmp_path / "ru_seed.jsonl"
        seed.write_text("{}\n", encoding="utf-8")

        plan = build_authority_harvest_plan(
            [],
            discipline_seed_path=seed,
        )
        disc_tasks = [
            t for t in plan.tasks
            if t.task_type == "ingest_discipline_seed"
        ]
        assert len(disc_tasks) == 1
        assert disc_tasks[0].status == "ready"

    def test_empty_authorities(self):
        plan = build_authority_harvest_plan([])
        assert plan.tasks == []

    def test_counts_accurate(self):
        plan = build_authority_harvest_plan(SAMPLE_AUTHORITIES)
        ready = sum(1 for t in plan.tasks if t.status == "ready")
        blocked = sum(1 for t in plan.tasks if t.status == "blocked")
        assert plan.ready_count == ready
        assert plan.blocked_count == blocked


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_persist_plan(self, tmp_path: Path):
        plan = build_authority_harvest_plan(SAMPLE_AUTHORITIES)
        out = tmp_path / "harvest_plan.jsonl"
        persist_harvest_plan(plan, out)

        assert out.exists()
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == len(plan.tasks)

        for line in lines:
            d = json.loads(line)
            assert "task_id" in d
            assert "task_type" in d

    def test_persist_creates_parent_dir(self, tmp_path: Path):
        plan = HarvestPlan(tasks=[HarvestTask()])
        out = tmp_path / "sub" / "dir" / "plan.jsonl"
        persist_harvest_plan(plan, out)
        assert out.exists()
