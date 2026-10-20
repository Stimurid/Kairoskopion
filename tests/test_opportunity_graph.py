"""Fail-closed tests for Indago W12 opportunity substrate (CODE_ONLY, no W12 data)."""
import hashlib
from io import BytesIO
from zipfile import ZipFile

import pytest

from kairoskopion.kairon_provider.opportunity_graph import (
    OpportunityGraphStore,
    assess_route,
    inspect_w12_workbook,
    validate_record,
    venue_world_status,
)


def evidence():
    items = {
        "policy": {
            "id": "policy", "revision": "r1", "source_ref": "https://journal.example/rules",
            "kind": "OFFICIAL_CFP", "official": True, "read_depth": "SECTIONS",
            "passage_anchors": ["section:abstract-stage"],
        },
    }
    for i in (1, 2, 3):
        items[f"example-{i}"] = {
            "id": f"example-{i}", "revision": "r1",
            "kind": "PUBLISHED_ARTICLE",
            "source_ref": f"https://journal.example/volume/2026/{i}",
            "read_depth": "FULL_TEXT", "passage_anchors": [f"paragraph:{i}"],
        }
    return items


def world():
    return {
        "id": "venue-world-1", "revision": "r1", "journal_id": "journal-1",
        "target_world_version": "world@r1",
        "published_example_evidence_ids": ["example-1", "example-2", "example-3"],
    }


def route(**changes):
    value = {
        "id": "route-1", "revision": "r1", "journal_id": "journal-1",
        "opportunity_id": "opportunity-1",
        "route_type": "FORMAL_ABSTRACT_CFP",
        "deadline": "2026-12-20",
        "deadline_stage": "FORMAL_ABSTRACT_CFP",
        "submission_channel_kind": "OFFICIAL_FORM",
        "submission_channel_ref": "https://journal.example/proposal",
        "policy_evidence_ids": ["policy"],
    }
    value.update(changes)
    return value


def test_source_read_depth_must_be_explicit():
    with pytest.raises(ValueError, match="read_depth"):
        validate_record("Evidence", {
            "id": "a", "revision": "1", "source_ref": "https://example.test/a",
        })


def test_journal_discovery_candidate_rejects_canonical_official_url(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    store.put("JournalDiscoveryCandidate", {
        "id": "journal-cand-1",
        "revision": "1",
        "canonical_name": "Candidate Journal",
        "research_status": "PROVISIONAL_DISCOVERY",
        "official_author_policy_status": "UNRESOLVED",
    })
    with pytest.raises(ValueError, match="must not assert canonical official_url"):
        store.put("JournalDiscoveryCandidate", {
            "id": "journal-cand-2",
            "revision": "1",
            "canonical_name": "Bad Candidate",
            "official_url": "https://example.test/policy",
        })


def test_a_journal_is_not_a_special_issue_and_has_a_stable_identity(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    journal = {
        "id": "journal-1", "revision": "1",
        "canonical_name": "Test Journal",
        "issn": "1234-5678", "official_url": "https://journal.example",
    }
    assert store.put("Journal", journal) == store.put("Journal", journal)
    store.put("JournalIssue", {
        "id": "journal-issue-2027", "revision": "1", "journal_id": "journal-1",
        "official_url": "https://journal.example/special-issue",
    })
    with pytest.raises(ValueError, match="journal identity"):
        store.put("Journal", {**journal, "id": "duplicate-id"})


def test_separate_opportunity_does_not_inflate_article_identities(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    seed = store.put("ArticleSeed", {
        "id": "MAI-A", "revision": "r1", "source_ref": "gdoc:seed-a",
        "author_authority": "ARTIKL", "protected_core": ["thesis-a"],
    })
    one = store.put("ArticleOpportunity", {
        "id": "opp-a-1", "revision": "r1", "seed_id": "MAI-A",
        "scholarly_problem": "first problem", "independent_claim": "first",
    })
    two = store.put("ArticleOpportunity", {
        "id": "opp-a-2", "revision": "r1", "seed_id": "MAI-A",
        "scholarly_problem": "second problem", "independent_claim": "second",
    })
    assert seed["id"] == one["seed_id"] == two["seed_id"]
    assert one["id"] != two["id"]
    assert store.get("ArticleSeed", "MAI-A", "r1") == seed


def test_world_needs_three_anchored_full_read_published_exemplars():
    e = evidence()
    assert venue_world_status(world(), e) == "FULL_EVIDENCE"
    e["example-3"] = {**e["example-3"], "read_depth": "ABSTRACT"}
    assert venue_world_status(world(), e) == "PARTIAL_EVIDENCE"
    e["example-3"] = {**e["example-3"], "read_depth": "FULL_TEXT", "passage_anchors": []}
    assert venue_world_status(world(), e) == "PARTIAL_EVIDENCE"
    e["example-3"] = {**e["example-3"], "kind": "OFFICIAL_POLICY", "passage_anchors": ["x"]}
    assert venue_world_status(world(), e) == "PARTIAL_EVIDENCE"


def test_route_distinguishes_real_cfp_from_unverified_policy():
    e = evidence()
    accepted = assess_route(route(), e, world(), author_decision="ACCEPT")
    assert accepted["status"] == "AUTHOR_APPROVED_FOR_REVIEW"
    assert accepted["external_action"] == "NOT_SENT"
    e["policy"] = {**e["policy"], "kind": "OFFICIAL_POLICY"}
    blocked = assess_route(route(), e, world(), author_decision="ACCEPT")
    assert "formal_cfp_not_verified" in blocked["blockers"]


def test_no_generic_editorial_email_or_forged_fulltext():
    blocked = assess_route(
        route(submission_channel_kind="GENERIC_EMAIL"),
        evidence(), world(), author_decision="ACCEPT",
    )
    assert "unverified_editorial_channel" in blocked["blockers"]
    e = evidence()
    e["example-1"] = {**e["example-1"], "read_depth": "INDEX_ONLY"}
    blocked = assess_route(route(), e, world(), author_decision="ACCEPT")
    assert "venue_world_partial_evidence" in blocked["blockers"]


def test_author_and_coauthor_gates_are_separate():
    e = evidence()
    held = assess_route(route(), e, world(), author_decision="HOLD")
    assert "author_decision_pending" in held["blockers"]
    no_consent = assess_route(
        route(), e, world(), author_decision="ACCEPT", coauthor_consent=False
    )
    assert "coauthor_consent_missing" in no_consent["blockers"]


def test_deadline_is_bound_to_correct_editorial_stage():
    with pytest.raises(ValueError, match="deadline_stage"):
        validate_record("OpportunityRoute", route(deadline_stage="FULL_MANUSCRIPT_ONLY"))


def test_route_type_policy_unverified_fails_closed():
    blocked = assess_route(
        route(route_type="POLICY_UNVERIFIED", deadline_stage="POLICY_UNVERIFIED"),
        evidence(), world(), author_decision="ACCEPT",
    )
    assert "route_policy_unverified" in blocked["blockers"]


def test_record_versions_and_event_ids_are_immutable(tmp_path):
    s = OpportunityGraphStore(tmp_path)
    original = {"id": "MAI-A", "revision": "1", "source_ref": "gdoc:one", "author_authority": "ARTIKL"}
    assert s.put("ArticleSeed", original) == s.put("ArticleSeed", original)
    with pytest.raises(ValueError, match="immutable identity"):
        s.put("ArticleSeed", {**original, "source_ref": "gdoc:different"})
    assert s.put("ArticleSeed", {**original, "revision": "2"})["revision"] == "2"
    event = {
        "event_id": "W12:T1", "kind": "HUNT_RESULT",
        "subject_id": "opp-a-1", "source_ref": "official:journal:2026",
        "at": "2026-10-13T00:00:00Z", "result": "REJECTED_UNVERIFIED_CFP",
        "intellectual_consequence": "no live formal CFP can be claimed",
        "next_action": "verify official policy or reject route",
    }
    assert s.append_event(event) == s.append_event(event)
    assert len(s.replay_events()) == 1
    with pytest.raises(ValueError, match="immutable identity"):
        s.append_event({**event, "result": "ACCEPTED"})


def test_w12_metadata_is_not_a_successful_byte_import():
    result = inspect_w12_workbook(None)
    assert result["status"] == "BLOCKED_SOURCE_BYTES_UNAVAILABLE"
    assert result["expected_counts_unverified"]["editorial_routes"] == 53
    assert result["imported_records"] == 0


def test_w12_corrupted_bytes_and_wrong_digest_are_not_admitted():
    with pytest.raises(ValueError, match="sha256"):
        inspect_w12_workbook(b"bad-zip", expected_sha256="f" * 64)
    with pytest.raises(ValueError, match="xlsx"):
        inspect_w12_workbook(b"bad-zip")


def test_ooxml_byte_verification_does_not_silently_claim_row_import():
    xml = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="01 Начало" sheetId="1"/></sheets></workbook>'
    )
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", xml)
    raw = buf.getvalue()
    result = inspect_w12_workbook(raw, hashlib.sha256(raw).hexdigest())
    assert result["status"] == "SOURCE_BYTES_VERIFIED_MAPPING_PENDING"
    assert result["sheet_names"] == ["01 Начало"]
    assert result["imported_records"] == 0


def test_packet_never_pretends_to_be_sent():
    with pytest.raises(ValueError, match="external submission"):
        validate_record("EditorialPacket", {
            "id": "p", "revision": "1", "route_id": "route-1",
            "send_status": "SENT",
        })


def test_negative_discovery_cannot_disappear_without_intellectual_consequence(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    negative = {
        "event_id": "W12:NEG2", "kind": "HUNT_RESULT",
        "subject_id": "MAI-A", "source_ref": "doi:source",
        "result": "REJECTED_NOVELTY",
        "next_action": "revisit underlying claim",
    }
    with pytest.raises(ValueError, match="intellectual_consequence"):
        store.append_event(negative)
    with pytest.raises(ValueError, match="next_action"):
        store.append_event({
            **negative,
            "intellectual_consequence": "rival already established the previous result",
            "next_action": "",
        })


def test_reopen_is_a_proposal_not_a_silent_change_to_protected_core(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    seed = {
        "id": "MAI-A", "revision": "r1",
        "source_ref": "gdoc:original", "author_authority": "ARTIKL",
        "protected_core": ["institutional judgment"],
    }
    store.put("ArticleSeed", seed)
    finding = {
        "event_id": "W12:NEG3", "kind": "HUNT_RESULT",
        "subject_id": "MAI-A", "source_ref": "doi:counterexample",
        "result": "CONTRADICTED",
        "intellectual_consequence": "original claim no longer defensible",
        "next_action": "reopen conceptual basis",
    }
    store.append_event(finding)
    proposal = store.propose_field_reopen(
        "W12:NEG3", reopen_level="L2",
        next_question="Which distinction makes the claim testable?",
    )
    assert proposal["kind"] == "FIELD_REOPEN_PROPOSAL"
    assert proposal["semantic_mutation"] == "NONE"
    assert proposal["author_gate"] == "AUTHOR_REVIEW_REQUIRED"
    assert store.propose_field_reopen(
        "W12:NEG3", reopen_level="L2",
        next_question="Which distinction makes the claim testable?",
    ) == proposal
    assert store.get("ArticleSeed", "MAI-A", "r1")["protected_core"] == ["institutional judgment"]


def test_reopen_rejects_positive_observation_and_invalid_level(tmp_path):
    store = OpportunityGraphStore(tmp_path)
    store.append_event({
        "event_id": "W12:POS", "kind": "HUNT_RESULT",
        "subject_id": "opp-e", "source_ref": "doi:new",
        "result": "MATCH_FOUND",
    })
    with pytest.raises(ValueError, match="negative research finding"):
        store.propose_field_reopen(
            "W12:POS", reopen_level="L1", next_question="What changed?",
        )
    with pytest.raises(ValueError, match="L0..L5"):
        store.append_event({
            "event_id": "W12:BAD", "kind": "FIELD_REOPEN_PROPOSAL",
            "subject_id": "opp-e", "source_ref": "doi:new",
            "reopen_level": "L9", "author_gate": "AUTHOR_REVIEW_REQUIRED",
        })
