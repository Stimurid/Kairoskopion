"""Run the *existing* Kairoskopion local pipeline over W12 source abstracts.

One pipeline invocation per independent route. This is a diagnostic pass on
source abstracts and W12 route notes; it is not a full manuscript submission
nor an independent full-text evidence search. No external SEND/SUBMIT actions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def atomic_json(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)

def prepare_input(packet: dict[str,Any], directory: Path) -> dict[str,Any]:
    r=packet["route"]
    directory.mkdir(parents=True,exist_ok=True)
    abstract=(
        "# SOURCE ABSTRACT FROM MAI W12 — NOT A COMPLETE MANUSCRIPT\n\n"+
        r.get("title_ru","")+"\n\n"+r.get("abstract_ru","")+"\n\n"+
        "Source citation: "+str(r.get("original_spreadsheet_id"))+
        " / "+str(r.get("source_cell_range"))+"\n"
    )
    guidelines=(
        "# MAI W12 ROUTE SUMMARY — NOT VERIFIED OFFICIAL GUIDELINES\n\n"+
        "Journal: "+r.get("journal","")+"\n\n"+
        "Original W12 editorial route: "+r.get("route_raw","")+"\n\n"+
        "Deadline recorded in W12: "+r.get("deadline_raw","")+"\n\n"+
        "Official page recorded in W12: "+r.get("official_url","")+"\n\n"+
        "Published prior art recorded in W12 (NOT venue-native unless verified): "+
        r.get("literature_url","")+"\n\n"+
        "Route verification: POLICY_UNVERIFIED. Treat submission eligibility as UNKNOWN.\n"
    )
    scenario={
        "goal":"Pre-author local diagnostic on existing MAI W12 abstract; no manuscript ready claim",
        "target_venue_type":"journal",
        "target_indexing":"unknown",
        "rewrite_depth":"none",
        "language_constraints":"source-russian, eventual target-english",
        "deadline":r.get("deadline_raw") or "unspecified",
        "risk_tolerance":"low",
        "field_core_preservation":"strict",
        "notes":"W12 source abstract only. Journal guidelines are unverified W12 summary. No automatic external submit, no claim of research validation.",
    }
    a=directory/"source_abstract.md"
    b=directory/"w12_route_notes.md"
    c=directory/"scenario.json"
    a.write_text(abstract,encoding="utf-8")
    b.write_text(guidelines,encoding="utf-8")
    c.write_text(json.dumps(scenario,ensure_ascii=False,indent=2),encoding="utf-8")
    return {
        "article_path":str(a),"venue_path":str(b),"scenario_path":str(c),
        "source_sha256":digest(abstract.encode("utf-8")),
        "venue_summary_sha256":digest(guidelines.encode("utf-8")),
        "scenario_sha256":digest(c.read_bytes()),
    }

def run(source_root: Path, output_root: Path, limit: int = 10, start: int=0, rerun: bool=False, cli_module: str="kairoskopion.cli") -> dict[str,Any]:
    if limit<1 or limit>53 or start<0:
        raise ValueError("limit must be 1-53 and start >=0")
    paths=sorted((source_root/"routes").glob("MAI-W12-*.json"))
    if not paths:
        raise ValueError("no W12 packet files")
    if start>=len(paths):
        raise ValueError("start past end")
    selected=paths[start:start+limit]
    receipts=[]
    for i,path in enumerate(selected,1):
        packet=json.loads(path.read_text(encoding="utf-8"))
        rid=packet["route"]["route_id"]
        jobroot=output_root/rid
        inputs=prepare_input(packet,jobroot/"inputs")
        receipt_file=jobroot/"receipt.json"
        # Only the three actual run-local inputs control the diagnostic
        # cache. Editorial emails and newly attached INDAGO objections
        # change the board, not the underlying manuscript/venue analysis.
        input_key=digest("|".join([inputs["source_sha256"],inputs["venue_summary_sha256"],inputs["scenario_sha256"]]).encode("ascii"))
        if receipt_file.exists() and not rerun:
            old=json.loads(receipt_file.read_text(encoding="utf-8"))
            previous=old.get("inputs") or {}
            same_inputs=all(previous.get(k)==inputs[k] for k in (
                "source_sha256","venue_summary_sha256","scenario_sha256"))
            same_source=(old.get("real_source_snapshot")==packet.get("source_jsonl_sha256"))
            valid_old=(old.get("status")=="LOCAL_DIAGNOSTIC_COMPLETED"
                and old.get("route_id")==rid and same_inputs and same_source
                and old.get("adapter_mode")=="mock"
                and old.get("outbound_send_count")==0)
            if valid_old:
                receipts.append({"route_id":rid,"status":"CACHED","input_key":input_key,"original_status":"LOCAL_DIAGNOSTIC_COMPLETED"})
                continue
        cmd=[
            sys.executable,"-m",cli_module,
            "--storage-root",str(jobroot/"kairoskopion"),
            "run-local","--manuscript",inputs["article_path"],
            "--venue-guidelines",inputs["venue_path"],"--scenario",inputs["scenario_path"],
        ]
        env=os.environ.copy()
        cp=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180,env=env)
        stdout=jobroot/"stdout.log";stderr=jobroot/"stderr.log"
        stdout.write_text(cp.stdout,encoding="utf-8")
        stderr.write_text(cp.stderr,encoding="utf-8")
        state="LOCAL_DIAGNOSTIC_COMPLETED" if cp.returncode==0 else "LOCAL_DIAGNOSTIC_FAILED"
        receipt={
            "schema":"TRIMURTI_MAI_EXISTING_KAIROSKOPION_RUN_LOCAL_v1",
            "route_id":rid,"input_key":input_key,"status":state,
            "operation":"kairoskopion.cli.run-local",
            "real_source_snapshot":packet.get("source_jsonl_sha256"),
            "manuscript_kind":"W12_ABSTRACT_NOT_MANUSCRIPT",
            "venue_policy":"W12_SUMMARY_UNVERIFIED",
            "adapter_mode":"mock",
            "outbound_send_count":0,
            "scientific_qa_status":"NOT_YET_VERIFIED",
            "author_gate":"CLOSED",
            "ran_at_utc":datetime.now(timezone.utc).isoformat(),
            "command":cmd,"exit_code":cp.returncode,
            "inputs":inputs,
            "stdout_sha256":digest(cp.stdout.encode("utf-8")),
            "stderr_sha256":digest(cp.stderr.encode("utf-8")),
        }
        atomic_json(receipt_file,receipt)
        receipts.append({"route_id":rid,"status":state,"input_key":input_key})
    summary={
        "schema":"TRIMURTI_MAI_RUN_LOCAL_BATCH_v1",
        "requested":len(selected),"start":start,"total_source":len(paths),
        "by_result":{status:sum(x["status"]==status for x in receipts) for status in set(x["status"] for x in receipts)},
        "receipts":receipts,"no_external_send":True,"author_rework_during_run":False
    }
    atomic_json(output_root/"run-summary.json",summary)
    return summary

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-packets",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--limit",type=int,default=10)
    p.add_argument("--start",type=int,default=0)
    p.add_argument("--rerun",action="store_true")
    args=p.parse_args(argv)
    summary=run(args.source_packets,args.output,args.limit,args.start,args.rerun)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return int(any(x["status"]=="LOCAL_DIAGNOSTIC_FAILED" for x in summary["receipts"]))

if __name__=="__main__":
    sys.exit(main())
