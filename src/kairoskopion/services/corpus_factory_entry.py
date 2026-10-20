"""Bounded FACTORY-FIRST operator entry over existing Kairoskopion/LitOps/WhiteCrow.

A reproducible, *no-submit* source/research staging entry. Explicitly DOES
NOT run an external Indago hunt, certify journal policy, approve ArticleSeed,
write WORLD, create manuscripts, or send to journals.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..integrations.litops_bridge import admit_talk_context_into_installed_litops
from .talk_corpus_intake import run_case
from .talk_corpus_research_bridge import export_talk_research_evidence
from .talk_corpus_reopen import propose_w1_return
from .trm073_research_stage import (
    MAX_PACKET_BYTES, PACKET_SCHEMA, PACKET_SCHEMA_W3, PACKET_SCHEMA_W4,
    _read_packet_file, _validate_w2_packet, _validate_w3_packet,
    stage_research_packet,
)


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_manifest(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("owner case manifest must be a regular local file")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_PACKET_BYTES:
        raise ValueError("case manifest exceeds bounded input policy")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("case manifest must be UTF-8 JSON") from exc
    if not isinstance(obj, dict) or obj.get("schema") != "TRM074_COLD_CASE_V1":
        raise ValueError("unsupported case manifest schema")
    if obj.get("publication_send") != "DISALLOWED":
        raise ValueError("external send must remain DISALLOWED")
    return obj, _digest(raw)


def execute_factory_source_stage(
    manifest_path: Path | str,
    storage_root: Path | str,
    *,
    research_packet_path: Path | str | None = None,
    research_packet_paths: list[Path | str] | None = None,
    venue_route_packet_paths: list[Path | str] | None = None,
    litops_root: Path | str | None = None,
    native_capture_root: Path | str | None = None,
    manual_w1_reopen: bool = False,
) -> dict[str, Any]:
    """Compose installed components with exact input pins and idempotent readback.

    Replays are safe after failure: each child is persistent and idempotent.
    Research input may be omitted for a new source corpus. W1 requires
    explicitly pinned manual W1 notebook and author-HOLD source evidence.
    """
    manifest_path = Path(manifest_path)
    storage = Path(storage_root).resolve()
    case, manifest_sha = _safe_manifest(manifest_path)
    case_id = str(case.get("case_id", ""))
    if not case_id or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
                              for c in case_id):
        raise ValueError("invalid case identity")
    if manifest_path.resolve().is_relative_to(storage):
        raise ValueError("private input manifest must not be generated inside output storage")
    research_paths = (
        ([Path(research_packet_path)] if research_packet_path is not None else [])
        + [Path(x) for x in (research_packet_paths or [])]
    )
    if len(research_paths) > 8:
        raise ValueError("research-wave count exceeds bounded operator stage")
    research_pins: list[dict[str, str]] = []
    wave_ids: set[str] = set()
    for research_path in research_paths:
        packet, raw = _read_packet_file(research_path)
        schema = str(packet.get("schema") or "")
        if schema == PACKET_SCHEMA:
            _validate_w2_packet(packet)
        elif schema == PACKET_SCHEMA_W3:
            _validate_w3_packet(packet)
        elif schema == PACKET_SCHEMA_W4:
            if (packet.get("author_decision") != "HOLD"
                    or packet.get("world_mutation") is not False
                    or packet.get("article_seed_created") is not False
                    or packet.get("external_send") != "DISABLED"):
                raise ValueError("W4 packet cannot bypass scientific source/owner gate")
            if Path(str(packet.get("private_packet_path") or "")).resolve() != research_path.resolve():
                raise ValueError("W4 packet private source path does not identify input bytes")
        else:
            raise ValueError("unsupported research packet schema")
        if packet.get("case_id") != case_id:
            raise ValueError("external research packet belongs to a different case")
        wave = str(packet.get("wave_id") or "")
        if wave in wave_ids:
            raise ValueError("duplicate research-wave ID in one factory invocation")
        wave_ids.add(wave)
        research_pins.append({
            "wave_id": wave, "schema": schema,
            "source_packet_sha256": _digest(raw),
        })
    research_sha = research_pins[0]["source_packet_sha256"] if len(research_pins) == 1 else None
    research_set_sha = _digest(_canonical({"waves": research_pins})) if research_pins else None
    venue_paths = [Path(x) for x in (venue_route_packet_paths or [])]
    if len(venue_paths) > 80:
        raise ValueError("venue-route batch exceeds bounded operator stage")
    venue_pins: list[dict[str, str]] = []
    route_keys: set[tuple[str, str]] = set()
    for venue_path in venue_paths:
        route_raw = venue_path.read_bytes()
        if not 0 < len(route_raw) <= 75_000:
            raise ValueError("venue route packet exceeds bounded input policy")
        route = json.loads(route_raw.decode("utf-8"))
        if route.get("schema") != "TRM073_W12_SOURCE_VENUE_ROUTE_INPUT_V1":
            raise ValueError("unknown or unsupported W12 route schema")
        if route.get("case_id") != case_id:
            raise ValueError("W12 route belongs to another source case")
        pair = (str(route.get("claim_version_id") or ""), str(route.get("journal_id") or ""))
        if not all(pair) or pair in route_keys:
            raise ValueError("duplicate or empty claim-version/journal pairing")
        route_keys.add(pair)
        venue_pins.append({"route_candidate_id": str(route.get("route_candidate_id") or ""),
                           "source_packet_sha256": _digest(route_raw)})
    venue_set_sha = _digest(_canonical({"venue_routes": venue_pins})) if venue_pins else None
    if litops_root is not None:
        if not os.environ.get("LITOPS_SKIP_DOTENV"):
            raise ValueError("isolated LitOps requires LITOPS_SKIP_DOTENV")
        if Path(litops_root).resolve() == storage:
            raise ValueError("LitOps registry must use a distinct isolated target")
    # Host-native Google Docs intake reuses immutable TRM040 source snapshots.
    # Pinned per-source checkpoint resumes partial 429/fetch failures without
    # repeating completed reads, and NEVER silently refreshes a prior revision.
    native_count = new_native_captures = reused_native_captures = 0
    derived_manifest_sha = None
    modes = {s.get("capture_transport") for s in case.get("sources", [])}
    if any(mode not in {None, "local", "native_docs"} for mode in modes):
        raise ValueError("unsupported source capture transport")
    if "native_docs" in modes:
        if native_capture_root is None:
            raise ValueError("native Docs input requires explicit private capture root")
        capture_root = Path(native_capture_root).resolve()
        if capture_root.is_relative_to(storage) or storage.is_relative_to(capture_root):
            raise ValueError("native captures and Factory storage must be isolated")
        if manifest_path.resolve().is_relative_to(capture_root):
            raise ValueError("original source manifest must be outside materialized native capture root")
        from ..integrations.native_docs_capture import materialize_native_manifest
        manifest_path, native_count, new_native_captures, reused_native_captures = (
            materialize_native_manifest(case, manifest_sha, capture_root)
        )
        case, derived_manifest_sha = _safe_manifest(manifest_path)

    report_file = storage / "factory_research_cases" / case_id / "source_stage_receipt.json"
    if report_file.exists():
        previous = json.loads(report_file.read_text(encoding="utf-8"))
        if (previous.get("input_manifest_sha256") != manifest_sha
                or previous.get("research_packet_sha256") != research_sha
                or previous.get("research_set_sha256") != research_set_sha
                or previous.get("venue_route_set_sha256") != venue_set_sha):
            raise ValueError("immutable case checkpoint pins different source/research bytes")
        case_file = storage / "talk_corpora" / case_id / "case_ledger.json"
        if not case_file.is_file() or _digest(case_file.read_bytes()) != previous.get("source_ledger_sha256"):
            raise ValueError("prior case checkpoint's corpus ledger was replaced or lost")
        # The manifest may be byte-identical while a private file it points
        # to has changed. Re-read each input with the EXISTING source adapter
        # before any new registry mutation. File names and mtime are not proof.
        from ..adapters.source_intake import register_local_source, SourceRole
        old_sources = {
            s["source_id"]: s for s in json.loads(case_file.read_text(encoding="utf-8"))["source_snapshots"]
        }
        for source in case.get("sources", []):
            pin = old_sources.get(source["source_id"])
            if pin is None:
                raise ValueError("immutable checkpoint is missing a manifest source identity")
            snapshot, observed_text = register_local_source(
                Path(source["local_path"]),
                role=SourceRole.BACKGROUND_RESEARCH,
                source_id=source["source_id"],
            )
            if source.get("read_coverage") == "STRUCTURAL_TEXT_PROJECTION_COMMENTS_NOT_ACQUIRED":
                from ..integrations.native_docs_capture import verify_native_source
                verify_native_source(source)
            if (snapshot.extraction_status != "extracted"
                    or _digest(observed_text.encode("utf-8")) != pin["content_sha256"]):
                raise ValueError("immutable checkpoint source content changed or disappeared")

    intake = run_case(manifest_path, storage)
    stage = export_talk_research_evidence(storage, case_id)
    w1 = propose_w1_return(storage, case_id) if manual_w1_reopen else None
    wave_receipts = [
        stage_research_packet(path, storage) for path in research_paths
    ]
    by_schema = {
        pin["schema"]: [receipt for p, receipt in zip(research_pins, wave_receipts)
                         if p["schema"] == pin["schema"]]
        for pin in research_pins
    }
    w2 = (by_schema.get(PACKET_SCHEMA) or [None])[0]
    w3 = (by_schema.get(PACKET_SCHEMA_W3) or [None])[0]
    w4 = (by_schema.get(PACKET_SCHEMA_W4) or [None])[0]
    from .trm073_w12_route_stage import stage_w12_research_route
    venue_receipts = [stage_w12_research_route(path, storage) for path in venue_paths]
    litops = (
        admit_talk_context_into_installed_litops(storage, litops_root, case_id)
        if litops_root is not None else None
    )

    graph = OpportunityGraphStore(storage)
    if graph.list_records("ArticleSeed") or graph.list_records("World"):
        raise ValueError("source-stage workspace contains unapproved ArticleSeed or World records")
    if graph.list_records("OpportunityRoute") or graph.list_records("ArticleOpportunity"):
        raise ValueError("source stage must not create or inherit publishable opportunities")
    case_ledger = storage / "talk_corpora" / case_id / "case_ledger.json"
    if _digest(case_ledger.read_bytes()) != intake["ledger_sha256"]:
        raise ValueError("source ledger readback mismatch")
    if len(graph.list_records("Evidence")) < stage["evidence_count"]:
        raise ValueError("source Evidence lost during research staging")

    receipt = {
        "schema": "FACTORY_SOURCE_RESEARCH_STAGE_V1",
        "case_id": case_id,
        "input_manifest_sha256": manifest_sha,
        "native_source_count": native_count,
        "derived_manifest_sha256": derived_manifest_sha,
        "native_replay_policy": "IMMUTABLE_PIN_NO_PROVIDER_RECHECK",
        "research_packet_sha256": research_sha,
        "research_set_sha256": research_set_sha,
        "venue_route_set_sha256": venue_set_sha,
        "venue_route_packets": venue_pins,
        "venue_route_receipts": [
            {"route_candidate_id": pin["route_candidate_id"],
             "receipt_sha256": receipt["receipt_sha256"],
             "readback_verified": receipt["readback"]["verified"]}
            for pin, receipt in zip(venue_pins, venue_receipts)
        ],
        "research_packet_pins": research_pins,
        "research_wave_receipts": [
            {"wave_id": pin["wave_id"], "schema": pin["schema"],
             "receipt_sha256": result["receipt_sha256"],
             "readback_sha256": result["readback_sha256"],
             "counts": result["counts"]}
            for pin, result in zip(research_pins, wave_receipts)
        ],
        "source_ledger_sha256": intake["ledger_sha256"],
        "research_handoff_sha256": stage["handoff_sha256"],
        "manual_w1_reopen_sha256": w1["sha256"] if w1 else None,
        "research_wave_receipt_sha256": w2["receipt_sha256"] if w2 else None,
        "litops_whitecrow_receipt_sha256": litops["sha256"] if litops else None,
        "source_snapshots_count": intake["source_count"],
        "discussion_event_count": intake["discussion_events"],
        "kairon_evidence_count": len(graph.list_records("Evidence")),
        "w1_return_proposals": w1["count"] if w1 else 0,
        "w2_return_proposals": (w2.get("counts", {}).get("field_reopen_proposals", 0) if w2 else 0),
        "w3_return_proposals": (w3.get("counts", {}).get("field_reopen_proposals", 0) if w3 else 0),
        "w3_proposed_unqualified_routes": (w3.get("counts", {}).get("proposed_routes", 0) if w3 else 0),
        "w4_scientific_challenges": (w4.get("counts", {}).get("scientific_challenges", 0) if w4 else 0),
        "w4_rejected_comparators": (w4.get("counts", {}).get("rejected_comparator_trails", 0) if w4 else 0),
        "w4_field_reopen_proposals": (w4.get("counts", {}).get("field_reopen_proposals", 0) if w4 else 0),
        "w4_held_article_hypotheses": (w4.get("counts", {}).get("article_versions_proposed_held", 0) if w4 else 0),
        "whitecrow_context_packs": (litops["whitecrow_imported"] if litops else 0),
        "whitecrow_status": (
            "CONTEXT_ONLY_SCIENCE_HOLD" if litops else "NOT_RUN"
        ),
        "indago_new_hunt": "NOT_RUN_EXISTING_MANUAL_RESEARCH_ONLY",
        "w12_equivalent_routes": sum(
            int(receipt["counts"]["W12_EQUIVALENT_HELD"]) for receipt in venue_receipts
        ),
        "qualified_targetworld": 0,
        "article_seed_created": 0,
        "author_approved": False,
        "world_mutated": False,
        "external_send": "DISABLED",
        "full_real_case_accepted": False,
        "production_deployed": False,
    }
    encoded = _canonical(receipt)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    temp = report_file.with_suffix(".tmp")
    temp.write_bytes(encoded)
    os.replace(temp, report_file)
    if report_file.read_bytes() != encoded:
        raise ValueError("factory receipt durable readback mismatch")
    return {
        "receipt_path": str(report_file),
        "receipt_sha256": _digest(encoded),
        "source_count": receipt["source_snapshots_count"],
        "kairon_evidence_count": receipt["kairon_evidence_count"],
        "whitecrow_context_packs": receipt["whitecrow_context_packs"],
        "manual_w1_proposals": receipt["w1_return_proposals"],
        "w2_proposals": receipt["w2_return_proposals"],
        "w3_proposals": receipt["w3_return_proposals"],
        "w3_proposed_unqualified_routes": receipt["w3_proposed_unqualified_routes"],
        "w4_scientific_challenges": receipt["w4_scientific_challenges"],
        "w4_rejected_comparators": receipt["w4_rejected_comparators"],
        "w4_field_reopen_proposals": receipt["w4_field_reopen_proposals"],
        "w4_held_article_hypotheses": receipt["w4_held_article_hypotheses"],
        "w12_equivalent_routes_held": receipt["w12_equivalent_routes"],
        "research_wave_count": len(research_pins),
        "new_source_snapshots": intake["new_source_snapshots"],
        "new_native_captures": new_native_captures,
        "reused_native_captures": reused_native_captures,
        "new_discussion_events": intake["new_discussion_events"],
        "new_whitecrow_sources": litops["new_sources"] if litops else None,
        "new_whitecrow_contexts": litops["new_context_packs"] if litops else None,
        "article_seed_created": 0,
        "external_send": "DISABLED",
    }
