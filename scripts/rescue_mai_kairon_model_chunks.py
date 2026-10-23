"""Recover individually valid route rows from a FAILED multi-route model batch.

This is a strict zero-provider salvage operation. It retains the failed original
response and the complete original source input; rows whose quotations don't
appear in the actual captured publisher text are never salvaged. Follow with
run_mai_kairon_policy_claims.py to resume ONLY still-missing routes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import run_mai_kairon_policy_claims as policy

def salvage(packets:Path,venue_root:Path,output:Path)->dict[str,Any]:
    valid=[]
    invalid=[]
    visited=[]
    for chunk in sorted((output/"chunks").glob("*")):
        input_path=chunk/"input.json"
        reply=chunk/"model_output.json"
        if not input_path.is_file() or not reply.is_file():
            continue
        original=policy.load(input_path)
        input_digest=policy.sha(policy.stable(original))
        if not chunk.name.endswith(input_digest[:12]):
            raise ValueError("model source input chunk path digest mismatch "+str(chunk))
        ids=[v["route_id"] for v in original["route_inputs"]]
        current={rid:policy.read_sources(packets,venue_root,rid) for rid in ids}
        actual=[policy.prompt_item(current[rid]) for rid in ids]
        if (actual!=original["route_inputs"] or
                original["source_W12_sha256"]!=policy.load(packets/"manifest.json")["source_jsonl_sha256"]):
            raise ValueError("model source input changed after original query "+str(chunk))
        model=policy.load(reply)
        rows=model.get("routes",[])
        if not isinstance(rows,list) or len(rows)!=len(ids):
            invalid.extend({"route_id":rid,"reason":"SOURCE_BATCH_MODEL_IDS_DRIFT"} for rid in ids)
            continue
        seen=set()
        if set(x.get("route_id") for x in rows)!=set(ids):
            invalid.extend({"route_id":rid,"reason":"MODEL_ROUTE_ID_SET_MISMATCH"} for rid in ids)
            continue
        for row in rows:
            rid=row.get("route_id")
            if rid in seen:
                raise ValueError("duplicate model route candidate "+str(rid))
            seen.add(rid)
            visit={"route_id":rid,"original_chunk":chunk.name}
            visited.append(visit)
            # A pre-existing valid receipt must remain authoritative; never rewrite it.
            cached=policy.check_cached_policy_record(current[rid],output)
            if cached:
                continue
            try:
                approved=policy.validate({"routes":[row]},[rid],{rid:current[rid]})[0]
            except (ValueError,TypeError,KeyError) as exc:
                invalid.append({"route_id":rid,"reason":str(exc)[:200]})
                continue
            # This *subset* is provenance-preserving; the full failed batch
            # is retained byte-for-byte for later independent audit.
            rescue=output/"chunks"/("recovered_"+rid+"_"+input_digest[:12])
            proof={
                "schema":"MAI_KAIRON_POLICY_OPERATION_RECEIPT_v1",
                "input_digest":input_digest,
                "model_output_sha256":policy.sha(policy.stable({"routes":[row]})),
                "model_output":{"routes":[row]},
                "verified_policy_claims":[approved],
                "provider":"claude",
                "rescued_from_multi_route_model_response_sha256":policy.sha(reply.read_bytes()),
                "rescued_from_original_source_input_sha256":policy.sha(input_path.read_bytes()),
                "original_failed_batch":chunk.name,
                "recovery_is_source_quote_checked":True,
                "all_policy_authority_gates":"HOLD",
                "human_author_gate":"HOLD","external_submission_count":0,
            }
            policy.write(rescue/"accepted.json",proof)
            source=current[rid]
            policy.write(output/"routes"/(rid+".json"),{
                "schema":policy.SCHEMA,"route_id":rid,
                "source_W12_sha256":original["source_W12_sha256"],
                "captured_web_receipt_sha256":policy.sha(policy.stable(source["capture"])),
                "visible_page_excerpt_sha256":source["excerpt_sha256"],
                "full_visible_page_truncated_chars":source["text_omitted_chars"],
                "model_operation_input_digest":input_digest,
                "model_operation_receipt_sha256":policy.sha((rescue/"accepted.json").read_bytes()),
                "model_provider":"claude",
                "status":"QUOTED_POLICY_CANDIDATES_PROVISIONAL",
                "web_source_state":source["source_web_status"],
                **approved,
            })
            valid.append(rid)
    result={
        "schema":"MAI_KAIRON_PARTIAL_MODEL_BATCH_RECOVERY_v1",
        "zero_new_provider_calls":True,
        "salvaged_valid_source_quoted_route_ids":sorted(set(valid)),
        "still_invalid_route_claims":invalid,
        "visited_parent_model_route_rows":len(visited),
        "all_policy_approvals":"HOLD",
        "external_send_count":0,
    }
    policy.write(output/"source_quote_recovery_receipt.json",result)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--venue-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=salvage(a.packets,a.venue_root,a.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
