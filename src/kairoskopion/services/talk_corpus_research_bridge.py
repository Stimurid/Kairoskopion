"""TRM-074: admit source-addressed talk *evidence* to existing Kairon graph.

This is a read-only semantic boundary: sources -> evidence with SECTIONS
read-depth. It never manufactures ArticleSeed, author approval, policy
evidence, WORLD modifications, venue routes, manuscripts, or submissions.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..registry import read_all


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def export_talk_research_evidence(
    storage_root: Path | str, case_id: str,
) -> dict[str, Any]:
    """Export passage-anchor facts only, with exact source/ledger revision pins.

    Every Evidence record is marked unqualified; passage anchors show *where*
    text differs or a discussion quotation occurs, not what science proves.
    """
    storage = Path(storage_root)
    ledger_path = storage / "talk_corpora" / case_id / "case_ledger.json"
    if not ledger_path.is_file():
        raise ValueError("talk corpus ledger missing")
    ledger_bytes = ledger_path.read_bytes()
    ledger_sha256 = _sha(ledger_bytes)
    ledger = json.loads(ledger_bytes.decode("utf-8"))
    if ledger.get("schema") != "TRM074_COLD_CASE_LEDGER_V1" or ledger.get("case_id") != case_id:
        raise ValueError("case ledger identity mismatch")
    if ledger.get("publication_send") != "DISALLOWED":
        raise ValueError("research bridge refuses external send authorization")
    if any(x.get("article_seed_created") or x.get("author_approved")
           for x in ledger.get("held_article_seed_envelopes", [])):
        raise ValueError("semantic/author gate already changed outside this bridge")

    snapshots = {x["source_id"]: x for x in ledger["source_snapshots"]}
    if len(snapshots) != len(ledger["source_snapshots"]):
        raise ValueError("duplicate source identity in corpus ledger")
    persisted_snapshots = read_all(
        "source_snapshots", base_dir=storage / "registries",
    )
    observed = {
        (s.get("source_id"), s.get("content_hash"))
        for s in persisted_snapshots
        if s.get("extraction_status") == "extracted"
    }
    for source in snapshots.values():
        if (source["source_id"], source["content_sha256"][:16]) not in observed:
            raise ValueError("ledger source missing from original intake registry")

    passages: dict[str, list[dict[str, Any]]] = {}
    def add_anchor(source_id: str, anchor: dict[str, Any] | None,
                   anchor_kind: str) -> None:
        if anchor is None:
            return
        if source_id not in snapshots:
            raise ValueError("passage anchor references unknown source")
        passages.setdefault(source_id, []).append({
            "anchor_kind": anchor_kind, **anchor,
        })

    for delta in ledger.get("textual_deltas", []):
        for change in delta.get("changes", []):
            add_anchor(change["before_source_id"], change.get("before_passage"),
                       "TEXTUAL_CHANGE_BEFORE")
            add_anchor(change["after_source_id"], change.get("after_passage"),
                       "TEXTUAL_CHANGE_AFTER")
    for event in ledger.get("discussion_events", []):
        source_id = event["source_id"]
        add_anchor(source_id, {
            "start_character": event["start_character"],
            "end_character": event["end_character"],
            "quote_sha256": event["quote_sha256"],
            "excerpt": event["quote_exact"][:360],
            "attribution": event["speaker_attribution"],
            "event_class": event["event_class"],
            "provisional_subject_ref": event.get("subject_ref"),
        }, (
            "RESEARCH_RETURN_QUOTE_NOT_PRIMARY_EVIDENCE"
            if event["event_class"] == "RESEARCH_RETURN"
            else "DISCUSSION_QUOTE_UNVERIFIED_SPEAKER"
        ))
    for event in ledger.get("discussion_decisions", []):
        source_id = event["source_id"]
        add_anchor(source_id, {
            "start_character": event["start_character"],
            "end_character": event["end_character"],
            "quote_sha256": _sha(event["quote_exact"].encode("utf-8")),
            "excerpt": event["quote_exact"][:360],
            "authority_scope": event["authority_scope"],
        }, "DOCUMENTED_DECISION_WITH_LIMITED_SCOPE")

    graph = OpportunityGraphStore(storage)
    before_seeds = graph.list_records("ArticleSeed")
    # Version the bridge schema in immutable Evidence revisions. A later
    # semantic/anchor contract must never rewrite a prior research record.
    revision = "case:" + ledger_sha256[:24] + ":bridge-v2"
    evidence_refs = []
    for source_id in sorted(passages):
        source = snapshots[source_id]
        anchors = list({
            json.dumps(x, ensure_ascii=False, sort_keys=True): x
            for x in passages[source_id]
        }.values())
        anchors.sort(key=lambda a: json.dumps(a, ensure_ascii=False, sort_keys=True))
        identity = _sha((case_id + "|" + source_id).encode("utf-8"))[:22]
        evidence = {
            "id": "t3-ev-" + identity,
            "revision": revision,
            "source_ref": source_id,
            "source_kind": source["kind"],
            "read_depth": "SECTIONS",
            "passage_anchors": anchors,
            "source_content_sha256": source["content_sha256"],
            "capture_read_coverage": source["read_coverage"],
            "source_version_label": source["version"],
            "source_version_label_conflict": source.get("version_label_conflict", False),
            "author_state": source["author_state"],
            "interpretation_class": "TEXT_SPANS_ONLY_NOT_SCIENTIFIC_FINDING",
            "case_id": case_id,
            "case_ledger_sha256": ledger_sha256,
            "qualified_for_article": False,
            "qualified_as_journal_policy": False,
            "author_approved": False,
        }
        stored = graph.put("Evidence", evidence)
        evidence_refs.append({
            "id": stored["id"],
            "revision": stored["revision"],
            "source_ref": stored["source_ref"],
            "anchors": len(stored["passage_anchors"]),
        })
    if graph.list_records("ArticleSeed") != before_seeds:
        raise ValueError("research bridge must not create ArticleSeed records")

    handoff = {
        "schema": "TRM074_TO_KAIRON_RESEARCH_STAGE_V1",
        "case_id": case_id,
        "source_ledger_sha256": ledger_sha256,
        "world_ref": ledger.get("world_ref"),
        "graph_namespace": "kairon_provider/opportunity_graph",
        "graph_record_kind": "Evidence",
        "bridge_schema_version": "v2",
        "evidence_refs": evidence_refs,
        "unread_media": [
            {
                "source_id": item["source_id"],
                "read_state": item["read_state"],
                "structure_sha256": item["structure_sha256"],
            } for item in ledger.get("related_media", [])
        ],
        "article_seed_status": "NONE_CREATED_REQUIRES_ARTIKL_AUTHOR_GATES",
        "trm073_status": "RESEARCH_SOURCE_STAGE_ONLY_NOT_A_HUNT",
        "external_send": "DISABLED",
    }
    path = storage / "talk_corpora" / case_id / "research_stage_handoff.json"
    encoded = _canonical(handoff).encode("utf-8")
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(encoded)
    os.replace(tmp, path)
    return {
        "case_id": case_id,
        "handoff_path": str(path),
        "handoff_sha256": _sha(encoded),
        "evidence_count": len(evidence_refs),
        "sources_with_anchors": len(passages),
        "article_seed_created": 0,
        "external_send": "DISABLED",
    }
