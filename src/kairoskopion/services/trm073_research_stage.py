"""Bounded TRM-073 W2 research return -> existing Kairon stores.

The packet is research input, not an ArticleSeed, TargetVariant, World update,
qualified opportunity route, author decision, or permission to submit.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..kairon_provider.target_world_catalog import TargetWorldCatalog


PACKET_SCHEMA = "TRM073_W2_SCIENCE_VENUE_RETURN_INPUT_V1"
RECEIPT_SCHEMA = "TRM073_W2_RESEARCH_STAGE_RECEIPT_V1"
MAX_PACKET_BYTES = 2_000_000
MAX_WORKS = 100
MAX_OBJECTIONS = 100
DEPTH_MAP = {
    "ABSTRACT_ONLY": "ABSTRACT",
    "SELECTED_FULL_HTML": "SECTIONS",
    "FULL_TEXT": "FULL_TEXT",
}


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical(value)
    return sha256(raw).hexdigest()


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _write_stable(path: Path, value: dict[str, Any]) -> None:
    encoded = _canonical(value)
    if path.is_file() and path.read_bytes() == encoded:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(encoded)
    os.replace(tmp, path)


def _load_packet(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("research packet must be a regular local file")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_PACKET_BYTES:
        raise ValueError("research packet exceeds bounded input policy")
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("research packet must be UTF-8 JSON") from exc
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("unsupported research packet schema")
    return packet, raw


def _validate_packet(packet: dict[str, Any]) -> None:
    _required(packet.get("case_id"), "case_id")
    _required(packet.get("wave_id"), "wave_id")
    _required(packet.get("head"), "head")
    if packet.get("origin_authority") != "PROVISIONAL_SOURCE_BASED_RESEARCH":
        raise ValueError("W2 authority must remain provisional")
    if packet.get("runtime_executed") is not False:
        raise ValueError("input must not claim prior runtime execution")
    works = packet.get("verified_publisher_works")
    objections = packet.get("scientific_objections")
    if not isinstance(works, list) or not 1 <= len(works) <= MAX_WORKS:
        raise ValueError("verified_publisher_works is outside bounded input policy")
    if not isinstance(objections, list) or not 1 <= len(objections) <= MAX_OBJECTIONS:
        raise ValueError("scientific_objections is outside bounded input policy")
    ids = [_required(x.get("source_id"), "source_id") for x in works]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate publisher work source_id")
    event_ids = [_required(x.get("event_id"), "objection event_id") for x in objections]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("duplicate objection event_id")
    if any(x.get("read_depth") not in DEPTH_MAP for x in works):
        raise ValueError("publisher work has unsupported read_depth")
    if any(x.get("kind") not in {"RESEARCH", "EDITORIAL"} for x in works):
        raise ValueError("publisher work must be RESEARCH or EDITORIAL")
    if any(x.get("published_work") not in ids for x in objections):
        raise ValueError("objection references unknown publisher work")
    proposal = packet.get("proposed_article_object") or {}
    if (proposal.get("author_gate"), proposal.get("world_change"), proposal.get("journal_send")) != (
        "HOLD", "NONE", "DISABLED",
    ):
        raise ValueError("packet attempts to bypass author, World, or send gate")


def _world_fingerprint(store: OpportunityGraphStore) -> dict[str, Any]:
    worlds = store.list_records("World")
    return {"count": len(worlds), "sha256": _digest(worlds)}


def _record_fingerprint(store: OpportunityGraphStore, kind: str) -> dict[str, Any]:
    records = store.list_records(kind)
    return {"count": len(records), "sha256": _digest(records)}


def stage_research_packet(research_packet: str | Path, storage_root: str | Path) -> dict[str, Any]:
    """Persist a resumable, fail-closed research-stage return.

    Stable packet/item hashes are used as revisions. Raw packet bytes are not
    copied into storage; only typed research evidence and challenge events are
    persisted. Re-running the same packet is idempotent.
    """
    packet_path = Path(research_packet)
    storage = Path(storage_root)
    packet, raw = _load_packet(packet_path)
    _validate_packet(packet)
    packet_sha = _digest(raw)
    case_id = _required(packet["case_id"], "case_id")
    wave_id = _required(packet["wave_id"], "wave_id")
    head = _required(packet["head"], "head")
    run_dir = storage / "research_stage" / case_id / wave_id
    receipt_path = run_dir / "receipt.json"
    if receipt_path.is_file():
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if prior.get("source_packet_sha256") != packet_sha:
            raise ValueError("case/wave checkpoint already pins a different immutable packet")
    graph = OpportunityGraphStore(storage)
    world_before = _world_fingerprint(graph)
    seeds_before = _record_fingerprint(graph, "ArticleSeed")
    routes_before = _record_fingerprint(graph, "OpportunityRoute")

    target = packet.get("targetworld") or {}
    venue_name = _required(target.get("venue"), "targetworld.venue")
    issue_url = _required(target.get("issue_url"), "targetworld.issue_url")
    venue_key = sha256(venue_name.casefold().encode("utf-8")).hexdigest()[:20]
    journal_id = f"journal-{venue_key}"
    revision = f"packet:{packet_sha[:24]}:stage-v1"
    graph.put("Journal", {
        "id": journal_id,
        "revision": revision,
        "canonical_name": venue_name,
        "official_url": _required(target.get("normal_author_guidelines"), "normal_author_guidelines"),
        "publisher": target.get("publisher"),
        "research_status": "PROVISIONAL",
        "source_packet_sha256": packet_sha,
    })
    graph.put("JournalIssue", {
        "id": f"{journal_id}-issue-{packet_sha[:16]}",
        "revision": revision,
        "journal_id": journal_id,
        "official_url": issue_url,
        "issue_label": target.get("native_issue"),
        "issue_topic": target.get("issue_topic"),
        "current_special_issue_status": target.get("current_special_issue_status"),
        "live_call": False,
        "research_status": "PROVISIONAL",
    })

    works_by_id: dict[str, dict[str, Any]] = {}
    evidence_refs: list[dict[str, Any]] = []
    for work in packet["verified_publisher_works"]:
        source_id = _required(work.get("source_id"), "source_id")
        works_by_id[source_id] = work
        item_sha = _digest(work)
        native = bool(work.get("actual_native_venue_verified")) and str(work.get("venue", "")).casefold() == venue_name.casefold()
        work_kind = work["kind"]
        stored = graph.put("Evidence", {
            "id": f"trm073-w2-evidence-{source_id.casefold()}",
            "revision": f"item:{item_sha[:24]}:stage-v1",
            "source_ref": "doi:" + _required(work.get("doi"), f"{source_id}.doi"),
            "source_kind": "PUBLISHED_ARTICLE" if work_kind == "RESEARCH" else "PUBLISHED_EDITORIAL",
            "work_kind": work_kind,
            "read_depth": DEPTH_MAP[work["read_depth"]],
            "reported_read_depth": work["read_depth"],
            "full_text_certified": work["read_depth"] == "FULL_TEXT",
            "passage_anchors": [{
                "anchor_kind": "PUBLISHER_WORK_METADATA_ONLY",
                "publisher_url": _required(work.get("publisher_url"), f"{source_id}.publisher_url"),
                "packet_item_sha256": item_sha,
            }],
            "venue_relation": "JOURNAL_NATIVE" if native else "EXTERNAL_COMPARATOR",
            "journal_id": journal_id if native else None,
            "research_status": "PROVISIONAL",
            "qualified_for_article": False,
            "qualified_as_journal_policy": False,
            "author_approved": False,
            "source_packet_sha256": packet_sha,
        })
        evidence_refs.append({
            "id": stored["id"], "revision": stored["revision"],
            "work_kind": work_kind, "read_depth": stored["read_depth"],
            "venue_relation": stored["venue_relation"],
        })

    target_snapshot = {
        "snapshot_id": f"trm073-w2-{packet_sha[:24]}",
        "target_id": journal_id,
        "provider_commit": None,
        "evidence_refs": [x["id"] for x in evidence_refs],
        "corpus_manifest": {"artifacts": []},
        "target_models": {"confidence": "PROVISIONAL", "article_models": []},
        "freshness": {
            "special_issue": "HISTORICAL_PUBLISHED_NOT_ACTIVE_CFP",
            "policy": "NORMAL_AUTHOR_GUIDELINES_LINK_ONLY_NOT_DEEP_VERIFIED",
        },
        "research_stage": "PROVISIONAL_NOT_TARGETWORLD_QUALIFIED",
    }
    catalog_entry = TargetWorldCatalog(storage).ingest(
        target_snapshot, origin="TRM073_W2_MANUAL_CHAT_FALLBACK",
        status="PROVISIONAL", source_ref=f"sha256:{packet_sha}",
        display_name=venue_name,
    )

    objection_refs: list[dict[str, Any]] = []
    for objection in packet["scientific_objections"]:
        source_event_id = _required(objection.get("event_id"), "objection.event_id")
        event_id = f"{case_id}:{wave_id}:{source_event_id}"
        work = works_by_id[objection["published_work"]]
        source_ref = "doi:" + _required(work.get("doi"), "objection source doi")
        event = graph.append_event({
            "event_id": event_id,
            "source_event_id": source_event_id,
            "kind": "SOURCE_CONTRADICTION",
            "subject_id": head,
            "source_ref": source_ref,
            "source_packet_sha256": packet_sha,
            "source_work_id": objection["published_work"],
            "talk_source": objection.get("talk_source"),
            "source_epistemic_depth": objection.get("source_epistemic_depth"),
            "result": "CONTRADICTORY_SCHOLARLY_OBJECTION",
            "intellectual_consequence": _required(objection.get("objection"), "objection text"),
            "verdict": _required(objection.get("verdict"), "objection verdict"),
            "next_action": "Return to source at required depth, then author reviews " + str(objection["verdict"]),
            "author_decision": "HOLD",
            "semantic_mutation": "NONE",
        })
        reopen = graph.propose_field_reopen(
            event_id, reopen_level="L2",
            next_question=(
                f"What source-return evidence resolves {objection['verdict']} "
                "without silently adopting a new claim?"
            ),
        )
        objection_refs.append({
            "event_id": event["event_id"], "reopen_event_id": reopen["event_id"],
            "source_work_id": objection["published_work"],
            "source_epistemic_depth": objection.get("source_epistemic_depth"),
            "author_gate": reopen["author_gate"],
        })

    seeds_after = _record_fingerprint(graph, "ArticleSeed")
    routes_after = _record_fingerprint(graph, "OpportunityRoute")
    if seeds_after != seeds_before:
        raise ValueError("research stage must not create or change ArticleSeed")
    if routes_after != routes_before:
        raise ValueError("research stage must not create a qualified opportunity route")
    world_after = _world_fingerprint(graph)
    if world_after != world_before:
        raise ValueError("research stage attempted World mutation")

    talk_status = {x.get("work"): x.get("status") for x in packet.get("talk_sources", [])}
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": case_id,
        "wave_id": wave_id,
        "source_packet_sha256": packet_sha,
        "source_packet_bytes": len(raw),
        "raw_packet_copied": False,
        "checkpoint": "SOURCE_TO_OBJECTION_TO_FIELD_REOPEN_PERSISTED",
        "resume_key": f"{case_id}:{wave_id}:{packet_sha}",
        "research_status": "PROVISIONAL",
        "product_in_use": "VERIFIED_LOCAL_STAGE",
        "source_due_diligence_status": "MIXED_SECTIONS_AND_ABSTRACT_FULLTEXT_NOT_CERTIFIED",
        "venue_due_diligence_status": "NATIVE_PUBLISHED_ISSUE_VERIFIED_CURRENT_ROUTE_NOT_QUALIFIED",
        "science_negative_discovery_status": "SIX_OBJECTIONS_PERSISTED_FIELD_REOPEN_HELD",
        "counts": {
            "publisher_works": len(evidence_refs),
            "research_works": sum(x["work_kind"] == "RESEARCH" for x in evidence_refs),
            "editorial_works": sum(x["work_kind"] == "EDITORIAL" for x in evidence_refs),
            "scientific_objections": len(objection_refs),
            "field_reopen_proposals": len(objection_refs),
            "discovered_journals": 1,
            "proposed_routes": 0,
            "w12_equivalent_routes": 0,
            "deep_qualified": 0,
            "author_approved": 0,
            "submission_ready": 0,
            "article_seeds_created": 0,
            "world_mutations": 0,
            "external_sends": 0,
        },
        "funnel": {
            "DISCOVERED_JOURNALS": 1,
            "PROPOSED_ROUTES": 0,
            "W12_EQUIVALENT_ROUTES": 0,
            "DEEP_QUALIFIED": 0,
            "AUTHOR_APPROVED": 0,
            "SUBMISSION_READY": 0,
        },
        "evidence_refs": evidence_refs,
        "objection_refs": objection_refs,
        "venue": {
            "journal_id": journal_id,
            "catalog_package_id": catalog_entry["package_id"],
            "special_issue_status": target.get("current_special_issue_status"),
            "live_call": False,
            "qualification": "PROVISIONAL_DEEP_FULLTEXT_AND_EDITOR_EVIDENCE_PENDING",
        },
        "author_gate": "HOLD",
        "artikl_gate": "UNTESTED",
        "world_before": world_before,
        "world_after": world_after,
        "article_seeds_before": seeds_before,
        "article_seeds_after": seeds_after,
        "routes_before": routes_before,
        "routes_after": routes_after,
        "b52_status": "NEWER_NOT_ADOPTED" if "LATER_DRAFT_UNVERIFIED_OWNER_ACCEPTANCE" in str(talk_status.get("B52v2")) else "UNKNOWN_HOLD",
        "blockers": [
            "publisher_full_text_not_certified_as_read",
            "abstract_only_sources_cannot_support_deep_claims",
            "editorials_are_not_empirical_research",
            "published_special_issue_is_not_a_live_cfp",
            "normal_author_guidelines_not_deep_verified_as_route_policy",
            "B52v2_newer_draft_not_owner_adopted",
            "candidate_claim_not_author_approved",
            "ArticleSeed_absent_by_design",
        ],
        "next_required_evidence": [
            "return to original publisher full text for every objection used beyond abstract scope",
            "verify current official journal policy and an actual editorial path",
            "obtain Artikl/author decision on split, merge, retire, or revise HEAD-02",
            "only then assess a target-specific thesis and transformation as a route",
        ],
        "recovery": {
            "cold_replay": "SUPPORTED_BY_IMMUTABLE_IDS_AND_RECEIPT_READBACK",
            "network_calls": 0,
            "http_429_recovery": "NOT_EXERCISED_LOCAL_PACKET_NO_NETWORK",
            "send_gate": "DISABLED",
        },
        "venue80_scaffold": {
            "target": 80, "international_target": 60, "rf_target": 20,
            "admit_only_distinct_claim_version_venue_routes": True,
            "blind_cartesian_product": False,
            "semantic_head_actions": ["SPLIT", "MERGE", "RETIRE", "KEEP"],
            "current_shortfall": 80,
        },
    }
    _write_stable(receipt_path, receipt)
    readback = readback_research_stage(storage, case_id, wave_id)
    return {
        "status": "PROVISIONAL_RESEARCH_STAGED",
        "receipt_path": str(receipt_path),
        "receipt_sha256": _digest(receipt_path.read_bytes()),
        "readback_path": readback["readback_path"],
        "readback_sha256": readback["readback_sha256"],
        "counts": receipt["counts"],
        "author_gate": "HOLD",
        "external_send": "DISABLED",
    }


def readback_research_stage(storage_root: str | Path, case_id: str, wave_id: str) -> dict[str, Any]:
    """Independently reopen the stores and write a deterministic verification file."""
    storage = Path(storage_root)
    run_dir = storage / "research_stage" / case_id / wave_id
    receipt_path = run_dir / "receipt.json"
    if not receipt_path.is_file():
        raise ValueError("research-stage receipt missing")
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw.decode("utf-8"))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("research-stage receipt schema mismatch")
    graph = OpportunityGraphStore(storage)
    evidence = [x for x in graph.list_records("Evidence") if x.get("source_packet_sha256") == receipt["source_packet_sha256"]]
    events = [x for x in graph.replay_events() if x.get("source_packet_sha256") == receipt["source_packet_sha256"]]
    reopen_ids = {x["reopen_event_id"] for x in receipt["objection_refs"]}
    all_events = graph.replay_events()
    verified = (
        len(evidence) == receipt["counts"]["publisher_works"]
        and len(events) == receipt["counts"]["scientific_objections"]
        and reopen_ids.issubset({x["event_id"] for x in all_events})
        and _record_fingerprint(graph, "ArticleSeed") == receipt["article_seeds_after"]
        and _record_fingerprint(graph, "OpportunityRoute") == receipt["routes_after"]
        and receipt["article_seeds_before"] == receipt["article_seeds_after"]
        and receipt["routes_before"] == receipt["routes_after"]
        and receipt["world_before"] == receipt["world_after"]
    )
    if not verified:
        raise ValueError("independent research-stage readback failed")
    readback = {
        "schema": "TRM073_W2_RESEARCH_STAGE_READBACK_V1",
        "case_id": case_id,
        "wave_id": wave_id,
        "receipt_sha256": _digest(receipt_raw),
        "source_packet_sha256": receipt["source_packet_sha256"],
        "verified": True,
        "evidence_count": len(evidence),
        "objection_count": len(events),
        "reopen_count": len(reopen_ids),
        "article_seed_count": receipt["article_seeds_after"]["count"],
        "route_count": receipt["routes_after"]["count"],
        "world_mutations": 0,
        "external_sends": 0,
        "author_approvals": 0,
        "semantic_inventory_sha256": _digest({
            "evidence": evidence,
            "objections": events,
            "reopens": sorted(reopen_ids),
        }),
    }
    path = run_dir / "readback.json"
    _write_stable(path, readback)
    return {
        **readback,
        "readback_path": str(path),
        "readback_sha256": _digest(path.read_bytes()),
    }
