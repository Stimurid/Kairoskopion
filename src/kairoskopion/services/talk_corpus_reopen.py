"""TRM-074: manual W1 objections -> author-gated Kairon field-reopen proposals.

Reuses OpportunityGraphStore HUNT_RESULT and FIELD_REOPEN_PROPOSAL event
contracts. No source-world rewriting, ArticleSeed authority or send action.
A quote in a manual W1 notebook is not proof of the underlying published paper.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from ..kairon_provider.opportunity_graph import OpportunityGraphStore


_HEADS = {"A": "HEAD-01", "B": "HEAD-02", "C": "HEAD-03"}
_NEXT_QUESTION = {
    "HEAD-01": (
        "Which precise predecessor already explains AI redistribution of work, "
        "and which distinct operation would demonstrate production of new means?"
    ),
    "HEAD-02": (
        "Which existing organizational learning models already explain knowledge "
        "generation, and what source-anchored difference survives?"
    ),
    "HEAD-03": (
        "Which entrepreneurship studies already demonstrate AI-enabled startups, "
        "and which independent test establishes industrial reproducibility?"
    ),
}


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def propose_w1_return(
    storage_root: Path | str,
    case_id: str = "T3-TALK-20261019",
) -> dict[str, Any]:
    root = Path(storage_root)
    corpus_file = root / "talk_corpora" / case_id / "case_ledger.json"
    handoff_file = root / "talk_corpora" / case_id / "research_stage_handoff.json"
    if not corpus_file.is_file() or not handoff_file.is_file():
        raise ValueError("corpus ledger or research-stage handoff missing")
    raw = corpus_file.read_bytes()
    digest = _digest(raw)
    corpus = json.loads(raw.decode("utf-8"))
    handoff = json.loads(handoff_file.read_text(encoding="utf-8"))
    if corpus.get("case_id") != case_id or handoff.get("case_id") != case_id:
        raise ValueError("mismatched case identity")
    if handoff.get("source_ledger_sha256") != digest:
        raise ValueError("handoff not pinned to current case ledger")
    if corpus.get("publication_send") != "DISALLOWED":
        raise ValueError("publication send prohibited")
    if corpus.get("world_ref") is None:
        raise ValueError("source WORLD pointer missing")
    if any(x.get("article_seed_created") or x.get("author_approved")
           for x in corpus.get("held_article_seed_envelopes", [])):
        raise ValueError("article-seed gate modified without owner authorization")
    if not any(x.get("kind") == "2025_COAUTHORED_FULL_TEXT"
               and x.get("status") == "NOT_ACQUIRED_FULL_READ_BLOCKED"
               for x in corpus.get("missing_carriers", [])):
        raise ValueError("2025 course fulltext limitation not recorded")

    by_id = {x["source_id"]: x for x in corpus["source_snapshots"]}
    evidence_pins = {x["source_ref"]: x for x in handoff["evidence_refs"]}
    store = OpportunityGraphStore(root)
    before_articles = store.list_records("ArticleSeed")
    before_world = store.list_records("World")

    candidates: dict[str, dict[str, Any]] = {}
    for event in corpus.get("discussion_events", []):
        if event.get("event_class") != "RESEARCH_RETURN":
            continue
        quote = str(event["quote_exact"])
        prefix = quote[:8]
        if not prefix.startswith("RETURN-") or len(prefix) < 8:
            continue
        letter = prefix[7]
        expected = _HEADS.get(letter)
        if not expected:
            continue
        if event.get("subject_ref") != expected:
            raise ValueError("manual return subject mismatch")
        if expected in candidates:
            raise ValueError("duplicate W1 return for provisional head")
        source = by_id.get(event["source_id"])
        if source is None or source["kind"] != "RESEARCH_SYNTHESIS" or source["read_coverage"] != "RESEARCH_SYNTHESIS_TEXT_ONLY":
            raise ValueError("manual W1 return source is not a bounded research notebook")
        if source["author_state"] != "RESEARCH_RETURN_NOT_AUTHOR_APPROVAL":
            raise ValueError("manual return improperly granted author authority")
        pinned = evidence_pins.get(source["source_id"])
        if not pinned:
            raise ValueError("manual W1 return lacks graph Evidence pin")
        proof = store.get("Evidence", pinned["id"], pinned["revision"])
        if proof is None or proof.get("read_depth") != "SECTIONS":
            raise ValueError("manual W1 source missing section-only Evidence record")
        if proof.get("qualified_for_article") or proof.get("author_approved"):
            raise ValueError("manual W1 cannot self-certify science")
        if (proof.get("source_ref") != source["source_id"]
                or proof.get("source_content_sha256") != source["content_sha256"]
                or proof.get("case_ledger_sha256") != digest):
            raise ValueError("manual W1 Evidence provenance does not match case")
        if not any(
            a.get("anchor_kind") == "RESEARCH_RETURN_QUOTE_NOT_PRIMARY_EVIDENCE"
            and a.get("quote_sha256") == event["quote_sha256"]
            and a.get("start_character") == event["start_character"]
            and a.get("end_character") == event["end_character"]
            and a.get("provisional_subject_ref") == expected
            for a in proof.get("passage_anchors", [])
        ):
            raise ValueError("manual W1 quote is not anchored in pinned Evidence")
        candidates[expected] = {"event": event, "source": source, "evidence": pinned}
    if set(candidates) != set(_HEADS.values()):
        raise ValueError("three independent W1 returns required before cohort export")

    events: list[dict[str, Any]] = []
    for head in sorted(candidates):
        entry = candidates[head]
        event = entry["event"]
        source = entry["source"]
        pin = entry["evidence"]
        eid = f"TRM074:{case_id}:{head}:w1:{digest[:16]}"
        negative = {
            "event_id": eid,
            "kind": "HUNT_RESULT",
            "result": "REJECT_AUTOMATIC_NOVELTY_CLAIM_PENDING_FULLTEXT_VALIDATION",
            "subject_id": head,
            "source_ref": source["source_id"],
            "source_evidence_pin": {"id": pin["id"], "revision": pin["revision"]},
            "source_passage_sha256": event["quote_sha256"],
            "source_span": [event["start_character"], event["end_character"]],
            "read_depth": "SECTIONS",
            "source_kind": "MANUAL_W1_RESEARCH_NOTEBOOK",
            "epistemic_authority": "MANUAL_PROVISIONAL_ONLY",
            "intellectual_consequence": event["quote_exact"],
            "next_action": _NEXT_QUESTION[head],
            "author_decision": "HOLD",
            "world_mutation": "NONE",
            "external_send": "DISABLED",
        }
        store.append_event(negative)
        proposal = store.propose_field_reopen(
            eid, reopen_level="L0", next_question=_NEXT_QUESTION[head],
        )
        events.append({
            "head": head, "negative_event_id": eid,
            "reopen_event_id": proposal["event_id"],
            "reopen_level": proposal["reopen_level"],
            "proposal_author_gate": proposal["author_gate"],
            "source_ref": source["source_id"],
            "source_evidence_id": pin["id"],
        })
    if store.list_records("ArticleSeed") != before_articles:
        raise ValueError("reopen operation changed ArticleSeed objects")
    if store.list_records("World") != before_world:
        raise ValueError("reopen operation changed WORLD")
    result = {
        "schema": "TRM074_W1_REOPEN_RETURN_V1",
        "case_id": case_id,
        "corpus_ledger_sha256": digest,
        "research_stage_handoff_sha256": _digest(handoff_file.read_bytes()),
        "semantic_change": "PROPOSALS_ONLY",
        "manual_research_status": "W1_MANUAL_NOT_RUNTIME_HUNT",
        "source_truth": "SECONDARY_NOTEBOOK_UNVERIFIED_PRIMARY_FULLTEXT",
        "reopen_proposals": events,
        "article_seed_created": False,
        "world_mutated": False,
        "external_send": "DISABLED",
    }
    out = corpus_file.parent / "w1_field_reopen_proposals.json"
    encoded = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(encoded)
    tmp.replace(out)
    return {
        "path": str(out),
        "sha256": _digest(encoded),
        "count": len(events),
        "article_seed_created": 0,
        "world_mutated": False,
        "external_send": "DISABLED",
    }
