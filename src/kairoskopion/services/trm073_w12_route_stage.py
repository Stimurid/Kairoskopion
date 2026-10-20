"""First W12-equivalent *research-route* admission over existing W3/Kairon graph.

A route-qualified research opportunity is NOT an ArticleSeed, manuscript,
full Publisher TargetWorld, author decision or right to submit. Its
evidence is rechecked from real user source and immutable publisher bytes
on replay. This local stage performs zero network calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from typing import Any

from ..adapters.venue.guidelines_extractor import _strip
from ..kairon_provider.opportunity_graph import OpportunityGraphStore


SCHEMA = "TRM073_W12_SOURCE_VENUE_ROUTE_INPUT_V1"
_RECEIPT = "TRM073_W12_SOURCE_VENUE_ROUTE_RECEIPT_V1"
MAX_BYTES = 75_000


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _file(path: str | Path, bound: int) -> bytes:
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise ValueError("pinned evidence file is missing or a symlink")
    if not (0 < p.stat().st_size <= bound):
        raise ValueError("pinned evidence file is outside byte limits")
    return p.read_bytes()


def _pin_bytes(path: str | Path, expected: str, bound: int) -> bytes:
    raw = _file(path, bound)
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected or "")) or _sha(raw) != expected:
        raise ValueError("pinned evidence byte SHA mismatch")
    return raw


def _url(url: str, host: str) -> str:
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname != host or p.username or p.password:
        raise ValueError("publisher source URL must be exact authorized HTTPS host")
    if len(url) > 1500 or p.fragment:
        raise ValueError("publisher evidence URL unsafe")
    return url


def _anchor(text: str, quote: str, kind: str) -> dict[str, Any]:
    if not isinstance(quote, str) or len(quote) < 48 or len(quote) > 1000:
        raise ValueError(f"{kind} quote outside bounded evidence limits")
    start = text.find(quote)
    if start < 0 or text.count(quote) != 1:
        raise ValueError(f"{kind} source quote missing or ambiguous")
    return {"start_character": start, "end_character": start + len(quote),
            "quote_sha256": _sha(quote.encode("utf-8")),
            "scope": kind}


def _source(raw: bytes, quote: str, version: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError("original source must be extracted UTF-8") from exc
    anch = _anchor(text, quote, "SOURCE_TEXT")
    line_no = text[:anch["start_character"]].count("\n") + 1
    if line_no <= 0 or version == "":
        raise ValueError("unversioned source quote")
    return {"source_sha256": _sha(raw), "quote": anch, "line": line_no}


def _raw_publisher_evidence(
    capture_manifest: dict[str, Any], kind: str,
    source_url: str, html_host: str, quote: str,
) -> dict[str, Any]:
    cap = capture_manifest.get(kind)
    if not isinstance(cap, dict) or cap.get("status") != "validated":
        raise ValueError(f"{kind}: actual publisher HTML was not acquired and validated")
    if not isinstance(cap.get("validation"), dict) or not cap["validation"].get("valid"):
        raise ValueError(f"{kind}: unvalidated content cannot qualify route")
    if cap.get("content_type", "").split(";")[0].strip().lower() != "text/html":
        raise ValueError(f"{kind}: publisher evidence is not HTML")
    _url(source_url, html_host)
    if cap.get("url") != source_url:
        raise ValueError(f"{kind}: publisher URL does not match authenticated capture")
    data = _pin_bytes(cap["path"], cap["sha256"], 4 * 1024 * 1024)
    if cap.get("readback_sha256") != _sha(data):
        raise ValueError(f"{kind}: native acquisition receipt SHA/readback mismatch")
    # A downloaded HTML source is not ipso facto a FULL scholarly reading.
    read_text = _strip(data.decode("utf-8", errors="replace"))
    anch = _anchor(read_text, quote, kind)
    return {"url": source_url, "source_sha256": _sha(data),
            "anchor": anch, "read_depth": "SELECTED_SECTIONS",
            "html_bytes_acquired": len(data)}


def _validate(packet: dict[str, Any], graph: OpportunityGraphStore) -> dict[str, Any]:
    if packet.get("schema") != SCHEMA:
        raise ValueError("unsupported research-route schema")
    if packet.get("author_gate") != "HOLD" or packet.get("article_seed_created") is not False:
        raise ValueError("cannot invent ArticleSeed or author approval")
    if packet.get("world_mutation") is not False or packet.get("external_send") != "DISABLED":
        raise ValueError("publication and World changes not authorized")
    if packet.get("scientific_status") != "OPPONENT_GROUNDED_AUTHOR_REVIEW_PENDING":
        raise ValueError("cannot claim independent scientific acceptance")
    if packet.get("route_type") != "REGULAR_ROLLING":
        raise ValueError("regular-submission claim must have exact route type")
    if packet.get("deadline") is not None or packet.get("current_cfp") is not False:
        raise ValueError("regular journal route cannot be disguised as special CFP")
    if packet.get("coauthor_consent") != "UNVERIFIED":
        raise ValueError("coauthor approval cannot be synthesized")
    case_id = str(packet.get("case_id") or "")
    wave_id = str(packet.get("wave_id") or "")
    route_id = str(packet.get("route_candidate_id") or "")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{3,100}", t)
               for t in [case_id, wave_id, route_id]):
        raise ValueError("route/case/wave identity invalid")
    if str(packet.get("claim_version_id") or "").strip() == "":
        raise ValueError("independent claim/version identity required")
    if str(packet.get("head_id") or "").strip() == "":
        raise ValueError("source head identity required")
    journal = str(packet.get("journal_name") or "")
    if not journal or not str(packet.get("journal_id") or ""):
        raise ValueError("canonical journal identity missing")
    source = packet.get("original_source") or {}
    if not isinstance(source, dict) or not source.get("source_id", "").startswith("drive:"):
        raise ValueError("exact original Drive source ID required")
    if not source.get("source_version") or not source.get("path") or not source.get("sha256"):
        raise ValueError("source version/raw source bytes must be pinned")
    evidence = _source(
        _pin_bytes(source["path"], source["sha256"], 4 * 1024 * 1024),
        source.get("anchor_quote", ""), source["source_version"],
    )
    if int(source.get("anchor_line") or -1) != evidence["line"]:
        raise ValueError("original source quote line locator changed")
    evidence.update({"source_id": source["source_id"],
                     "version": source["source_version"]})
    # Source identity and accepted version must already exist in the
    # actual three-talk Factory corpus, not merely in the caller's packet.
    ledger_path = graph.root.parents[1] / "talk_corpora" / case_id / "case_ledger.json"
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise ValueError("prior Factory case ledger unavailable")
    ledger = json.loads(_file(ledger_path, 2_000_000).decode("utf-8"))
    original_matches = [
        s for s in ledger.get("source_snapshots", [])
        if s.get("source_id") == source["source_id"]
        and s.get("version") == source["source_version"]
    ]
    if len(original_matches) != 1:
        raise ValueError("versioned original source is not uniquely bound to admitted Factory corpus")
    graph_sources = [
        r for r in graph.list_records("Evidence")
        if r.get("source_ref") == source["source_id"]
    ]
    if not graph_sources:
        raise ValueError("no existing Kairon original-source Evidence for route")
    graph_events = [
        x for x in graph.replay_events()
        if x.get("kind") == "SCHOLARLY_ROUTE_CHALLENGE"
        and x.get("route_candidate_id") == route_id
        and x.get("subject_id") == packet["head_id"]
        and x.get("journal_id") == packet["journal_id"]
    ]
    if len(graph_events) != 1:
        raise ValueError("route candidate is not uniquely staged by existing W3")
    event = graph_events[0]
    head_refs = [
        x for x in graph.replay_events()
        if x.get("kind") == "SOURCE_CONTRADICTION"
        and x.get("subject_id") == packet["head_id"]
        and isinstance(x.get("original_source_binding"), dict)
    ]
    certified = [
        x["original_source_binding"] for x in head_refs
        if x["original_source_binding"].get("source_id") == source["source_id"]
        and x["original_source_binding"].get("version") == source["source_version"]
        and str(x["original_source_binding"].get("content_sha256") or "").lower()
            == evidence["source_sha256"]
        and x["original_source_binding"].get("binding_verification") == "VERIFIED_BYTES"
    ]
    if len(certified) != 1:
        raise ValueError("prior W3 original versioned source byte binding not verified")
    if event.get("opponent_resolved") is not True:
        raise ValueError("W3 research opponent not resolved")
    if event.get("source_ref") != "doi:" + str(packet.get("opponent_doi")):
        raise ValueError("W3 exact scientific opponent DOI mismatch")
    if event.get("w12_equivalent") is not False:
        raise ValueError("earlier W3 must remain provisional and immutable")

    host = str(packet.get("official_host") or "")
    if host not in {"link.springer.com", "academic.oup.com", "www.tandfonline.com",
                    "journal.iphras.ru"}:
        raise ValueError("official publisher domain not in bounded allowlist")
    captures = json.loads(_file(packet.get("capture_manifest"), MAX_BYTES).decode("utf-8"))
    official = packet.get("official_evidence") or {}
    refs: dict[str, dict[str, Any]] = {}
    for kind in ("scope", "submission_policy", "published_opponent"):
        info = official.get(kind) or {}
        capture_key = info.get("capture_key")
        if not isinstance(capture_key, str) or not capture_key:
            raise ValueError(f"missing publisher evidence capture ref {kind}")
        refs[kind] = _raw_publisher_evidence(
            captures, capture_key, info.get("url", ""), host,
            info.get("anchor_quote", ""),
        )
    if refs["published_opponent"]["url"] != packet.get("opponent_url"):
        raise ValueError("journal-native published opponent URL mismatch")
    if str(packet.get("opponent_doi") or "") not in _strip(
        _pin_bytes(captures[official["published_opponent"]["capture_key"]]["path"],
                   captures[official["published_opponent"]["capture_key"]]["sha256"],
                   4 * 1024 * 1024).decode("utf-8", errors="replace")
    ):
        raise ValueError("opponent DOI absent from publisher page")
    if len({v["source_sha256"] for v in refs.values()}) != 3:
        raise ValueError("identical publisher pages cannot self-certify three evidence roles")

    for lang in ("ru", "en"):
        prose = str((packet.get("target_thesis") or {}).get(lang) or "").strip()
        if len(prose.split()) < 75 or len(prose) > 6_000:
            raise ValueError(f"venue-specific {lang} thesis lacks substantive research content")
    analysis = packet.get("opponent_analysis") or {}
    for key in ("strongest_objection", "source_distinction", "empirical_falsifier",
                "methodological_plan", "admissible_source_change", "negative_evidence"):
        if len(str(analysis.get(key) or "").strip()) < 60:
            raise ValueError(f"research route missing explicit {key}")
    if (packet.get("rights_gate") != "OWNER_REVIEW_PENDING"
            or packet.get("author_decision") != "HOLD"):
        raise ValueError("copyright/author authorization pending")
    if packet.get("venue_submission_type") != "REGULAR_MANUSCRIPT":
        raise ValueError("special issue and regular submission cannot be conflated")
    observation = str(packet.get("publisher_observed_date") or "")
    try:
        observed = datetime.strptime(observation, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("official policy observation date must be explicit ISO date") from exc
    if observed > datetime.now(timezone.utc).date():
        raise ValueError("official policy cannot be observed in the future")
    return {"case_id": case_id, "wave_id": wave_id, "route_candidate_id": route_id,
            "journal_id": packet["journal_id"], "head_id": packet["head_id"],
            "claim_version_id": packet["claim_version_id"],
            "source": evidence, "official": refs,
            "W12_equivalent_held": True, "deep_targetworld_qualified": False}


def stage_w12_research_route(
    packet_path: Path | str, storage_root: Path | str,
) -> dict[str, Any]:
    """Stage only a scientifically contestable, source-pinned author-HOLD route."""
    path = Path(packet_path)
    raw = _file(path, MAX_BYTES)
    packet = json.loads(raw.decode("utf-8"))
    root = Path(storage_root)
    graph = OpportunityGraphStore(root)
    before = {k: graph.list_records(k) for k in ("World", "ArticleSeed", "OpportunityRoute")}
    safe = _validate(packet, graph)
    fingerprint = _sha(raw)
    key = _sha(("|".join([
        safe["case_id"], safe["claim_version_id"], safe["journal_id"]
    ])).encode("utf-8"))
    record_id = f"trm073-w12-route-{key[:24]}"
    previous_route = [x for x in graph.list_records("HuntTrace") if x["id"] == record_id]
    if any(x.get("revision") != "route:"+fingerprint for x in previous_route):
        raise ValueError("same claim-version/journal route already pins different input bytes")
    if len(previous_route) > 1:
        raise ValueError("duplicate route research records detected before admission")
    record = {
        "id": record_id,
        "revision": "route:"+fingerprint,
        "route_candidate_id": safe["route_candidate_id"],
        "claim_version_id": safe["claim_version_id"],
        "head_id": safe["head_id"],
        "journal_id": safe["journal_id"],
        "source_packet_sha256": fingerprint,
        "source_ref": safe["source"]["source_id"],
        "original_source_sha256": safe["source"]["source_sha256"],
        "journal_policy_pins": {
            k: v["source_sha256"] for k, v in safe["official"].items()
        },
        "research_qualification": "W12_EQUIVALENT_HELD_AUTHOR_REVIEW",
        "deep_targetworld_qualified": False,
        "article_seed_created": False,
        "world_mutated": False,
        "external_send": "DISABLED",
    }
    graph.put("HuntTrace", record)
    if any(graph.list_records(k) != before[k] for k in before):
        raise ValueError("W12 research qualification violated publication authority")
    report = {
        "schema": _RECEIPT,
        "case_id": safe["case_id"],
        "wave_id": safe["wave_id"],
        "route_id": record_id,
        "claim_version_id": safe["claim_version_id"],
        "journal_id": safe["journal_id"],
        "source_packet_sha256": fingerprint,
        "source_original_sha256": safe["source"]["source_sha256"],
        "source_anchor": safe["source"]["quote"],
        "source_line": safe["source"]["line"],
        "publisher_evidence": safe["official"],
        "source_read_depth": "EXACT_QUOTE_VERSION_PINNED",
        "opponent_read_depth": "SELECTED_SECTIONS_NOT_CERTIFIED_FULL_TEXT",
        "editorial_route_kind": "REGULAR_MANUSCRIPT",
        "readback_required": True,
        "counts": {"W12_EQUIVALENT_HELD": 1, "DEEP_QUALIFIED": 0,
                   "ARTICLE_SEED": 0, "AUTHOR_APPROVED": 0, "SEND": 0},
        "author_gate": "HOLD",
        "science_review": "OPPONENT_GROUNDED_AUTHOR_REVIEW_PENDING",
        "external_send": "DISABLED",
    }
    target = root / "research_stage" / safe["case_id"] / safe["wave_id"]
    target.mkdir(parents=True, exist_ok=True)
    receipt_path = target / "w12_route_receipt.json"
    encoded = _canonical(report)
    if receipt_path.is_file() and receipt_path.read_bytes() != encoded:
        raise ValueError("immutable route attempt cannot overwrite prior qualification")
    if not receipt_path.is_file():
        receipt_path.write_bytes(encoded)
    replay = readback_w12_research_route(packet_path, storage_root)
    return {"receipt_path": str(receipt_path), "receipt_sha256": _sha(encoded),
            "readback": replay, "counts": report["counts"]}


def readback_w12_research_route(packet_path: Path | str, storage_root: Path | str) -> dict[str, Any]:
    """Re-read every source and official provider byte; no receipt self-certification."""
    raw = _file(packet_path, MAX_BYTES)
    packet = json.loads(raw.decode("utf-8"))
    root = Path(storage_root)
    graph = OpportunityGraphStore(root)
    verified = _validate(packet, graph)
    receipt_path = root / "research_stage" / verified["case_id"] / verified["wave_id"] / "w12_route_receipt.json"
    receipt = json.loads(_file(receipt_path, 125_000).decode("utf-8"))
    if receipt.get("source_packet_sha256") != _sha(raw):
        raise ValueError("W12 route receipt source packet has been replaced")
    route_id = receipt["route_id"]
    stored = [x for x in graph.list_records("HuntTrace") if x["id"] == route_id]
    if len(stored) != 1 or stored[0].get("revision") != "route:"+_sha(raw):
        raise ValueError("W12 route graph revision missing or ambiguous")
    if (stored[0].get("research_qualification") != "W12_EQUIVALENT_HELD_AUTHOR_REVIEW"
            or stored[0].get("source_ref") != verified["source"]["source_id"]
            or stored[0].get("original_source_sha256") != verified["source"]["source_sha256"]
            or stored[0].get("journal_policy_pins") != {
                k: v["source_sha256"] for k, v in verified["official"].items()
            }):
        raise ValueError("W12 research route graph provenance tampered")
    if (receipt.get("publisher_evidence") != verified["official"]
            or receipt.get("source_anchor") != verified["source"]["quote"]
            or receipt.get("counts", {}).get("W12_EQUIVALENT_HELD") != 1):
        raise ValueError("W12 receipt passage anchors or counts tampered")
    return {"verified": True, "route_id": route_id, "w12_equivalent_held": 1,
            "deep_qualified": 0, "author_approved": 0, "external_send": "DISABLED",
            "receipt_sha256": _sha(_file(receipt_path, 125_000))}
