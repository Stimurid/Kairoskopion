"""Cross-axis contract: a research selection is not an Article or submission."""
import copy

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.kairon_provider.opportunity_execution_handoff import (
    prepare_opportunity_execution_handoff,
)
from kairoskopion.kairon_provider.target_world_catalog import _digest as target_digest


def graph(tmp_path, *, record_author=True, consent=True):
    store = OpportunityGraphStore(tmp_path)
    store.put("ArticleSeed", {
        "id": "MAI-E", "revision": "r1", "source_ref": "gdoc:mai-e",
        "author_authority": "ARTIKL", "author_ref": "author:owner",
        "protected_core": ["academic-agency"], "coauthor_consent_required": True,
        "coauthor_consent_verified": consent,
    })
    store.put("ArticleOpportunity", {
        "id": "op-e-1", "revision": "r1", "seed_id": "MAI-E",
        "scholarly_problem": "changes in academic judgment",
        "independent_claim": "distinct original argument",
        "author_decision": "ACCEPT",
    })
    store.put("Journal", {
        "id": "j-e", "revision": "r1", "canonical_name": "Example venue",
        "official_url": "https://journal.example",
    })
    store.put("OpportunityRoute", {
        "id": "route-e", "revision": "r1",
        "journal_id": "j-e", "opportunity_id": "op-e-1",
        "route_type": "FORMAL_ABSTRACT_CFP",
        "deadline": "2026-12-20", "deadline_stage": "FORMAL_ABSTRACT_CFP",
        "policy_evidence_ids": ["policy"],
        "submission_channel_kind": "OFFICIAL_FORM",
        "target_world_version": "world:123",
        "target_world_package_id": "world:123@sha",
    })
    store.put("VenueWorld", {
        "id": "venue-e", "revision": "r1", "journal_id": "j-e",
        "target_world_version": "world:123",
        "published_example_evidence_ids": ["p1", "p2", "p3"],
    })
    store.put("TargetVariant", {
        "id": "variant-e", "revision": "r1", "seed_id": "MAI-E",
        "opportunity_id": "op-e-1", "target_world_version": "world:123",
        "target_world_package_id": "world:123@sha",
    })
    store.put("Evidence", {
        "id": "policy", "revision": "r1",
        "source_ref": "https://journal.example/cfp",
        "source_kind": "OFFICIAL_CFP", "official": True,
        "read_depth": "FULL_TEXT", "passage_anchors": ["section-proposals"],
    })
    for i in (1, 2, 3):
        store.put("Evidence", {
            "id": f"p{i}", "revision": "r1",
            "source_ref": f"doi:p{i}", "source_kind": "PUBLISHED_ARTICLE",
            "read_depth": "FULL_TEXT", "passage_anchors": [f"argument-{i}"],
        })
    if record_author:
        store.append_event({
            "event_id": "author:select:e1", "kind": "AUTHOR_DECISION",
            "actor_role": "AUTHOR", "author_ref": "author:owner",
            "subject_id": "op-e-1", "opportunity_revision": "r1",
            "route_id": "route-e", "route_revision": "r1",
            "variant_id": "variant-e", "variant_revision": "r1",
            "decision": "ACCEPT", "source_ref": "author:decision-log",
        })
    pins = {
        "seed": {"id": "MAI-E", "revision": "r1"},
        "opportunity": {"id": "op-e-1", "revision": "r1"},
        "journal": {"id": "j-e", "revision": "r1"},
        "route": {"id": "route-e", "revision": "r1"},
        "variant": {"id": "variant-e", "revision": "r1"},
        "world": {"id": "venue-e", "revision": "r1"},
    }
    snapshot = {"snapshot_id": "world:123", "target_id": "j-e"}
    package = {
        "package_id": "world:123@sha", "snapshot": snapshot,
        "content_digest": target_digest(snapshot), "status": "PROD_ACCEPTED",
    }
    return store, pins, package


def handoff(store, pins, package, *, event="author:select:e1"):
    return prepare_opportunity_execution_handoff(
        store, pins=pins,
        author_selection_event_id=event,
        target_world_package=package,
    )


def test_pinned_candidate_is_deterministic_and_never_runs_article_factory(tmp_path):
    store, pins, package = graph(tmp_path)
    first = handoff(store, pins, package)
    assert first == handoff(store, pins, package)
    assert first["status"] == "CANDIDATE_FOR_ARTIKL_REVIEW"
    assert first["next_actor"] == "ARTIKL_REVIEW"
    assert first["authoritative_sibling"] is None
    assert first["publication_runner_manifest"] is None
    assert first["finalization_request"] is None
    assert first["article_created"] is False
    assert first["external_submission"] == "FORBIDDEN"
    assert first["qa_pass_claim"] is False


def test_author_claim_without_event_is_not_approval(tmp_path):
    store, pins, package = graph(tmp_path, record_author=False)
    result = handoff(store, pins, package)
    assert result["status"] == "BLOCKED"
    assert "author_selection_event_missing" in result["blockers"]


def test_coauthor_consent_remains_distinct_from_author_selection(tmp_path):
    store, pins, package = graph(tmp_path, consent=False)
    result = handoff(store, pins, package)
    assert "coauthor_consent_missing" in result["blockers"]


def test_target_catalog_status_and_digest_are_separate_gates(tmp_path):
    store, pins, package = graph(tmp_path)
    invalid = {**package, "status": "QUALIFIED_DEV"}
    assert "target_world_not_prod_accepted" in handoff(store, pins, invalid)["blockers"]
    stale = {**package, "content_digest": "0" * 64}
    assert "target_world_digest_mismatch" in handoff(store, pins, stale)["blockers"]


def test_unpinned_revision_and_cross_journal_id_fail_closed(tmp_path):
    store, pins, package = graph(tmp_path)
    bad = copy.deepcopy(pins)
    bad["route"]["revision"] = "not-present"
    assert "unknown_pinned_record:route" in handoff(store, bad, package)["blockers"]
    bad = copy.deepcopy(pins)
    bad["journal"]["id"] = "other"
    assert "unknown_pinned_record:journal" in handoff(store, bad, package)["blockers"]


def test_conflicting_evidence_revision_cannot_be_silently_promoted(tmp_path):
    store, pins, package = graph(tmp_path)
    store.put("Evidence", {
        "id": "policy", "revision": "r2",
        "source_ref": "https://journal.example/replaced-cfp",
        "source_kind": "OFFICIAL_CFP", "official": True,
        "read_depth": "ABSTRACT", "passage_anchors": [],
    })
    result = handoff(store, pins, package)
    assert "ambiguous_evidence_revision:policy" in result["blockers"]
    assert result["status"] == "BLOCKED"


def test_agent_forged_selection_event_does_not_approve(tmp_path):
    store, pins, package = graph(tmp_path, record_author=False)
    store.append_event({
        "event_id": "author:select:e1", "kind": "AUTHOR_DECISION",
        "actor_role": "AGENT", "author_ref": "author:owner",
        "subject_id": "op-e-1", "opportunity_revision": "r1",
        "route_id": "route-e", "route_revision": "r1",
        "variant_id": "variant-e", "variant_revision": "r1",
        "decision": "ACCEPT", "source_ref": "agent:decision-log",
    })
    result = handoff(store, pins, package)
    assert "author_selection_lineage_or_authority_mismatch" in result["blockers"]


def test_variant_revision_pinned_to_wrong_venue_world_is_blocked(tmp_path):
    store, pins, package = graph(tmp_path)
    store.put("TargetVariant", {
        "id": "variant-e", "revision": "r2", "seed_id": "MAI-E",
        "opportunity_id": "op-e-1", "target_world_version": "world:old",
        "target_world_package_id": "world:123@sha",
    })
    bad = copy.deepcopy(pins)
    bad["variant"]["revision"] = "r2"
    result = handoff(store, bad, package)
    assert "variant_world_version_mismatch" in result["blockers"]


def test_absent_frozen_target_package_blocks_even_fully_grounded_route(tmp_path):
    store, pins, _ = graph(tmp_path)
    result = handoff(store, pins, None)
    assert result["status"] == "BLOCKED"
    assert "frozen_target_world_package_missing" in result["blockers"]


def test_pending_owner_science_cannot_forge_author_event(tmp_path):
    store, pins, package = graph(tmp_path, record_author=False)
    store.append_event({
        "event_id": "author:select:e1", "kind": "AUTHOR_DECISION",
        "actor_role": "AUTHOR", "author_ref": "author:owner",
        "subject_id": "op-e-1", "opportunity_revision": "r1",
        "route_id": "route-e", "route_revision": "r1",
        "variant_id": "variant-e", "variant_revision": "r1",
        "decision": "ACCEPT", "source_ref": "owner-private:pending",
        "owner_prior_receipt_case": "L3-CORPUS-20261020",
    })
    assert len(store.replay_events()) == 1
    result = handoff(store, pins, package)
    assert "author_selection_event_missing" in result["blockers"]
    assert result["external_submission"] == "FORBIDDEN"
