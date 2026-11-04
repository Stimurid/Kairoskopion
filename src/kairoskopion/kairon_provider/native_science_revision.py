"""F4: existing Factory manuscript return after pinned Indago->D24->Artikl decision.

A post-research REVISION_CANDIDATE is a working editorial permission, not
scientific readiness, author acceptance or publication. Reuse existing Artikl
writer, independent CodeX reader and draft intake. No new hunt/queue/service.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from .publication_runner import EvidenceBlocked, sha256
from .native_add006_factory import _model_inner, _assert_science_choice
from .native_editorial_cycle import read, readsha, emit, native_call
from .native_editorial_return import (
    preflight, _writer_prompt, _writer_file_after_gateway_timeout,
    _independent_next_review, _intake,
)
from .native_editorial_cycle import _verify_review

SCHEMA = "T3_F4_POSTRESEARCH_EDITORIAL_WORKING_REVISION_V1"


def _pinned(path: Path, checksum: str) -> dict:
    if not path.is_file():
        raise EvidenceBlocked("science_revision_missing_file:" + path.name)
    b = readsha(path, checksum)
    return {"path": path, "sha256": checksum, "bytes": b}


def _original_session_store_recovery(root:Path,target:Path,
        materialization_gateway:Path,materialization_sha:str,
        trajectory:Path,trajectory_sha:str)->dict:
    """Read original failed call, genuine materialization write+read and trace.
    
    No new manuscript is generated here; this is a strictly bounded readback of
    the exact same-session store value. Original pre-write SHA is unavailable,
    so the receipt does not claim a before-SHA identity comparison.
    """
    _pinned(materialization_gateway,materialization_sha)
    _pinned(trajectory,trajectory_sha)
    first=read(root/"return_writer.gateway.json")
    gateway_bytes=materialization_gateway.read_bytes()
    recovered=json.loads(gateway_bytes.decode(
        "utf-16" if gateway_bytes.startswith((bytes([255,254]),bytes([254,255]))) else "utf-8-sig"))
    agent=((first.get("result") or {}).get("meta") or {}).get("agentMeta") or {}
    receipt=agent.get("terminalReceipt") or {}
    if (first.get("status")!="timeout"
        or first.get("timeoutPhase")!="provider"
        or first.get("providerStarted") is not True
        or first.get("runId")!="c4ca772d-9d47-4357-bc6e-0d01e5cb36cd"
        or agent.get("sessionId")!="f46cee06-b72a-59dd-95cc-10eaa559a4ec"
        or receipt.get("runId")!=first.get("runId")
        or "write" in (receipt.get("successfulToolNames") or [])):
        raise EvidenceBlocked("science_revision_prior_timeout_proof_invalid")
    ts=trajectory.read_text(encoding="utf-8")
    if (not ts.startswith("{")
        or '"type":"tool.result"' not in ts.replace(" ","")
        or '"chars\\":48741' not in ts
        or '"words\\":5789' not in ts):
        raise EvidenceBlocked("science_revision_original_store_trace_not_proven")
    summary=((recovered.get("result") or {}).get("meta") or {}).get("toolSummary") or {}
    if (recovered.get("status")!="ok"
        or summary.get("failures")!=0
        or not {"write","read"}.issubset(set(summary.get("tools") or []))):
        raise EvidenceBlocked("science_revision_materialization_execution_untrusted")
    payloads=((recovered.get("result") or {}).get("payloads") or [])
    if not payloads or not isinstance(payloads[0].get("text"),str):
        raise EvidenceBlocked("science_revision_materialization_no_agent_receipt")
    try:
        details=json.loads(payloads[0]["text"])
    except ValueError as exc:
        raise EvidenceBlocked("science_revision_materialization_receipt_not_json") from exc
    if (details.get("schema")!="T3_F4_ORIGINAL_SESSION_STORE_MATERIALIZATION_V1"
        or details.get("status")!="WRITTEN_VERIFIED"
        or details.get("source_run_id")!=first.get("runId")
        or details.get("source_session_id")!=agent.get("sessionId")
        or details.get("chars")!=48741
        or details.get("author_gate")!="HOLD"
        or details.get("send") is not False
        or details.get("world_mutation") is not False):
        raise EvidenceBlocked("science_revision_materialization_lineage_mismatch")
    if not target.is_file():
        raise EvidenceBlocked("science_revision_materialization_file_missing")
    raw=target.read_bytes()
    text=raw.decode("utf-8")
    if (len(text)!=48741 or not 5788<=len(text.split())<=5789
        or len(raw)<20000 or not text.startswith("# ")
        or text.count("\n## ")<7 or "\ufffd" in text):
        raise EvidenceBlocked("science_revision_materialization_byte_count_invalid")
    info={
      "schema":"T3_F4_SAME_SESSION_MATERIALIZED_ARTIKL_WORKING_DRAFT_V1",
      "source_session_id":agent.get("sessionId"),
      "source_run_id":first.get("runId"),
      "failed_original_gateway_sha256":sha256((root/"return_writer.gateway.json").read_bytes()),
      "source_trajectory_sha256":trajectory_sha,
      "recovery_gateway_sha256":materialization_sha,
      "source_store_char_count":48741,
      "materialized_file_chars":len(text),
      "materialized_file_words":len(text.split()),
      "materialized_file_sha256":sha256(raw),
      "original_store_content_sha256_available":False,
      "source_by_session_continuity_not_byte_comparison":True,
      "new_manuscript_model_generation_in_recovery":False,
      "author_gate":"HOLD","send":False,"world_mutation":False,
    }
    emit(root/"return_writer_store_recovery_receipt.json",info)
    return {"sha256":sha256(raw),"author_gate":"HOLD","send":False,
            "recovered_original_session_store":True}


def run(*, manifest: Path, manifest_sha: str, factory_state: Path,
        factory_sha: str, native_artikl_stdout: Path, artikl_sha: str,
        evidence: Path, evidence_sha: str, whitecrow_report: Path,
        report_sha: str, request: Path, request_sha: str,
        output_root: Path,
        materialization_gateway: Path|None=None,materialization_sha: str|None=None,
        original_trajectory: Path|None=None,trajectory_sha: str|None=None) -> dict:
    pinned = {
        "factory": _pinned(factory_state, factory_sha),
        "agent": _pinned(native_artikl_stdout, artikl_sha),
        "evidence": _pinned(evidence, evidence_sha),
        "whitecrow": _pinned(whitecrow_report, report_sha),
        "request": _pinned(request, request_sha),
    }
    source = _pinned(manifest, manifest_sha)
    m = json.loads(source["bytes"].decode("utf-8-sig"))
    f = preflight(m)  # exact current C04 v0.6, M117, original source and rc9
    fs = read(factory_state)
    if (fs.get("schema")!="trimurti-native-add006-factory-receipt-v1"
        or fs.get("case_id")!="T3-TALK-20261019"
        or fs.get("status")!="EDITORIAL_WORKING_REVISION_PROPOSED_NOT_YET_WRITTEN"
        or fs.get("real_evidence_sha256")!=evidence_sha
        or fs.get("native_indago_run_status") not in ("PASS", "PARTIAL")
        or fs.get("artikl_research_decision")!="REVISION_CANDIDATE"
        or fs.get("original_native_hunt_reused") is not True
        or fs.get("native_indago_executed_this_command") is not False
        or fs.get("author_gate")!="HOLD"
        or fs.get("send") is not False
        or fs.get("world_mutation") is not False
        or fs.get("d25_manuscript_go") is not False):
        raise EvidenceBlocked("science_revision_factory_not_pinned_or_not_authorized")
    wc = fs.get("whitecrow_return") or {}
    if (wc.get("whitecrow_report_sha256")!=report_sha
        or wc.get("whitecrow_admission")!="REAL_FIELDCORE_D24"
        or wc.get("indago_native_evidence_sha256")!=evidence_sha
        or wc.get("author_gate")!="HOLD"):
        raise EvidenceBlocked("science_revision_untrusted_d24_return")
    if (fs.get("artikl_native") or {}).get("stdout_sha256")!=artikl_sha:
        raise EvidenceBlocked("science_revision_untrusted_artikl_stdout")
    request_obj = json.loads(pinned["request"]["bytes"].decode("utf-8-sig"))
    inner, outer = _model_inner(pinned["agent"]["bytes"])
    decision = _assert_science_choice(inner,request_obj,evidence_sha,report_sha)
    if (decision!="REVISION_CANDIDATE"
        or inner.get("revision_allowed_now") is not True
        or inner.get("d25_manuscript_go") is not False
        or inner.get("source_novelty_accepted") is not False
        or inner.get("author_gate")!="HOLD"
        or inner.get("send") is not False
        or inner.get("world_mutation") is not False):
        raise EvidenceBlocked("science_revision_native_artikl_chose_no_revision")
    report=read(whitecrow_report)
    native_ev=read(evidence)
    if (report.get("semantic_action_mode")!="CRITIQUE"
        or native_ev.get("research_request_id")!=request_obj.get("research_request_id")
        or native_ev.get("dispatch_event_id")!=request_obj.get("dispatch_event_id")
        or fs.get("research_request_id")!=native_ev.get("research_request_id")
        or wc.get("research_run_id")!=native_ev.get("research_run_id")
        or native_ev.get("transport_sha256")!="c3be0a98b26d588b20a787846c7844940279a5378dd4cea31eadb6578527b7c7"):
        raise EvidenceBlocked("science_revision_wrong_research_lineage")
    if (native_ev.get("claim_state")!="COMPLETED"
        or native_ev.get("author_gate")!="HOLD"
        or native_ev.get("send") is not False
        or native_ev.get("world_mutation") is not False):
        raise EvidenceBlocked("science_revision_native_return_not_terminal")
    out=output_root.resolve()
    out.mkdir(parents=True,exist_ok=True)
    receipt=out/"science_revision_receipt.json"
    target=out/"draft_v0_7.md"
    review_path=out/"review.json"
    if receipt.exists():
        prev=read(receipt)
        if (prev.get("schema")!=SCHEMA
            or prev.get("author_gate")!="HOLD"
            or prev.get("factory_state_sha256")!=factory_sha
            or not target.is_file()
            or not review_path.is_file()
            or sha256(target.read_bytes())!=prev.get("candidate_sha256")
            or sha256(review_path.read_bytes())!=prev.get("independent_review_sha256")):
            raise EvidenceBlocked("science_revision_replay_integrity_fail")
        return {**prev,"replay":"IDENTICAL_ZERO_NEW_MODEL_CALLS"}
    lock=out/"science_revision.lock"
    try:
        fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise EvidenceBlocked("science_revision_owner_run_lock") from exc
    try:
        with os.fdopen(fd,"w") as fh:
            fh.write("NATIVE_ARTIKL_RESEARCH_REVISION\n")
        context=(
          "\n=== F4 VERIFIED POSTRESEARCH REVISION AUTHORITY ===\n"
          "The registered Artikl rc9 independently chose REVISION_CANDIDATE "
          "against WhiteCrow report SHA "+report_sha+" and actual Indago "
          "EvidenceReturn SHA "+evidence_sha+". The EXACT native choice "
          "was "+json.dumps(inner,ensure_ascii=False)+".\n"
          "Read the COMPLETE new WhiteCrow report at "+str(whitecrow_report)
          +" and the COMPLETE EvidenceReturn at "+str(evidence)
          +". Check hashes yourself before making source-claims. "
          "The original native hunt is PARTIAL; D15 full-primary and source novelty "
          "are NOT admitted. The new manuscript must not simulate evidence, "
          "causal validation, coded observations, or source-page citations. "
          "Preserve explicit rival explanations, failed cases, organogenesis "
          "hypothesis and five protected conceptual nuclei. Use the COMPLETE "
          "C04 v0.6 and complete M117 read in the existing writer prompt, "
          "not only an old v0.5. Keep D25_MANUSCRIPT_GO=false and AUTHOR HOLD. "
          "Do not SEND, register a new seed, alter WORLD or original draft.\n"
        )
        try:
            writer=native_call(out,"return_writer",
                               _writer_prompt(m,f,inner,target)+context,
                               timeout=480)
        except EvidenceBlocked:
            if (materialization_gateway is not None and original_trajectory is not None
                and materialization_sha is not None and trajectory_sha is not None):
                writer=_original_session_store_recovery(
                    out,target,materialization_gateway,materialization_sha,
                    original_trajectory,trajectory_sha)
            else:
                writer=_writer_file_after_gateway_timeout(out,target)
        if not target.is_file():
            raise EvidenceBlocked("science_revision_writer_no_file")
        raw=target.read_bytes()
        text=raw.decode("utf-8")
        if (not text.startswith("# ") or not 3100<=len(text.split())<=11000
            or text.count("\n## ")<7 or len(raw)<20000):
            raise EvidenceBlocked("science_revision_incomplete_working_manuscript")
        candidate_sha=sha256(raw)
        if (writer.get("sha256")!=candidate_sha
            or writer.get("author_gate")!="HOLD"
            or writer.get("send") is not False):
            raise EvidenceBlocked("science_revision_writer_receipt_mismatch")
        intake_sha=_intake(out,f,target)
        review=_independent_next_review(
            out,m,f,target,latest_whitecrow=whitecrow_report,
            latest_evidence=evidence,latest_decision=inner)
        _verify_review(review,target)
        if (review.get("reviewer")!="CODEX_DISTINCT_PROCESS"
            or review.get("verdict") not in {"SCOPED_PASS","REVISION_REQUIRED","PARK"}):
            raise EvidenceBlocked("science_revision_independent_review_not_admitted")
        final={
            "schema":SCHEMA,"status":"WORKING_REVISION_AND_REVIEW_AUTHOR_HOLD",
            "case_id":"T3-TALK-20261019",
            "source_sha256":f["source"]["sha256"],
            "baseline_sha256":f["baseline"]["sha256"],
            "M117_review_sha256":f["review"]["sha256"],
            "factory_state_sha256":factory_sha,
            "real_indago_evidence_sha256":evidence_sha,
            "whitecrow_postreturn_sha256":report_sha,
            "registered_artikl_decision_stdout_sha256":artikl_sha,
            "research_run_id":native_ev["research_run_id"],
            "research_request_id":native_ev["research_request_id"],
            "candidate_sha256":candidate_sha,
            "candidate_words":len(text.split()),
            "candidate_path":str(target),
            "independent_review_sha256":sha256(review_path.read_bytes()),
            "independent_review_verdict":review["verdict"],
            "draft_intake_sha256":intake_sha,
            "new_manuscripts":1,"independent_reviews":1,
            "D27_canonical_mounted":False,
            "full_F4_science_pass":False,
            "source_novelty_accepted":False,
            "d25_manuscript_go":False,
            "author_gate":"HOLD","send":False,"world_mutation":False,
            "new_W12_routes":0,"production_deployed":False,
        }
        emit(receipt,final)
        return final
    finally:
        lock.unlink(missing_ok=True)


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="Trimurti existing Factory F4 science-revision")
    for name in ("manifest","factory-state","native-artikl-stdout","evidence",
                 "whitecrow-report","request","out"):
        p.add_argument("--"+name,type=Path,required=True)
    for name in ("manifest-sha","factory-sha","artikl-sha","evidence-sha",
                 "report-sha","request-sha"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--materialization-gateway",type=Path)
    p.add_argument("--materialization-sha")
    p.add_argument("--original-trajectory",type=Path)
    p.add_argument("--trajectory-sha")
    a=p.parse_args(argv)
    try:
        result=run(manifest=a.manifest,manifest_sha=a.manifest_sha,
            factory_state=a.factory_state,factory_sha=a.factory_sha,
            native_artikl_stdout=a.native_artikl_stdout,artikl_sha=a.artikl_sha,
            evidence=a.evidence,evidence_sha=a.evidence_sha,
            whitecrow_report=a.whitecrow_report,report_sha=a.report_sha,
            request=a.request,request_sha=a.request_sha,output_root=a.out,
            materialization_gateway=a.materialization_gateway,
            materialization_sha=a.materialization_sha,
            original_trajectory=a.original_trajectory,trajectory_sha=a.trajectory_sha)
    except (OSError,ValueError,KeyError,EvidenceBlocked,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"WORKING_REVISION_HOLD",
            "reason":str(exc)[:300],"author_gate":"HOLD","send":False,
            "world_mutation":False},ensure_ascii=False))
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
