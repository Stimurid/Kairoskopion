"""W4 science-return receipt over the *existing* Kairon/Factory evidence graph.

Consumes exact owner-version and external manual research dossier bytes, ties
opposition to already-staged W3 paper refs, and proposes held FieldReopens.
A connector-relayed W4 research document is NEVER certified as a native TRM040
carrier, publisher full text, autonomous Indago hunt, author-approved manuscript
or production WORLD revision. No HTTP, new OAuth, World writes or journal sends.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from ..adapters.venue.fulltext_fetch import validate_download
from ..adapters.venue.guidelines_extractor import _strip
from ..kairon_provider.opportunity_graph import OpportunityGraphStore

SCHEMA = "TRM073_W4_SCHOLARLY_SOURCE_RETURN_INPUT_V1"
RECEIPT_SCHEMA = "TRM073_W4_SCHOLARLY_SOURCE_RETURN_RECEIPT_V1"
MAX_BYTES = 400_000
READ_DEPTHS = frozenset({"ABSTRACT_ONLY", "SELECTED_FULL_HTML", "METADATA_ONLY"})
RESULTS = frozenset({"SCIENTIFIC_OBJECTION_HELD", "REJECTED_READING_INSUFFICIENT"})
GENRES = frozenset({"RESEARCH", "EDITORIAL", "TARGET_ARTICLE", "REVIEW"})


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canon(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _safe_id(value: Any) -> str:
    s = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", s):
        raise ValueError("W4 scientific identity must be bounded and stable")
    return s


def _source_bytes(spec: dict[str, Any], *, max_bytes: int = 2_000_000) -> bytes:
    if not isinstance(spec, dict):
        raise ValueError("W4 source descriptor missing")
    filename = Path(str(spec.get("path") or ""))
    if filename.is_symlink() or not filename.is_file() or not 0 < filename.stat().st_size <= max_bytes:
        raise ValueError("W4 source file absent, symbolic or over limit")
    data = filename.read_bytes()
    expected = str(spec.get("sha256") or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or _sha(data) != expected:
        raise ValueError("W4 original or research-dossier source byte SHA mismatch")
    return data


def _anchor(raw_text: str, quote: Any, label: str, min_chars: int = 48) -> dict[str, Any]:
    if not isinstance(quote, str) or not min_chars <= len(quote) <= 900:
        raise ValueError(f"{label} anchored passage length invalid")
    loc = raw_text.find(quote)
    if loc < 0 or raw_text.count(quote) != 1:
        raise ValueError(f"{label} exact source passage missing or ambiguous")
    return {"quote_sha256": _sha(quote.encode("utf-8")),
            "start_char": loc, "line": raw_text[:loc].count("\n") + 1}


def _verify_head(graph: OpportunityGraphStore, source: dict[str, Any]) -> None:
    head_id = str(source.get("head_id") or "")
    source_id = str(source.get("source_id") or "")
    version = str(source.get("version") or "")
    exact_sha = str(source.get("sha256") or "").lower()
    if not head_id or not source_id.startswith("drive:") or not version:
        raise ValueError("W4 must preserve exact original Head/source/version")
    old_returns = [
        e for e in graph.replay_events()
        if e.get("kind") == "SOURCE_CONTRADICTION"
        and e.get("subject_id") == head_id
        and isinstance(e.get("original_source_binding"), dict)
        and e["original_source_binding"].get("binding_verification") == "VERIFIED_BYTES"
        and e["original_source_binding"].get("source_id") == source_id
        and e["original_source_binding"].get("version") == version
        and str(e["original_source_binding"].get("content_sha256") or "").lower() == exact_sha
    ]
    if len(old_returns) != 1:
        raise ValueError("W4 source has no unique W3 VERIFIED_BYTES original Head binding")
    direct = [r for r in graph.list_records("Evidence") if r.get("source_ref") == source_id]
    if not direct:
        raise ValueError("W4 source does not exist in prior Factory source evidence")


def _check_packet(packet: dict[str, Any], graph: OpportunityGraphStore) -> dict[str, Any]:
    if packet.get("schema") != SCHEMA:
        raise ValueError("unsupported W4 research packet schema")
    case_id = _safe_id(packet.get("case_id"))
    wave_id = _safe_id(packet.get("wave_id"))
    if packet.get("author_decision") != "HOLD" or packet.get("scientific_status") != "SOURCE_DISCUSSION_PROPOSAL":
        raise ValueError("W4 science/author decision must remain HOLD")
    if packet.get("article_seed_created") is not False or packet.get("world_mutation") is not False or packet.get("external_send") != "DISABLED":
        raise ValueError("W4 cannot create a manuscript, change WORLD or send a submission")
    dossier = packet.get("dossier") or {}
    if dossier.get("carrier") != "GOOGLE_DRIVE_CONNECTOR_CHAT_RELAY_NOT_NATIVE_TRM040":
        raise ValueError("W4 dossier may not self-certify TRM040 native acquisition")
    source_id = str(dossier.get("source_id") or "")
    if not re.fullmatch(r"drive:[A-Za-z0-9_-]{5,200}", source_id):
        raise ValueError("W4 research dossier requires fixed safe Drive object ID")
    dossier_bytes = _source_bytes(dossier)
    dossier_text = dossier_bytes.decode("utf-8-sig")
    if "CHAT_RESEARCH_FALLBACK_TO_FACTORY" not in dossier_text:
        raise ValueError("W4 chat-origin research dossier status not explicitly documented")
    original = packet.get("original_head") or {}
    original_bytes = _source_bytes(original)
    original_text = original_bytes.decode("utf-8-sig")
    base_anchor = _anchor(original_text, original.get("anchor_quote"), "original C04")
    if int(original.get("anchor_line") or 0) != base_anchor["line"]:
        raise ValueError("W4 original C04 source line changed")
    _verify_head(graph, original)

    challenges = packet.get("challenges")
    if not isinstance(challenges, list) or not 1 <= len(challenges) <= 12:
        raise ValueError("W4 source challenges must be a bounded nonempty list")
    ids = [_safe_id(x.get("challenge_id")) for x in challenges]
    if len(set(ids)) != len(ids):
        raise ValueError("W4 duplicate scientific challenge ID")
    evidence = graph.list_records("Evidence")
    verified: list[dict[str, Any]] = []
    for item in challenges:
        cid = _safe_id(item.get("challenge_id"))
        if item.get("head_id") != original["head_id"]:
            raise ValueError(f"{cid}: W4 scholarly return references wrong original Head")
        doi = str(item.get("opponent_doi") or "").strip()
        genre = str(item.get("genre") or "")
        depth = str(item.get("read_depth") or "")
        decision = str(item.get("result") or "")
        if genre not in GENRES or depth not in READ_DEPTHS or decision not in RESULTS:
            raise ValueError(f"{cid}: unsupported genre, read-depth or result")
        found = [x for x in evidence if x.get("source_ref") == "doi:"+doi]
        if len(found) != 1 or found[0].get("work_kind") != genre:
            raise ValueError(f"{cid}: no uniquely matching original W3 DOI/genre evidence")
        w3depth = found[0].get("read_depth")
        if decision == "SCIENTIFIC_OBJECTION_HELD":
            if genre != "RESEARCH":
                raise ValueError(f"{cid}: non-research comparator cannot qualify")
            if w3depth == "INDEX_ONLY" and depth != "SELECTED_FULL_HTML":
                raise ValueError(f"{cid}: W3 metadata alone cannot support scholarly objection")
            if depth == "METADATA_ONLY":
                raise ValueError(f"{cid}: metadata cannot qualify scientific opposition")
        if len(str(item.get("strongest_objection") or "")) < 75 or len(str(item.get("negative_evidence") or "")) < 75:
            raise ValueError(f"{cid}: opponent and negative evidence too short")
        if len(str(item.get("falsifier") or "")) < 75 or len(str(item.get("reopen_question") or "")) < 60:
            raise ValueError(f"{cid}: explicit test or source-return question missing")
        note_anchor = _anchor(dossier_text, item.get("dossier_anchor_quote"), cid+" dossier")
        paper_pin = None
        if depth == "SELECTED_FULL_HTML":
            publisher = item.get("publisher_capture")
            if not isinstance(publisher, dict):
                raise ValueError(f"{cid}: selected full HTML needs independent publisher byte capture")
            raw = _source_bytes(publisher, max_bytes=4 * 1024 * 1024)
            path = Path(publisher["path"])
            w3_sources = found[0].get("passage_anchors") or []
            w3_url = next((p.get("publisher_url") for p in w3_sources
                           if isinstance(p, dict) and p.get("publisher_url")), None)
            if publisher.get("url") != w3_url or not str(w3_url or "").startswith("https://"):
                raise ValueError(f"{cid}: publisher HTML URL not bound to prior native W3 locator")
            if path.suffix.lower() != ".html" or not validate_download(path, "text/html").get("valid"):
                raise ValueError(f"{cid}: publisher HTML is not a valid full carrier")
            html = raw.decode("utf-8", errors="replace")
            if doi.lower() not in _strip(html).lower():
                raise ValueError(f"{cid}: publisher page does not identify the cited DOI")
            passage = _anchor(_strip(html), publisher.get("anchor_quote"), cid+" publisher")
            paper_pin = {"source_sha256": _sha(raw), "passage": passage,
                         "official_url": publisher.get("url"),
                         "read_depth": "SELECTED_SECTIONS_NOT_FULLTEXT_CERTIFIED"}
        verified.append({"challenge_id": cid, "doi": doi,
                         "genre": genre, "w3_evidence_id": found[0]["id"],
                         "w3_depth": w3depth, "read_depth": depth,
                         "result": decision, "note_anchor": note_anchor,
                         "publisher": paper_pin})
    proposed = packet.get("candidate_article_version") or {}
    _safe_id(proposed.get("id"))
    if proposed.get("author_gate") != "HOLD" or proposed.get("status") != "ARTICLE_HYPOTHESIS":
        raise ValueError("W4 may only create author-HOLD article hypotheses")
    if len(str(proposed.get("theoretical_delta") or "")) < 80:
        raise ValueError("W4 proposed ArticleVersion missing defensible theoretical delta")
    return {
        "case_id": case_id, "wave_id": wave_id,
        "dossier_sha256": _sha(dossier_bytes),
        "source_sha256": _sha(original_bytes),
        "source_ref": original["source_id"],
        "original_anchor": base_anchor,
        "challenges": verified,
        "article_id": proposed["id"],
        "article_hypothesis_sha256": _sha(_canon(proposed)),
    }


def stage_w4_science_packet(packet: dict[str, Any], raw: bytes, storage: Path) -> dict[str, Any]:
    """Stage source-specific opposition, negative trails and article hypothesis."""
    from .trm073_research_stage import _checkpoint_reject, readback_research_stage
    graph = OpportunityGraphStore(storage)
    private_path = Path(str(packet.get("private_packet_path") or ""))
    if private_path.is_symlink() or not private_path.is_file() or private_path.read_bytes() != raw:
        raise ValueError("W4 private original research packet bytes cannot be independently read")
    checked = _check_packet(packet, graph)
    case_id, wave_id = checked["case_id"], checked["wave_id"]
    packet_sha = _sha(raw)
    _checkpoint_reject(storage, case_id, wave_id, packet_sha)
    baseline = {k: graph.list_records(k) for k in ("World", "ArticleSeed", "OpportunityRoute")}
    events, reopens = [], []
    for item, pinned in zip(packet["challenges"], checked["challenges"]):
        cid = pinned["challenge_id"]
        qualifying = pinned["result"] == "SCIENTIFIC_OBJECTION_HELD"
        eid = f"{case_id}:{wave_id}:{cid}:W4-SOURCE-RETURN"
        event = graph.append_event({
            "event_id": eid,
            "kind": "SOURCE_CONTRADICTION" if qualifying else "HUNT_RESULT",
            "subject_id": item["head_id"],
            "source_ref": "doi:"+pinned["doi"],
            "source_packet_sha256": packet_sha,
            "source_original_sha256": checked["source_sha256"],
            "dossier_source_sha256": checked["dossier_sha256"],
            "dossier_carrier": "CONNECTOR_CHAT_FALLBACK_NOT_NATIVE_TRM040",
            "opponent_read_depth": pinned["read_depth"],
            "w3_evidence_id": pinned["w3_evidence_id"],
            "dossier_anchor": pinned["note_anchor"],
            "publisher_capture": pinned["publisher"],
            "result": "CONTRADICTS_UNCONSTRAINED_ORIGINAL_CLAIM" if qualifying else "BLOCKED_READING_OR_GENRE_INSUFFICIENT",
            "intellectual_consequence": item["strongest_objection"],
            "negative_evidence": item["negative_evidence"],
            "falsifier": item["falsifier"],
            "next_action": item["reopen_question"],
            "author_decision": "HOLD",
            "semantic_mutation": "NONE",
        })
        events.append(event["event_id"])
        if qualifying:
            reopen = graph.propose_field_reopen(
                event["event_id"], reopen_level="L2",
                next_question=item["reopen_question"],
            )
            reopens.append(reopen["event_id"])
    trace_id = f"trm073-w4-claim-{checked['article_id']}"
    trace = graph.put("HuntTrace", {
        "id": trace_id, "revision": "w4-packet:"+packet_sha,
        "research_status": "SCIENTIFIC_ARTICLE_VERSION_PROPOSAL_HELD",
        "source_ref": checked["source_ref"],
        "source_sha256": checked["source_sha256"],
        "dossier_sha256": checked["dossier_sha256"],
        "article_version_id": checked["article_id"],
        "article_hypothesis_sha256": checked["article_hypothesis_sha256"],
        "author_gate": "HOLD", "World_change": "NONE", "ArticleSeed_created": False,
        "external_send": "DISABLED",
    })
    if any(graph.list_records(k) != baseline[k] for k in baseline):
        raise ValueError("W4 research exceeded World/ArticleSeed/route authority")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": case_id, "wave_id": wave_id,
        "source_packet_sha256": packet_sha,
        "private_packet_path": str(private_path),
        "dossier_sha256": checked["dossier_sha256"],
        "source_original_sha256": checked["source_sha256"],
        "dossier_carrier": "CONNECTOR_CHAT_FALLBACK_NOT_NATIVE_TRM040",
        "original_source_id": checked["source_ref"],
        "original_source_anchor": checked["original_anchor"],
        "challenge_refs": checked["challenges"],
        "challenge_event_ids": events,
        "reopen_event_ids": reopens,
        "article_hypothesis_record_id": trace["id"],
        "article_hypothesis_sha256": checked["article_hypothesis_sha256"],
        "counts": {
            "scientific_challenges": len(reopens),
            "rejected_comparator_trails": len(events)-len(reopens),
            "field_reopen_proposals": len(reopens),
            "article_versions_proposed_held": 1,
            "proposed_routes": 0,
            "w12_equivalent_routes": 0,
            "article_seeds_created": 0,
            "world_mutations": 0,
            "external_sends": 0,
        },
        "author_gate": "HOLD", "artikl_gate": "UNTESTED",
        "deep_qualified": False, "indago_runtime_hunt": False,
        "world_before": baseline["World"],
        "world_after": graph.list_records("World"),
        "article_seeds_before": baseline["ArticleSeed"],
        "article_seeds_after": graph.list_records("ArticleSeed"),
        "opportunity_routes_before": baseline["OpportunityRoute"],
        "opportunity_routes_after": graph.list_records("OpportunityRoute"),
    }
    folder = storage / "research_stage" / case_id / wave_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "receipt.json"
    encoded = _canon(receipt)
    if path.is_file() and path.read_bytes() != encoded:
        raise ValueError("W4 frozen receipt cannot be replaced")
    if not path.is_file():
        path.write_bytes(encoded)
    readback = readback_research_stage(storage, case_id, wave_id)
    return {
        "status": "PROVISIONAL_RESEARCH_STAGED",
        "receipt_path": str(path), "receipt_sha256": _sha(encoded),
        "readback_sha256": readback["readback_sha256"], "counts": receipt["counts"],
    }


def readback_w4(storage: Path, case_id: str, wave_id: str,
                receipt: dict[str, Any], raw: bytes) -> dict[str, Any]:
    """Cold verification rereads BOTH private source carriers + W3 DOI edges."""
    graph = OpportunityGraphStore(storage)
    packet_sha = receipt["source_packet_sha256"]
    packet_path = receipt.get("private_packet_path")
    original_packet = _source_bytes({"path": packet_path, "sha256": packet_sha},
                                   max_bytes=MAX_BYTES)
    original = json.loads(original_packet.decode("utf-8"))
    verified = _check_packet(original, graph)  # Re-hash W4 dossier, C04 and every paper capture
    if (verified["dossier_sha256"] != receipt["dossier_sha256"]
            or verified["source_sha256"] != receipt["source_original_sha256"]
            or verified["original_anchor"] != receipt["original_source_anchor"]
            or verified["challenges"] != receipt["challenge_refs"]
            or verified["article_hypothesis_sha256"] != receipt["article_hypothesis_sha256"]):
        raise ValueError("W4 cold readback source/publisher/claim pins changed")
    events = graph.replay_events()
    by_id = {e["event_id"]: e for e in events}
    for ref in receipt["challenge_refs"]:
        cid = ref["challenge_id"]
        key = f"{case_id}:{wave_id}:{cid}:W4-SOURCE-RETURN"
        e = by_id.get(key)
        if not e or e.get("source_packet_sha256") != packet_sha or e.get("dossier_source_sha256") != receipt["dossier_sha256"]:
            raise ValueError("W4 independently replayed evidence event absent or changed")
        if e.get("dossier_anchor") != ref["note_anchor"] or e.get("publisher_capture") != ref["publisher"]:
            raise ValueError("W4 publisher/dossier event provenance changed")
        if e.get("author_decision") != "HOLD" or e.get("semantic_mutation") != "NONE":
            raise ValueError("W4 event attempted authority promotion")
    if not set(receipt["reopen_event_ids"]).issubset(by_id):
        raise ValueError("W4 research reopen events missing")
    if len(receipt["challenge_refs"]) != len(receipt["challenge_event_ids"]):
        raise ValueError("W4 challenge/event inventory changed")
    accepted = sum(ref["result"] == "SCIENTIFIC_OBJECTION_HELD"
                   for ref in receipt["challenge_refs"])
    if (accepted != len(receipt["reopen_event_ids"])
            or accepted != receipt["counts"]["scientific_challenges"]
            or len(receipt["challenge_refs"]) - accepted != receipt["counts"]["rejected_comparator_trails"]):
        raise ValueError("W4 source science counters inconsistent")
    claims = [x for x in graph.list_records("HuntTrace") if x["id"] == receipt["article_hypothesis_record_id"]]
    if len(claims) != 1 or claims[0].get("article_hypothesis_sha256") != receipt["article_hypothesis_sha256"]:
        raise ValueError("W4 article hypothesis lost or changed")
    if (graph.list_records("World") != receipt["world_after"]
            or graph.list_records("ArticleSeed") != receipt["article_seeds_after"]
            or graph.list_records("OpportunityRoute") != receipt["opportunity_routes_after"]
            or receipt["world_before"] != receipt["world_after"]
            or receipt["article_seeds_before"] != receipt["article_seeds_after"]
            or receipt["opportunity_routes_before"] != receipt["opportunity_routes_after"]):
        raise ValueError("W4 independent authority isolation failed")
    return {
        "schema": "TRM073_W4_SCIENCE_READBACK_V1",
        "case_id": case_id, "wave_id": wave_id,
        "receipt_sha256": _sha(raw), "source_packet_sha256": packet_sha,
        "verified": True,
        "challenge_count": receipt["counts"]["scientific_challenges"],
        "reopen_count": len(receipt["reopen_event_ids"]),
        "rejected_count": receipt["counts"]["rejected_comparator_trails"],
        "proposed_article_versions": 1,
        "w12_equivalent_routes": 0, "ArticleSeed_created": 0,
        "world_mutations": 0, "external_sends": 0,
        "provider_mode": receipt["dossier_carrier"],
    }
