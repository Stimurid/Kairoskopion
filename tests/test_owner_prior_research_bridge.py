"""Cold replay & adversarial tests: prior source-bound L3 research, no private data.

The fixture constructs real Kairon Evidence/Journal/events using synthetic
identities and text. It separately builds a frozen legacy receipt/readback
and the newly admitted 8+1 source stage. No DOI fulltexts or author assent.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.owner_prior_research_bridge import (
    _fp, _legacy_evidence, import_owner_prior_science, readback_owner_prior_science,
)


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _seed_synthetic_owner_science(tmp_path: Path):
    case_id = "L3-CORPUS-20261020"
    legacy, storage = tmp_path / "legacy", tmp_path / "factory"
    ownerdir = tmp_path / "private-owner"
    ownerdir.mkdir()
    keys = [
        "F02_v03", "F02_ACD_gate", "F01_B09", "F01_R13", "F01_R12",
        "L3_W2_source_venue_opponents", "L3_W1", "L3-ORIGINAL-DOCX",
        "L3-VAK-2023",
    ]
    samples = {
        "L3_W2_source_venue_opponents":
            "Initial owner research note.\n"
            "SR-03 / F01 B09: Spitale E04 already covers consent. "
            "The distinct research question concerns operational force of past; "
            "author decision HOLD.\n",
    }
    owner_refs, intake, auxiliary, registry = [], [], [], []
    g = OpportunityGraphStore(legacy)
    trial = "synthetic-private-trial-sha"
    for idx, key in enumerate(keys):
        is_binary = key == "L3-VAK-2023"
        source_id = f"drive:TEST-PROVIDER-{idx:02d}"
        body = samples.get(key, f"Owner source {key}; science not accepted.\n")
        raw = body.encode("utf-8")
        path = ownerdir / (key + (".xlsx" if is_binary else ".txt"))
        path.write_bytes(raw)
        identity = "old-source-" + str(idx)
        old_evidence = g.put("Evidence", {
            "id": identity, "revision": "source-test-v1",
            "source_ref": source_id, "source_kind": "OWNER_PRIVATE_BINARY"
                if key in {"L3-ORIGINAL-DOCX","L3-VAK-2023"}
                else "OWNER_PRIVATE_MANUSCRIPT",
            "read_depth": "INDEX_ONLY" if is_binary else "SECTIONS",
            "full_text_certified": False,
            "passage_anchors": [{"path_hint": str(path), "content_sha256": _sha(raw)}],
            "l3_trial_sha256": trial,
        })
        owner_refs.append({
            "id": old_evidence["id"], "key": key,
            "source_ref": source_id, "sha256": _sha(raw),
        })
        if is_binary:
            auxiliary.append({"source_id": source_id, "byte_sha256": _sha(raw)})
        else:
            snapshot_id = f"snapshot-synthetic-{idx}"
            intake.append({
                "source_id": source_id, "key": key,
                "snapshot_id": snapshot_id,
                "author_state": "NOT_VERIFIED",
                "raw_source_sha256": _sha(raw),
            })
            registry.append({
                "snapshot_id":snapshot_id,
                "source_id":source_id,
                "extraction_status":"extracted",
                "text_ref":str(path),
            })
    doi_refs = [
        ("E03", "10.1007/s10676-026-09922-0"),
        ("E04", "10.1007/s10676-026-09910-4"),
    ]
    opps = []
    for label, doi in doi_refs:
        evidence = g.put("Evidence", {
            "id": "opponent-" + label, "revision": "publisher-index-v1",
            "source_ref": "doi:" + doi, "source_kind": "PUBLISHED_ARTICLE",
            "read_depth": "SECTIONS", "full_text_certified": False,
            "passage_anchors": [{"anchor_kind":"L3_W2_SCIENTIFIC_RETURN_METADATA"}],
            "l3_trial_sha256": trial,
        })
        opps.append({"id": evidence["id"], "doi": doi, "l3_anchor": label})
    g.put("Journal", {
        "id": "journal-synthetic-1",
        "revision": "journal-v1",
        "canonical_name": "Ethics and Information Technology",
        "official_url": "https://example.org/journal-10676",
        "l3_trial_sha256": trial,
    })
    negative_event_id = case_id + ":L3-FACTORY-TRIAL-V1:L3-SR-03-B09-OPERATIONAL-FORCE"
    obj = g.append_event({
        "event_id": negative_event_id,
        "kind": "SOURCE_CONTRADICTION",
        "subject_id": "F01_B09",
        "source_ref": "doi:" + doi_refs[1][1],
        "result": "CONTRADICTORY_SCHOLARLY_OBJECTION",
        "intellectual_consequence":
            "Overlap with consent governance; need falsifiable descendant-propagation test.",
        "next_action": "Verify author and published article passage anchors.",
        "l3_trial_sha256": trial,
    })
    reopened = g.propose_field_reopen(
        obj["event_id"], reopen_level="L2",
        next_question="What experiment distinguishes operational memory governance?",
    )
    # Real L3 stamps the trial ID on its reopen event, but fingerprinting is
    # based on the exact expected event IDs, not a count-only search.
    reopens = g.replay_events()
    assert len(reopens) == 2 and reopened["event_id"] in {e["event_id"] for e in reopens}
    old_evidence = [e for e in g.list_records("Evidence") if e.get("l3_trial_sha256") == trial]
    old_journal = [e for e in g.list_records("Journal") if e.get("l3_trial_sha256") == trial]
    fp = {
        "schema": "L3_FULL_CONTENT_FINGERPRINTS_V1",
        "evidence": _fp(old_evidence, "id"),
        "journal": _fp(old_journal, "id"),
        "scientific_events": _fp(g.replay_events(), "event_id"),
        "expected_scientific_event_ids": sorted(e["event_id"] for e in g.replay_events()),
    }
    base = {"count": 0, "sha256": _sha(b"[]")}
    packet = {
        "schema":"L3_CORPUS_FACTORY_TRIAL_RECEIPT_V3",
        "case_id":case_id,"l3_pass":False,
        "l3_trial_sha256": trial,"wave_id":"L3-FACTORY-TRIAL-V1",
        "counts": {
            "owner_sources_admitted":9, "near_opponent_evidence":2,
            "scientific_objections":1,"field_reopen_proposals":1,
            "article_seeds":0,"opportunity_routes_persisted":0,
            "w12_equivalent_routes":0,"world_mutations":0,"external_sends":0,
        },
        "world_before":base,"world_after":base,
        "article_seeds_before":base,"article_seeds_after":base,
        "routes_before":base,"routes_after":base,
        "owner_evidence_refs":owner_refs,
        "opponent_evidence_refs":opps,
        "content_fingerprints":fp,
        "readback_expected": {
            "path": str(legacy/"l3_factory"/case_id/"L3-FACTORY-TRIAL-V1"/"readback.json")
        },
    }
    source_receipt = tmp_path / "old-owner-trial.json"
    _json(source_receipt, packet)
    _json(Path(packet["readback_expected"]["path"]), {
        "schema":"L3_CORPUS_FACTORY_TRIAL_READBACK_V3",
        "verified":True,
        "receipt_sha256":_sha(source_receipt.read_bytes()),
        "case_id":case_id,"l3_trial_sha256":trial,
        "evidence_count":11, "objection_count":1, "reopen_count":1,
    })
    _json(storage/"talk_corpora"/case_id/"case_ledger.json",{
        "case_id":case_id,"source_snapshots":intake,
    })
    registry_path = storage / "registries" / "source_snapshots.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in registry),
        encoding="utf-8",
    )
    _json(storage/"factory_research_cases"/case_id/"source_stage_receipt.json",{
        "case_id":case_id, "source_snapshots_count":8,
        "auxiliary_binary_count":1, "auxiliary_binary_pins":auxiliary,
        "article_seed_created":0,"external_send":"DISABLED",
    })
    return source_receipt, legacy, storage, ownerdir


def test_reuses_actual_graph_objects_and_cold_replays_without_publication(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    first = import_owner_prior_science(source, legacy, storage)
    second = import_owner_prior_science(source, legacy, storage)
    assert first == second
    assert first["readback_verified"]
    assert first["counts"] == {
        "owner_original_sources":9, "indexed_published_refs":2,
        "provisional_objections":1, "field_reopen_proposals":1,
        "w12_equivalent_routes":0, "article_seeds":0, "author_approvals":0,
        "world_mutations":0, "external_sends":0,
    }
    g = OpportunityGraphStore(storage)
    assert len(g.list_records("Evidence")) == 2
    assert all(e["read_depth"] == "INDEX_ONLY" and e["full_text_certified"] is False
               for e in g.list_records("Evidence"))
    assert len(g.list_records("HuntTrace")) == 1
    events = g.replay_events()
    assert len(events) == 2
    assert len({e["event_id"] for e in events}) == 2
    assert {e["kind"] for e in events} == {
        "SOURCE_CONTRADICTION","FIELD_REOPEN_PROPOSAL"}
    assert not any(g.list_records(k) for k in ("World","ArticleSeed","OpportunityRoute"))
    assert readback_owner_prior_science(storage)["verified"]


def test_tampered_original_w2_note_refused_even_when_receipt_remains(tmp_path):
    source, legacy, storage, ownerdir = _seed_synthetic_owner_science(tmp_path)
    (ownerdir/"L3_W2_source_venue_opponents.txt").write_text(
        "SR-03 / F01 B09: Spitale E04 " + "Falsified" * 12,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="raw (?:source |)bytes|owner bytes|source SHA"):
        import_owner_prior_science(source, legacy, storage)
    assert not (storage/"research_stage").exists()


def test_tampered_prior_graph_evidence_content_refused(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    g = OpportunityGraphStore(legacy)
    for path in g.records.glob("*.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("kind") == "Evidence":
            obj["read_depth"] = "FULL_TEXT"
            _json(path, obj)
            break
    with pytest.raises(ValueError, match="fingerprints|content hashes|read depth"):
        import_owner_prior_science(source, legacy, storage)


def test_duplicate_legacy_physical_events_refused_without_collapsing_ids(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    g = OpportunityGraphStore(legacy)
    duplicate = next(e for e in g.replay_events() if e["kind"] == "SOURCE_CONTRADICTION")
    _json(g.events/"duplicate-file.json", duplicate)
    with pytest.raises(ValueError, match="duplication"):
        import_owner_prior_science(source, legacy, storage)


def test_legacy_author_approved_status_cannot_be_forged(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    obj = json.loads(source.read_text(encoding="utf-8"))
    obj["l3_pass"] = True
    _json(source, obj)
    with pytest.raises(ValueError, match="authority invalid"):
        import_owner_prior_science(source, legacy, storage)


def test_unapproved_article_objects_in_legacy_graph_block_transfer(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    g = OpportunityGraphStore(legacy)
    g.put("ArticleSeed", {
        "id":"spurious-seed", "revision":"v1",
        "source_ref":"not-accepted", "author_authority":"UNKNOWN",
        "protected_core":[],
    })
    with pytest.raises(ValueError, match="unapproved publication authority"):
        import_owner_prior_science(source, legacy, storage)


def test_cold_readback_detects_deleted_or_modified_imported_event(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    g = OpportunityGraphStore(storage)
    for file in g.events.glob("*.json"):
        obj = json.loads(file.read_text(encoding="utf-8"))
        if obj.get("kind") == "SOURCE_CONTRADICTION":
            obj["scientific_read_depth"] = "FULL_TEXT"
            _json(file, obj)
            break
    with pytest.raises(ValueError, match="graph was deleted/duplicated/tampered"):
        readback_owner_prior_science(storage)


def test_partial_legacy_receipt_or_missing_reopen_fails_closed(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    packet = json.loads(source.read_text(encoding="utf-8"))
    packet["counts"]["field_reopen_proposals"] = 0
    _json(source, packet)
    with pytest.raises(ValueError, match="bounded author-HOLD"):
        import_owner_prior_science(source, legacy, storage)



def test_cold_readback_rehashes_all_nine_owner_files_not_just_w2(tmp_path):
    source, legacy, storage, ownerdir = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    victim = ownerdir / "F02_v03.txt"
    victim.write_bytes(victim.read_bytes() + b" UNAPPROVED_CHANGE")
    with pytest.raises(ValueError, match="source raw bytes changed|owner source bytes changed"):
        readback_owner_prior_science(storage)


def test_original_xlsx_byte_tamper_refused_on_cold_readback(tmp_path):
    source, legacy, storage, ownerdir = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    victim = ownerdir / "L3-VAK-2023.xlsx"
    victim.write_bytes(victim.read_bytes() + b" TAINTED")
    with pytest.raises(ValueError, match="historical L3 owner source bytes changed"):
        readback_owner_prior_science(storage)


def test_broken_current_source_registry_identity_fails_preflight(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    reg = storage / "registries" / "source_snapshots.jsonl"
    records = [json.loads(x) for x in reg.read_text(encoding="utf-8").splitlines()]
    records[0]["source_id"] = "drive:WRONG-AUTHORITY"
    reg.write_text("".join(json.dumps(x) + "\n" for x in records), encoding="utf-8")
    with pytest.raises(ValueError, match="source snapshot registry identity missing"):
        import_owner_prior_science(source, legacy, storage)



def test_stale_writer_lock_is_refused_not_stolen(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    lock = (storage / "research_stage" / "L3-CORPUS-20261020"
            / "L3-PRIOR-SCIENCE-IMPORT" / ".owner-prior-import.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("other-writer", encoding="utf-8")
    with pytest.raises(ValueError, match="writer is active or a lock needs inspection"):
        import_owner_prior_science(source, legacy, storage)
    assert lock.read_text(encoding="utf-8") == "other-writer"
    assert not (lock.parent / "receipt.json").exists()


def test_successful_writer_removes_own_lock(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    lock = (storage / "research_stage" / "L3-CORPUS-20261020"
            / "L3-PRIOR-SCIENCE-IMPORT" / ".owner-prior-import.lock")
    assert not lock.exists()
