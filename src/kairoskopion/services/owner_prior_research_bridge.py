"""Re-admit a verified private earlier research trial into the SAME Factory graph.

Scope is an already executed L3_CORPUS_FACTORY_TRIAL_RECEIPT_V3. Do not
re-run another research engine, synthesize literature or promote author work.
Every source, W2 note, journal comparator and legacy graph event is reopened
by source hash. Output = provisional research note, two indexed DOI pointers,
one field reopen and explicit HOLD. Never original journal fulltext, new
ArticleSeed, deep VenueWorld, autonomous Indago, or submission rights.
"""
from __future__ import annotations

from hashlib import sha256
from contextlib import contextmanager
import json
import os
import stat
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..kairon_provider.opportunity_graph import OpportunityGraphStore

SCHEMA = "TRM074_OWNER_LEGACY_SCIENCE_BRIDGE_RECEIPT_V1"
SOURCE_SCHEMA = "L3_CORPUS_FACTORY_TRIAL_RECEIPT_V3"
READBACK_SCHEMA = "L3_CORPUS_FACTORY_TRIAL_READBACK_V3"
MAX_BYTES = 3_000_000


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canon(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _fp(items: list[dict[str, Any]], field: str) -> dict[str, Any]:
    ordered = sorted(items, key=lambda r: (str(r.get(field, "")), str(r.get("revision", ""))))
    return {"count": len(ordered), "sha256": _sha(_canon(ordered))}


def _private_file(path: str | Path, upper: int = MAX_BYTES) -> bytes:
    if not isinstance(path, (str, Path)) or not str(path):
        raise ValueError("owner private source path/locator missing")
    p = Path(path)
    if ".." in p.parts:
        raise ValueError("owner private source parent traversal is forbidden")
    # Inspect the lexical path, not Path.resolve(), which would conceal a
    # symlink or a Windows directory junction in an otherwise pinned path.
    probe = p if p.is_absolute() else Path.cwd() / p
    while True:
        try:
            attrs = probe.lstat()
        except OSError as exc:
            raise ValueError("owner private frozen source/receipt absent or unsafe") from exc
        if (stat.S_ISLNK(attrs.st_mode)
                or getattr(attrs, "st_file_attributes", 0)
                   & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError("owner private path traverses symlink/junction")
        if probe.parent == probe:
            break
        probe = probe.parent
    if not p.is_file() or not 0 < p.stat().st_size <= upper:
        raise ValueError("owner private frozen source/receipt absent or unsafe")
    data = p.read_bytes()
    if not 0 < len(data) <= upper:
        raise ValueError("owner private frozen source/receipt changed during read")
    return data


def _legacy_evidence(
    receipt_path: Path, legacy_store: Path, factory_store: Path,
) -> dict[str, Any]:
    raw_receipt = _private_file(receipt_path)
    old = json.loads(raw_receipt.decode("utf-8"))
    if old.get("schema") != SOURCE_SCHEMA or old.get("l3_pass") is not False:
        raise ValueError("legacy owner research receipt schema or authority invalid")
    if old.get("case_id") != "L3-CORPUS-20261020":
        raise ValueError("legacy L3 receipt cannot be relabelled as another study")
    cnt = old.get("counts") or {}
    if (cnt.get("owner_sources_admitted") != 9
            or cnt.get("near_opponent_evidence") != 2
            or cnt.get("scientific_objections") != 1
            or cnt.get("field_reopen_proposals") != 1
            or any(cnt.get(k) != 0 for k in (
                "article_seeds", "opportunity_routes_persisted",
                "w12_equivalent_routes", "world_mutations", "external_sends"))):
        raise ValueError("legacy science receipt is not a bounded author-HOLD trial")
    rbmeta = old.get("readback_expected") or {}
    rb_path = Path(str(rbmeta.get("path") or ""))
    if (rb_path.resolve() != (legacy_store / "l3_factory" / old["case_id"]
                             / str(old.get("wave_id")) / "readback.json").resolve()):
        raise ValueError("legacy independent readback path not in owner storage")
    rb = json.loads(_private_file(rb_path).decode("utf-8"))
    if (rb.get("schema") != READBACK_SCHEMA or rb.get("verified") is not True
            or rb.get("receipt_sha256") != _sha(raw_receipt)
            or rb.get("case_id") != old["case_id"]
            or rb.get("l3_trial_sha256") != old.get("l3_trial_sha256")
            or rb.get("evidence_count") != 11
            or rb.get("objection_count") != 1 or rb.get("reopen_count") != 1):
        raise ValueError("legacy L3 independent readback not authentic or incomplete")
    case_id = old["case_id"]
    case_path = factory_store / "talk_corpora" / case_id / "case_ledger.json"
    fctreceipt = factory_store / "factory_research_cases" / case_id / "source_stage_receipt.json"
    if not case_path.is_file() or not fctreceipt.is_file():
        raise ValueError("same Factory did not admit owner source corpus yet")
    case = json.loads(_private_file(case_path).decode("utf-8"))
    owner_fct = json.loads(_private_file(fctreceipt).decode("utf-8"))
    if (case.get("case_id") != case_id or owner_fct.get("case_id") != case_id
            or owner_fct.get("source_snapshots_count") != 8
            or owner_fct.get("auxiliary_binary_count") != 1
            or owner_fct.get("article_seed_created") != 0
            or owner_fct.get("external_send") != "DISABLED"):
        raise ValueError("new Factory source and authority proof missing")
    src_index = {
        row["source_id"]: row for row in case.get("source_snapshots") or []
    }
    bin_index = {
        row["source_id"]: row for row in owner_fct.get("auxiliary_binary_pins") or []
    }
    owner_refs = old.get("owner_evidence_refs") or []
    if (len(src_index) != 8 or len(bin_index) != 1
            or len({s.get("snapshot_id") for s in case.get("source_snapshots") or []}) != 8):
        raise ValueError("current source corpus registry has extra or colliding source identities")
    if len(owner_refs) != 9 or len({r.get("source_ref") for r in owner_refs}) != 9:
        raise ValueError("legacy owner evidence identity coverage lost")
    for ref in owner_refs:
        actual = src_index.get(ref.get("source_ref"))
        sha = (actual or {}).get("raw_source_sha256") or (
            bin_index.get(ref.get("source_ref")) or {}).get("byte_sha256")
        if sha != ref.get("sha256"):
            raise ValueError("legacy owner raw source was changed or omitted from new Factory")

    graph = OpportunityGraphStore(legacy_store)
    if (graph.list_records("World") or graph.list_records("ArticleSeed")
            or graph.list_records("OpportunityRoute")):
        raise ValueError("legacy owner research graph contains unapproved publication authority")
    if (not isinstance(old.get("world_before"), dict)
            or not isinstance(old.get("article_seeds_before"), dict)
            or not isinstance(old.get("routes_before"), dict)
            or old["world_before"] != old.get("world_after")
            or old["article_seeds_before"] != old.get("article_seeds_after")
            or old["routes_before"] != old.get("routes_after")):
        raise ValueError("legacy source research receipt altered protected baseline")
    trial_sha = old.get("l3_trial_sha256")
    native = [x for x in graph.list_records("Evidence") if x.get("l3_trial_sha256") == trial_sha]
    journals = [x for x in graph.list_records("Journal") if x.get("l3_trial_sha256") == trial_sha]
    all_events = graph.replay_events()
    event_ids = (old.get("content_fingerprints") or {}).get("expected_scientific_event_ids") or []
    if len(event_ids) != 2 or len(event_ids) != len(set(event_ids)):
        raise ValueError("legacy source event identifiers absent or ambiguous")
    physical_ids = [x.get("event_id") for x in all_events]
    if (len(physical_ids) != len(set(physical_ids))
            or any(not isinstance(x, str) or not x or x != x.strip()
                   for x in physical_ids)):
        raise ValueError("legacy graph event duplication or invalid identity must fail closed")
    selected = [x for x in all_events if x.get("event_id") in event_ids]
    past_fp = old.get("content_fingerprints") or {}
    if (past_fp.get("schema") != "L3_FULL_CONTENT_FINGERPRINTS_V1"
            or _fp(native, "id") != past_fp.get("evidence")
            or _fp(journals, "id") != past_fp.get("journal")
            or _fp(selected, "event_id") != past_fp.get("scientific_events")):
        raise ValueError("legacy graph evidence content hashes changed or vanished")
    if (len(journals) != 1 or len(native) != 11 or len(selected) != 2
            or len({x["id"] for x in native}) != 11
            or len({x["id"] for x in journals}) != 1):
        raise ValueError("legacy graph cardinality or physical identity not trusted")
    old_events = [e for e in selected if e.get("kind") == "SOURCE_CONTRADICTION"]
    old_reopens = [e for e in selected if e.get("kind") == "FIELD_REOPEN_PROPOSAL"]
    if len(old_events) != 1 or len(old_reopens) != 1:
        raise ValueError("legacy exact objection and return not distinguishable")
    original_event, original_reopen = old_events[0], old_reopens[0]
    if (original_event.get("subject_id") != "F01_B09"
            or original_event.get("result") != "CONTRADICTORY_SCHOLARLY_OBJECTION"
            or original_reopen.get("source_event_id") != original_event["event_id"]
            or original_reopen.get("author_gate") != "AUTHOR_REVIEW_REQUIRED"
            or original_reopen.get("reopen_level") != "L2"):
        raise ValueError("legacy paper/source-return authority changed")
    opp_refs = old.get("opponent_evidence_refs") or []
    if (len(opp_refs) != 2
            or len({o.get("doi") for o in opp_refs}) != 2
            or original_event.get("source_ref") not in {"doi:"+x["doi"] for x in opp_refs}):
        raise ValueError("legacy published-opponent identities absent")
    native_index = {x["id"]: x for x in native}
    # On cold re-entry, a preserved receipt alone is not fresh source proof.
    # Re-read BOTH original owner bytes (all nine from the legacy graph) and
    # the 8 current local source snapshots from the actual Factory registry.
    # This is a byte integrity check, never a claim about DOCX comments or
    # interpretation of a historical XLSX workbook.
    snapshots_raw = _private_file(
        factory_store / "registries" / "source_snapshots.jsonl", upper=5_000_000
    )
    snapshots = [json.loads(line) for line in snapshots_raw.decode("utf-8").splitlines()
                 if line.strip()]
    by_snapshot = {x.get("snapshot_id"): x for x in snapshots}
    if len(by_snapshot) != len(snapshots):
        raise ValueError("current Factory source registry contains colliding snapshot IDs")
    for record in case.get("source_snapshots") or []:
        pinned = by_snapshot.get(record["snapshot_id"])
        if (pinned is None or pinned.get("source_id") != record["source_id"]
                or pinned.get("extraction_status") != "extracted"
                or not pinned.get("text_ref")):
            raise ValueError("current Factory source snapshot registry identity missing")
        if _sha(_private_file(pinned["text_ref"], upper=30_000_000)) != record.get("raw_source_sha256"):
            raise ValueError("current Factory private source raw bytes changed on cold readback")
    for ref in owner_refs:
        inherited = native_index.get(ref.get("id"))
        origin = (inherited.get("passage_anchors") or [{}])[0] if inherited else {}
        if (not inherited or inherited.get("source_ref") != ref.get("source_ref")
                or _sha(_private_file(origin.get("path_hint"),upper=30_000_000)) != ref.get("sha256")):
            raise ValueError("historical L3 owner source bytes changed or reference lost")
    for ref in opp_refs:
        olde = native_index.get(ref.get("id"))
        if (not olde or olde.get("source_ref") != "doi:"+str(ref.get("doi"))
                or olde.get("source_kind") != "PUBLISHED_ARTICLE"
                or olde.get("full_text_certified") is not False
                or (olde.get("passage_anchors") or [{}])[0].get("anchor_kind")
                    != "L3_W2_SCIENTIFIC_RETURN_METADATA"):
            raise ValueError("legacy opponent has no verified bounded metadata trail")
    key_map = {s.get("key"):s for s in case.get("source_snapshots") or []}
    src_b09 = key_map.get("F01_B09")
    src_w2 = key_map.get("L3_W2_source_venue_opponents")
    if not src_b09 or not src_w2 or src_b09.get("author_state") != "NOT_VERIFIED":
        raise ValueError("legacy source author HOLD or W2 note absent")
    # Freeze exact original W2 research-note passage, not a journal article.
    # The source compiler's SHA is independently rehashed by the current
    # Factory checkpoint; this adapter also reads the exact original file.
    private_file = next(
        (x for x in old.get("owner_evidence_refs",[]) if x.get("key")=="L3_W2_source_venue_opponents"),
        None,
    )
    if private_file is None:
        raise ValueError("historical W2 research note missing")
    original_record = native_index.get(private_file["id"])
    old_hint = (original_record.get("passage_anchors") or [{}])[0].get("path_hint")
    raw_note = _private_file(old_hint)
    if _sha(raw_note) != src_w2.get("raw_source_sha256"):
        raise ValueError("L3 research note actual owner bytes changed")
    note = raw_note.decode("utf-8-sig")
    note_line = next((line for line in note.splitlines() if line.startswith("SR-03 / F01 B09:")), None)
    if not note_line or "Spitale E04" not in note_line:
        raise ValueError("L3 source return lacks exact W2 SR-03 passage")
    anchor = note_line[:min(240,len(note_line))]
    if note.count(anchor) != 1:
        raise ValueError("L3 SR-03 passage anchor ambiguous")
    return {
        "source_receipt_sha256": _sha(raw_receipt),
        "source_readback_sha256": _sha(_private_file(rb_path)),
        "trial_sha256": trial_sha, "case_id": case_id,
        "old_graph_fingerprints": past_fp,
        "source_b09_id": src_b09["source_id"],
        "source_b09_raw_sha": src_b09["raw_source_sha256"],
        "source_w2_id": src_w2["source_id"],
        "source_w2_raw_sha": src_w2["raw_source_sha256"],
        "source_w2_line": next(i+1 for i,line in enumerate(note.splitlines()) if line.startswith("SR-03 / F01 B09:")),
        "source_w2_anchor_sha": _sha(anchor.encode("utf-8")),
        "opponents": [{"id":r["id"],"doi":r["doi"],"l3_anchor":r["l3_anchor"]} for r in opp_refs],
        "objection": original_event,
        "reopen": original_reopen,
        "journal_name": journals[0]["canonical_name"],
        "journal_id": journals[0]["id"],
    }


def _current_graph_fingerprint(graph: OpportunityGraphStore, case: str) -> dict[str, Any]:
    traces = [x for x in graph.list_records("HuntTrace")
              if x.get("owner_prior_receipt_case") == case]
    evidence = [x for x in graph.list_records("Evidence")
                if x.get("owner_prior_receipt_case") == case]
    all_events = graph.replay_events()
    original_ids = {
        x["event_id"] for x in all_events
        if x.get("owner_prior_receipt_case") == case
    }
    events = [x for x in all_events
              if x.get("owner_prior_receipt_case") == case
              or (x.get("kind") == "FIELD_REOPEN_PROPOSAL"
                  and x.get("source_event_id") in original_ids)]
    return {"HuntTrace": _fp(traces,"id"),"Evidence":_fp(evidence,"id"),
            "events":_fp(events,"event_id")}


@contextmanager
def _exclusive_prior_import(storage: Path, case_id: str):
    """One local graph writer; stale locks require human inspection."""
    directory = storage / "research_stage" / case_id / "L3-PRIOR-SCIENCE-IMPORT"
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".owner-prior-import.lock"
    token = f"{os.getpid()}:{uuid4().hex}"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("owner prior science writer is active or a lock needs inspection") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(token)
            out.flush()
            os.fsync(out.fileno())
        yield
    finally:
        if not lock.is_file() or lock.read_text(encoding="utf-8") != token:
            raise ValueError("owner prior science writer lock disappeared or changed")
        lock.unlink()


def import_owner_prior_science(
    receipt_path: str | Path, legacy_graph_root: str | Path,
    factory_storage_root: str | Path,
) -> dict[str, Any]:
    """Verify original source body first; then import under exclusive write lock."""
    receipt = Path(receipt_path)
    legacy = Path(legacy_graph_root)
    storage = Path(factory_storage_root)
    verified = _legacy_evidence(receipt, legacy, storage)
    with _exclusive_prior_import(storage, verified["case_id"]):
        return _import_owner_prior_science_unlocked(receipt, legacy, storage, verified)


def _import_owner_prior_science_unlocked(
    receipt: Path, legacy: Path, storage: Path, verified: dict[str, Any],
) -> dict[str, Any]:
    graph = OpportunityGraphStore(storage)
    baseline = {k:graph.list_records(k) for k in ("World","ArticleSeed","OpportunityRoute")}
    case_id = verified["case_id"]
    path = storage/"research_stage"/case_id/"L3-PRIOR-SCIENCE-IMPORT"/"receipt.json"
    pin = verified["source_receipt_sha256"]
    if path.is_file():
        old = json.loads(_private_file(path).decode("utf-8"))
        if old.get("source_receipt_sha256") != pin:
            raise ValueError("prior L3 science route checkpoint points to different receipt")
    # Intent is durable BEFORE any graph writes. A crash may leave provisional
    # evidence behind, but the absent completion receipt marks it INCOMPLETE.
    # The same CLI invocation resumes from these immutable identities; it
    # must never create an ArticleSeed or silently steal a stale writer lock.
    intent_path = path.with_name("intent.json")
    intent_bytes = _canon({
        "schema": "TRM074_PRIOR_SCIENCE_INTENT_V1",
        "case_id": case_id, "source_receipt_sha256": pin,
        "owner_note_sha256": verified["source_w2_raw_sha"],
        "author_gate": "HOLD",
        "semantic_status": "STAGING_UNTIL_COMPLETION_RECEIPT",
        "publication_send": "DISABLED",
    })
    if intent_path.exists() and intent_path.read_bytes() != intent_bytes:
        raise ValueError("owner prior import intent is pinned to other source bytes")
    if not intent_path.exists():
        intent_path.parent.mkdir(parents=True, exist_ok=True)
        intent_tmp = intent_path.with_suffix(".pending")
        intent_tmp.write_bytes(intent_bytes)
        os.replace(intent_tmp, intent_path)
    if intent_path.read_bytes() != intent_bytes:
        raise ValueError("owner prior science intent was not durably recorded")
    for work in verified["opponents"]:
        graph.put("Evidence", {
            "id": "trm074-l3-ref-"+_sha(("doi:"+work["doi"]).encode("utf-8"))[:20],
            "revision": "note:"+pin,
            "source_ref": "doi:"+work["doi"],
            "source_kind": "PUBLISHED_ARTICLE",
            "read_depth": "INDEX_ONLY",
            "full_text_certified": False,
            "passage_anchors": [{
                "kind": "OWNER_PRIOR_SCIENCE_NOTES_ONLY",
                "source_ref": verified["source_w2_id"],
                "content_sha256":verified["source_w2_raw_sha"],
                "anchor_type":"L3_W2_RESEARCH_NOTE_NOT_PUBLISHER_SOURCE",
                "legacy_locator": work["l3_anchor"],
            }],
            "science_acceptance": "SOURCE_NOTE_PROVISIONAL",
            "author_approved": False, "owner_prior_receipt_case": case_id,
        })
    objection = verified["objection"]
    orig_id = str(objection["event_id"])
    new_id = case_id+":IMPORTED:"+_sha(orig_id.encode("utf-8"))[:28]
    graph.append_event({
        "event_id": new_id,
        "kind": "SOURCE_CONTRADICTION",
        "subject_id": "F01_B09",
        "source_ref": objection["source_ref"],
        "result": "CONTRADICTS_NOVELTY_CLAIM_HELD_PRIOR_NOTE",
        "intellectual_consequence":objection["intellectual_consequence"],
        "next_action": verified["reopen"].get("next_question") or objection["next_action"],
        "legacy_event_id":orig_id,
        "source_original_id":verified["source_b09_id"],
        "source_original_sha256":verified["source_b09_raw_sha"],
        "w2_source_id":verified["source_w2_id"],
        "w2_source_sha256":verified["source_w2_raw_sha"],
        "w2_passage_line":verified["source_w2_line"],
        "w2_passage_sha256":verified["source_w2_anchor_sha"],
        "scientific_read_depth":"OWNER_SCIENCE_NOTE_ONLY_NO_PUBLISHER_FULLTEXT",
        "original_author_decision":"HOLD",
        "semantic_mutation":"NONE",
        "owner_prior_receipt_case":case_id,
    })
    prior_question = verified["reopen"].get("next_question") or verified["reopen"].get("next_action")
    if not prior_question:
        raise ValueError("prior owner source reopen text missing")
    reopen=graph.propose_field_reopen(
        new_id, reopen_level="L2",
        next_question=prior_question,
    )
    graph.put("HuntTrace",{
        "id":"trm074-owner-science-"+case_id,
        "revision":"legacy-receipt:"+pin,
        "source_ref":verified["source_b09_id"],
        "owner_prior_receipt_case":case_id,
        "source_receipt_sha256":pin,
        "source_note_sha256":verified["source_w2_raw_sha"],
        "research_status":"PROVISIONAL_LEGACY_OWNER_SCIENCE_NOTE_RECONCILED",
        "w12_equivalent":False,"deep_qualified":False,
        "author_approved":False,"article_seed_created":False,
        "world_mutation":False,"external_send":"DISABLED",
    })
    if any(graph.list_records(k)!=baseline[k] for k in baseline):
        raise ValueError("prior science import attempted World/ArticleSeed/route mutation")
    snap = _current_graph_fingerprint(graph,case_id)
    report={
        "schema":SCHEMA,"case_id":case_id,
        "source_receipt_path":str(receipt.resolve()),
        "legacy_graph_root":str(legacy.resolve()),
        "source_receipt_sha256":pin,
        "source_readback_sha256":verified["source_readback_sha256"],
        "original_source_sha256":verified["source_b09_raw_sha"],
        "w2_source_sha256":verified["source_w2_raw_sha"],
        "w2_passage_line":verified["source_w2_line"],
        "w2_passage_sha256":verified["source_w2_anchor_sha"],
        "opponent_source_refs":["doi:"+p["doi"] for p in verified["opponents"]],
        "source_event_id":new_id,"reopen_event_id":reopen["event_id"],
        "graph_fingerprint":snap,
        "counts":{"owner_original_sources":9,"indexed_published_refs":2,
                  "provisional_objections":1,"field_reopen_proposals":1,
                  "w12_equivalent_routes":0,"article_seeds":0,
                  "author_approvals":0,"world_mutations":0,"external_sends":0},
        "author_gate":"HOLD","science_status":"OWNER_NOTE_ONLY_NOT_FULL_PUBLISHER_READ",
        "external_send":"DISABLED",
    }
    data=_canon(report)
    if path.is_file() and path.read_bytes()!=data:
        raise ValueError("immutable owner source science receipt cannot change")
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.is_file():
        path.write_bytes(data)
    readback=readback_owner_prior_science(storage)
    return {"schema":SCHEMA,"receipt_path":str(path),
            "receipt_sha256":_sha(data),"readback_verified":readback["verified"],
            "readback_sha256":readback["receipt_sha256"],"counts":report["counts"]}


def readback_owner_prior_science(factory_storage_root: str | Path) -> dict[str, Any]:
    """Rehash both owner-private prior corpora and the live new graph on cold entry."""
    storage=Path(factory_storage_root)
    # One owner case per isolated storage root for this scoped adapter.
    path=storage/"research_stage"/"L3-CORPUS-20261020"/"L3-PRIOR-SCIENCE-IMPORT"/"receipt.json"
    data=_private_file(path)
    receipt=json.loads(data.decode("utf-8"))
    if receipt.get("schema")!=SCHEMA or receipt.get("author_gate")!="HOLD":
        raise ValueError("owner science import readback schema/authority invalid")
    intent_path = path.with_name("intent.json")
    intent = json.loads(_private_file(intent_path).decode("utf-8"))
    if (intent.get("schema") != "TRM074_PRIOR_SCIENCE_INTENT_V1"
            or intent.get("case_id") != receipt.get("case_id")
            or intent.get("source_receipt_sha256") != receipt.get("source_receipt_sha256")
            or intent.get("owner_note_sha256") != receipt.get("w2_source_sha256")
            or intent.get("author_gate") != "HOLD"
            or intent.get("publication_send") != "DISABLED"):
        raise ValueError("owner prior science import intent/receipt mismatch")
    proof=_legacy_evidence(Path(receipt["source_receipt_path"]),
                           Path(receipt["legacy_graph_root"]),storage)
    if (proof["source_receipt_sha256"] != receipt["source_receipt_sha256"]
            or proof["source_readback_sha256"] != receipt["source_readback_sha256"]
            or proof["source_b09_raw_sha"] != receipt["original_source_sha256"]
            or proof["source_w2_raw_sha"] != receipt["w2_source_sha256"]
            or proof["source_w2_line"] != receipt["w2_passage_line"]
            or proof["source_w2_anchor_sha"] != receipt["w2_passage_sha256"]
            or ["doi:"+r["doi"] for r in proof["opponents"]] != receipt["opponent_source_refs"]):
        raise ValueError("owner science cold readback underlying source pins changed")
    graph=OpportunityGraphStore(storage)
    if _current_graph_fingerprint(graph,receipt["case_id"])!=receipt["graph_fingerprint"]:
        raise ValueError("imported owner science graph was deleted/duplicated/tampered")
    events={e["event_id"]:e for e in graph.replay_events()}
    original=events.get(receipt["source_event_id"])
    reopen=events.get(receipt["reopen_event_id"])
    if (not original or not reopen
            or original.get("kind")!="SOURCE_CONTRADICTION"
            or original.get("source_original_id")!=proof["source_b09_id"]
            or original.get("scientific_read_depth")!="OWNER_SCIENCE_NOTE_ONLY_NO_PUBLISHER_FULLTEXT"
            or reopen.get("source_event_id")!=original["event_id"]
            or reopen.get("author_gate")!="AUTHOR_REVIEW_REQUIRED"):
        raise ValueError("imported owner source objection/reopen semantics changed")
    if any(graph.list_records(k) for k in ("World","ArticleSeed","OpportunityRoute")):
        raise ValueError("owner science import cannot self-certify an approved paper")
    return {"verified":True,"receipt_sha256":_sha(data),
            "verified_event_ids":[receipt["source_event_id"], receipt["reopen_event_id"]],
            "owner_science_status":"PROVISIONAL_NOT_AUTHOR_APPROVED",
            "indexed_published_refs":2,"provisional_objections":1,
            "field_reopen_proposals":1,"w12_equivalent_routes":0,
            "author_approved":False,"external_send":"DISABLED"}
