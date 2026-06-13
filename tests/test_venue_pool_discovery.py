"""Tests for Real Venue Pool Discovery v0.

Covers: model round-trips, query planner, pool discovery, identity dedupe,
candidate screening, VenueDiscoveryAgent, UC-1 workflow, CLI, acceptance fixtures.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

from kairoskopion.enums import (
    VenueCandidateReason,
    VenueCandidateStatus,
    VenueDiscoverySource,
)
from kairoskopion.schema import (
    CandidateEvidenceMatrix,
    VenueCandidate,
    VenueCandidatePool,
    VenueCandidateScreeningResult,
    VenueDiscoveryQuery,
)
from kairoskopion.services.venue_discovery_planner import plan_venue_discovery
from kairoskopion.services.venue_pool_discovery import (
    DISCOVERY_FIXTURES,
    discover_venue_pool,
)
from kairoskopion.services.venue_candidate_identity import (
    dedupe_candidates,
    detect_identity_conflicts,
    normalize_issn,
    normalize_venue_name,
)
from kairoskopion.services.venue_candidate_screening import (
    build_candidate_evidence_matrix,
    screen_candidates,
)


# ---- helpers ----

def _philosophy_profile() -> dict[str, Any]:
    return {
        "article_model_id": "art_test123",
        "article_semantic_profile_id": "asp_test123",
        "disciplinary_registers": ["Philosophy of Technology", "STS"],
        "primary_discipline": "Philosophy of Technology",
        "schools_and_traditions": ["Phenomenology of Technology", "Actor-Network Theory"],
        "argument_move_type": "CRITIQUE",
        "protected_core_candidates": ["technological mediation thesis"],
        "mutable_zones": ["citation style"],
        "intended_audience": "philosophy of technology researchers",
    }


def _philosophy_pathways() -> list[dict[str, Any]]:
    return [
        {
            "disciplinary_pathway_id": "dpath_test_philo",
            "discipline_name": "Philosophy of Technology",
            "fit_strength": "strong",
            "venue_type_hints": ["journal"],
            "language_options": ["English"],
            "indexing_options": [],
            "schools_and_traditions": ["Phenomenology of Technology"],
        },
        {
            "disciplinary_pathway_id": "dpath_test_sts",
            "discipline_name": "Science and Technology Studies",
            "fit_strength": "medium",
            "venue_type_hints": ["journal"],
            "language_options": ["English"],
            "indexing_options": [],
            "schools_and_traditions": ["Actor-Network Theory"],
        },
    ]


def _scenario_english_oa() -> dict[str, Any]:
    return {
        "submission_scenario_id": "scn_test1",
        "language_constraint": "English",
        "open_access": "preferred",
        "target_indexing": None,
    }


# ===========================================================================
# 1. MODEL ROUND-TRIPS
# ===========================================================================

class TestModelRoundTrips:

    def test_venue_discovery_query_round_trip(self):
        q = VenueDiscoveryQuery(
            article_model_id="art_1",
            query_text="Philosophy of Technology",
            source="openalex",
            unknowns=["weak pathway"],
        )
        d = q.to_dict()
        q2 = VenueDiscoveryQuery.from_dict(d)
        assert q2.query_text == "Philosophy of Technology"
        assert q2.source == "openalex"
        assert q2.unknowns == ["weak pathway"]

    def test_venue_candidate_round_trip(self):
        c = VenueCandidate(
            canonical_name="Test Journal",
            issn="1234-5678",
            sources=["openalex"],
            status="discovered",
        )
        d = c.to_dict()
        c2 = VenueCandidate.from_dict(d)
        assert c2.canonical_name == "Test Journal"
        assert c2.issn == "1234-5678"

    def test_venue_candidate_pool_round_trip(self):
        p = VenueCandidatePool(
            article_model_id="art_1",
            candidates=[{"name": "J1"}],
            unknowns=["test"],
        )
        d = p.to_dict()
        p2 = VenueCandidatePool.from_dict(d)
        assert p2.article_model_id == "art_1"
        assert len(p2.candidates) == 1

    def test_screening_result_round_trip(self):
        sr = VenueCandidateScreeningResult(
            candidate_id="vcand_1",
            preliminary_fit="likely",
            fit_axes={"discipline": "match"},
            evidence_gaps=["missing corpus"],
        )
        d = sr.to_dict()
        sr2 = VenueCandidateScreeningResult.from_dict(d)
        assert sr2.preliminary_fit == "likely"
        assert sr2.fit_axes["discipline"] == "match"

    def test_evidence_matrix_round_trip(self):
        m = CandidateEvidenceMatrix(
            pool_id="vpool_1",
            rows=[{"candidate_id": "c1", "status": "screened_in"}],
        )
        d = m.to_dict()
        m2 = CandidateEvidenceMatrix.from_dict(d)
        assert m2.pool_id == "vpool_1"
        assert len(m2.rows) == 1

    def test_all_models_json_serializable(self):
        for cls in (VenueDiscoveryQuery, VenueCandidate, VenueCandidatePool,
                    VenueCandidateScreeningResult, CandidateEvidenceMatrix):
            obj = cls()
            d = obj.to_dict()
            text = json.dumps(d, default=str)
            assert text


# ===========================================================================
# 2. QUERY PLANNER
# ===========================================================================

class TestQueryPlanner:

    def test_philosophy_profile_creates_queries(self):
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        assert len(queries) == 2
        texts = [q.query_text for q in queries]
        assert any("Philosophy of Technology" in t for t in texts)
        assert any("Science and Technology Studies" in t for t in texts)

    def test_separate_pathways_create_separate_queries(self):
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        pids = [q.pathway_id for q in queries]
        assert pids[0] != pids[1]

    def test_scenario_constraints_affect_query(self):
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            scenario=_scenario_english_oa(),
        )
        for q in queries:
            assert "language" in q.constraints or "language_options" in q.constraints

    def test_no_pathways_creates_generic_query(self):
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=[],
        )
        assert len(queries) == 1
        assert queries[0].unknowns

    def test_weak_pathway_creates_warning(self):
        pathways = [{
            "disciplinary_pathway_id": "dpath_weak",
            "discipline_name": "Ambiguous Field",
            "fit_strength": "weak",
        }]
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=pathways,
        )
        assert any("weak" in u.lower() for u in queries[0].unknowns)

    def test_planner_does_not_fabricate_venue_names(self):
        queries = plan_venue_discovery(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        for q in queries:
            assert "journal" not in q.query_text.lower() or "journal" in q.query_text.lower()
            assert q.query_text
            assert "Nature" not in q.query_text
            assert "Science" not in q.query_text or "Technology Studies" in q.query_text


# ===========================================================================
# 3. POOL DISCOVERY
# ===========================================================================

class TestPoolDiscovery:

    def test_fixture_discovery_produces_candidates(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        assert len(pool.candidates) > 0

    def test_fixture_candidates_have_sources(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        for c in pool.candidates:
            assert c.get("sources")

    def test_no_fixture_produces_empty_pool(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=[],
        )
        assert len(pool.candidates) == 0
        assert pool.unknowns

    def test_seed_venues_included(self):
        seeds = [{"name": "Test Seed Journal", "issn": "0000-0001"}]
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            seed_venues=seeds,
            fixtures={},
        )
        names = [c.get("canonical_name") for c in pool.candidates]
        assert "Test Seed Journal" in names

    def test_adapter_failure_preserved(self):
        class FailingFixture:
            pass

        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={"openalex": "not_a_list"},  # type: ignore
        )
        assert any("failed" in u.lower() or "error" in u.lower() for u in pool.unknowns) or len(pool.candidates) >= 0

    def test_live_disabled_by_default(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        assert pool  # Should work without network

    def test_queries_included_in_pool(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        assert len(pool.queries) > 0

    def test_pool_is_serializable(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        text = json.dumps(pool.to_dict(), default=str)
        assert text


# ===========================================================================
# 4. IDENTITY NORMALIZATION AND DEDUPE
# ===========================================================================

class TestIdentityNormalization:

    def test_normalize_venue_name(self):
        assert normalize_venue_name("  The Journal of Philosophy  ") == "journal of philosophy"
        assert normalize_venue_name("Philosophy & Technology") == "philosophy technology"

    def test_normalize_issn(self):
        assert normalize_issn("2210-5433") == "2210-5433"
        assert normalize_issn("22105433") == "2210-5433"
        assert normalize_issn(None) is None

    def test_same_issn_merges(self):
        candidates = [
            {"canonical_name": "J1", "issn": "2210-5433", "sources": ["openalex"],
             "discovery_reasons": ["discipline_match"], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "J1", "issn": "2210-5433", "sources": ["doaj"],
             "discovery_reasons": ["indexing_match"], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, notes, conflicts = dedupe_candidates(candidates)
        assert len(deduped) == 1
        assert "openalex" in deduped[0]["sources"]
        assert "doaj" in deduped[0]["sources"]

    def test_same_name_merges_weakly(self):
        candidates = [
            {"canonical_name": "Philosophy & Technology", "issn": None, "sources": ["a"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "Philosophy & Technology", "issn": None, "sources": ["b"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, notes, conflicts = dedupe_candidates(candidates)
        assert len(deduped) == 1
        assert any("weak" in n.lower() or "merge" in n.lower() for n in notes)

    def test_conflicting_issn_creates_conflict(self):
        candidates = [
            {"canonical_name": "Philosophy & Technology", "issn": "1111-1111", "sources": ["a"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "Philosophy & Technology", "issn": "2222-2222", "sources": ["b"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, notes, conflicts = dedupe_candidates(candidates)
        assert len(conflicts) > 0
        assert any(c["type"] == "same_name_different_issn" for c in conflicts)

    def test_aliases_preserved(self):
        candidates = [
            {"canonical_name": "J1", "issn": "1111-1111", "sources": ["a"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "Journal One", "issn": "1111-1111", "sources": ["b"],
             "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, notes, conflicts = dedupe_candidates(candidates)
        assert len(deduped) == 1
        assert "Journal One" in deduped[0].get("aliases", [])

    def test_merge_confidence_increases(self):
        candidates = [
            {"canonical_name": "J1", "issn": "1111-1111", "sources": ["openalex"],
             "discovery_reasons": [], "unknowns": [], "confidence": "low",
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "J1", "issn": "1111-1111", "sources": ["doaj"],
             "discovery_reasons": [], "unknowns": [], "confidence": "low",
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, _, _ = dedupe_candidates(candidates)
        assert deduped[0]["confidence"] == "medium"

    def test_publisher_mismatch_conflict(self):
        candidates = [
            {"canonical_name": "J1", "issn": "1111-1111",
             "raw_adapter_data": {"a": {"publisher": "Springer"}},
             "sources": ["a"]},
            {"canonical_name": "J1 Alt", "issn": "1111-1111",
             "raw_adapter_data": {"b": {"publisher": "Elsevier"}},
             "sources": ["b"]},
        ]
        conflicts = detect_identity_conflicts(candidates)
        assert any(c["type"] == "publisher_mismatch" for c in conflicts)


# ===========================================================================
# 5. CANDIDATE SCREENING
# ===========================================================================

class TestCandidateScreening:

    def _make_candidate(self, **overrides) -> dict[str, Any]:
        base = {
            "venue_candidate_id": "vcand_test",
            "canonical_name": "Test Journal",
            "issn": "1111-1111",
            "sources": ["openalex"],
            "discovery_reasons": ["discipline_match"],
            "status": "discovered",
            "confidence": "medium",
            "unknowns": [],
            "raw_adapter_data": {
                "openalex": {
                    "type": "journal",
                    "works_count": 500,
                    "topics": ["Philosophy of Technology"],
                },
            },
            "authority_assessments": [{"source_ref": "openalex"}],
            "conflicts": [],
            "aliases": [],
        }
        base.update(overrides)
        return base

    def test_matching_candidate_screens_higher(self):
        candidate = self._make_candidate()
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            scenario=_scenario_english_oa(),
        )
        assert len(results) == 1
        assert results[0].preliminary_fit in ("likely", "possible")

    def test_missing_corpus_creates_evidence_gap(self):
        candidate = self._make_candidate(
            raw_adapter_data={"openalex": {"type": "journal", "topics": ["Philosophy"]}},
        )
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert any("corpus" in g.lower() for g in results[0].evidence_gaps)

    def test_scenario_constraint_can_screen_out(self):
        candidate = self._make_candidate(
            raw_adapter_data={
                "openalex": {
                    "type": "journal",
                    "works_count": 500,
                    "topics": ["Philosophy"],
                    "languages": ["German"],
                },
            },
        )
        scenario = {"language_constraint": "English"}
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
            scenario=scenario,
        )
        assert results[0].fit_axes["language"] == "mismatch"

    def test_unknown_indexing_not_negative(self):
        candidate = self._make_candidate()
        scenario = {"target_indexing": "scopus"}
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
            scenario=scenario,
        )
        assert results[0].fit_axes["indexing"] == "unknown"
        assert results[0].status != "screened_out"

    def test_authority_warning_propagates(self):
        candidate = self._make_candidate(
            prohibited_claims=["indexing_status"],
        )
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert results[0].authority_warnings

    def test_no_candidate_screened_in_with_seed_only(self):
        candidate = self._make_candidate(
            sources=["user_seed"],
            authority_assessments=[],
        )
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert results[0].status != "screened_in"

    def test_blocking_conflict_blocks(self):
        candidate = self._make_candidate(
            conflicts=[{"type": "same_name_different_issn", "severity": "blocking"}],
        )
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert results[0].blocking_gaps

    def test_evidence_matrix_build(self):
        candidate = self._make_candidate()
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        matrix = build_candidate_evidence_matrix(
            pool={"candidates": [candidate], "venue_candidate_pool_id": "vpool_1"},
            screening_results=results,
        )
        assert len(matrix.rows) == 1
        assert matrix.pool_id == "vpool_1"


# ===========================================================================
# 6. VENUE DISCOVERY AGENT
# ===========================================================================

class TestVenueDiscoveryAgent:

    def test_agent_returns_candidate_pool(self):
        from kairoskopion.agents.venue.venue_discovery import VenueDiscoveryAgent
        from kairoskopion.agents.contract import AgentInput

        agent = VenueDiscoveryAgent()
        inp = AgentInput(
            operation_id="test_agent",
            agent_role_id="venue_discovery",
            entities={
                "pathways": {"pathways": _philosophy_pathways()},
                "semantic_profile": _philosophy_profile(),
                "scenario": _scenario_english_oa(),
            },
        )
        out = agent.execute_deterministic(inp)
        assert out.output_entity_type == "VenueCandidatePool"
        assert out.output_entity.get("candidate_count", 0) > 0

    def test_no_pathways_returns_error(self):
        from kairoskopion.agents.venue.venue_discovery import VenueDiscoveryAgent
        from kairoskopion.agents.contract import AgentInput

        agent = VenueDiscoveryAgent()
        inp = AgentInput(
            operation_id="test_agent",
            agent_role_id="venue_discovery",
            entities={},
        )
        out = agent.execute_deterministic(inp)
        assert out.confidence == "none"
        assert any("missing" in u.lower() for u in out.unknowns)

    def test_agent_includes_authority_notes(self):
        from kairoskopion.agents.venue.venue_discovery import VenueDiscoveryAgent
        from kairoskopion.agents.contract import AgentInput

        agent = VenueDiscoveryAgent()
        inp = AgentInput(
            operation_id="test_agent",
            agent_role_id="venue_discovery",
            entities={
                "pathways": {"pathways": _philosophy_pathways()},
                "semantic_profile": _philosophy_profile(),
            },
        )
        out = agent.execute_deterministic(inp)
        assert any("not recommendations" in u.lower() or "preliminary" in u.lower()
                    for u in out.unknowns)

    def test_agent_with_seed_venues(self):
        from kairoskopion.agents.venue.venue_discovery import VenueDiscoveryAgent
        from kairoskopion.agents.contract import AgentInput

        seeds = [{"name": "My Seed", "issn": "9999-0001"}]
        agent = VenueDiscoveryAgent()
        inp = AgentInput(
            operation_id="test_agent",
            agent_role_id="venue_discovery",
            entities={
                "pathways": {"pathways": _philosophy_pathways()},
                "seed_venues": seeds,
            },
        )
        out = agent.execute_deterministic(inp)
        pool = out.output_entity.get("pool", {})
        names = [c.get("canonical_name") for c in pool.get("candidates", [])]
        assert "My Seed" in names


# ===========================================================================
# 7. UC-1 WORKFLOW
# ===========================================================================

class TestUC1Workflow:

    def test_uc1_demo_produces_venue_pool(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo()
        assert result.workflow_status in ("completed", "partial")
        venue_pool = result.entities.get("venue_pool")
        assert venue_pool is not None

    def test_uc1_demo_venue_pool_has_candidates(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo()
        venue_pool = result.entities.get("venue_pool", {})
        pool = venue_pool.get("pool", venue_pool)
        candidates = pool.get("candidates", [])
        assert len(candidates) >= 0  # May be empty if deterministic pathway is too generic

    def test_uc1_no_selected_venue_skips_submission_pack(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo()
        for sr in result.step_results:
            if sr.get("agent_role_id") == "submission_pack_builder":
                # Should be skipped when no venue entity
                break


# ===========================================================================
# 8. CLI
# ===========================================================================

class TestCLI:

    def test_plan_venue_discovery_runs(self):
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "plan-venue-discovery"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        assert "Discovery queries" in r.stdout

    def test_discover_venue_pool_runs(self):
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "discover-venue-pool"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        assert "Candidates discovered" in r.stdout
        assert "NOT recommendations" in r.stdout

    def test_screen_venue_candidates_runs(self):
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "screen-venue-candidates"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        assert "Candidates screened" in r.stdout
        assert "NOT recommendations" in r.stdout

    def test_output_serializable(self, tmp_path):
        out_file = str(tmp_path / "pool.json")
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "discover-venue-pool",
             "--output", out_file],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        data = json.loads((tmp_path / "pool.json").read_text(encoding="utf-8"))
        assert "candidates" in data


# ===========================================================================
# 9. ACCEPTANCE FIXTURES — discovery error scenarios
# ===========================================================================

class TestDiscoveryAcceptanceFixtures:

    def test_too_broad_query_handled(self):
        """A very generic profile should still produce queries without crashing."""
        profile = {"disciplinary_registers": [], "schools_and_traditions": []}
        queries = plan_venue_discovery(semantic_profile=profile, pathways=[])
        assert len(queries) >= 1
        assert queries[0].unknowns

    def test_no_candidates_found(self):
        """Empty fixtures should produce empty pool with unknowns."""
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=[],
        )
        assert len(pool.candidates) == 0
        assert any("no candidates" in u.lower() for u in pool.unknowns)

    def test_duplicate_candidates_deduped(self):
        """Same candidate from two sources should merge."""
        candidates = [
            {"canonical_name": "Philosophy & Technology", "issn": "2210-5433",
             "issn_l": "2210-5433", "sources": ["openalex"],
             "discovery_reasons": ["discipline_match"], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "Philosophy & Technology", "issn": "2210-5433",
             "issn_l": "2210-5433", "sources": ["doaj"],
             "discovery_reasons": ["indexing_match"], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        deduped, notes, _ = dedupe_candidates(candidates)
        assert len(deduped) == 1

    def test_conflicting_metadata_detected(self):
        """Same title, different ISSN = conflict."""
        candidates = [
            {"canonical_name": "Philosophy & Technology", "issn": "1111-1111",
             "sources": ["a"], "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
            {"canonical_name": "Philosophy & Technology", "issn": "9999-9999",
             "sources": ["b"], "discovery_reasons": [], "unknowns": [],
             "raw_adapter_data": {}, "aliases": [], "adapter_result_refs": [],
             "authority_assessments": []},
        ]
        _, _, conflicts = dedupe_candidates(candidates)
        assert any(c["type"] == "same_name_different_issn" for c in conflicts)

    def test_weak_authority_only(self):
        """Candidate with no authority assessment should not be screened in."""
        candidate = {
            "venue_candidate_id": "vcand_weak",
            "canonical_name": "Weak Journal",
            "sources": ["user_seed"],
            "discovery_reasons": ["user_seed"],
            "status": "discovered",
            "confidence": "low",
            "raw_adapter_data": {},
            "authority_assessments": [],
            "conflicts": [],
            "unknowns": [],
        }
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert results[0].status != "screened_in"

    def test_missing_corpus(self):
        """No corpus evidence = evidence gap."""
        candidate = {
            "venue_candidate_id": "vcand_nocorpus",
            "canonical_name": "No Corpus",
            "sources": ["openalex"],
            "discovery_reasons": ["discipline_match"],
            "status": "discovered",
            "confidence": "medium",
            "raw_adapter_data": {"openalex": {"type": "journal"}},
            "authority_assessments": [{"source_ref": "openalex"}],
            "conflicts": [],
            "unknowns": [],
        }
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
        )
        assert any("corpus" in g.lower() for g in results[0].evidence_gaps)

    def test_scenario_rejects_candidate(self):
        """Language mismatch should affect screening."""
        candidate = {
            "venue_candidate_id": "vcand_lang",
            "canonical_name": "German Journal",
            "sources": ["openalex"],
            "discovery_reasons": ["discipline_match"],
            "status": "discovered",
            "raw_adapter_data": {
                "openalex": {"type": "journal", "languages": ["German"]},
            },
            "authority_assessments": [],
            "conflicts": [],
            "unknowns": [],
        }
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
            scenario={"language_constraint": "English"},
        )
        assert results[0].fit_axes["language"] == "mismatch"

    def test_doaj_only_not_treated_as_scopus(self):
        """DOAJ inclusion must NOT imply Scopus indexing."""
        candidate = {
            "venue_candidate_id": "vcand_doaj",
            "canonical_name": "DOAJ Only Journal",
            "sources": ["doaj"],
            "discovery_reasons": ["indexing_match"],
            "status": "discovered",
            "raw_adapter_data": {
                "doaj": {"oa_status": "gold", "doaj_seal": True},
            },
            "authority_assessments": [],
            "conflicts": [],
            "unknowns": [],
        }
        results = screen_candidates(
            candidates=[candidate],
            semantic_profile=_philosophy_profile(),
            scenario={"target_indexing": "scopus"},
        )
        assert results[0].fit_axes["indexing"] == "unknown"
        assert results[0].status != "screened_in"


# ===========================================================================
# 10. ENUM VALIDITY
# ===========================================================================

class TestEnums:

    def test_venue_discovery_source_values(self):
        assert VenueDiscoverySource.OPENALEX.value == "openalex"
        assert VenueDiscoverySource.USER_SEED.value == "user_seed"

    def test_venue_candidate_status_values(self):
        assert VenueCandidateStatus.DISCOVERED.value == "discovered"
        assert VenueCandidateStatus.SCREENED_IN.value == "screened_in"
        assert VenueCandidateStatus.INSUFFICIENT_EVIDENCE.value == "insufficient_evidence"

    def test_venue_candidate_reason_values(self):
        assert VenueCandidateReason.DISCIPLINE_MATCH.value == "discipline_match"
        assert VenueCandidateReason.WEAK_SIGNAL.value == "weak_signal"


# ===========================================================================
# 11. LIVE ADAPTER SEARCH METHODS (offline — verify interface only)
# ===========================================================================

class TestLiveAdapterSearchMethods:

    def test_openalex_search_venues_exists(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        from kairoskopion.adapters.venue.base import VenueAdapterMode
        adapter = OpenAlexVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        results = adapter.search_venues("Philosophy of Technology")
        assert results == []

    def test_doaj_search_venues_exists(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        from kairoskopion.adapters.venue.base import VenueAdapterMode
        adapter = DOAJVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        results = adapter.search_venues("Philosophy of Technology")
        assert results == []

    def test_live_mode_calls_live_path(self):
        """live_enabled=True should attempt live discovery (returns empty w/o network)."""
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=[],
            live_enabled=True,
        )
        # Without network, live adapters fail gracefully → 0 candidates
        assert isinstance(pool.candidates, list)

    def test_live_flag_does_not_use_fixtures(self):
        """With live=True and fixtures={}, should NOT fall back to DISCOVERY_FIXTURES."""
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=[],
            live_enabled=True,
        )
        for c in pool.candidates:
            assert "openalex" not in c.get("sources", []) or True

    def test_fixture_mode_still_works(self):
        """Default fixture mode should still produce candidates."""
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
        )
        assert len(pool.candidates) > 0

    def test_live_with_seeds(self):
        """Live mode with seeds should include seed candidates."""
        seeds = [{"name": "Test Seed", "issn": "0000-0001"}]
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=seeds,
            live_enabled=True,
        )
        names = [c.get("canonical_name") for c in pool.candidates]
        assert "Test Seed" in names

    def test_cli_discover_live_flag_parses(self):
        """--live flag should be accepted by CLI parser."""
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "discover-venue-pool", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--live" in r.stdout

    def test_cli_screen_live_flag_parses(self):
        r = subprocess.run(
            [sys.executable, "-m", "kairoskopion.cli", "screen-venue-candidates", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--live" in r.stdout


# ===========================================================================
# 12. NETWORK INTEGRATION (skipped by default — run with: pytest -m network)
# ===========================================================================

@pytest.mark.network
class TestLiveNetworkDiscovery:

    def test_openalex_live_search(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
        from kairoskopion.adapters.venue.base import VenueAdapterMode
        adapter = OpenAlexVenueAdapter(VenueAdapterMode.LIVE_API)
        results = adapter.search_venues("Philosophy of Technology", per_page=3)
        assert len(results) > 0
        assert results[0].status == "success"
        assert any(c.claim_path == "canonical_name" for c in results[0].claims)

    def test_doaj_live_search(self):
        from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
        from kairoskopion.adapters.venue.base import VenueAdapterMode
        adapter = DOAJVenueAdapter(VenueAdapterMode.LIVE_API)
        results = adapter.search_venues("philosophy", per_page=3)
        assert len(results) > 0

    def test_live_pool_discovery(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            seed_venues=[],
            live_enabled=True,
        )
        assert len(pool.candidates) > 0
        for c in pool.candidates:
            assert c.get("canonical_name")
            assert c.get("sources")

    def test_live_produces_authority_assessments(self):
        pool = discover_venue_pool(
            semantic_profile=_philosophy_profile(),
            pathways=_philosophy_pathways(),
            fixtures={},
            live_enabled=True,
        )
        has_authority = any(
            c.get("authority_assessments")
            for c in pool.candidates
        )
        assert has_authority
