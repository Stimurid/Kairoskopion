"""Bounded TRM-073 research returns (W2 venue return, W3 multi-head discovery).

Packets are research input, not ArticleSeed, TargetVariant, World updates,
qualified opportunity routes, author decisions, or permission to submit.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Callable

from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..kairon_provider.target_world_catalog import TargetWorldCatalog
from .trm073_w1_source_binding import (
    enrich_packet_from_env,
    manifest_for_packet,
    resolve_head_bindings,
    verify_persisted_head_bindings_on_readback,
)


PACKET_SCHEMA = "TRM073_W2_SCIENCE_VENUE_RETURN_INPUT_V1"
PACKET_SCHEMA_W3 = "TRM073_W3_A_C_SEED_STAGE_V1"
PACKET_SCHEMA_W4 = "TRM073_W4_SCHOLARLY_SOURCE_RETURN_INPUT_V1"
RECEIPT_SCHEMA = "TRM073_W2_RESEARCH_STAGE_RECEIPT_V1"
RECEIPT_SCHEMA_W3 = "TRM073_W3_DISCOVERY_STAGE_RECEIPT_V1"

MAX_PACKET_BYTES = 2_000_000
MAX_WORKS = 100
MAX_OBJECTIONS = 100
MAX_W3_WORK_REFS = 200
MAX_W3_ROUTES = 200

W2_DEPTH_MAP = {
    "ABSTRACT_ONLY": "ABSTRACT",
    "SELECTED_FULL_HTML": "SECTIONS",
    "FULL_TEXT": "FULL_TEXT",
}

W3_DEPTH_MAP = {
    "ABSTRACT_ONLY": "ABSTRACT",
    "SELECTED_FULL_HTML": "SECTIONS",
    "FULL_TEXT": "FULL_TEXT",
    "METADATA_ONLY": "INDEX_ONLY",
    "INSTITUTION_ABSTRACT_ONLY": "ABSTRACT",
}

W3_GENRE_KIND = {
    "RESEARCH": ("PUBLISHED_ARTICLE", "RESEARCH"),
    "EDITORIAL": ("PUBLISHED_EDITORIAL", "EDITORIAL"),
    "REVIEW": ("PUBLISHED_ARTICLE", "REVIEW"),
    "TARGET_ARTICLE": ("PUBLISHED_ARTICLE", "TARGET_ARTICLE"),
}

W3_HEADS = frozenset({"HEAD-01", "HEAD-02", "HEAD-03"})

W3_NON_FULLTEXT_DEPTHS = frozenset({
    "ABSTRACT_ONLY",
    "METADATA_ONLY",
    "SELECTED_FULL_HTML",
    "INSTITUTION_ABSTRACT_ONLY",
})

W3_VENUE_VERIFICATION = frozenset({
    "UNKNOWN",
    "PUBLISHER_PAGE_VERIFIED",
    "REQUIRES_JOURNAL_CONFIRMATION",
})


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


def _read_packet_file(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("research packet must be a regular local file")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_PACKET_BYTES:
        raise ValueError("research packet exceeds bounded input policy")
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("research packet must be UTF-8 JSON") from exc
    if not isinstance(packet, dict):
        raise ValueError("research packet must be a JSON object")
    return packet, raw


def _checkpoint_reject(storage: Path, case_id: str, wave_id: str, packet_sha: str) -> None:
    receipt_path = storage / "research_stage" / case_id / wave_id / "receipt.json"
    if not receipt_path.is_file():
        return
    prior = json.loads(receipt_path.read_text(encoding="utf-8"))
    if prior.get("source_packet_sha256") != packet_sha:
        raise ValueError("case/wave checkpoint already pins a different immutable packet")


def _journal_id_from_name(venue_name: str) -> str:
    venue_key = sha256(venue_name.casefold().encode("utf-8")).hexdigest()[:20]
    return f"journal-{venue_key}"


def _work_source_ref(work: dict[str, Any]) -> str:
    doi = str(work.get("doi") or "").strip()
    if doi:
        return f"doi:{doi}"
    return "url:" + _required(work.get("source_url"), "source_url")


def _validate_w2_packet(packet: dict[str, Any]) -> None:
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
    if any(x.get("read_depth") not in W2_DEPTH_MAP for x in works):
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


def _w3_full_text_certified(work: dict[str, Any]) -> bool:
    """W3 discovery intake is references-only; never certify full text from packet flags."""
    return False


def _validate_w3_packet(packet: dict[str, Any]) -> None:
    _required(packet.get("case_id"), "case_id")
    _required(packet.get("wave_id"), "wave_id")
    if packet.get("scientific_owner_decision") != "HOLD":
        raise ValueError("W3 scientific owner decision must remain HOLD")
    safety = packet.get("safety") or {}
    if safety.get("send") or safety.get("article_seed_created") or safety.get("world_mutation"):
        raise ValueError("packet attempts to bypass author, World, or send gate")
    works = packet.get("work_refs")
    routes = packet.get("route_candidates")
    if not isinstance(works, list) or not 1 <= len(works) <= MAX_W3_WORK_REFS:
        raise ValueError("work_refs is outside bounded input policy")
    if not isinstance(routes, list) or not 1 <= len(routes) <= MAX_W3_ROUTES:
        raise ValueError("route_candidates is outside bounded input policy")
    work_ids = [_required(x.get("id"), "work_ref id") for x in works]
    if len(work_ids) != len(set(work_ids)):
        raise ValueError("duplicate work_ref id")
    route_ids = [_required(x.get("route_candidate_id"), "route_candidate_id") for x in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("duplicate route_candidate_id")
    for work in works:
        work_id = _required(work.get("id"), "work_ref id")
        if work.get("genre") not in W3_GENRE_KIND:
            raise ValueError("work_ref has unsupported genre")
        if work.get("read_depth") not in W3_DEPTH_MAP:
            raise ValueError("work_ref has unsupported read_depth")
        verification = str(work.get("venue_native_verification") or "UNKNOWN")
        if verification not in W3_VENUE_VERIFICATION:
            raise ValueError(f"{work_id} has unsupported venue_native_verification")
        if work.get("read_depth") == "FULL_TEXT":
            raise ValueError(
                f"{work_id}: FULL_TEXT read_depth is not allowed on W3 discovery references-only intake"
            )
        if bool(work.get("full_text_certified")):
            raise ValueError(
                f"{work_id}: full_text_certified cannot be asserted without independently verified source text"
            )
    for route in routes:
        head_id = _required(route.get("head_id"), "route head_id")
        if head_id not in W3_HEADS:
            raise ValueError("route head_id must be HEAD-01, HEAD-02 or HEAD-03")
        _required(route.get("journal_name"), "route journal_name")
        _required(route.get("opponent_id"), "route opponent_id")
        if route.get("route_status") != "DISCOVERED_PREQUALIFICATION":
            raise ValueError("route must remain DISCOVERED_PREQUALIFICATION")
        if route.get("w12_equivalent") is not False:
            raise ValueError("route cannot claim W12 equivalence at intake")
        if route.get("author_gate") != "HOLD":
            raise ValueError("route author_gate must remain HOLD")


def _world_fingerprint(store: OpportunityGraphStore) -> dict[str, Any]:
    worlds = store.list_records("World")
    return {"count": len(worlds), "sha256": _digest(worlds)}


def _record_fingerprint(store: OpportunityGraphStore, kind: str) -> dict[str, Any]:
    records = store.list_records(kind)
    return {"count": len(records), "sha256": _digest(records)}


def _assert_no_promotion(
    graph: OpportunityGraphStore,
    *,
    world_before: dict[str, Any],
    seeds_before: dict[str, Any],
    routes_before: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    seeds_after = _record_fingerprint(graph, "ArticleSeed")
    routes_after = _record_fingerprint(graph, "OpportunityRoute")
    if seeds_after != seeds_before:
        raise ValueError("research stage must not create or change ArticleSeed")
    if routes_after != routes_before:
        raise ValueError("research stage must not create a qualified opportunity route")
    world_after = _world_fingerprint(graph)
    if world_after != world_before:
        raise ValueError("research stage attempted World mutation")
    return seeds_after, routes_after, world_after


def _finish_stage(
    storage: Path,
    case_id: str,
    wave_id: str,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    run_dir = storage / "research_stage" / case_id / wave_id
    receipt_path = run_dir / "receipt.json"
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


def _stage_w2_packet(packet: dict[str, Any], raw: bytes, storage: Path) -> dict[str, Any]:
    _validate_w2_packet(packet)
    packet_sha = _digest(raw)
    case_id = _required(packet["case_id"], "case_id")
    wave_id = _required(packet["wave_id"], "wave_id")
    head = _required(packet["head"], "head")
    _checkpoint_reject(storage, case_id, wave_id, packet_sha)

    graph = OpportunityGraphStore(storage)
    world_before = _world_fingerprint(graph)
    seeds_before = _record_fingerprint(graph, "ArticleSeed")
    routes_before = _record_fingerprint(graph, "OpportunityRoute")

    target = packet.get("targetworld") or {}
    venue_name = _required(target.get("venue"), "targetworld.venue")
    issue_url = _required(target.get("issue_url"), "targetworld.issue_url")
    journal_id = _journal_id_from_name(venue_name)
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
            "read_depth": W2_DEPTH_MAP[work["read_depth"]],
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

    seeds_after, routes_after, world_after = _assert_no_promotion(
        graph, world_before=world_before, seeds_before=seeds_before, routes_before=routes_before,
    )

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
    return _finish_stage(storage, case_id, wave_id, receipt)


def _policy_url(packet: dict[str, Any], journal_name: str) -> str | None:
    for policy in packet.get("official_policies") or []:
        if str(policy.get("venue") or "").casefold() == journal_name.casefold():
            url = str(policy.get("url") or "").strip()
            return url or None
    return None


def _stage_w3_packet(packet: dict[str, Any], raw: bytes, storage: Path) -> dict[str, Any]:
    _validate_w3_packet(packet)
    packet_sha = _digest(raw)
    case_id = _required(packet["case_id"], "case_id")
    wave_id = _required(packet["wave_id"], "wave_id")
    _checkpoint_reject(storage, case_id, wave_id, packet_sha)

    w1_manifest = manifest_for_packet(packet)
    head_source_bindings = resolve_head_bindings(packet, w1_manifest)

    graph = OpportunityGraphStore(storage)
    world_before = _world_fingerprint(graph)
    seeds_before = _record_fingerprint(graph, "ArticleSeed")
    routes_before = _record_fingerprint(graph, "OpportunityRoute")
    revision = f"packet:{packet_sha[:24]}:stage-w3-v1"

    works_by_id = {work["id"]: work for work in packet["work_refs"]}
    journal_names = sorted({str(r["journal_name"]) for r in packet["route_candidates"]})
    journal_ids: dict[str, str] = {}
    catalog_packages: list[dict[str, str]] = []
    journal_evidence_ids: dict[str, list[str]] = {name: [] for name in journal_names}

    for route in packet["route_candidates"]:
        opponent_id = route["opponent_id"]
        journal_name = str(route["journal_name"])
        if opponent_id in works_by_id:
            journal_evidence_ids.setdefault(journal_name, []).append(
                f"trm073-w3-evidence-{opponent_id.casefold()}"
            )

    for journal_name in journal_names:
        journal_id = _journal_id_from_name(journal_name)
        journal_ids[journal_name] = journal_id
        packet_policy_url = _policy_url(packet, journal_name)
        candidate_record: dict[str, Any] = {
            "id": journal_id,
            "revision": revision,
            "canonical_name": journal_name,
            "research_status": "PROVISIONAL_DISCOVERY",
            "official_author_policy_status": (
                "UNVERIFIED_PACKET_CLAIM" if packet_policy_url else "UNRESOLVED"
            ),
            "source_packet_sha256": packet_sha,
        }
        if packet_policy_url:
            candidate_record["packet_claimed_policy_url"] = packet_policy_url
        graph.put("JournalDiscoveryCandidate", candidate_record)
        route_evidence = sorted(set(journal_evidence_ids.get(journal_name) or []))
        snapshot = {
            "snapshot_id": f"trm073-w3-{journal_id}-{packet_sha[:16]}",
            "target_id": journal_id,
            "provider_commit": None,
            "evidence_refs": route_evidence,
            "corpus_manifest": {
                "artifacts": [
                    {"artifact_id": ref, "source_ref": ref, "role": "ROUTE_COMPARATOR_EVIDENCE"}
                    for ref in route_evidence
                ],
            },
            "target_models": {"confidence": "PROVISIONAL", "article_models": []},
            "freshness": {"route_policy": "NOT_W12_QUALIFIED_AT_INTAKE"},
            "research_stage": "DISCOVERED_PREQUALIFICATION_ONLY",
        }
        catalog_entry = TargetWorldCatalog(storage).ingest(
            snapshot,
            origin="TRM073_W3_DISCOVERY_INTAKE",
            status="PROVISIONAL",
            source_ref=f"sha256:{packet_sha}",
            display_name=journal_name,
        )
        catalog_packages.append({
            "journal_id": journal_id,
            "package_id": catalog_entry["package_id"],
            "route_evidence_count": str(len(route_evidence)),
        })

    evidence_refs: list[dict[str, Any]] = []
    for work in packet["work_refs"]:
        work_id = work["id"]
        item_sha = _digest(work)
        source_kind, work_kind = W3_GENRE_KIND[work["genre"]]
        verification = str(work.get("venue_native_verification") or "UNKNOWN")
        venue_relation = "EXTERNAL_COMPARATOR"
        if verification == "REQUIRES_JOURNAL_CONFIRMATION":
            venue_relation = "INSTITUTION_OR_JOURNAL_UNCONFIRMED"
        stored = graph.put("Evidence", {
            "id": f"trm073-w3-evidence-{work_id.casefold()}",
            "revision": f"item:{item_sha[:24]}:stage-w3-v1",
            "source_ref": _work_source_ref(work),
            "source_kind": source_kind,
            "work_kind": work_kind,
            "read_depth": W3_DEPTH_MAP[work["read_depth"]],
            "reported_read_depth": work["read_depth"],
            "full_text_certified": _w3_full_text_certified(work),
            "passage_anchors": [{
                "anchor_kind": "PUBLISHER_WORK_METADATA_ONLY",
                "publisher_url": _required(work.get("source_url"), f"{work_id}.source_url"),
                "packet_item_sha256": item_sha,
                "actual_venue": work.get("actual_venue"),
            }],
            "venue_relation": venue_relation,
            "venue_native_verification": verification,
            "epistemic_role": work.get("epistemic_role"),
            "journal_id": None,
            "research_status": "PROVISIONAL",
            "qualified_for_article": False,
            "qualified_as_journal_policy": False,
            "author_approved": False,
            "source_packet_sha256": packet_sha,
            "publisher_ref": {
                "title": work.get("title"),
                "actual_venue": work.get("actual_venue"),
                "doi": work.get("doi"),
            },
        })
        evidence_refs.append({
            "id": stored["id"],
            "revision": stored["revision"],
            "work_id": work_id,
            "work_kind": work_kind,
            "read_depth": stored["read_depth"],
            "venue_relation": stored["venue_relation"],
            "packet_item_sha256": item_sha,
        })

    route_refs: list[dict[str, Any]] = []
    challenge_refs: list[dict[str, Any]] = []
    unresolved_opponents: list[str] = []

    for route in packet["route_candidates"]:
        route_id = route["route_candidate_id"]
        head_id = route["head_id"]
        opponent_id = route["opponent_id"]
        opponent_resolved = opponent_id in works_by_id
        if not opponent_resolved:
            unresolved_opponents.append(opponent_id)
        opponent = works_by_id.get(opponent_id)
        source_ref = f"unresolved:{opponent_id}"
        evidence_id = None
        if opponent:
            source_ref = _work_source_ref(opponent)
            evidence_id = f"trm073-w3-evidence-{opponent_id.casefold()}"
        journal_name = route["journal_name"]
        journal_id = journal_ids[journal_name]
        event_id = f"{case_id}:{wave_id}:route:{route_id}"
        challenge = graph.append_event({
            "event_id": event_id,
            "kind": "SCHOLARLY_ROUTE_CHALLENGE",
            "subject_id": head_id,
            "source_ref": source_ref,
            "source_packet_sha256": packet_sha,
            "route_candidate_id": route_id,
            "journal_id": journal_id,
            "opponent_work_id": opponent_id,
            "opponent_evidence_id": evidence_id,
            "opponent_resolved": opponent_resolved,
            "route_status": route.get("route_status"),
            "w12_equivalent": False,
            "scholarly_problem": _required(route.get("scholarly_problem"), "scholarly_problem"),
            "required_next_test": route.get("required_next_test"),
            "result": "PROVISIONAL_ROUTE_CHALLENGE_NOT_W12_QUALIFIED",
            "intellectual_consequence": (
                f"Published comparator may challenge {head_id} only after "
                f"{route.get('required_next_test') or 'source return'}; "
                f"original WORLD claim anchor: {packet.get('primary_claim_text_status', 'SOURCE_ANCHOR_PENDING')}"
            ),
            "next_action": "Hold route as DISCOVERED_PREQUALIFICATION; no ArticleSeed or send",
            "author_decision": "HOLD",
            "semantic_mutation": "NONE",
        })
        challenge_refs.append({
            "event_id": challenge["event_id"],
            "route_candidate_id": route_id,
            "head_id": head_id,
            "opponent_work_id": opponent_id,
            "opponent_resolved": opponent_resolved,
        })
        route_refs.append({
            "route_candidate_id": route_id,
            "head_id": head_id,
            "journal_id": journal_id,
            "journal_name": journal_name,
            "packet_claimed_policy_url": _policy_url(packet, journal_name),
            "opponent_work_id": opponent_id,
            "opponent_evidence_id": evidence_id,
            "opponent_doi": opponent.get("doi") if opponent else None,
            "route_status": "PROPOSED_UNQUALIFIED",
            "w12_equivalent": False,
            "challenge_event_id": challenge["event_id"],
        })

    head_return_refs: list[dict[str, Any]] = []
    head_ids = sorted({str(r["head_id"]) for r in packet["route_candidates"]})
    anchor_status = str(packet.get("primary_claim_text_status") or "SOURCE_ANCHOR_PENDING")

    for head_id in head_ids:
        routes_for_head = [r for r in packet["route_candidates"] if r["head_id"] == head_id]
        comparator_refs = []
        for route in routes_for_head:
            opp = route["opponent_id"]
            if opp in works_by_id:
                comparator_refs.append(_work_source_ref(works_by_id[opp]))
            else:
                comparator_refs.append(f"unresolved:{opp}")
        original_binding = head_source_bindings.get(head_id)
        held_source_ref = (
            str(original_binding.get("source_id"))
            if original_binding and original_binding.get("source_id")
            else (comparator_refs[0] if comparator_refs else f"packet:{packet_sha[:16]}")
        )
        research_method = (
            str(original_binding.get("research_method") or "UNKNOWN")
            if original_binding
            else "UNKNOWN"
        )
        head_event_id = f"{case_id}:{wave_id}:{head_id}:DISCOVERY-RETURN"
        head_event = graph.append_event({
            "event_id": head_event_id,
            "kind": "SOURCE_CONTRADICTION",
            "subject_id": head_id,
            "source_ref": held_source_ref,
            "source_packet_sha256": packet_sha,
            "result": "CONTRADICTORY_SCHOLARLY_DISCOVERY_RETURN",
            "original_source_anchor_status": anchor_status,
            "original_source_binding": original_binding,
            "research_method": research_method,
            "route_candidate_ids": [r["route_candidate_id"] for r in routes_for_head],
            "comparator_source_refs": comparator_refs,
            "intellectual_consequence": (
                f"Head {head_id}: published literature ({len(routes_for_head)} provisional routes) "
                f"may challenge original source claims; paragraph anchors "
                f"{'pending' if 'PENDING' in anchor_status else 'not verified at intake'}."
            ),
            "next_action": "Author and Artikl review held field reopen before any WORLD mutation",
            "author_decision": "HOLD",
            "semantic_mutation": "NONE",
        })
        reopen = graph.propose_field_reopen(
            head_event_id,
            reopen_level="L2",
            next_question=(
                f"Which {head_id} original-source passages survive these "
                f"{len(routes_for_head)} provisional route challenges without adopting unverified comparators?"
            ),
        )
        head_return_refs.append({
            "head_id": head_id,
            "event_id": head_event["event_id"],
            "reopen_event_id": reopen["event_id"],
            "route_candidate_ids": [r["route_candidate_id"] for r in routes_for_head],
            "author_gate": reopen["author_gate"],
            "reopen_level": reopen["reopen_level"],
            "reopen_source_ref": reopen["source_ref"],
            "reopen_intellectual_consequence": reopen["intellectual_consequence"],
            "reopen_next_action": reopen["next_action"],
            "reopen_next_question": reopen["next_action"],
            "reopen_semantic_mutation": reopen["semantic_mutation"],
            "original_source_anchor_status": anchor_status,
            "original_source_binding": original_binding,
            "research_method": research_method,
        })

    seeds_after, routes_after, world_after = _assert_no_promotion(
        graph, world_before=world_before, seeds_before=seeds_before, routes_before=routes_before,
    )

    w12_count = sum(1 for r in packet["route_candidates"] if r.get("w12_equivalent"))
    receipt = {
        "schema": RECEIPT_SCHEMA_W3,
        "case_id": case_id,
        "wave_id": wave_id,
        "source_packet_sha256": packet_sha,
        "source_packet_bytes": len(raw),
        "raw_packet_copied": False,
        "checkpoint": "EVIDENCE_TO_ROUTE_CHALLENGE_TO_HEAD_FIELD_REOPEN_PERSISTED",
        "resume_key": f"{case_id}:{wave_id}:{packet_sha}",
        "research_status": "PROVISIONAL",
        "product_in_use": "VERIFIED_LOCAL_STAGE",
        "science_discovery_status": "MULTI_HEAD_ROUTE_CHALLENGES_HELD",
        "counts": {
            "publisher_references": len(evidence_refs),
            "scholarly_route_challenges": len(challenge_refs),
            "head_discovery_returns": len(head_return_refs),
            "field_reopen_proposals": len(head_return_refs),
            "discovered_journals": len(journal_names),
            "proposed_routes": len(route_refs),
            "w12_equivalent_routes": w12_count,
            "deep_qualified": 0,
            "author_approved": 0,
            "submission_ready": 0,
            "article_seeds_created": 0,
            "world_mutations": 0,
            "external_sends": 0,
        },
        "funnel": {
            "DISCOVERED_JOURNALS": len(journal_names),
            "PROPOSED_ROUTES": len(route_refs),
            "W12_EQUIVALENT_ROUTES": 0,
            "DEEP_QUALIFIED": 0,
            "AUTHOR_APPROVED": 0,
            "SUBMISSION_READY": 0,
        },
        "evidence_refs": evidence_refs,
        "route_refs": route_refs,
        "challenge_refs": challenge_refs,
        "head_return_refs": head_return_refs,
        "catalog_packages": catalog_packages,
        "author_gate": "HOLD",
        "artikl_gate": "UNTESTED",
        "world_before": world_before,
        "world_after": world_after,
        "article_seeds_before": seeds_before,
        "article_seeds_after": seeds_after,
        "routes_before": routes_before,
        "routes_after": routes_after,
        "primary_claim_text_status": anchor_status,
        "head_source_bindings": head_source_bindings,
        "w1_source_manifest_path": str(packet.get("w1_source_manifest_path") or "").strip() or None,
        "blockers": [
            "original_world_claim_anchors_not_fully_verified_at_intake",
            "abstract_and_metadata_only_comparators_not_fulltext_certified",
            "editorials_and_reviews_are_not_primary_empirical_evidence",
            "institution_abstracts_are_not_journal_native_verified",
            "route_candidates_are_proposed_unqualified_not_w12",
            "author_gate_hold_no_article_seed",
            "ArticleSeed_absent_by_design",
        ],
        "unresolved_refs": sorted(set(unresolved_opponents)),
        "recovery": {
            "cold_replay": "SUPPORTED_BY_IMMUTABLE_IDS_AND_RECEIPT_READBACK",
            "network_calls": 0,
            "http_429_recovery": "NOT_EXERCISED_LOCAL_PACKET_NO_NETWORK",
            "send_gate": "DISABLED",
        },
        "venue80_scaffold": {
            "target": packet.get("route_target_min_w12_equivalent", 80),
            "international_target": (packet.get("geography_planning") or {}).get("international", 60),
            "rf_target": (packet.get("geography_planning") or {}).get("russian", 20),
            "current_shortfall": packet.get("route_target_min_w12_equivalent", 80),
        },
    }
    return _finish_stage(storage, case_id, wave_id, receipt)


def _stage_w4_packet(packet: dict[str, Any], raw: bytes, storage: Path) -> dict[str, Any]:
    """Admit source-anchored W4 objections via existing W3 DOI and Kairon graph."""
    from .trm073_w4_science_return import stage_w4_science_packet
    return stage_w4_science_packet(packet, raw, storage)


_PACKET_STAGERS: dict[str, Callable[[dict[str, Any], bytes, Path], dict[str, Any]]] = {
    PACKET_SCHEMA: _stage_w2_packet,
    PACKET_SCHEMA_W3: _stage_w3_packet,
    PACKET_SCHEMA_W4: _stage_w4_packet,
}


def register_packet_stager(schema: str, stager: Callable[[dict[str, Any], bytes, Path], dict[str, Any]]) -> None:
    """Register an additional wave schema without copying W2/W3 staging logic."""
    _PACKET_STAGERS[schema] = stager


def stage_research_packet(research_packet: str | Path, storage_root: str | Path) -> dict[str, Any]:
    """Persist a resumable, fail-closed research-stage return.

    Stable packet/item hashes are used as revisions. Raw packet bytes are not
    copied into storage; only typed research evidence and challenge events are
    persisted. Re-running the same packet is idempotent.
    """
    packet_path = Path(research_packet)
    storage = Path(storage_root)
    packet, raw = _read_packet_file(packet_path)
    packet = enrich_packet_from_env(packet)
    schema = packet.get("schema")
    stager = _PACKET_STAGERS.get(str(schema or ""))
    if stager is None:
        raise ValueError("unsupported research packet schema")
    return stager(packet, raw, storage)


def _readback_w2(storage: Path, case_id: str, wave_id: str, receipt: dict[str, Any], receipt_raw: bytes) -> dict[str, Any]:
    graph = OpportunityGraphStore(storage)
    packet_sha = receipt["source_packet_sha256"]
    evidence = [x for x in graph.list_records("Evidence") if x.get("source_packet_sha256") == packet_sha]
    events = [
        x for x in graph.replay_events()
        if x.get("source_packet_sha256") == packet_sha and x.get("kind") == "SOURCE_CONTRADICTION"
    ]
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
    return {
        "schema": "TRM073_W2_RESEARCH_STAGE_READBACK_V1",
        "case_id": case_id,
        "wave_id": wave_id,
        "receipt_sha256": _digest(receipt_raw),
        "source_packet_sha256": packet_sha,
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


def _event_by_id(graph: OpportunityGraphStore, event_id: str) -> dict[str, Any] | None:
    for event in graph.replay_events():
        if event.get("event_id") == event_id:
            return event
    return None


def _verify_w3_per_route_readback(graph: OpportunityGraphStore, packet_sha: str, receipt: dict[str, Any]) -> None:
    evidence_by_id = {
        row["id"]: row
        for row in graph.list_records("Evidence")
        if row.get("source_packet_sha256") == packet_sha
    }
    for ref in receipt.get("evidence_refs") or []:
        if not isinstance(ref, dict):
            raise ValueError("readback evidence_refs entries must be objects")
        evid_id = ref.get("id")
        if not evid_id:
            raise ValueError("readback evidence_refs missing id")
        evidence = evidence_by_id.get(evid_id)
        if evidence is None:
            raise ValueError(f"readback missing evidence record for {evid_id}")
        expected_depth = ref.get("read_depth")
        actual_depth = evidence.get("read_depth")
        if expected_depth and actual_depth != expected_depth:
            raise ValueError("readback evidence read_depth mismatch")
        if evidence.get("full_text_certified") and actual_depth != "FULL_TEXT":
            raise ValueError("readback evidence full_text_certified inconsistent with depth")
        if not evidence.get("full_text_certified") and actual_depth == "FULL_TEXT":
            raise ValueError("readback evidence FULL_TEXT depth without certification")
        expected_item_sha = ref.get("packet_item_sha256")
        if expected_item_sha:
            anchors = evidence.get("passage_anchors") or []
            anchor_sha = anchors[0].get("packet_item_sha256") if anchors else None
            if anchor_sha != expected_item_sha:
                raise ValueError("readback evidence packet_item_sha256 mismatch")
    candidates_by_id = {
        row["id"]: row
        for row in graph.list_records("JournalDiscoveryCandidate")
        if row.get("source_packet_sha256") == packet_sha
    }
    challenges_by_route = {
        event["route_candidate_id"]: event
        for event in graph.replay_events()
        if event.get("source_packet_sha256") == packet_sha
        and event.get("kind") == "SCHOLARLY_ROUTE_CHALLENGE"
    }
    for route_ref in receipt.get("route_refs") or []:
        route_id = route_ref["route_candidate_id"]
        challenge = challenges_by_route.get(route_id)
        if challenge is None:
            raise ValueError(f"readback missing route challenge for {route_id}")
        if challenge.get("subject_id") != route_ref.get("head_id"):
            raise ValueError("readback route head_id mismatch")
        if challenge.get("journal_id") != route_ref.get("journal_id"):
            raise ValueError("readback route journal_id mismatch")
        if challenge.get("opponent_work_id") != route_ref.get("opponent_work_id"):
            raise ValueError("readback route opponent mismatch")
        if challenge.get("author_decision") != "HOLD":
            raise ValueError("readback route author_gate must remain HOLD")
        journal_id = route_ref.get("journal_id")
        candidate = candidates_by_id.get(journal_id) if journal_id else None
        if candidate is None:
            raise ValueError(f"readback missing journal discovery candidate for {route_id}")
        if candidate.get("canonical_name") != route_ref.get("journal_name"):
            raise ValueError("readback journal discovery candidate name mismatch")
        expected_policy = route_ref.get("packet_claimed_policy_url")
        actual_policy = candidate.get("packet_claimed_policy_url")
        if (expected_policy or None) != (actual_policy or None):
            raise ValueError("readback journal packet_claimed_policy_url mismatch")
        opponent_id = route_ref.get("opponent_work_id")
        evidence_id = route_ref.get("opponent_evidence_id")
        if evidence_id:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                raise ValueError(f"readback missing opponent evidence for {opponent_id}")
            if evidence.get("full_text_certified") and evidence.get("read_depth") != "FULL_TEXT":
                raise ValueError("readback evidence full_text_certified inconsistent with depth")
            expected_ref = challenge.get("source_ref")
            if expected_ref and evidence.get("source_ref") != expected_ref:
                raise ValueError("readback route source_ref does not match opponent evidence")
            expected_doi = route_ref.get("opponent_doi")
            actual_doi = (evidence.get("publisher_ref") or {}).get("doi")
            if (expected_doi or None) != (actual_doi or None):
                raise ValueError("readback opponent evidence DOI mismatch")
        elif challenge.get("opponent_resolved"):
            raise ValueError(f"readback opponent {opponent_id} must remain unresolved")
    if graph.list_records("Journal"):
        staged_journals = [
            j for j in graph.list_records("Journal")
            if j.get("source_packet_sha256") == packet_sha
        ]
        if staged_journals:
            raise ValueError("readback must not promote discovery journals to canonical Journal records")
    for candidate in graph.list_records("JournalDiscoveryCandidate"):
        if candidate.get("source_packet_sha256") != packet_sha:
            continue
        if candidate.get("official_url"):
            raise ValueError("readback discovery candidate must not assert canonical official_url")
        policy_status = str(candidate.get("official_author_policy_status") or "")
        if policy_status == "UNVERIFIED_PACKET_CLAIM":
            if not candidate.get("packet_claimed_policy_url"):
                raise ValueError("readback discovery candidate missing packet_claimed_policy_url")
        elif policy_status != "UNRESOLVED":
            raise ValueError("readback discovery candidate has unexpected policy authority status")
    for head_ref in receipt.get("head_return_refs") or []:
        head_event = _event_by_id(graph, head_ref["event_id"])
        if head_event is None:
            raise ValueError("readback missing head discovery return event")
        if head_event.get("author_decision") != "HOLD":
            raise ValueError("readback head return must remain HOLD")
        binding = head_ref.get("original_source_binding")
        event_binding = head_event.get("original_source_binding")
        if binding != event_binding:
            raise ValueError("readback head return original_source_binding mismatch")
        if binding:
            if head_event.get("source_ref") != binding.get("source_id"):
                raise ValueError("readback head return must bind versioned original source_id")
            if head_ref.get("research_method") != head_event.get("research_method"):
                raise ValueError("readback head return research_method mismatch")
            if head_event.get("research_method") == "":
                raise ValueError("readback head return research_method must not be empty")
            if binding.get("passage_anchor_status") != "SOURCE_ANCHOR_PENDING":
                raise ValueError("readback head binding paragraph anchors must remain pending")
        reopen = _event_by_id(graph, head_ref["reopen_event_id"])
        if reopen is None:
            raise ValueError("readback missing head field reopen proposal")
        if reopen.get("kind") != "FIELD_REOPEN_PROPOSAL":
            raise ValueError("readback head reopen must be FIELD_REOPEN_PROPOSAL")
        if reopen.get("subject_id") != head_ref.get("head_id"):
            raise ValueError("readback head reopen subject_id mismatch")
        if reopen.get("source_event_id") != head_ref["event_id"]:
            raise ValueError("readback head reopen must reference held discovery return event")
        if reopen.get("author_gate") != head_ref.get("author_gate"):
            raise ValueError("readback head reopen author_gate mismatch")
        if reopen.get("author_gate") != "AUTHOR_REVIEW_REQUIRED":
            raise ValueError("readback head reopen must remain author-gated")
        if reopen.get("source_ref") != head_ref.get("reopen_source_ref"):
            raise ValueError("readback head reopen source_ref mismatch")
        if reopen.get("reopen_level") != head_ref.get("reopen_level"):
            raise ValueError("readback head reopen level mismatch")
        if reopen.get("intellectual_consequence") != head_ref.get("reopen_intellectual_consequence"):
            raise ValueError("readback head reopen intellectual_consequence mismatch")
        expected_question = head_ref.get("reopen_next_question") or head_ref.get("reopen_next_action")
        if expected_question:
            if reopen.get("next_action") != expected_question:
                raise ValueError("readback head reopen next_question mismatch")
            stored_question = reopen.get("next_question")
            if stored_question != expected_question:
                raise ValueError("readback head reopen next_question mismatch")
        elif reopen.get("next_action") != head_ref.get("reopen_next_action"):
            raise ValueError("readback head reopen next_action mismatch")
        if reopen.get("semantic_mutation") != head_ref.get("reopen_semantic_mutation"):
            raise ValueError("readback head reopen semantic_mutation mismatch")


def _readback_w3(storage: Path, case_id: str, wave_id: str, receipt: dict[str, Any], receipt_raw: bytes) -> dict[str, Any]:
    graph = OpportunityGraphStore(storage)
    packet_sha = receipt["source_packet_sha256"]
    evidence = [x for x in graph.list_records("Evidence") if x.get("source_packet_sha256") == packet_sha]
    challenges = [
        x for x in graph.replay_events()
        if x.get("source_packet_sha256") == packet_sha and x.get("kind") == "SCHOLARLY_ROUTE_CHALLENGE"
    ]
    head_returns = [
        x for x in graph.replay_events()
        if x.get("source_packet_sha256") == packet_sha
        and x.get("kind") == "SOURCE_CONTRADICTION"
        and str(x.get("event_id", "")).endswith(":DISCOVERY-RETURN")
    ]
    reopen_ids = {x["reopen_event_id"] for x in receipt["head_return_refs"]}
    all_events = graph.replay_events()
    verified = (
        len(evidence) == receipt["counts"]["publisher_references"]
        and len(challenges) == receipt["counts"]["scholarly_route_challenges"]
        and len(head_returns) == receipt["counts"]["head_discovery_returns"]
        and reopen_ids.issubset({x["event_id"] for x in all_events})
        and _record_fingerprint(graph, "ArticleSeed") == receipt["article_seeds_after"]
        and _record_fingerprint(graph, "OpportunityRoute") == receipt["routes_after"]
        and receipt["routes_before"] == receipt["routes_after"]
        and receipt["world_before"] == receipt["world_after"]
    )
    if not verified:
        raise ValueError("independent research-stage readback failed")
    manifest_path_text = str(receipt.get("w1_source_manifest_path") or "").strip()
    verify_persisted_head_bindings_on_readback(
        Path(manifest_path_text) if manifest_path_text else None,
        receipt.get("head_source_bindings") or {},
    )
    _verify_w3_per_route_readback(graph, packet_sha, receipt)
    return {
        "schema": "TRM073_W3_DISCOVERY_STAGE_READBACK_V1",
        "case_id": case_id,
        "wave_id": wave_id,
        "receipt_sha256": _digest(receipt_raw),
        "source_packet_sha256": packet_sha,
        "verified": True,
        "evidence_count": len(evidence),
        "route_challenge_count": len(challenges),
        "head_return_count": len(head_returns),
        "reopen_count": len(reopen_ids),
        "proposed_route_count": receipt["counts"]["proposed_routes"],
        "w12_equivalent_route_count": receipt["counts"]["w12_equivalent_routes"],
        "article_seed_count": receipt["article_seeds_after"]["count"],
        "opportunity_route_count": receipt["routes_after"]["count"],
        "world_mutations": 0,
        "external_sends": 0,
        "author_approvals": 0,
        "unresolved_refs": receipt.get("unresolved_refs") or [],
        "per_route_edges_verified": True,
        "semantic_inventory_sha256": _digest({
            "evidence": evidence,
            "route_challenges": challenges,
            "head_returns": head_returns,
            "reopens": sorted(reopen_ids),
        }),
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
    schema = receipt.get("schema")
    if schema == RECEIPT_SCHEMA:
        readback = _readback_w2(storage, case_id, wave_id, receipt, receipt_raw)
    elif schema == RECEIPT_SCHEMA_W3:
        readback = _readback_w3(storage, case_id, wave_id, receipt, receipt_raw)
    elif schema == "TRM073_W4_SCHOLARLY_SOURCE_RETURN_RECEIPT_V1":
        from .trm073_w4_science_return import readback_w4
        readback = readback_w4(storage, case_id, wave_id, receipt, receipt_raw)
    else:
        raise ValueError("research-stage receipt schema mismatch")
    path = run_dir / "readback.json"
    _write_stable(path, readback)
    return {
        **readback,
        "readback_path": str(path),
        "readback_sha256": _digest(path.read_bytes()),
    }
