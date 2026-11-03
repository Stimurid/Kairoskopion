"""F240: ONE existing Kairoskopion entry point for ADD-006 Indago→WhiteCrow→Artikl.

Use immutable scientific source/dispatch pins; running a NEW dispatch calls
actual installed indago_port add006-oneshot with O_EXCL claim-first and real
OpenClaw Indago. A prior COMPLETED dispatch can be replayed without new provider
or model calls. Author HOLD and no SEND are hard constraints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from .publication_runner import EvidenceBlocked, atomic_write, sha256
from .add006_return_bridge import bridge as whitecrow_return

SCHEMA="trimurti-native-add006-factory-input-v1"
RECEIPT="trimurti-native-add006-factory-receipt-v1"

def _read(p:Path)->dict:
    o=json.loads(p.read_text(encoding="utf-8-sig"))
    if not isinstance(o,dict):
        raise EvidenceBlocked("required JSON object: "+p.name)
    return o

def _pin(p:Path,digest:str)->bytes:
    if not re.fullmatch(r"[0-9a-f]{64}",digest or "") or not p.is_file():
        raise EvidenceBlocked("missing trusted file/pin: "+p.name)
    value=p.read_bytes()
    if sha256(value)!=digest:
        raise EvidenceBlocked("trusted source pin mismatch: "+p.name)
    return value

def _save(path:Path,body:bytes):
    if path.exists():
        if path.read_bytes()!=body:
            raise EvidenceBlocked("immutable factory output conflict: "+path.name)
    else:
        atomic_write(path,body)

def _emit(path:Path,obj:dict)->str:
    b=(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    _save(path,b)
    return sha256(b)

def _model_inner(stdout:bytes)->tuple[dict,dict]:
    try:
        data=json.loads(stdout.decode("utf-8-sig"))
    except (UnicodeError,ValueError):
        try:data=json.loads(stdout.decode("utf-16"))
        except (UnicodeError,ValueError) as e:raise EvidenceBlocked("native_artikl_stdout_unparseable") from e
    if data.get("status")!="ok":
        raise EvidenceBlocked("native_artikl_gateway_not_ok")
    result=data.get("result") or {}
    payloads=result.get("payloads") or []
    try:inner=json.loads(payloads[0]["text"])
    except (ValueError,IndexError,KeyError,TypeError) as e:
        raise EvidenceBlocked("native_artikl_reply_not_typed_json") from e
    return inner,data

def _assert_science_choice(inner:dict,request:dict,evidence_sha:str,report_sha:str)->str:
    if inner.get("schema")!="trimurti-artikl-f240-research-vs-revision-decision-v1":
        raise EvidenceBlocked("native_artikl_response_schema_invalid")
    if inner.get("agent_id")!="artikl" or inner.get("organ_not_actor") is not True or inner.get("current_release")!="ARTIKL 1.0.0-rc9":
        raise EvidenceBlocked("native_artikl_agent_or_release_invalid")
    if inner.get("whitecrow_report_sha256")!=report_sha or inner.get("real_indago_evidence_sha256")!=evidence_sha:
        raise EvidenceBlocked("native_artikl_scientific_source_sha_conflict")
    if (inner.get("author_gate")!="HOLD" or inner.get("send") is not False
        or inner.get("world_mutation") is not False or inner.get("d25_manuscript_go") is not False
        or inner.get("source_novelty_accepted") is not False):
        raise EvidenceBlocked("native_artikl_illegal_scientific_promotion")
    choice=inner.get("decision")
    if choice == "REVISION_CANDIDATE":
        # A working revision is an editorial action, not publication approval.
        # An evidence weakness belongs in the candidate assessment, not here.
        if inner.get("revision_allowed_now") is not True:
            raise EvidenceBlocked("native_artikl_revision_choice_inconsistent")
    elif choice in ("MORE_RESEARCH","HOLD_BLOCKED"):
        if inner.get("revision_allowed_now") is not False:
            raise EvidenceBlocked("native_artikl_unreviewed_revision_not_allowed")
    else:
        raise EvidenceBlocked("native_artikl_unqualified_decision")
    if not isinstance(inner.get("next_research_questions"),list) or not inner.get("reason"):
        raise EvidenceBlocked("native_artikl_research_need_missing")
    return inner["decision"]

def _native_artikl(*,root:Path,source:Path,report_path:Path,
                   report_sha:str,evidence_sha:str,request:dict,
                   imported_response:Path|None,imported_response_sha:str|None)->tuple[dict,dict]:
    stdout=root/"native_artikl_stdout.json"
    if imported_response is not None:
        body=_pin(imported_response,imported_response_sha or "")
        _save(stdout,body)
        attestation="IMPORTED_PREVIOUS_NATIVE_AGENT_REPLY_NOT_NEW_CALL"
    elif stdout.exists():
        attestation="COLD_REPLAY_NO_NEW_MODEL_CALL"
    else:
        exe=shutil.which("openclaw.cmd") or shutil.which("openclaw")
        if not exe:raise EvidenceBlocked("openclaw_registered_artikl_missing")
        prompt=(
          "TRIMURTI CURRENT ARTIKL organ, registered OpenClaw agent artikl. "
          "Read FULL current SOURCE_ARTIKL entry/release/base/gateway/livecore/capability "
          "and source-bound report "+str(report_path)+" (SHA "+report_sha+"). "
          "If source_reliability_currentness includes F241_OWNER_PRIVATE_PDF_FULL_BYTE_AND_PAGE_EXTRACTION, "
          "open the two listed private full-text paths and read substantive original-method and "
          "source-competitor passages across each article; verify original PDF/section/page "
          "support. Distinguish all-pages machine extraction from your own source reading. "
          "Report which source claims and objections remain unverified; do not call an abstract "
          "full-text evidence. Cross-check C04 author v0.5 and M116 if available. "
          "Native evidence SHA "+evidence_sha+". This is scientific triage, NOT a "
          "request to rewrite C04 or publish. Inspect report fully before deciding. "
          "Independently decide MORE_RESEARCH, HOLD_BLOCKED, or REVISION_CANDIDATE. "
          "D24 and D15 provide source evaluations, never permission to improve a draft. "
          "A working REVISION_CANDIDATE is permitted even with unresolved source gaps: "
          "keep disputed assertions clearly tentative and preserve strong hypotheses. "
          "For REVISION_CANDIDATE set revision_allowed_now=true; otherwise false. "
          "Only publication or author acceptance needs its separate authorization. "
          "No autonomous additional "
          "research requests, file writes, messages, or journal SEND. "
          "Return ONLY JSON with keys schema:trimurti-artikl-f240-research-vs-revision-decision-v1, "
          "agent_id:artikl, organ_not_actor:true, current_release:ARTIKL 1.0.0-rc9, "
          "canonical_read:FULL_RC9|PARTIAL|BLOCKED, whitecrow_report_sha256:"+report_sha+
          ", real_indago_evidence_sha256:"+evidence_sha+
          ", decision:MORE_RESEARCH|HOLD_BLOCKED|REVISION_CANDIDATE, reason:string, next_research_questions:array,"
          "next_source_requirements:array, revision_allowed_now:boolean, d25_manuscript_go:false, "
          "source_novelty_accepted:false, author_gate:HOLD, send:false, world_mutation:false."
        )
        f=root/"artikl_message.txt"
        _save(f,prompt.encode("utf-8"))
        sid=str(uuid.uuid5(uuid.NAMESPACE_URL,sha256(prompt.encode("utf-8"))))
        pending=root/"artikl_native_started.txt"
        if pending.exists():
            raise EvidenceBlocked("native_artikl_orphan_requires_operator_triage")
        _save(pending,("native agent invoked "+sid+"\n").encode("utf-8"))
        try:
            cp=subprocess.run([exe,"agent","--agent","artikl","--json","--session-id",sid,
                    "--timeout","240","--message-file",str(f)],capture_output=True,
                    timeout=300,check=False)
        except subprocess.TimeoutExpired as e:
            raise EvidenceBlocked("native_artikl_timeout_requires_operator_triage") from e
        _save(root/"artikl_native_stderr.log",cp.stderr)
        _save(stdout,cp.stdout)
        if cp.returncode!=0:
            raise EvidenceBlocked("native_artikl_exit_"+str(cp.returncode))
        attestation="NEW_REGISTERED_ARTIKL_GATEWAY_INVOCATION"
    inner,outer=_model_inner(stdout.read_bytes())
    choice=_assert_science_choice(inner,request,evidence_sha,report_sha)
    meta=(outer.get("result") or {}).get("meta") or {}
    evidence={"agent":"artikl","gateway_status":outer.get("status"),
        "gateway_run_id":outer.get("runId"),
        "tool_summary":meta.get("toolSummary"),"stdout_sha256":sha256(stdout.read_bytes()),
        "invocation_class":attestation,"choice":choice,"model_self_attested_canon_read":inner.get("canonical_read")}
    return inner,evidence

def _terminal_science_gate(*,finite:bool,whitecrow_status:str,choice:str)->str:
    """Source-depth HOLD is scientific insufficiency, not a failed runtime.

    A native Artikl HOLD_BLOCKED may mean no D15 primary-claim admission
    despite a successful registered model invocation. Treat only actual
    missing scientific prerequisites as insufficient evidence. Never
    rewrite a historical immutable receipt when fixing categorization.
    """
    if choice=="REVISION_CANDIDATE":
        return "EDITORIAL_WORKING_REVISION_PROPOSED_NOT_YET_WRITTEN"
    if not finite:
        return "MORE_RESEARCH_AUTHOR_HOLD" if choice=="MORE_RESEARCH" else "HOLD_BLOCKED"
    if whitecrow_status in {"REQUALIFIED_RESEARCH_MORE_D15_HOLD", "REQUALIFIED_RESEARCH_STATUS_REPORTED"}:
        return "MORE_RESEARCH_RECOMMENDED_AUTHOR_HOLD" if choice=="MORE_RESEARCH" else "EDITORIAL_HOLD_CHOSEN"
    return "HOLD_TECHNICAL_BLOCKER"


def run(*,input_manifest:Path,request_path:Path,transport_path:Path,
        stage_receipt:Path,baseline_path:Path,
        trusted_request_sha:str,trusted_transport_sha:str,
        trusted_stage_sha:str,trusted_baseline_sha:str,
        port_root:Path,indago_state_root:Path,whitecrow_root:Path,
        trusted_wc_commit:str,trusted_wc_module_sha:str,
        output_root:Path,imported_artikl_response:Path|None=None,
        imported_artikl_response_sha:str|None=None,
        cycle_contract_path:Path|None=None,expected_cycle_contract_sha:str|None=None,
        source_carrier_packet:Path|None=None,expected_source_carrier_sha:str|None=None)->dict:
    manifest=_read(input_manifest)
    if (manifest.get("schema")!=SCHEMA or manifest.get("case_id")!="T3-TALK-20261019"
        or manifest.get("author_gate")!="HOLD" or manifest.get("send") is not False
        or manifest.get("world_mutation") is not False):
        raise EvidenceBlocked("unsupported_or_untrusted_factory_manifest")
    for p,h in ((request_path,trusted_request_sha),(transport_path,trusted_transport_sha),
                (stage_receipt,trusted_stage_sha),(baseline_path,trusted_baseline_sha)):
        _pin(p,h)
    req=_read(request_path)
    if (req.get("semantic_action_mode")!="CRITIQUE"
        or req.get("research_request_id")!=manifest.get("research_request_id")
        or req.get("dispatch_event_id")!=manifest.get("dispatch_event_id")):
        raise EvidenceBlocked("manifest_wrong_d24_request")
    contract=None
    if req["research_request_id"].startswith("T3-F241-"):
        if cycle_contract_path is None or not expected_cycle_contract_sha:
            raise EvidenceBlocked("finite_f241_cycle_contract_mandatory")
        _pin(cycle_contract_path,expected_cycle_contract_sha)
        contract=_read(cycle_contract_path)
        caps=contract.get("limits") or {}
        if (contract.get("schema")!="T3_F241_FINITE_C04_EXECUTION_CONTRACT_V1"
            or contract.get("new_research_request_id")!=req["research_request_id"]
            or contract.get("new_dispatch_event_id")!=req["dispatch_event_id"]
            or manifest.get("cycle_contract_sha256")!=expected_cycle_contract_sha
            or caps.get("new_scientific_request_count")!=1
            or caps.get("native_indago_hunt_count")!=1
            or caps.get("maximum_indago_waves")!=2
            or caps.get("maximum_total_provider_calls")!=8
            or caps.get("extra_recursive_hunts")!=0
            or caps.get("external_sends")!=0):
            raise EvidenceBlocked("f241_cycle_lifecycle_scope_invalid")
    # Host's claim key is immutable SHA(dispatch event). Same ID always
    # resolves to the same native claim regardless of rerun nonce.
    key=hashlib.sha256(req["dispatch_event_id"].encode("utf-8")).hexdigest()[:32]
    claim_root=indago_state_root/"add006_claims"
    claim=claim_root/key/"claim.json"
    ev=claim_root/key/"evidence_return.json"
    ledger=claim_root/"runtime_receipts.jsonl"
    out=output_root.resolve()
    out.mkdir(parents=True,exist_ok=True)
    digest=sha256((trusted_transport_sha+"|"+trusted_request_sha+"|"+trusted_stage_sha).encode("ascii"))
    root=out/digest
    root.mkdir(exist_ok=True)
    final=root/"native_factory_state.json"
    if final.exists():
        saved=_read(final)
        if (saved.get("schema")!=RECEIPT
            or saved.get("dispatch_event_id")!=req["dispatch_event_id"]
            or saved.get("author_gate")!="HOLD" or saved.get("send") is not False):
            raise EvidenceBlocked("native_factory_saved_state_invalid")
        if (sha256(ev.read_bytes())!=saved["real_evidence_sha256"]
            or sha256(claim.read_bytes())!=saved["claim_sha256"]
            or sha256(ledger.read_bytes())!=saved["runtime_ledger_sha256"]):
            raise EvidenceBlocked("native_factory_saved_source_changed")
        recorded=(saved.get("whitecrow_return") or {}).get("whitecrow_report_sha256")
        report=root/"whitecrow"/"whitecrow_d24_after_add006.json"
        if recorded and (not report.is_file() or sha256(report.read_bytes())!=recorded):
            raise EvidenceBlocked("native_factory_whitecrow_report_replay_tampered")
        recorded_agent=(saved.get("artikl_native") or {}).get("stdout_sha256")
        agent=root/"native_artikl_stdout.json"
        if recorded_agent and (not agent.is_file() or sha256(agent.read_bytes())!=recorded_agent):
            raise EvidenceBlocked("native_factory_artikl_response_replay_tampered")
        return {**saved,"replay_status":"IDENTICAL_STATE_ZERO_NEW_MODELS_OR_HUNTS"}
    lock=root/"runner.lock"
    try:fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as e:raise EvidenceBlocked("native_add006_factory_owner_run_lock") from e
    try:
        with os.fdopen(fd,"w") as f:f.write("RUNNING\n")
        reused=ev.is_file() and claim.is_file() and _read(claim).get("state")=="COMPLETED"
        if not reused:
            if (root/"native_hunt_started.txt").exists():
                raise EvidenceBlocked("native_indago_orphan_requires_operator_triage")
            # This executes the genuine native Indago port, not the old
            # historical M108 import. The port enforces its own live Drive
            # authority gate, OpenClaw isolation, O_EXCL claim and HuntLease.
            cmd=[sys.executable,"-m","indago_port","--state-root",str(indago_state_root),
                "--mutex-name","Local\\AIYE_INDAGO_ADD006_STAGING",
                "add006-oneshot","--request-file",str(transport_path),
                "--expected-sha256",trusted_transport_sha,"--waves","2",
                "--wave-timeout","180","--max-total","580"]
            began=root/"native_hunt_started.txt"
            _save(began,("NEW_NATIVE_ADD006_PROVIDER_INVOCATION\n").encode("utf-8"))
            try:
                cp=subprocess.run(cmd,cwd=port_root,capture_output=True,timeout=710,check=False)
            except subprocess.TimeoutExpired as e:
                raise EvidenceBlocked("native_indago_timeout_owner_triage") from e
            _save(root/"native_indago_stdout.json",cp.stdout)
            _save(root/"native_indago_stderr.log",cp.stderr)
            if cp.returncode not in (0,10,20):
                raise EvidenceBlocked("native_indago_unexpected_exit_"+str(cp.returncode))
        if not ev.is_file() or not claim.is_file() or not ledger.is_file():
            raise EvidenceBlocked("native_indago_no_durable_host_evidence")
        raw=_read(ev)
        if raw.get("research_request_id")!=req["research_request_id"] or raw.get("dispatch_event_id")!=req["dispatch_event_id"]:
            raise EvidenceBlocked("native_indago_foreign_dispatch_return")
        if contract:
            calls=raw.get("provider_calls")
            if type(calls) is not int or calls>contract["limits"]["maximum_total_provider_calls"]:
                raise EvidenceBlocked("f241_native_provider_budget_exceeded")
            if raw.get("task_label")!="TRIMURTI_F241_C04_FINITE":
                raise EvidenceBlocked("f241_unexpected_native_task")
            sessions=(raw.get("hunt") or {}).get("session_ids") or []
            if len(sessions)>contract["limits"]["maximum_indago_waves"]:
                raise EvidenceBlocked("f241_native_wave_budget_exceeded")
        esha=sha256(ev.read_bytes())
        csha=sha256(claim.read_bytes())
        lsha=sha256(ledger.read_bytes())
        wc=whitecrow_return(
            evidence_path=ev,request_path=request_path,transport_path=transport_path,
            whitecrow_root=whitecrow_root,trusted_whitecrow_commit=trusted_wc_commit,
            trusted_whitecrow_module_sha=trusted_wc_module_sha,
            expected_evidence_sha=esha,expected_request_sha=trusted_request_sha,
            expected_transport_sha=trusted_transport_sha,baseline_path=baseline_path,
            stage_receipt_path=stage_receipt,expected_stage_receipt_sha=trusted_stage_sha,
            native_claim_path=claim,expected_native_claim_sha=csha,
            native_ledger_path=ledger,expected_native_ledger_sha=lsha,
            output_root=root/"whitecrow",source_carrier_packet=source_carrier_packet,
            expected_source_carrier_sha=expected_source_carrier_sha,
            expected_cycle_contract_sha=expected_cycle_contract_sha)
        report=root/"whitecrow"/"whitecrow_d24_after_add006.json"
        if wc.get("whitecrow_admission")=="REAL_FIELDCORE_D24" and report.is_file():
            choice,agent=_native_artikl(root=root,source=ev,report_path=report,
                 report_sha=wc["whitecrow_report_sha256"],evidence_sha=esha,request=req,
                 imported_response=imported_artikl_response,
                 imported_response_sha=imported_artikl_response_sha)
            # Even a proposed revision is not a written/reviewed manuscript.
            # Source-depth D15 HOLD + an actual Artikl HOLD_BLOCKED is scientific
            # insufficiency, not an agent runtime error.
            status=_terminal_science_gate(finite=contract is not None,
                    whitecrow_status=wc.get("status") or "",choice=choice["decision"])
        else:
            choice=None;agent=None;status="HOLD_TECHNICAL_BLOCKER" if contract else "NATIVE_HUNT_BLOCKED_AUTHOR_HOLD"
        state={"schema":RECEIPT,"status":status,"case_id":manifest["case_id"],
             "research_request_id":req["research_request_id"],"dispatch_event_id":req["dispatch_event_id"],
             "native_indago_hunt_id":(raw.get("hunt") or {}).get("hunt_id"),
             "native_indago_run_status":raw["run_status"],
             "native_indago_executed_this_command":not reused,
             "original_native_hunt_reused":reused,"real_evidence_sha256":esha,
             "claim_sha256":csha,"runtime_ledger_sha256":lsha,
             "whitecrow_return":wc,
             "source_carrier_packet_sha256":expected_source_carrier_sha if source_carrier_packet else None,
             "artikl_research_decision":choice["decision"] if choice else None,
             "editorial_candidate_creation_allowed":bool(choice and choice["decision"]=="REVISION_CANDIDATE"),
             "artikl_native":agent,"f4_full_manuscript_closed_loop":"NOT_PASSED",
             "independently_verified_full_primary":False,
             "scientific_novelty_accepted":False,"d25_manuscript_go":False,
             "bounded_cycle_contract_sha256":expected_cycle_contract_sha if contract else None,
             "subsequent_research_requests_authorized":0,
             "author_gate":"HOLD","send":False,"world_mutation":False,
             "new_w12_routes":0,"production_deployed":False}
        _emit(final,state)
        return state
    finally:
        lock.unlink(missing_ok=True)

def prepare_finite_followup(*,contract_path:Path,expected_contract_sha:str,
        previous_merged_path:Path,expected_previous_merged_sha:str,
        previous_artikl_stdout:Path,expected_previous_artikl_sha:str,
        source_file:Path,draft_file:Path,review_file:Path,
        whitecrow_root:Path,trusted_wc_commit:str,trusted_wc_module_sha:str,
        output_root:Path)->dict:
    """F241 one allowed request derived from actual prior Artikl/D24 evidence.

    The canonical WhiteCrow report decides what remains open. Its three typed
    needs are then *routed* with the three source-bound Artikl search lanes;
    no new reviewer, source claim, study, or recursive request is invented.
    """
    from .native_whitecrow_stage import _validate_source, WHITE_CROW_SOURCE
    import copy
    import importlib
    contract=_read(contract_path)
    if (contract.get("schema")!="T3_F241_FINITE_C04_EXECUTION_CONTRACT_V1"
        or contract.get("status")!="OWNER_SCOPED_PREFLIGHT_NO_DISPATCH"
        or contract.get("new_research_request_id") is None
        or contract.get("semantic_action_mode")!="CRITIQUE"
        or contract.get("author_gate")!="HOLD"
        or contract.get("send") is not False
        or contract.get("world_mutation") is not False):
        raise EvidenceBlocked("finite_f241_owner_contract_invalid")
    _pin(contract_path,expected_contract_sha)
    caps=contract.get("limits") or {}
    for key,wanted in (("new_scientific_request_count",1),
                       ("native_indago_hunt_count",1),
                       ("maximum_indago_waves",2),
                       ("maximum_seed_provider_calls",6),
                       ("maximum_model_requested_provider_calls",2),
                       ("maximum_total_provider_calls",8),
                       ("extra_recursive_hunts",0),
                       ("new_git_branches",0),("new_github_issues",0),
                       ("external_sends",0),("world_mutations",0)):
        if type(caps.get(key)) is not int or caps[key]!=wanted:
            raise EvidenceBlocked("f241_budget_contract_mismatch:"+key)
    for path,key in ((source_file,"source_original_sha256"),
                     (draft_file,"manuscript_baseline_sha256"),
                     (review_file,"independent_review_sha256")):
        _pin(path,contract[key])
    merged=json.loads(_pin(previous_merged_path,expected_previous_merged_sha).decode("utf-8-sig"))
    if (merged.get("research_evidence_return") or {}).get("research_run_id")!=contract["completed_parent_run_id"]:
        raise EvidenceBlocked("prior_native_research_return_not_bound_to_contract")
    model_body=_pin(previous_artikl_stdout,expected_previous_artikl_sha)
    previous_decision,outer=_model_inner(model_body)
    if (previous_decision.get("decision")!="MORE_RESEARCH"
        or previous_decision.get("revision_allowed_now") is not False
        or previous_decision.get("real_indago_evidence_sha256")!=contract["completed_parent_evidence_sha256"]
        or previous_decision.get("author_gate")!="HOLD" or previous_decision.get("send") is not False):
        raise EvidenceBlocked("prior_artikl_did_not_authorize_bounded_research")
    pinned=_validate_source(whitecrow_root,trusted_wc_commit,trusted_wc_module_sha)
    wcpath=str(whitecrow_root.resolve())
    if wcpath not in sys.path:sys.path.insert(0,wcpath)
    wc=importlib.import_module("fieldcore.academic_due_diligence")
    if Path(wc.__file__).resolve()!=(whitecrow_root.resolve()/WHITE_CROW_SOURCE).resolve():
        raise EvidenceBlocked("whitecrow_pinned_code_not_imported")
    lanes=contract.get("search_lanes") or []
    if len(lanes)!=3 or len({x.get("code") for x in lanes})!=3:
        raise EvidenceBlocked("requires_exactly_three_distinct_science_lanes")
    for lane in lanes:
        q=lane.get("query","")
        if (not isinstance(q,str) or not 8<=len(q)<=150 or
            any(ch in q for ch in ("\r","\n",":",";","|","->"))):
            raise EvidenceBlocked("unsafe_scientific_search_lane")
    # Retain old negative and source traces, but do not carry old open need
    # records as new executions. D24 recreates THREE current source deficits.
    payload=copy.deepcopy(merged)
    payload["open_research_needs"]=[]
    report=wc.build_disciplinary_positioning_report(
        payload,semantic_action_mode="CRITIQUE",
        trigger_ref="F240:"+contract["completed_parent_evidence_sha256"])
    needs=report.get("open_research_needs") or []
    if (report.get("research_readiness")!="BLOCKED_ON_DUE_DILIGENCE"
        or len(needs)!=3 or report.get("coverage_status")=="HIGH"):
        raise EvidenceBlocked("not_the_expected_three_D24_research_deficits")
    routing=copy.deepcopy(report)
    for need,lane in zip(routing["open_research_needs"],lanes):
        need["question_or_gap"]="SEARCH_QUERY: "+lane["query"]
        need["required_evidence_or_action"]=(
            lane["scientific_gap"]+
            "; read original primary scholarly bodies with verified source bytes,"
            " exact passage/page anchors and a bounded negative result if absent")
        need["provenance"]=[{"source":"PREVIOUS_NATIVE_ARTIKL_DECISION",
            "source_sha256":expected_previous_artikl_sha,
            "parent_request_id":contract["original_request_id"],
            "lane":lane["code"]}]
        need["priority"]="BLOCKING"
    request_prefix=contract["new_research_request_id"].removesuffix(":research-request")
    request=wc.build_research_handoff(routing,request_id=request_prefix)
    if (request.get("research_request_id")!=contract["new_research_request_id"]
        or request.get("dispatch_event_id")!=contract["new_dispatch_event_id"]
        or request.get("semantic_action_mode")!="CRITIQUE"
        or len(request.get("research_needs") or [])!=3):
        raise EvidenceBlocked("new_canonical_D24_request_identity_wrong")
    transport=wc.render_indago_direct_hunt_task(
        request,task_label="TRIMURTI_F241_C04_FINITE")
    if len(__import__("re").findall(r"(?m)^- SEARCH_QUERY: (.{8,150}) -> ",transport))!=3:
        raise EvidenceBlocked("source_bound_three_research_queries_lost")
    output_root.mkdir(parents=True,exist_ok=True)
    report_sha=_emit(output_root/"due_diligence_report.json",report)
    request_sha=_emit(output_root/"research_request_pending.json",request)
    transport_bytes=(transport.rstrip("\n")+"\n").encode("utf-8")
    _save(output_root/"indago_one_shot_task_PENDING.txt",transport_bytes)
    transport_sha=sha256(transport_bytes)
    stage={
       "schema":"trimurti-whitecrow-d24-native-stage-v1",
       "runtime":"REAL_WHITE_CROW_FIELDCORE_D24_CODE_INVOKED",
       "canonical_code_source":pinned,
       "request_sha256":request_sha,"report_sha256":report_sha,
       "research_request_id":request["research_request_id"],
       "dispatch_event_id":request["dispatch_event_id"],
       "direct_hunt_transport_sha256":transport_sha,
       "dispatch_status":"NOT_DISPATCHED_FROM_THIS_RUN",
       "source_original_sha256":contract["source_original_sha256"],
       "draft_sha256":contract["manuscript_baseline_sha256"],
       "independent_review_sha256":contract["independent_review_sha256"],
       "parent_evidence_sha256":contract["completed_parent_evidence_sha256"],
       "parent_artikl_sha256":expected_previous_artikl_sha,
       "cycle_contract_sha256":expected_contract_sha,
       "search_lanes":[x["code"] for x in lanes],
       "count_new_research_requests_authorized":1,
       "max_hunts":1,"max_waves":2,"max_provider_calls":8,
       "new_w12_routes":0,"author_gate":"HOLD","send":False,
       "world_mutation":False}
    stage_sha=_emit(output_root/"whitecrow_stage_receipt.json",stage)
    manifest={
       "schema":SCHEMA,"case_id":contract["case_id"],
       "research_request_id":request["research_request_id"],
       "dispatch_event_id":request["dispatch_event_id"],
       "cycle_contract_sha256":expected_contract_sha,
       "author_gate":"HOLD","send":False,"world_mutation":False,
    }
    manifest_sha=_emit(output_root/"input_manifest.json",manifest)
    return {"status":"F241_SINGLE_D24_REQUEST_PREPARED_NOT_DISPATCHED",
            "research_request_id":request["research_request_id"],
            "dispatch_event_id":request["dispatch_event_id"],
            "contract_sha256":expected_contract_sha,
            "transport_sha256":transport_sha,"request_sha256":request_sha,
            "stage_sha256":stage_sha,"baseline_sha256":report_sha,
            "manifest_sha256":manifest_sha,
            "native_hunts_launched":0,"additional_request_created":False,
            "science":"HOLD","send":False}

def _prepare_cli(argv:list[str])->int:
    p=argparse.ArgumentParser(prog="manuscript_cycle_runner add006 prepare")
    for k in ("contract","previous-merged","previous-artikl-stdout",
              "source-file","draft-file","review-file","whitecrow-root","out"):
        p.add_argument("--"+k,type=Path,required=True)
    for k in ("expected-contract-sha","expected-previous-merged-sha",
              "expected-previous-artikl-sha","trusted-whitecrow-commit",
              "trusted-whitecrow-module-sha"):
        p.add_argument("--"+k,required=True)
    a=p.parse_args(argv)
    try:
        result=prepare_finite_followup(
            contract_path=a.contract,expected_contract_sha=a.expected_contract_sha,
            previous_merged_path=a.previous_merged,
            expected_previous_merged_sha=a.expected_previous_merged_sha,
            previous_artikl_stdout=a.previous_artikl_stdout,
            expected_previous_artikl_sha=a.expected_previous_artikl_sha,
            source_file=a.source_file,draft_file=a.draft_file,
            review_file=a.review_file,whitecrow_root=a.whitecrow_root,
            trusted_wc_commit=a.trusted_whitecrow_commit,
            trusted_wc_module_sha=a.trusted_whitecrow_module_sha,
            output_root=a.out)
    except (ValueError,OSError,KeyError,EvidenceBlocked) as e:
        print(json.dumps({"status":"HOLD_TECHNICAL_BLOCKER","reason":str(e)[:250],
                          "author_gate":"HOLD","send":False}))
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0


def main(argv:list[str]|None=None)->int:
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=="prepare":
        return _prepare_cli(argv[1:])
    p=argparse.ArgumentParser(prog="manuscript_cycle_runner add006")
    for key in ["manifest","request","transport","stage-receipt","baseline","port-root","indago-state-root","whitecrow-root","output-root"]:
        p.add_argument("--"+key,type=Path,required=True)
    for key in ["trusted-request-sha","trusted-transport-sha","trusted-stage-sha","trusted-baseline-sha",
                "trusted-whitecrow-commit","trusted-whitecrow-module-sha"]:
        p.add_argument("--"+key,required=True)
    p.add_argument("--imported-artikl-response",type=Path)
    p.add_argument("--imported-artikl-response-sha")
    p.add_argument("--cycle-contract",type=Path)
    p.add_argument("--expected-cycle-contract-sha")
    p.add_argument("--source-carrier-packet",type=Path)
    p.add_argument("--expected-source-carrier-sha")
    a=p.parse_args(argv)
    try:
        result=run(input_manifest=a.manifest,request_path=a.request,transport_path=a.transport,
            stage_receipt=a.stage_receipt,baseline_path=a.baseline,
            trusted_request_sha=a.trusted_request_sha,
            trusted_transport_sha=a.trusted_transport_sha,
            trusted_stage_sha=a.trusted_stage_sha,
            trusted_baseline_sha=a.trusted_baseline_sha,
            port_root=a.port_root,indago_state_root=a.indago_state_root,
            whitecrow_root=a.whitecrow_root,trusted_wc_commit=a.trusted_whitecrow_commit,
            trusted_wc_module_sha=a.trusted_whitecrow_module_sha,output_root=a.output_root,
            imported_artikl_response=a.imported_artikl_response,
            imported_artikl_response_sha=a.imported_artikl_response_sha,
            cycle_contract_path=a.cycle_contract,
            expected_cycle_contract_sha=a.expected_cycle_contract_sha,
            source_carrier_packet=a.source_carrier_packet,
            expected_source_carrier_sha=a.expected_source_carrier_sha)
    except (OSError,ValueError,KeyError,EvidenceBlocked,subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"BLOCKED_NATIVE_ADD006","reason":str(e)[:250],
                         "author_gate":"HOLD","send":False,"world_mutation":False}))
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
