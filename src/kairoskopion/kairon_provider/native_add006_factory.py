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
    if inner.get("revision_allowed_now") is not False:
        raise EvidenceBlocked("native_artikl_unreviewed_revision_not_allowed")
    if inner.get("decision") not in {"MORE_RESEARCH","HOLD_BLOCKED"}:
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
          "TRIMURTI F240 CURRENT ARTIKL organ, registered OpenClaw agent artikl. "
          "Read FULL current SOURCE_ARTIKL entry/release/base/gateway/livecore/capability "
          "and source-bound report "+str(report_path)+" (SHA "+report_sha+"). "
          "Native evidence SHA "+evidence_sha+". This is scientific triage, NOT a "
          "request to rewrite C04 or publish. Unless verified primary fulltexts "
          "are present, D15/D24 imply MORE_RESEARCH and author HOLD. "
          "DO NOT change files, send messages, or launch another hunt. "
          "Return ONLY JSON with keys schema:trimurti-artikl-f240-research-vs-revision-decision-v1, "
          "agent_id:artikl, organ_not_actor:true, current_release:ARTIKL 1.0.0-rc9, "
          "canonical_read:FULL_RC9|PARTIAL|BLOCKED, whitecrow_report_sha256:"+report_sha+
          ", real_indago_evidence_sha256:"+evidence_sha+
          ", decision:MORE_RESEARCH|HOLD_BLOCKED, reason:string, next_research_questions:array,"
          "next_source_requirements:array, revision_allowed_now:false, d25_manuscript_go:false, "
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

def run(*,input_manifest:Path,request_path:Path,transport_path:Path,
        stage_receipt:Path,baseline_path:Path,
        trusted_request_sha:str,trusted_transport_sha:str,
        trusted_stage_sha:str,trusted_baseline_sha:str,
        port_root:Path,indago_state_root:Path,whitecrow_root:Path,
        trusted_wc_commit:str,trusted_wc_module_sha:str,
        output_root:Path,imported_artikl_response:Path|None=None,
        imported_artikl_response_sha:str|None=None)->dict:
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
            output_root=root/"whitecrow")
        report=root/"whitecrow"/"whitecrow_d24_after_add006.json"
        if wc["status"]=="REQUALIFIED_RESEARCH_MORE_D15_HOLD" and report.is_file():
            choice,agent=_native_artikl(root=root,source=ev,report_path=report,
                 report_sha=wc["whitecrow_report_sha256"],evidence_sha=esha,request=req,
                 imported_response=imported_artikl_response,
                 imported_response_sha=imported_artikl_response_sha)
            status="MORE_RESEARCH_AUTHOR_HOLD" if choice["decision"]=="MORE_RESEARCH" else "HOLD_BLOCKED"
        else:
            choice=None;agent=None;status="NATIVE_HUNT_BLOCKED_AUTHOR_HOLD"
        state={"schema":RECEIPT,"status":status,"case_id":manifest["case_id"],
             "research_request_id":req["research_request_id"],"dispatch_event_id":req["dispatch_event_id"],
             "native_indago_hunt_id":(raw.get("hunt") or {}).get("hunt_id"),
             "native_indago_run_status":raw["run_status"],
             "native_indago_executed_this_command":not reused,
             "original_native_hunt_reused":reused,"real_evidence_sha256":esha,
             "claim_sha256":csha,"runtime_ledger_sha256":lsha,
             "whitecrow_return":wc,
             "artikl_research_decision":choice["decision"] if choice else None,
             "artikl_native":agent,"f4_full_manuscript_closed_loop":"NOT_PASSED",
             "independently_verified_full_primary":False,
             "scientific_novelty_accepted":False,"d25_manuscript_go":False,
             "author_gate":"HOLD","send":False,"world_mutation":False,
             "new_w12_routes":0,"production_deployed":False}
        _emit(final,state)
        return state
    finally:
        lock.unlink(missing_ok=True)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="manuscript_cycle_runner add006")
    for key in ["manifest","request","transport","stage-receipt","baseline","port-root","indago-state-root","whitecrow-root","output-root"]:
        p.add_argument("--"+key,type=Path,required=True)
    for key in ["trusted-request-sha","trusted-transport-sha","trusted-stage-sha","trusted-baseline-sha",
                "trusted-whitecrow-commit","trusted-whitecrow-module-sha"]:
        p.add_argument("--"+key,required=True)
    p.add_argument("--imported-artikl-response",type=Path)
    p.add_argument("--imported-artikl-response-sha")
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
            imported_artikl_response_sha=a.imported_artikl_response_sha)
    except (OSError,ValueError,KeyError,EvidenceBlocked,subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"BLOCKED_NATIVE_ADD006","reason":str(e)[:250],
                         "author_gate":"HOLD","send":False,"world_mutation":False}))
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
