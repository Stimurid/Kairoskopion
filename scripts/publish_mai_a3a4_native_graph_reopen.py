"""MAI A3/A4 native scientific World-return -> EXISTING Kairon OpportunityGraphStore.

No separate event ontology. Actual evidence is the three same-venue publisher
articles, their SHA-bound machine readings, and source-anchored Artikl synthesis.
The existing store emits HUNT_RESULT + FIELD_REOPEN_PROPOSAL, with author HOLD.
Import never changes a World, ArticleSeed, ArticleOpportunity or external email.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
from typing import Any

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
if __package__:
    from .fetch_mai_venue_pages import load,sha,stable,write
else:
    from fetch_mai_venue_pages import load,sha,stable,write
if __package__:
    from .run_mai_a_education_field_reopen import build_input,validate_synthesis
else:
    from run_mai_a_education_field_reopen import build_input,validate_synthesis

SCHEMA="MAI_ARTIKL_A3A4_NATIVE_GRAPH_REOPEN_EVENT_IMPORT_v1"

def import_held_return(
    packets:Path,native:Path,book:Path,reads:Path,reopen:Path,graph_root:Path,
)->dict[str,Any]:
    data=build_input(packets,native,book,reads)
    receipt_file=reopen/"field_reopen_proposal.json"
    model_file=reopen/"model_output.json"
    if not receipt_file.is_file() or not model_file.is_file():
        raise ValueError("no actual model source-anchored World-return producer receipt")
    envelope=load(receipt_file)
    original=load(model_file)
    content=validate_synthesis(original,data)
    if (envelope.get("schema")!="MAI_ARTIKL_A3A4_NATIVE_FIELD_REOPEN_RECEIPT_v1"
            or envelope.get("source_input_sha256")!=sha(stable(data))
            or envelope.get("original_scholarship_model_output_sha256")!=sha(stable(original))
            or envelope.get("verified_proposal")!=content
            or envelope.get("author_decision")!="HOLD"
            or envelope.get("world_mutations")!=0
            or envelope.get("journal_send_count")!=0
            or envelope.get("human_scientific_evaluation")!="REQUIRED"
            or content.get("decision_candidate") not in (
                "RESEARCH_HOLD","REVISE_SOURCE_CANDIDATE","NOVELTY_OVERLAP_WARNING","REJECT_CANDIDATE"
            )):
        raise ValueError("semantic source/author gate drift on World return")
    store=OpportunityGraphStore(graph_root)
    protected_before={
       kind:store.list_records(kind)
       for kind in ("World","ArticleSeed","ArticleOpportunity","EditorialPacket","TargetVariant")
    }
    evidence_refs=[]
    source_rows={x["doi"]:x for x in data["three_published_native_paper_evidence"]}
    for doi,paper in sorted(source_rows.items()):
        anchored=[link for link in content["source_anchor_ids"] if link["doi"]==doi]
        if not anchored:
            raise ValueError("source original paper has no literal downstream quotation")
        for link in anchored:
            if link.get("quote_source_type")!="ACTUAL_SAME_JOURNAL_PUBLISHER_MAIN_BODY":
                raise ValueError("invalid publisher-science citation role")
            source_link=next(
                (x for x in paper["source_anchors"] if x["quote_sha256"]==link["quote_sha256"]),
                None,
            )
            if not source_link or source_link["exact_quote"]!=link["exact_publisher_quote"]:
                raise ValueError("FieldReopen graph citation not in original publisher scholarly read")
        eid="MAI-A-EDUCATION:PUBLISHER:"+sha(doi.encode("utf-8"))[:20]
        original_sha=paper["publisher_main_body_sha256"]
        ref={
          "id":eid,
          "revision":original_sha[:24],
        }
        record={
          **ref,
          "kind":"Evidence",
          "source_ref":paper["article_original_url"],
          "source_kind":"PUBLISHED_ARTICLE",
          "read_depth":"SECTIONS",  # publisher HTML main body is *not* certified FULL_TEXT
          "source_content_sha256":original_sha,
          "publisher_review_receipt_sha256":paper["paper_review_receipt_sha256"],
          "origin_journal":"Studies in Philosophy and Education",
          "source_doi":doi,
          "passage_anchors":[
            {"quote_sha256":link["quote_sha256"],
             "exact_quote":link["exact_publisher_quote"],
             "anchor_kind":"LITERAL_PUBLISHER_MAIN_BODY_PASSAGE",
             "source_url":link["published_article_original_url"],
             "inference":link["why_this_proves_the_claim"]}
            for link in anchored
          ],
          "qualified_for_article":False,
          "author_approved":False,
          "scientific_adjudication":"ARTIKL_MODEL_PROVISIONAL",
          "author_gate":"HOLD",
        }
        result=store.put("Evidence",record)
        if result["id"]!=eid or result["revision"]!=ref["revision"]:
            raise ValueError("native source evidence could not retain graph identity")
        evidence_refs.append({**ref,"doi":doi,"source_url":paper["article_original_url"],
                              "sha256":original_sha})
    if len(evidence_refs)!=3:
        raise ValueError("three original same-journal paper evidence must be added first")
    canonical_id="MAI-A3A4:"+sha(receipt_file.read_bytes())[:20]
    negative_id=canonical_id+":negative"
    explanation=content["model_proposal"]["strongest_cross_paper_opposition"]
    next_question=content["model_proposal"]["additional_source_or_evidence_debt"]
    if len(explanation)<70 or len(next_question)<70:
        raise ValueError("theoretical pressure and new task not concretely specified")
    negative={
      "event_id":negative_id,
      "kind":"HUNT_RESULT",
      "result":"REJECT_UNGROUNDED_GENERAL_NOVELTY_PRESERVE_NARROWER_RESEARCH_HOLD",
      "subject_id":"MAI-W12-009",
      "source_ref":"MAI_W12_NATIVE_SAME_JOURNAL_THREE_WORKS",
      "source_evidence_pins":evidence_refs,
      "synthesis_receipt_sha256":sha(receipt_file.read_bytes()),
      "source_input_sha256":sha(stable(data)),
      "source_W12_sha256":data["source_W12_sha256"],
      "publisher_main_body_read_depth":"SECTIONS",
      "epistemic_authority":"PROVISIONAL_MODEL_CROSS_PAPER_COMPARISON",
      "intellectual_consequence":explanation,
      "next_action":next_question,
      "author_decision":"HOLD",
      "world_mutation":"NONE",
      "external_send":"DISABLED",
    }
    negative=store.append_event(negative)
    proposal=store.propose_field_reopen(
        negative_id,reopen_level="L0",
        next_question=content["model_proposal"]["proposed_revised_claim_v1"],
    )
    if (proposal["kind"]!="FIELD_REOPEN_PROPOSAL"
            or proposal["author_gate"]!="AUTHOR_REVIEW_REQUIRED"
            or proposal["semantic_mutation"]!="NONE"
            or proposal["source_event_id"]!=negative_id):
        raise ValueError("existing graph store failed to preserve author gate")
    for kind,old in protected_before.items():
        if store.list_records(kind)!=old:
            raise ValueError("World / protected publication authority changed during research return "+kind)
    event_ids={x["event_id"] for x in store.replay_events()}
    if negative_id not in event_ids or proposal["event_id"] not in event_ids:
        raise ValueError("existing Kairon graph cannot replay a new scientific World return")
    result={
      "schema":SCHEMA,
      "source_route_id":"MAI-W12-009",
      "source_W12_sha256":data["source_W12_sha256"],
      "case_publisher_original_work_count":3,
      "science_anchor_count":len(content["source_anchor_ids"]),
      "source_evidence_pins":evidence_refs,
      "research_negative_event_id":negative_id,
      "research_field_reopen_event_id":proposal["event_id"],
      "research_disposition":content["decision_candidate"],
      "scientific_stage":"PROVISIONAL_SECOND_ORDER_NORM_AUTHORITY_RETURN",
      "implementation":"EXISTING_OPPORTUNITY_GRAPH_STORE",
      "human_gate":"AUTHOR_REVIEW_REQUIRED",
      "world_mutations":0,"article_seeds_automatically_created":0,
      "outbound_submissions":0,
      "source_original_reopen_sha256":sha(receipt_file.read_bytes()),
    }
    write(graph_root/"MAI_A_EDUCATION_A3A4_GRAPH_WORLD_RETURN_RECEIPT.json",result)
    return result

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--native-root",type=Path,required=True)
    p.add_argument("--author-book",type=Path,required=True)
    p.add_argument("--reads",type=Path,required=True)
    p.add_argument("--field-reopen",type=Path,required=True)
    p.add_argument("--graph-root",type=Path,required=True)
    a=p.parse_args()
    r=import_held_return(a.packets,a.native_root,a.author_book,
                         a.reads,a.field_reopen,a.graph_root)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
