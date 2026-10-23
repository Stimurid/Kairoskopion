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
if __package__:
    from .fetch_mai_prior_art import execute as get_prior_art, stable as provider_stable, normalize_doi
else:
    from fetch_mai_prior_art import execute as get_prior_art, stable as provider_stable, normalize_doi
if __package__:
    from .run_mai_claim_challenge import run as run_criticism
else:
    from run_mai_claim_challenge import run as run_criticism
if __package__:
    from .merge_mai_scholarly_reviews import run as merge_criticism
else:
    from merge_mai_scholarly_reviews import run as merge_criticism
if __package__:
    from .fetch_mai_venue_pages import capture as capture_venues
else:
    from fetch_mai_venue_pages import capture as capture_venues
if __package__:
    from .run_mai_kairon_policy_claims import run as run_kairon_policy
else:
    from run_mai_kairon_policy_claims import run as run_kairon_policy
if __package__:
    from .run_mai_native_scholarly_read import run as run_native_scholarship
else:
    from run_mai_native_scholarly_read import run as run_native_scholarship
if __package__:
    from .run_mai_a_education_field_reopen import execute as run_scientific_field_reopen
else:
    from run_mai_a_education_field_reopen import execute as run_scientific_field_reopen
if __package__:
    from .publish_mai_a3a4_native_graph_reopen import import_held_return as emit_existing_graph_return
else:
    from publish_mai_a3a4_native_graph_reopen import import_held_return as emit_existing_graph_return

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

def attest_reusable_venues(root:Path,packets:Path)->dict[str,Any]:
    source=load(packets/"manifest.json")
    data=load(root/"venue_acquisition_receipt.json")
    if (data.get("schema")!="MAI_KAIRON_VENUE_WEB_ACQUISITION_BATCH_v1"
            or data.get("source_W12_sha256")!=source.get("source_jsonl_sha256")
            or data.get("routes_requested")!=source.get("records")
            or data.get("policies_certified")!=0 or data.get("cfp_deadlines_verified")!=0
            or data.get("author_gate_ready")!=0 or data.get("external_submissions")!=0):
        raise ValueError("Kairon cached web capture cannot promote policy / unknown W12 corpus")
    for f in sorted((packets/"routes").glob("MAI-W12-*.json")):
        original=load(f)["route"]
        rid=f.stem
        capfile=root/"routes"/f.name
        if not capfile.is_file():
            raise ValueError("missing actual Kairon web source route "+rid)
        route=load(capfile)
        web=route.get("web_source") or {}
        if (route.get("schema")!="MAI_KAIRON_OFFICIAL_VENUE_WEB_CAPTURE_v1"
                or route.get("route_id")!=rid
                or route.get("W12_source_sha256")!=source["source_jsonl_sha256"]
                or route.get("w12_listed_official_url")!=original.get("official_url","")
                or route.get("official_rules_acceptance")!="HOLD"
                or route.get("author_gate")!="CLOSED"
                or route.get("send_count")!=0
                or route.get("venue_page_domain_alone_is_not_policy_acceptance") is not True
                or route.get("policy_freshness_verified") is not False
                or any(web.get(k) is not False for k in (
                    "submission_policy_verified","cfp_deadline_verified",
                    "ai_authorship_policy_verified","official_publisher_status_verified"))):
            raise ValueError("stale or forged Kairon venue status "+rid)
        rawsha=web.get("raw_sha256")
        if rawsha:
            rootpath=root/"url_capture_cache"/hashlib.sha256(
                route["w12_listed_official_url"].encode("utf-8")).hexdigest()[:24]
            raw=rootpath/"source.bin"
            if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest()!=rawsha:
                raise ValueError("stale raw publisher HTML source "+rid)
        visible=web.get("visible_text_sha256")
        if visible:
            txt=root/"url_capture_cache"/hashlib.sha256(
                route["w12_listed_official_url"].encode("utf-8")).hexdigest()[:24]/"visible_text.txt"
            if not txt.is_file() or hashlib.sha256(txt.read_text(encoding="utf-8").rstrip("\r\n").encode("utf-8")).hexdigest()!=visible:
                raise ValueError("stale original extracted HTML paragraph "+rid)
    return data

def run_workflow(
    packets:Path, science_index:Path, published:Path, model:Path,
    merged:Path, *, existing_model_roots:list[Path]|None=None,
    replay_publications:bool=False, max_workers:int=4,
    chunk_size:int=5, provider:str="auto", timeout:int=540,
    board_repo:Path|None=None, board_root:Path|None=None,
    native_w12:Path|None=None, native_w12_snapshot:Path|None=None,
    outreach_events:Path|None=None, diagnostics:Path|None=None,
    venue_root:Path|None=None,replay_venues:bool=False,
    venue_policy_root:Path|None=None,policy_provider:str="claude",
    venue_native_root:Path|None=None,
    native_scholarly_root:Path|None=None,author_book_source:Path|None=None,
    field_reopen_root:Path|None=None,
    existing_opportunity_graph_root:Path|None=None,
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
    venue_data=None
    venue_phase="NOT_REQUESTED"
    if venue_root is not None:
        if replay_venues:
            venue_data=attest_reusable_venues(venue_root,packets)
            venue_phase="CACHED_BY_W12_AND_RAW_HTML_SHA256"
        else:
            venue_data=capture_venues(packets,venue_root,limit=53,
                                      workers=max_workers)
            if venue_data.get("routes_requested")!=53:
                raise RuntimeError("Kairon web source run incomplete")
            venue_phase="EXECUTED_OR_REPLAYED_OFFICIAL_URL_HTML_CAPTURE"
    policy_data=None
    if venue_policy_root is not None:
        if venue_root is None:
            raise ValueError("Kairon policy interpretation needs a real web source capture")
        policy_data=run_kairon_policy(packets,venue_root,venue_policy_root,limit=53,provider=policy_provider,timeout=timeout)
        if policy_data.get("missing_routes"):
            raise ValueError("Incomplete policy candidate source coverage: "+str(policy_data["missing_routes"]))
    native_data=None
    if venue_native_root is not None:
        native_data=load(venue_native_root/"native_work_batch_receipt.json")
        if (native_data.get("schema")!="MAI_KAIRON_NATIVE_PUBLISHER_WORK_BATCH_v1"
                or native_data.get("source_W12_sha256")!=source["source_jsonl_sha256"]
                or native_data.get("journal_send_count")!=0
                or native_data.get("read_depth_certified_scholarly_full_text")!=0):
            raise ValueError("publisher native work source cannot promote article science or authority")
    deep_model=None
    if native_scholarly_root is not None:
        if venue_native_root is None or author_book_source is None:
            raise ValueError("original publisher works and authenticated author book required for scholarly model reading")
        deep_model=run_native_scholarship(packets,venue_native_root,author_book_source,
                                         native_scholarly_root,provider="claude",timeout=timeout,limit=3)
        if deep_model.get("machine_source_grounded_papers_reviewed")!=3:
            raise ValueError("source-quote verified authorial challenge not completed on three real works")
    reopen_data=None
    if field_reopen_root is not None:
        if native_scholarly_root is None or venue_native_root is None or author_book_source is None:
            raise ValueError("source-anchored field reopen requires original scholarly reads and owner context")
        reopen_data=run_scientific_field_reopen(packets,venue_native_root,author_book_source,
                                               native_scholarly_root,field_reopen_root)
        if (reopen_data.get("source_articles")!=3
                or reopen_data.get("proposal",{}).get("author_world_change_approved") is not False
                or reopen_data.get("proposal",{}).get("external_send_count")!=0):
            raise ValueError("scientific World-return proposal cannot mutate owner authority")
    graph_data=None
    if existing_opportunity_graph_root is not None:
        if (field_reopen_root is None or native_scholarly_root is None
                or venue_native_root is None or author_book_source is None):
            raise ValueError("existing graph events require real source-validated three-work scientific return")
        graph_data=emit_existing_graph_return(packets,venue_native_root,author_book_source,
                                              native_scholarly_root,field_reopen_root,
                                              existing_opportunity_graph_root)
        if (graph_data.get("case_publisher_original_work_count")!=3
                or graph_data.get("world_mutations")!=0
                or graph_data.get("outbound_submissions")!=0):
            raise ValueError("native Kairon graph failed to preserve author control")
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
        if venue_root is not None:args.extend(["--venue-web",str(venue_root)])
        if venue_policy_root is not None:args.extend(["--venue-policy",str(venue_policy_root)])
        if venue_native_root is not None:args.extend(["--venue-native",str(venue_native_root)])
        if native_scholarly_root is not None:args.extend(["--native-scholarly",str(native_scholarly_root)])
        if field_reopen_root is not None:args.extend(["--field-reopen",str(field_reopen_root)])
        if existing_opportunity_graph_root is not None:
            args.extend(["--field-graph-root",str(existing_opportunity_graph_root)])
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
        if venue_data is not None and (board_meta.get("venue_pages_acquired_count")!=53
                or board_meta.get("venue_policies_certified_count")!=0):
            raise ValueError("board misrepresented actual Kairon web evidence")
        if policy_data is not None and (board_meta.get("venue_policy_candidate_count")!=53
                or board_meta.get("venue_policy_cited_claim_count")!=policy_data["route_evidence_claim_count"]
                or board_meta.get("venue_policies_certified_count")!=0):
            raise ValueError("Kairoskopion board dropped provisional venue-policy evidence")
        if native_data is not None and (board_meta.get("venue_native_publication_source_count")!=native_data["input_candidate_count"]
                or board_meta.get("venue_native_scholarly_full_texts_certified")!=0):
            raise ValueError("board misclassified native publisher source as full read")
        if deep_model is not None and (board_meta.get("native_scholarly_model_reads_count")!=3
                or board_meta.get("native_scholarly_model_read_anchors")!=deep_model["quoted_argument_anchors"]
                or board_meta.get("native_scholarly_independent_scholarly_acceptance")!=0):
            raise ValueError("board misreported actual source-quoted scientific reading")
        if reopen_data is not None and (board_meta.get("scientific_field_reopen_proposal_count")!=1
                or board_meta.get("scientific_field_reopen_world_mutations")!=0):
            raise ValueError("board cannot auto-adopt scientific field reopen proposal")
        if graph_data is not None and (board_meta.get("native_kairon_graph_field_reopens")!=1
                or board_meta.get("native_kairon_graph_original_evidence_count")!=3
                or board_meta.get("native_kairon_graph_author_approvals")!=0):
            raise ValueError("board lost real source-bound existing OpportunityGraphStore events")
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
        "kairon_venue_capture_phase":venue_phase,
        "kairon_pages_acquired_count":venue_data["routes_requested"] if venue_data else 0,
        "kairon_route_statuses":venue_data["routes_by_http_status"] if venue_data else {},
        "kairon_policy_candidate_routes":policy_data["route_policy_citations_validated"] if policy_data else 0,
        "kairon_policy_source_quotes":policy_data["route_evidence_claim_count"] if policy_data else 0,
        "kairon_policy_model_calls_this_invocation":policy_data["total_model_calls_this_run"] if policy_data else 0,
        "kairon_native_venue_source_count":native_data["input_candidate_count"] if native_data else 0,
        "artikl_native_publisher_scholarly_reviews":deep_model["machine_source_grounded_papers_reviewed"] if deep_model else 0,
        "artikl_native_article_quote_anchors":deep_model["quoted_argument_anchors"] if deep_model else 0,
        "artikl_scholarly_model_calls_this_invocation":deep_model["new_model_calls"] if deep_model else 0,
        "artikl_a3a4_field_reopen_proposals":1 if reopen_data else 0,
        "artikl_a3a4_field_reopen_model_calls_this_invocation":reopen_data["model_calls"] if reopen_data else 0,
        "artikl_a3a4_field_reopen_author_approved":0,
        "existing_kairon_graph_real_source_reopens":1 if graph_data else 0,
        "existing_kairon_graph_pinned_original_evidence":graph_data["case_publisher_original_work_count"] if graph_data else 0,
        "existing_kairon_graph_author_approved":0,
        "kairon_venue_policies_certified":0,
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
    p.add_argument("--venue-web",type=Path)
    p.add_argument("--reuse-venues",action="store_true")
    p.add_argument("--venue-policy-root",type=Path)
    p.add_argument("--venue-native-root",type=Path)
    p.add_argument("--native-scholarly-root",type=Path)
    p.add_argument("--author-book-source",type=Path)
    p.add_argument("--field-reopen-root",type=Path)
    p.add_argument("--opportunity-graph-root",type=Path)
    p.add_argument("--venue-policy-provider",choices=["claude","codex","auto"],default="claude")
    a=p.parse_args()
    result=run_workflow(a.packets,a.prior_index,a.published,a.model_output,
        a.merged_output,existing_model_roots=a.existing_model_root,
        replay_publications=a.reuse_published,max_workers=a.max_workers,
        chunk_size=a.chunk_size,provider=a.provider,timeout=a.timeout,
        board_repo=a.board_repo,board_root=a.board_output,
        native_w12=a.w12_rows,native_w12_snapshot=a.w12_native_snapshot,
        outreach_events=a.outreach_events,diagnostics=a.existing_diagnostics,
        venue_root=a.venue_web,replay_venues=a.reuse_venues,
        venue_policy_root=a.venue_policy_root,policy_provider=a.venue_policy_provider,
        venue_native_root=a.venue_native_root,
        native_scholarly_root=a.native_scholarly_root,author_book_source=a.author_book_source,
        field_reopen_root=a.field_reopen_root,
        existing_opportunity_graph_root=a.opportunity_graph_root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not result["pending_route_ids"] else 2

if __name__=="__main__":
    raise SystemExit(main())
