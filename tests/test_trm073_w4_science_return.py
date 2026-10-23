"""W4 source/version scientific-return controls, research-note ≠ publisher proof."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_research_stage import (
    readback_research_stage, stage_research_packet,
)
from tests.test_trm073_w12_route_stage import fixture_route


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _packet(tmp_path: Path):
    base_packet, _, stage, source, _, _ = fixture_route(tmp_path)
    graph = OpportunityGraphStore(stage)
    graph.put("Evidence", {
        "id": "source-opponent-research",
        "revision": "r1",
        "source_ref": "doi:10.1007/synth",
        "source_kind": "PUBLISHED_ARTICLE",
        "work_kind": "RESEARCH",
        "read_depth": "ABSTRACT",
        "passage_anchors": [{"publisher_url": "https://link.springer.com/article/synth"}],
    })
    graph.put("Evidence", {
        "id": "source-opponent-target-article",
        "revision": "r1",
        "source_ref": "doi:10.1007/genre",
        "source_kind": "PUBLISHED_ARTICLE",
        "work_kind": "TARGET_ARTICLE",
        "read_depth": "INDEX_ONLY",
        "passage_anchors": [{"publisher_url": "https://link.springer.com/article/genre"}],
    })
    dossier = tmp_path / "w4-dossier.txt"
    note = (
        "W4-R1 / CHAT_RESEARCH_FALLBACK_TO_FACTORY\n"
        "R1-01: A grounded peer-reviewed comparator examines managers and "
        "opportunity exploitation rather than collectively replicated industry.\n"
        "R1-02: This target article is not an empirical study of independent "
        "industrial standards and cannot be promoted into a certified finding.\n"
    )
    dossier.write_bytes(note.encode("utf-8"))
    target = {
        "id": "C-SYNTH-v0",
        "status": "ARTICLE_HYPOTHESIS",
        "author_gate": "HOLD",
        "theoretical_delta": (
            "A falsifiable distinction among entrepreneur opportunity realization, "
            "firm-level innovative efficiency, and the repeatable formation of "
            "industrial functions, standards and jointly maintained production roles."
        ),
    }
    sentence = "A falsifying case must trace actual organization-level roles over time."
    concern = "The journal abstract reports manager outcomes, not independent historical evidence that a new industry has reproducible productive arrangements."
    question = "How can our C04 version be falsified by actual industrial cases rather than an analogy with corporate innovation studies?"
    challenges = [
        {
            "challenge_id": "C-SCIENCE-1", "head_id": "HEAD-03",
            "opponent_doi": "10.1007/synth", "genre": "RESEARCH",
            "read_depth": "ABSTRACT_ONLY", "result": "SCIENTIFIC_OBJECTION_HELD",
            "dossier_anchor_quote": note.splitlines()[1][:124],
            "strongest_objection": concern,
            "negative_evidence": concern + " " + sentence,
            "falsifier": sentence + " " + concern,
            "reopen_question": question,
        },
        {
            "challenge_id": "C-BLOCKED-2", "head_id": "HEAD-03",
            "opponent_doi": "10.1007/genre", "genre": "TARGET_ARTICLE",
            "read_depth": "METADATA_ONLY", "result": "REJECTED_READING_INSUFFICIENT",
            "dossier_anchor_quote": note.splitlines()[2][:120],
            "strongest_objection": concern,
            "negative_evidence": concern + " " + sentence,
            "falsifier": sentence + " " + concern,
            "reopen_question": question,
        },
    ]
    packet_path = tmp_path / "w4-packet.json"
    packet = {
        "schema": "TRM073_W4_SCHOLARLY_SOURCE_RETURN_INPUT_V1",
        "case_id": "CASE-SYNTH-B", "wave_id": "W4-TEST-ONE",
        "private_packet_path": str(packet_path),
        "author_decision": "HOLD",
        "scientific_status": "SOURCE_DISCUSSION_PROPOSAL",
        "article_seed_created": False, "world_mutation": False,
        "external_send": "DISABLED",
        "dossier": {
            "source_id": "drive:1cwW5doPsSNBge0KNqu8ZBU9UY5Vebp_RmlC9rcWXvko",
            "carrier": "GOOGLE_DRIVE_CONNECTOR_CHAT_RELAY_NOT_NATIVE_TRM040",
            "path": str(dossier), "sha256": _sha(dossier.read_bytes()),
        },
        "original_head": {
            "head_id": "HEAD-03",
            "source_id": base_packet["original_source"]["source_id"],
            "version": "v0.4", "path": str(source),
            "sha256": _sha(source.read_bytes()), "anchor_line": 2,
            "anchor_quote": source.read_text(encoding="utf-8").splitlines()[1],
        },
        "challenges": challenges,
        "candidate_article_version": target,
    }
    def save() -> None:
        packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    save()
    return packet, save, packet_path, stage, source, dossier


def test_w4_registered_science_packet_and_independent_cold_replay(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    first = stage_research_packet(path, stage)
    second = stage_research_packet(path, stage)
    assert first["status"] == "PROVISIONAL_RESEARCH_STAGED"
    assert first["receipt_sha256"] == second["receipt_sha256"]
    assert first["readback_sha256"] == second["readback_sha256"]
    assert first["counts"]["scientific_challenges"] == 1
    assert first["counts"]["field_reopen_proposals"] == 1
    assert first["counts"]["rejected_comparator_trails"] == 1
    assert first["counts"]["article_versions_proposed_held"] == 1
    assert first["counts"]["article_seeds_created"] == 0
    assert readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")["verified"]
    graph = OpportunityGraphStore(stage)
    assert graph.list_records("World") == []
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert len(graph.list_records("HuntTrace")) == 1
    assert len([e for e in graph.replay_events() if e["kind"] == "FIELD_REOPEN_PROPOSAL"]) == 1


def test_w4_dossier_mutation_breaks_pinned_cold_readback(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    stage_research_packet(path, stage)
    dossier.write_bytes(dossier.read_bytes() + b"\nUnauthorized note")
    with pytest.raises(ValueError, match="source byte SHA mismatch"):
        readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")


def test_w4_original_c04_mutation_breaks_pinned_cold_readback(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    stage_research_packet(path, stage)
    source.write_bytes(source.read_bytes() + b"\nUnexpected changed source version")
    with pytest.raises(ValueError, match="source byte SHA mismatch"):
        readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")


def test_w4_research_packet_mutation_breaks_pinned_cold_readback(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    stage_research_packet(path, stage)
    packet["candidate_article_version"]["theoretical_delta"] += " revised without owner"
    save()
    with pytest.raises(ValueError, match="source byte SHA mismatch"):
        readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")


def test_w4_cannot_qualify_metadata_only_as_scientific_opponent(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["challenges"][0]["read_depth"] = "METADATA_ONLY"
    save()
    with pytest.raises(ValueError, match="metadata cannot qualify"):
        stage_research_packet(path, stage)
    assert OpportunityGraphStore(stage).list_records("HuntTrace") == []


def test_w4_target_article_cannot_be_an_original_research_opponent(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["challenges"][1]["result"] = "SCIENTIFIC_OBJECTION_HELD"
    save()
    with pytest.raises(ValueError, match="non-research comparator cannot qualify"):
        stage_research_packet(path, stage)


def test_w4_cannot_invent_author_permission_or_world_write(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["author_decision"] = "ACCEPT"
    packet["world_mutation"] = True
    save()
    with pytest.raises(ValueError, match="science/author decision must remain HOLD"):
        stage_research_packet(path, stage)


def test_w4_unverified_source_version_does_not_enter_graph(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["original_head"]["version"] = "v0.5"
    save()
    with pytest.raises(ValueError, match="original Head binding"):
        stage_research_packet(path, stage)


def test_w4_selected_full_html_requires_independent_capture(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["challenges"][0]["read_depth"] = "SELECTED_FULL_HTML"
    save()
    with pytest.raises(ValueError, match="needs independent publisher byte capture"):
        stage_research_packet(path, stage)


def test_w4_mixed_dossier_lineage_cannot_relabel_native_capture(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["dossier"]["carrier"] = "TRM040_NATIVE_VERIFIED"
    save()
    with pytest.raises(ValueError, match="may not self-certify"):
        stage_research_packet(path, stage)



def test_w4_dossier_can_be_different_pinned_drive_document_without_native_claim(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    packet["dossier"]["source_id"] = "drive:NEW-SECOND-CORPUS-RESEARCH-NOTE"
    save()
    out = stage_research_packet(path, stage)
    assert out["counts"]["scientific_challenges"] == 1
    assert readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")["provider_mode"] == (
        "CONNECTOR_CHAT_FALLBACK_NOT_NATIVE_TRM040"
    )


def test_w4_non_c04_head_can_return_when_original_w3_bytes_verified(tmp_path):
    packet, save, path, stage, source, dossier = _packet(tmp_path)
    graph = OpportunityGraphStore(stage)
    graph.append_event({
        "event_id": "CASE-SYNTH-B:W3:HEAD-01:SOURCE-PIN",
        "kind": "SOURCE_CONTRADICTION",
        "subject_id": "HEAD-01",
        "source_ref": packet["original_head"]["source_id"],
        "original_source_binding": {
            "source_id": packet["original_head"]["source_id"],
            "version": packet["original_head"]["version"],
            "content_sha256": packet["original_head"]["sha256"],
            "binding_verification": "VERIFIED_BYTES",
        },
    })
    packet["original_head"]["head_id"] = "HEAD-01"
    for item in packet["challenges"]:
        item["head_id"] = "HEAD-01"
    save()
    out = stage_research_packet(path, stage)
    assert out["counts"]["field_reopen_proposals"] == 1
    assert readback_research_stage(stage, "CASE-SYNTH-B", "W4-TEST-ONE")["verified"]
