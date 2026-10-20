"""Merge independently executed MAI claim-critique CLI batches with zero fake gates.

All route reviews are checked against their immutable model-operation receipt,
original authenticated W12 route, and actual abstract-source paragraph.
No draft, author-ready or send state may be created by aggregation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

SCHEMA="MAI_W12_SOURCE_LINKED_PROVISIONAL_SCHOLARLY_CHALLENGE_v1"

def stable(x:Any)->bytes:
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()
def load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))
def write(path:Path,obj:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(stable(obj));tmp.replace(path)
def verify_operation(root:Path,rid:str,record:dict[str,Any])->str:
    matches=[]
    for path in sorted((root/"chunks").glob("*/accepted_reviews.json")):
        op=load(path)
        if rid in op.get("route_ids",[]):matches.append((path,op))
    if len(matches)!=1:raise ValueError("missing/duplicate original model receipt "+rid)
    path,operation=matches[0]
    if (operation.get("schema")!=SCHEMA or
        operation.get("input_key")!=record.get("input_key") or
        operation.get("all_scientific_gates")!="HOLD" or
        operation.get("external_send_count")!=0 or
        operation.get("model_judgements_author_accepted") is not False):
        raise ValueError("model operation provenance/authority mismatch "+rid)
    model_reviews=operation.get("verified_reviews") or []
    material=[item for item in model_reviews if item.get("route_id")==rid]
    if len(material)!=1 or material[0]!=record.get("review"):
        raise ValueError("model operation review differs from child record "+rid)
    raw=path.read_bytes()
    return sha(raw)

def run(packets:Path,source_evidence:Path,source_roots:list[Path],output:Path)->dict[str,Any]:
    source_meta=load(packets/"manifest.json")
    evidence_meta=load(source_evidence/"source_batch_receipt.json")
    source_hash=source_meta.get("source_jsonl_sha256")
    if not source_hash or evidence_meta.get("source_W12_sha256")!=source_hash:
        raise ValueError("W12 corpus/scientific API source digest mismatch")
    originals={p.stem:p for p in (packets/"routes").glob("MAI-W12-*.json")}
    if len(originals)!=source_meta.get("records") or len(originals)<1:
        raise ValueError("W12 route corpus not complete")
    output_rows={}
    for root in source_roots:
        if not root.is_dir():raise ValueError("missing source operation root "+str(root))
        for p in sorted((root/"routes").glob("MAI-W12-*.json")):
            rid=p.stem
            if rid not in originals:raise ValueError("unknown route in model outputs "+rid)
            if rid in output_rows:raise ValueError("duplicate route model output "+rid)
            record=load(p)
            route=load(originals[rid])["route"]
            pub=load(source_evidence/"routes"/(rid+".json"))
            review=record.get("review") or {}
            if (record.get("schema")!=SCHEMA
                    or record.get("route_id")!=rid
                    or review.get("route_id")!=rid
                    or review.get("scientific_claim_accepted") is not False
                    or record.get("human_gate")!="HOLD"
                    or record.get("journal_send_count")!=0
                    or record.get("published_fulltext_read") is not False
                    or record.get("scientific_stage")!="PROVISIONAL_MODEL_ABSTRACT_CHALLENGE"
                    or pub.get("W12_source_sha256")!=source_hash
                    or route["family"]!=pub.get("scientific_family")):
                raise ValueError("scientific output/source gate mismatch "+rid)
            passage=review.get("source_passage")
            if passage is None:
                if review.get("status")!="INSUFFICIENT_ABSTRACT" or review.get("source_anchor_id"):
                    raise ValueError("source-less objection not an explicit abstention "+rid)
            else:
                doi=passage.get("doi","")
                anchor=passage.get("passage_id","")
                text=passage.get("text","")
                if (not text or anchor!=doi+"#"+sha(text.encode("utf-8"))[:12]
                        or review.get("source_anchor_id")!=anchor):
                    raise ValueError("invalid source passage anchor "+rid)
                works=pub.get("published_works") or []
                match=next((w for w in works if w.get("doi")==doi and
                    w.get("abstract",{}).get("doi_identity_match") is True and
                    w.get("abstract",{}).get("read_depth")=="DATABASE_ABSTRACT" and
                    text in w.get("abstract",{}).get("abstract_text","")),None)
                if match is None:raise ValueError("model's published work quote not in provider-returned abstract "+rid)
                if record.get("source_passage_sha256")!=sha(stable(passage)):
                    raise ValueError("source passage SHA drift "+rid)
            op_sha=verify_operation(root,rid,record)
            output_rows[rid]={
                "route_id":rid,
                "family":route["family"],"journal":route["journal"],
                "meaning_version":route["variant"],
                "model_status":review["status"],
                "read_depth":review.get("admitted_source_read_depth"),
                "cited_doi":passage["doi"] if passage else None,
                "cited_anchor":review.get("source_anchor_id",""),
                "source_operation_receipt_sha256":op_sha,
                "input_key":record["input_key"],
                "output_sha256":sha(p.read_bytes()),
                "source_dir":str(root),
                "artifact":f"routes/{rid}.json",
                "author_gate":"HOLD",
            }
            destination=output/"routes"/(rid+".json")
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(p.read_bytes())
    expected=set(originals)
    missing=sorted(expected-set(output_rows))
    rows=[output_rows[k] for k in sorted(output_rows)]
    summary={
        "schema":"MAI_PROVISIONAL_SCIENTIFIC_CHALLENGE_MERGED_v1",
        "source_W12_sha256":source_hash,
        "route_total":len(originals),
        "model_reviews_validated":len(rows),
        "objections_with_abstract_passage":sum(x["model_status"]=="ABSTRACT_SUPPORTED_CHALLENGE" for x in rows),
        "research_abstentions":sum(x["model_status"]=="INSUFFICIENT_ABSTRACT" for x in rows),
        "missing_routes":missing,"source_roots":[str(r) for r in source_roots],
        "route_receipts":rows,
        "publisher_fulltext_read_here":0,
        "human_author_gate_ready":0,
        "journal_send_actions":0,
        "model_outputs_are_provisional":True,
    }
    write(output/"merged_challenge_receipt.json",summary)
    return summary

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--published-sources",type=Path,required=True)
    p.add_argument("--root",action="append",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(a.packets,a.published_sources,a.root,a.output)
    print(json.dumps({k:v for k,v in result.items() if k!="route_receipts"},ensure_ascii=False,indent=2))
    return 0 if not result["missing_routes"] else 2
if __name__=="__main__":
    raise SystemExit(main())
