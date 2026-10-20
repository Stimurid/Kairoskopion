"""One-command, resume-safe MAI W12 science batch.

Stages: authenticated W12+INDAGO index -> Crossref/OpenAlex source records ->
real Codex/Claude source-anchored critique -> independently verified merge ->
Kairoskopion publication-control board (optional existing board provider).

This coordinator does NOT write articles, clear scholarly/author gates, deploy,
email journals or infer publisher full-text reading from database abstracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fetch_mai_prior_art import execute as get_prior_art, stable as provider_stable, normalize_doi
from run_mai_claim_challenge import run as run_criticism
from merge_mai_scholarly_reviews import run as merge_criticism

SCHEMA="MAI_W12_RESEARCH_OPERATOR_ONE_COMMAND_v1"

def load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def put(path:Path,x:Any)->None:
    raw=(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_bytes(raw);temp.replace(path)

def verify_cached_provider_sources(published_root:Path,work:dict[str,Any])->None:
    doi=normalize_doi(str(work.get("doi") or ""))
    directory=published_root/"published_work_cache"/hashlib.sha256(doi.encode("utf-8")).hexdigest()[:20]
    original=(work.get("abstract") or {})
    provider_abstracts=[]
    for backend in ("crossref","openalex"):
        record_file=directory/(backend+".json")
        if not record_file.is_file():
            raise ValueError("missing Crossref/OpenAlex provider receipt for "+doi)
        item=load(record_file)
        record_without_replay={key:value for key,value in item.items() if key!="from_cache"}
        content_sha=hashlib.sha256(provider_stable(record_without_replay)).hexdigest()
        if ((work.get("source_record_digests") or {}).get(backend)!=content_sha
                or item.get("requested_doi")!=doi
                or item.get("backend")!=backend
                or work.get(backend+"_status")!=item.get("http_status")):
            raise ValueError("provider-source identity drift for "+doi)
        parsed=item.get("parsed") or {}
        if item.get("http_status")==200:
            raw=directory/(backend+".response.json")
            if (not raw.is_file() or
                    hashlib.sha256(raw.read_bytes()).hexdigest()!=item.get("raw_response_sha256")):
                raise ValueError("actual raw Crossref/OpenAlex response SHA drift for "+doi)
            if (parsed.get("doi_identity_match") and parsed.get("abstract_text")):
                provider_abstracts.append(parsed["abstract_text"])
    if original.get("read_depth")=="DATABASE_ABSTRACT":
        if (not original.get("doi_identity_match")
                or original.get("abstract_text") not in provider_abstracts):
            raise ValueError("route abstract no longer equals verified provider return for "+doi)

def attest_reusable_publications(path:Path,packet_root:Path)->dict[str,Any]:
    w12=load(packet_root/"manifest.json")
    meta=load(path/"source_batch_receipt.json")
    if (meta.get("schema")!="MAI_PUBLISHED_WORK_API_BATCH_v1"
            or meta.get("source_W12_sha256")!=w12.get("source_jsonl_sha256")
            or meta.get("route_count")!=w12.get("records")):
        raise ValueError("live published-source receipt cannot be replayed against this corpus")
    originals=sorted((packet_root/"routes").glob("MAI-W12-*.json"))
    for f in originals:
        candidate=path/"routes"/f.name
        if not candidate.is_file():
            raise ValueError("published-source receipt missing for route "+f.stem)
        data=load(candidate)
        if (data.get("schema")!="MAI_PRIOR_ART_AUTHENTICATED_API_EVIDENCE_v1"
                or data.get("route_id")!=f.stem
                or data.get("W12_source_sha256")!=w12["source_jsonl_sha256"]
                or data.get("science_gate")!="HOLD"
                or data.get("human_author_gate")!="CLOSED"
                or data.get("publisher_fulltexts_read")!=0
                or data.get("external_send_count")!=0):
            raise ValueError("unsafe stale or promoted source receipt "+f.stem)
        for work in data.get("published_works") or []:
            verify_cached_provider_sources(path,work)
    return meta

def run_workflow(
    packets:Path, science_index:Path, published:Path, model:Path,
    merged:Path, *, existing_model_roots:list[Path]|None=None,
    replay_publications:bool=False, max_workers:int=4,
    chunk_size:int=5, provider:str="auto", timeout:int=540,
    board_repo:Path|None=None, board_root:Path|None=None,
    native_w12:Path|None=None, native_w12_snapshot:Path|None=None,
    outreach_events:Path|None=None, diagnostics:Path|None=None,
)->dict[str,Any]:
    source=load(packets/"manifest.json")
    if source.get("schema")!="MAI_W12_BATCH_OUTPUT_MANIFEST_v1" or source.get("records")!=53:
        raise ValueError("expected full authenticated W12 route packet corpus (53)")
    idx=load(science_index/"science_index.json")
    if (idx.get("schema")!="MAI_W12_PRIOR_RESEARCH_INDEX_V1"
            or idx.get("source_W12_sha256")!=source["source_jsonl_sha256"]):
        raise ValueError("original W12/Indago scientific index mismatch")
    if replay_publications:
        paper=attest_reusable_publications(published,packets)
        paper_phase="CACHED_BY_EXACT_SOURCE_AND_HOLD_GATE"
    else:
        paper=get_prior_art(packets,science_index,published,limit=53,max_workers=max_workers)
        if paper.get("route_count")!=53:
            raise RuntimeError("source provider incomplete")
        paper_phase="EXECUTED_OR_REPLAYED_API_SOURCE_COLLECTION"
    if existing_model_roots:
        roots=existing_model_roots
        model_phase="REUSE_SEPARATE_ATTESTED_MODEL_OPERATION_ROOTS"
        calls=0
    else:
        proposal=run_criticism(packets,science_index,published,model,
                limit=53,chunk_size=chunk_size,provider=provider,timeout=timeout)
        calls=proposal["provider_calls"]
        roots=[model]
        model_phase="EXECUTED_OR_REPLAYED_BOUNDED_CLI_CHALLENGE"
    combined=merge_criticism(packets,published,roots,merged)
    board_state="NOT_REQUESTED"
    board_manifest_sha=None
    if board_repo is not None:
        if board_root is None or native_w12 is None or native_w12_snapshot is None:
            raise ValueError("board requires path, authenticated original W12 route snapshot and native sheet source")
        if not (board_repo/"src"/"kairoskopion"/"kairon_provider"/"w12_packets.py").is_file():
            raise ValueError("existing Kairoskopion board module missing")
        args=[
            sys.executable,"-m","kairoskopion.kairon_provider.w12_packets",
            "--source",str(native_w12),"--snapshot",str(native_w12_snapshot),
            "--output",str(board_root),
            "--science-index",str(science_index/"science_index.json"),
            "--published-sources",str(published),
            "--model-challenges",str(merged),
        ]
        if outreach_events:args.extend(["--outreach",str(outreach_events)])
        if diagnostics:args.extend(["--analysis-root",str(diagnostics)])
        env=os.environ.copy()
        env["PYTHONPATH"]=str(board_repo/"src")
        proc=subprocess.run(args,cwd=str(board_repo),env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            encoding="utf-8",errors="replace",timeout=150)
        if proc.returncode!=0:
            raise RuntimeError("Kairoskopion actual board invocation failed: "+proc.stderr[-350:])
        board_meta=load(board_root/"manifest.json")
        if (board_meta.get("records")!=53
                or board_meta.get("source_jsonl_sha256")!=source["source_jsonl_sha256"]
                or board_meta.get("ready_for_author_rework")!=0
                or board_meta.get("ready_for_human_send")!=0):
            raise ValueError("board promoted or lost routes")
        if board_meta.get("provisional_model_critique_count")!=combined["model_reviews_validated"]:
            raise ValueError("board has missing scholarly critiques")
        board_manifest_sha=hashlib.sha256((board_root/"manifest.json").read_bytes()).hexdigest()
        board_state="UPDATED_FROM_VERIFIED_SOURCE_REVIEW_RECORDS"
    report={
        "schema":SCHEMA,"source_w12_sha256":source["source_jsonl_sha256"],
        "source_routes":source["records"],
        "published_source_operation":paper_phase,
        "published_unique_doi":paper["unique_requested_doi"],
        "published_route_abstract_bindings":paper["abstracts_retrieved_route_bindings"],
        "published_provider_queries":paper["provider_queries"],
        "published_provider_cache_hits":paper["cache_hits"],
        "scientific_provider_phase":model_phase,
        "scientific_provider_calls_this_invocation":calls,
        "model_reviews_validated":combined["model_reviews_validated"],
        "source_linked_objections":combined["objections_with_abstract_passage"],
        "explicit_abstentions":combined["research_abstentions"],
        "pending_route_ids":combined["missing_routes"],
        "merged_receipt_sha256":hashlib.sha256((merged/"merged_challenge_receipt.json").read_bytes()).hexdigest(),
        "board_state":board_state,
        "board_manifest_sha256":board_manifest_sha,
        "publisher_fulltexts_certified":0,"author_gates_ready":0,"external_submission_actions":0,
        "quality_claim":"PROVISIONAL_DATABASE_ABSTRACT_SCHOLARLY_CHALLENGE",
    }
    put(merged/"workflow_receipt.json",report)
    return report

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--prior-index",type=Path,required=True)
    p.add_argument("--published",type=Path,required=True)
    p.add_argument("--model-output",type=Path,required=True)
    p.add_argument("--merged-output",type=Path,required=True)
    p.add_argument("--existing-model-root",action="append",type=Path)
    p.add_argument("--reuse-published",action="store_true")
    p.add_argument("--provider",choices=["auto","codex","claude"],default="auto")
    p.add_argument("--chunk-size",type=int,default=5)
    p.add_argument("--timeout",type=int,default=540)
    p.add_argument("--max-workers",type=int,default=4)
    p.add_argument("--board-repo",type=Path)
    p.add_argument("--board-output",type=Path)
    p.add_argument("--w12-rows",type=Path)
    p.add_argument("--w12-native-snapshot",type=Path)
    p.add_argument("--outreach-events",type=Path)
    p.add_argument("--existing-diagnostics",type=Path)
    a=p.parse_args()
    result=run_workflow(a.packets,a.prior_index,a.published,a.model_output,
        a.merged_output,existing_model_roots=a.existing_model_root,
        replay_publications=a.reuse_published,max_workers=a.max_workers,
        chunk_size=a.chunk_size,provider=a.provider,timeout=a.timeout,
        board_repo=a.board_repo,board_root=a.board_output,
        native_w12=a.w12_rows,native_w12_snapshot=a.w12_native_snapshot,
        outreach_events=a.outreach_events,diagnostics=a.existing_diagnostics)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not result["pending_route_ids"] else 2

if __name__=="__main__":
    raise SystemExit(main())
