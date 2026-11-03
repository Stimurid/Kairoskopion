"""F2→F3 bounded native source-return lane in EXISTING Kairoskopion controller.

Native Indago is not Codex, and a native Artikl research consultation is not
D25 manuscript authorisation.  This narrow lane safely stops on insufficient
source-depth and emits a lineage-preserving ResearchNeed instead of rewriting.
No journal SEND; no external WORLD or publication mutations.  The historical
reuse mode is explicit: it does not falsely claim a new native hunt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Callable

from .publication_runner import EvidenceBlocked, atomic_write, sha256
from .indago_native_bridge import preflight as native_indago_plan
from .indago_evidence_intake import import_hunt

SCHEMA="trimurti-native-organ-source-cycle-v1"
RESULT_SCHEMA="trimurti-native-organ-cycle-state-v1"
ARTIKL_CONTRACT="trimurti-artikl-native-research-need-v1"
REQUIRED_ARTIKL_DOCS=(
    "ENTRY_MANIFEST.md","RELEASE_MANIFEST.md","BASE_COLD_REENTER.md",
    "GATEWAY.md","LIVE_CORE.md","CAPABILITY_REGISTRY.md",
)

def _readjson(path:Path)->dict:
    x=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(x,dict):
        raise EvidenceBlocked("json_object_required:"+path.name)
    return x

def _digest(x:str)->bool:
    return isinstance(x,str) and bool(re.fullmatch(r"[0-9a-f]{64}",x))

def _immutable(path:Path,data:bytes):
    if path.exists():
        if path.read_bytes()!=data:
            raise EvidenceBlocked("immutable_receipt_changed:"+path.name)
    else:
        atomic_write(path,data)

def _emit(path:Path,obj:dict):
    data=(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    _immutable(path,data)
    return sha256(data)

def _safe_hunt_name(s:str)->bool:
    return isinstance(s,str) and bool(re.fullmatch(r"h-[a-zA-Z0-9_-]{20,170}",s))

def preflight_inputs(*,manifest:Path,original:Path,draft:Path,review:Path,
                     trusted_source_sha:str,trusted_draft_sha:str,
                     trusted_review_sha:str,artikl_source_root:Path)->tuple[dict,dict]:
    m=_readjson(manifest)
    if m.get("schema")!=SCHEMA or m.get("evidence_mode")!="REAL":
        raise EvidenceBlocked("native_factory_real_manifest_required")
    if m.get("mode") not in {"REUSE_VERIFIED_NATIVE_HUNT","EXECUTE_BOUNDED_NATIVE_HUNT"}:
        raise EvidenceBlocked("native_factory_mode_invalid")
    if m.get("author_gate")!="HOLD" or m.get("submit") is not False or m.get("article_seed_accepted") is not False:
        raise EvidenceBlocked("native_factory_author_boundary_required")
    for name,p,expected in (("source",original,trusted_source_sha),("draft",draft,trusted_draft_sha),
                             ("review",review,trusted_review_sha)):
        if not _digest(expected) or not p.is_file() or sha256(p.read_bytes())!=expected:
            raise EvidenceBlocked("trusted_"+name+"_sha256_mismatch")
    if not isinstance(m.get("case_id"),str) or m["case_id"]!="T3-TALK-20261019":
        raise EvidenceBlocked("native_factory_case_id_invalid")
    if not isinstance(m.get("route_id"),str) or len(m["route_id"])<8:
        raise EvidenceBlocked("native_factory_route_id_invalid")
    task=m.get("task_id")
    if not isinstance(task,str) or not re.fullmatch(r"TRIMURTI_[A-Z0-9_]{5,100}",task):
        raise EvidenceBlocked("canonical_task_id_required")
    if m.get("artikl_release")!="ARTIKL 1.0.0-rc9":
        raise EvidenceBlocked("stale_artikl_release")
    if m["mode"]=="REUSE_VERIFIED_NATIVE_HUNT" and not _safe_hunt_name(m.get("historical_hunt_id")):
        raise EvidenceBlocked("exact_historical_hunt_id_required")
    if m["mode"]=="EXECUTE_BOUNDED_NATIVE_HUNT" and m.get("historical_hunt_id") not in (None,""):
        raise EvidenceBlocked("new_hunt_must_not_inherit_historical_id")
    if _readjson(review).get("author_gate") not in {"HOLD",None}:
        raise EvidenceBlocked("previous_review_promoted_outside_authority")
    # Check authoritative local organ body bytes, but never self-certify that
    # an LLM actually read them. Native agent transcript is evaluated separately.
    source_root=artikl_source_root.resolve(strict=True)
    docs={}
    for fn in REQUIRED_ARTIKL_DOCS:
        file=source_root/fn
        if not file.is_file() or file.stat().st_size<1000:
            raise EvidenceBlocked("artikl_canonical_body_missing:"+fn)
        docs[fn]={"sha256":sha256(file.read_bytes()),"bytes":file.stat().st_size}
    entry=(source_root/"ENTRY_MANIFEST.md").read_text(encoding="utf-8-sig")
    release=(source_root/"RELEASE_MANIFEST.md").read_text(encoding="utf-8-sig")
    if "CURRENT_RELEASE = ARTIKL 1.0.0-rc9" not in entry or "CURRENT_RELEASE remains ARTIKL 1.0.0-rc9" not in release:
        raise EvidenceBlocked("artikl_currentness_authority_not_rc9")
    return m,docs

def _native_hunt(*,port_root:Path,task_id:str,root:Path,waves:int=1,timeout:int=290,
                 executor:Callable=subprocess.run)->tuple[str,dict]:
    # The service owns all host and authority controls; there is no --force,
    # --offline, or --skip-agent-check in this executed hunt.
    if waves!=1 or not 210<=timeout<=540:
        raise EvidenceBlocked("bounded_native_hunt_required")
    pending=root/"native-hunt.started"
    finished=root/"native-hunt.outcome.json"
    if pending.exists() and not finished.exists():
        raise EvidenceBlocked("native_hunt_orphan_requires_operator_triage")
    if finished.exists():
        o=_readjson(finished)
        return o["hunt_id"],o
    _immutable(pending,b"INVOKED_NATIVE_INDAGO_ONCE\n")
    command=[sys.executable,"-m","indago_port","hunt","--task",task_id,
             "--waves","1","--wave-timeout",str(timeout),
             "--max-total",str(timeout+65)]
    try:
        cp=executor(command,cwd=port_root,capture_output=True,text=True,
                    encoding="utf-8",errors="replace",timeout=timeout+140,check=False)
    except subprocess.TimeoutExpired as e:
        raise EvidenceBlocked("native_hunt_timeout_triage_needed") from e
    _immutable(root/"native-hunt.stdout.log",cp.stdout.encode("utf-8"))
    _immutable(root/"native-hunt.stderr.log",cp.stderr.encode("utf-8"))
    try:
        value=json.loads(cp.stdout)
    except ValueError as e:
        raise EvidenceBlocked("native_hunt_invalid_json_triage_needed") from e
    if cp.returncode not in {0,10,20} or value.get("status") not in {"PASS","PARTIAL","BLOCKED"}:
        raise EvidenceBlocked("native_hunt_exit_or_status_invalid")
    loc=(value.get("paths") or {}).get("dir")
    if not loc:
        raise EvidenceBlocked("native_hunt_missing_verified_hunt_dir")
    name=Path(loc).name
    if not _safe_hunt_name(name):
        raise EvidenceBlocked("native_hunt_returned_unsafe_identity")
    rec={"hunt_id":name,"native_status":value["status"],
         "exit":cp.returncode,"stdout_sha256":sha256(cp.stdout.encode("utf-8")),
         "stderr_sha256":sha256(cp.stderr.encode("utf-8")),
         "executable":"python -m indago_port hunt",
         "hunt_executed_in_this_cycle":True}
    _emit(finished,rec)
    return name,rec

def _parse_openclaw(stdout:bytes)->tuple[dict,dict]:
    try:
        outer=json.loads(stdout.decode("utf-8-sig"))
    except (ValueError,UnicodeError) as e:
        raise EvidenceBlocked("native_artikl_gateway_json_invalid") from e
    if outer.get("status")!="ok" or not isinstance(outer.get("result"),dict):
        raise EvidenceBlocked("native_artikl_gateway_failed")
    result=outer["result"]
    payloads=result.get("payloads") or []
    if not payloads or not isinstance(payloads[0].get("text"),str):
        raise EvidenceBlocked("native_artikl_reply_missing")
    try:
        inner=json.loads(payloads[0]["text"])
    except ValueError as e:
        raise EvidenceBlocked("native_artikl_reply_not_json") from e
    meta=result.get("meta") or {}
    summary=meta.get("toolSummary") or {}
    # Shape in installed 2026.9.8 can have toolSummary under meta or raw
    if not summary:
        summary=(result.get("metadata") or {}).get("toolSummary") or {}
    if not isinstance(inner,dict):
        raise EvidenceBlocked("native_artikl_reply_not_object")
    return inner,{"runId":outer.get("runId"),"toolSummary":summary,
                  "result_status":outer.get("status")}

def _artikl_prompt(*,m:dict,source_sha:str,draft_sha:str,review_sha:str,
                   evidence:dict,need:dict,root:Path,artikl_workspace:Path)->Path:
    src=artikl_workspace/"SOURCE_ARTIKL"
    prompt=(
      "T3 FACTORY F3 / NATIVE ARTIKL READ-ONLY SCIENTIFIC RETURN, NOT MANUSCRIPT REWRITE. "
      "You are organ ARTIKL, NOT AIYE actor, not FORM_AGRIPPA. Do not change files, "
      "WORLD, Git, Drive or send any message; only read. From your actual workspace "
      "read FULL SOURCE_ARTIKL files in required dependency order: ENTRY_MANIFEST.md, "
      "RELEASE_MANIFEST.md, BASE_COLD_REENTER.md, GATEWAY.md, LIVE_CORE.md, "
      "CAPABILITY_REGISTRY.md. D27 is NOT canonical, ARTIKL CURRENT rc9. "
      "Read available local source evidence and independent reviewer if tools permit; "
      "do not infer full paper reading from metadata. "
      f"Factory case {m['case_id']}, route {m['route_id']}, task {m['task_id']}; "
      f"original source SHA {source_sha}; candidate SHA {draft_sha}; "
      f"independent reviewer SHA {review_sha}. "
      f"Native Indago real previous hunt {evidence['native_hunt_id']}, "
      f"status {evidence['native_status']}, calls {evidence['counts']['provider_calls']}, "
      f"new full evidence {evidence['counts']['new_verified']}. "
      "Its files are in existing owner-local INDAGO_STATE. "
      "This stage may formulate a ResearchNeed but MUST NOT issue a new hunt, "
      "rewrite a manuscript, grant D25 MANUSCRIPT_GO, claim WhiteCrow executed or "
      "send content. Don't lie about actual tool reads or provenance. "
      "The scientific evidence-depth gate is a host decision: if original primary "
      "passages are absent, reply EVIDENCE_DEPTH_HOLD. "
      "Output ONLY a JSON object with exact fields: "
      f"'schema':'{ARTIKL_CONTRACT}',"
      f"'task_id':'{m['task_id']}',"
      "'agent_id':'artikl','organ_not_actor':true,'current_release':'ARTIKL 1.0.0-rc9',"
      "'cold_reentry':'FULL_SIX_SOURCES_READ'|'PARTIAL'|'BLOCKED',"
      "'research_disposition':'EVIDENCE_DEPTH_HOLD'|'REVIEW_REQUIRED',"
      "'d14_concept':'...','d15_evidence':'...','d24_due_diligence':'...',"
      "'d25_state':'MANUSCRIPT_GO_FORBIDDEN',"
      "'research_need':{'reason':'...','missing_evidence':['...'],"
      "'strongest_unanswered_objection':'...','proposed_next_hunt':'...'},"
      "'can_proceed_to_full_manuscript':false,'author_gate':'HOLD',"
      "'send':false,'world_mutation':false,'notes':'...'."
    )
    msg=root/"native-artikl-message.txt"
    _immutable(msg,prompt.encode("utf-8"))
    return msg

def _native_artikl(*,m:dict,evidence:dict,need:dict,root:Path,
                   artikl_workspace:Path,source_sha:str,draft_sha:str,
                   review_sha:str,executor:Callable=subprocess.run)->tuple[dict,dict]:
    stdout=root/"artikl-native.stdout.json"
    stderr=root/"artikl-native.stderr.log"
    meta_path=root/"artikl-native.producer.json"
    if stdout.exists() and not meta_path.exists():
        raise EvidenceBlocked("native_artikl_orphan_requires_operator_triage")
    msg=_artikl_prompt(m=m,evidence=evidence,need=need,root=root,
                     artikl_workspace=artikl_workspace,source_sha=source_sha,
                     draft_sha=draft_sha,review_sha=review_sha)
    if not stdout.exists():
        exe=shutil.which("openclaw.cmd") or shutil.which("openclaw")
        if not exe:
            raise EvidenceBlocked("native_openclaw_executable_missing")
        sid=str(uuid.uuid5(uuid.NAMESPACE_URL,sha256(msg.read_bytes())))
        cp=executor([exe,"agent","--agent","artikl","--json","--session-id",
                    sid,"--timeout","180","--message-file",str(msg)],
                    capture_output=True,text=True,encoding="utf-8",
                    errors="replace",timeout=245,check=False)
        _immutable(stdout,cp.stdout.encode("utf-8"))
        _immutable(stderr,cp.stderr.encode("utf-8"))
        if cp.returncode!=0:
            raise EvidenceBlocked("native_artikl_cli_failed_exit_"+str(cp.returncode))
        _emit(meta_path,{"exit":cp.returncode,"session_id":sid,
                         "stdout_sha256":sha256(stdout.read_bytes()),
                         "stderr_sha256":sha256(stderr.read_bytes()),
                         "agent":"artikl","delivery":False})
    meta=_readjson(meta_path)
    if sha256(stdout.read_bytes())!=meta["stdout_sha256"]:
        raise EvidenceBlocked("native_artikl_response_tampered")
    result,details=_parse_openclaw(stdout.read_bytes())
    if result.get("schema")!=ARTIKL_CONTRACT or result.get("task_id")!=m["task_id"]:
        raise EvidenceBlocked("native_artikl_wrong_task_or_schema")
    if result.get("agent_id")!="artikl" or result.get("organ_not_actor") is not True:
        raise EvidenceBlocked("native_artikl_wrong_identity")
    if result.get("current_release")!="ARTIKL 1.0.0-rc9":
        raise EvidenceBlocked("native_artikl_stale_release")
    if result.get("author_gate")!="HOLD" or result.get("send") is not False or result.get("world_mutation") is not False:
        raise EvidenceBlocked("native_artikl_attempted_unapproved_promotion")
    if result.get("can_proceed_to_full_manuscript") is not False or result.get("d25_state")!="MANUSCRIPT_GO_FORBIDDEN":
        raise EvidenceBlocked("native_artikl_untrusted_d25_claim")
    if result.get("research_disposition") not in {"EVIDENCE_DEPTH_HOLD","REVIEW_REQUIRED"}:
        raise EvidenceBlocked("native_artikl_disposition_invalid")
    req=result.get("research_need") or {}
    if not isinstance(req.get("missing_evidence"),list) or not req.get("reason"):
        raise EvidenceBlocked("native_artikl_research_need_incomplete")
    return result,{"agent":"artikl","native_gateway":details,
                  "stdout_sha256":sha256(stdout.read_bytes()),
                  "stderr_sha256":sha256(stderr.read_bytes()),
                  "tool_read_claim_not_self_certifying":True}

def run(*,manifest_path:Path,original:Path,draft:Path,review:Path,
        port_root:Path,hunts_root:Path,artikl_workspace:Path,
        output_root:Path,trusted_source_sha:str,trusted_draft_sha:str,
        trusted_review_sha:str,run_hunt:Callable|None=None,
        run_artikl:Callable|None=None)->dict:
    m,docs=preflight_inputs(manifest=manifest_path,original=original,draft=draft,
        review=review,trusted_source_sha=trusted_source_sha,
        trusted_draft_sha=trusted_draft_sha,
        trusted_review_sha=trusted_review_sha,
        artikl_source_root=artikl_workspace/"SOURCE_ARTIKL")
    path=output_root.resolve()
    path.mkdir(parents=True,exist_ok=True)
    runid=sha256((sha256(manifest_path.read_bytes())+"|"+trusted_source_sha+
                 "|"+trusted_draft_sha+"|"+trusted_review_sha).encode("ascii"))
    root=path/runid
    root.mkdir(exist_ok=True)
    lock=root/".native-factory-run.lock"
    try:
        fd=os.open(str(lock),os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
    except FileExistsError as e:
        raise EvidenceBlocked("native_factory_existing_lock_operator_review") from e
    try:
        with os.fdopen(fd,"w",encoding="ascii") as f:
            f.write("LOCKED_F2_F3_NO_SEND\n")
        plan=native_indago_plan(port_root=port_root,task_id=m["task_id"],
                                output_root=root/"indago-plan")
        if plan.get("result")!="ADMITTED_FOR_SEPARATE_NATIVE_HUNT":
            raise EvidenceBlocked("native_indago_not_currently_admitted")
        if m["mode"]=="REUSE_VERIFIED_NATIVE_HUNT":
            huntid=m["historical_hunt_id"]
            huntmeta={"hunt_id":huntid,"hunt_executed_in_this_cycle":False,
                      "provenance":"VERIFIED_PRIOR_NATIVE_HUNT_REUSE"}
        else:
            huntid,huntmeta=_native_hunt(port_root=port_root,task_id=m["task_id"],
                                        root=root,executor=run_hunt or subprocess.run)
        evidence=import_hunt(hunts_root=hunts_root,hunt_dir=hunts_root/huntid,
            output_root=root/"indago-evidence",expected_task=m["task_id"],
            trusted_original_sha=trusted_source_sha,
            trusted_manuscript_sha=trusted_draft_sha,
            trusted_review_sha=trusted_review_sha)
        counts=evidence["counts"]
        # The original Indago candidate records are bibliographic hints until
        # D15/D24 can independently tie actual read passages to the exact claim.
        depth_ok=(evidence.get("evidence_depth")=="FULL_PRIMARY_READ_ADMITTED" and
                  counts.get("new_verified",0)>0)
        need={"schema":"trimurti-research-need-v1","case_id":m["case_id"],
              "route_id":m["route_id"],"task_id":m["task_id"],
              "trigger_review_sha256":trusted_review_sha,
              "original_sha256":trusted_source_sha,
              "manuscript_sha256":trusted_draft_sha,
              "source_hunt_id":huntid,
              "source_hunt_sha256":sha256((root/"indago-evidence"/("indago-intake-"+huntid+".json")).read_bytes()),
              "status":"SOURCE_DEPTH_HOLD" if not depth_ok else "SCIENTIFIC_REVIEW_REQUIRED",
              "reason":"NATIVE_METADATA_ONLY_UNQUALIFIED_FOR_D15" if not depth_ok
                      else "INDEPENDENT_D14_D15_D24_REVIEW_REQUIRED",
              "whitecrow_runtime":"NOT_INVOKED_IN_THIS_CYCLE",
              "author_gate":"HOLD","manuscript_go":False,"send":False,"new_w12_routes":0}
        _emit(root/"research-need.json",need)
        response,aprovenance=_native_artikl(m=m,evidence=evidence,need=need,
            root=root,artikl_workspace=artikl_workspace,
            source_sha=trusted_source_sha,draft_sha=trusted_draft_sha,
            review_sha=trusted_review_sha,
            executor=run_artikl or subprocess.run)
        state={"schema":RESULT_SCHEMA,"cycle_id":runid,"case_id":m["case_id"],
             "route_id":m["route_id"],"status":"SCIENTIFIC_RESEARCH_NEED_HOLD",
             "f1_one_command_actual":True,
             "f2_native_indago_admission":"LIVE_VERIFIED",
             "f2_native_indago_hunt":huntmeta,
             "f2_science_evidence_status":need["status"],
             "f3_native_artikl_agent_reply":"READ_ONLY_RESEARCH_NEED",
             "f3_artikl_source_docs":docs,"f3_artikl_native_provenance":aprovenance,
             "f3_artikl_reentry_self_report":response.get("cold_reentry"),
             "f3_artikl_reply_sha256":sha256((root/"artikl-native.stdout.json").read_bytes()),
             "f4_closed_loop":"NOT_PASSED_CONSISTENT_HOLD_NO_AUTONOMOUS_REWRITE",
             "whitecrow_native":"NOT_INVOKED",
             "source_original_sha256":trusted_source_sha,
             "draft_sha256":trusted_draft_sha,"prior_review_sha256":trusted_review_sha,
             "reviewer_response":"RESEARCH_NEED_NOT_MANUSCRIPT_REVIEW",
             "research_need":need,
             "author_gate":"HOLD","new_w12_routes":0,"send":False,
             "world_mutation":False,"production_deployed":False}
        _emit(root/"state.json",state)
        return {"status":state["status"],"cycle_id":runid,
                "state_path":str(root/"state.json"),
                "research_need_path":str(root/"research-need.json"),
                "source_hunt_id":huntid,
                "hunt_executed_in_this_cycle":huntmeta["hunt_executed_in_this_cycle"],
                "artikl_native":"READ_ONLY_RESEARCH_NEED",
                "f2":need["status"],"f3":"NATIVE_READ_ONLY_HOLD",
                "f4":"NOT_PASSED","author_gate":"HOLD","send":False}
    finally:
        lock.unlink(missing_ok=True)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="manuscript_cycle_runner native")
    for key in ("manifest","original","draft","review","port-root","hunts-root",
                "artikl-workspace","output-root"):
        p.add_argument("--"+key,required=True,type=Path)
    for key in ("source","draft","review"):
        p.add_argument("--trusted-"+key+"-sha256",required=True)
    a=p.parse_args(argv)
    try:
        result=run(manifest_path=a.manifest,original=a.original,draft=a.draft,
                   review=a.review,port_root=a.port_root,
                   hunts_root=a.hunts_root,artikl_workspace=a.artikl_workspace,
                   output_root=a.output_root,
                   trusted_source_sha=a.trusted_source_sha256,
                   trusted_draft_sha=a.trusted_draft_sha256,
                   trusted_review_sha=a.trusted_review_sha256)
    except (EvidenceBlocked,OSError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"BLOCKED_NATIVE_FACTORY","reason":str(e)[:250],
                          "author_gate":"HOLD","send":False,"new_w12_routes":0}))
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
