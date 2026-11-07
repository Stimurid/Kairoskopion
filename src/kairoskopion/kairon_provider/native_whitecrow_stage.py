"""Trimurti F236: execute EXISTING WhiteCrow FieldCore D24, not a copy of its semantics.

An old Indago hunt is input background, NOT EvidenceReturn to this NEW ResearchRequest.
WhiteCrow D24 marks inadequate scholarly coverage, produces a typed request whose
dispatch event remains PENDING; no source truth, author GO or journal SEND.
This is a local executable scientific admission stage, NOT a live WhiteCrow
model opponent or independent full-text review.
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

from .publication_runner import EvidenceBlocked, atomic_write, sha256

SCHEMA="trimurti-whitecrow-d24-native-stage-v1"
WHITE_CROW_SOURCE="fieldcore/academic_due_diligence.py"


def _read_json(path:Path)->dict:
    d=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(d,dict):
        raise EvidenceBlocked("whitecrow_science_review_must_be_object")
    return d


def _emit_unique(path:Path,object_:dict)->str:
    data=(json.dumps(object_,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    if path.exists():
        if path.read_bytes()!=data:
            raise EvidenceBlocked("native_whitecrow_receipt_mutated:"+path.name)
    else:
        atomic_write(path,data)
    return sha256(data)


def _validate_source(root:Path,trusted_commit:str,trusted_module_sha:str)->dict:
    root=root.resolve(strict=True)
    if not re.fullmatch(r"[0-9a-f]{40}",trusted_commit or ""):
        raise EvidenceBlocked("whitecrow_trusted_git_commit_required")
    if not re.fullmatch(r"[0-9a-f]{64}",trusted_module_sha or ""):
        raise EvidenceBlocked("whitecrow_trusted_module_sha_required")
    p=root/WHITE_CROW_SOURCE
    if not p.is_file() or sha256(p.read_bytes())!=trusted_module_sha:
        raise EvidenceBlocked("whitecrow_native_module_byte_mismatch")
    try:
        current=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,
                               capture_output=True,text=True,timeout=8).stdout.strip()
        dirty=subprocess.run(["git","-C",str(root),"status","--porcelain","--",
                              WHITE_CROW_SOURCE],check=True,capture_output=True,
                             text=True,timeout=8).stdout.strip()
    except (subprocess.SubprocessError,OSError) as e:
        raise EvidenceBlocked("whitecrow_native_git_source_not_verifiable") from e
    if current!=trusted_commit or dirty:
        raise EvidenceBlocked("whitecrow_git_pin_or_runtime_module_dirty")
    return {"git_commit":current,"module_sha256":sha256(p.read_bytes()),"dirty":False}


def _normalize_issues(review:dict,draft_text:str)->tuple[list[dict],list[dict]]:
    """Don't upgrade a reviewer's invented quote to a manuscript-grounded fact."""
    issues=review.get("new_major_issues") or []
    if not isinstance(issues,list) or not issues:
        raise EvidenceBlocked("whitecrow_m116_review_has_no_actual_issues")
    lines=draft_text.splitlines()
    accepted,unverified=[],[]
    for i,x in enumerate(issues,1):
        if not isinstance(x,dict) or not isinstance(x.get("issue"),str):
            raise EvidenceBlocked("whitecrow_invalid_reviewer_issue")
        name=x["issue"].strip()
        line=x.get("candidate_line")
        quote=x.get("literal_quote")
        if (not name or type(line) is not int or not (1<=line<=len(lines))
            or not isinstance(quote,str) or not quote.strip()
            or quote not in lines[line-1]):
            unverified.append({"index":i,"issue":name[:300],
                               "status":"UNVERIFIED_REVIEW_QUOTE_NOT_ADMITTED"})
        elif not any(y["issue"]==name for y in accepted):
            accepted.append({"issue":name,"line":line,"literal_quote":quote,
                             "status":"EXACT_MANUSCRIPT_LINE"})
    if not accepted:
        raise EvidenceBlocked("whitecrow_no_literal_grounded_review_issues")
    return accepted[:15],unverified


def qualify(*,whitecrow_root:Path,trusted_git_commit:str,
            trusted_module_sha:str,review_file:Path,trusted_review_sha:str,
            draft_file:Path,original_sha:str,draft_sha:str,native_evidence:dict,
            question:str,output_root:Path)->dict:
    """Canonical D24 function invocation with source-pinned prior research and review."""
    if not question or len(question.strip())<35 or len(question)>1200:
        raise EvidenceBlocked("whitecrow_exact_research_question_required")
    if not review_file.is_file() or sha256(review_file.read_bytes())!=trusted_review_sha:
        raise EvidenceBlocked("whitecrow_review_sha_mismatch")
    review=_read_json(review_file)
    if not draft_file.is_file() or sha256(draft_file.read_bytes())!=draft_sha:
        raise EvidenceBlocked("whitecrow_source_quoted_draft_sha_mismatch")
    if review.get("candidate_sha256")!=draft_sha or review.get("author_gate")!="HOLD":
        raise EvidenceBlocked("whitecrow_review_wrong_draft_or_author_boundary")
    if review.get("final_verdict")!="REVISION_REQUIRED":
        raise EvidenceBlocked("whitecrow_no_research_deficit_from_review")
    native_status=native_evidence.get("native_status")
    counts=native_evidence.get("counts") or {}
    if native_status not in {"PARTIAL","PASS"}:
        raise EvidenceBlocked("whitecrow_no_admissible_native_research_receipt")
    if native_evidence.get("original_sha256")!=original_sha or native_evidence.get("manuscript_sha256")!=draft_sha:
        raise EvidenceBlocked("whitecrow_native_evidence_source_mismatch")
    if native_evidence.get("evidence_depth")=="FULL_PRIMARY_READ_ADMITTED":
        raise EvidenceBlocked("whitecrow_full_primary_admission_requires_separate_case_gate")
    if counts.get("new_verified") not in (0,None):
        raise EvidenceBlocked("whitecrow_prior_verified_primary_needs_passage_review")
    hunt_id=native_evidence.get("native_hunt_id")
    if not isinstance(hunt_id,str) or not hunt_id.startswith("h-"):
        raise EvidenceBlocked("whitecrow_native_hunt_identity_invalid")
    pinned=_validate_source(whitecrow_root,trusted_git_commit,trusted_module_sha)

    # Invoke functions from exactly the pinned WhiteCrow checkout. This is NOT
    # a reimplemented/synthetic D24 scoring gate.
    root=str(whitecrow_root.resolve())
    if root not in sys.path:
        sys.path.insert(0,root)
    try:
        mod=importlib.import_module("fieldcore.academic_due_diligence")
    except (ImportError,ValueError) as e:
        raise EvidenceBlocked("whitecrow_runtime_import_unavailable") from e
    imported=Path(mod.__file__).resolve()
    if imported!=(whitecrow_root.resolve()/WHITE_CROW_SOURCE).resolve():
        raise EvidenceBlocked("whitecrow_runtime_import_source_not_pinned")

    issues,unverified_issues=_normalize_issues(review,draft_file.read_text(encoding="utf-8-sig"))
    base={
      "question":question.strip(),
      "read_bodies":[],
      "primary_passages":[],
      "locator_hits":[{"source":"NATIVE_INDAGO_PRIOR_HUNT_METADATA_ONLY",
        "hunt_id":hunt_id,"provider_calls":counts.get("provider_calls"),
        "verified_primary_new":counts.get("new_verified",0)}],
      "known_unknowns":[x["issue"] for x in issues]
         + ["UNVERIFIED_REVIEW_QUOTE_NOT_GROUNDED: "+x["issue"] for x in unverified_issues],
      "coverage_evidence":{},
      "source_reliability_currentness":[{"source":"native_prior_hunt",
        "hunt_id":hunt_id,"run_status":native_status,
        "read_depth":native_evidence.get("evidence_depth")}],
    }
    report=mod.build_disciplinary_positioning_report(
        base,semantic_action_mode="CRITIQUE",trigger_ref="M116:"+trusted_review_sha)
    if report.get("research_readiness")!="BLOCKED_ON_DUE_DILIGENCE" or report.get("coverage_status")=="HIGH":
        raise EvidenceBlocked("whitecrow_unjustified_scholarly_promotion")
    if not report.get("open_research_needs"):
        raise EvidenceBlocked("whitecrow_unexplained_missing_research_request")
    request_id="T3-F236-"+original_sha[:12]+"-"+trusted_review_sha[:12]
    request=mod.build_research_handoff(report,request_id=request_id)
    if not request or request.get("status")!="READY_FOR_RESEARCH" or request.get("execution_target")!="INDAGO":
        raise EvidenceBlocked("whitecrow_canonical_handoff_not_ready")
    if request.get("semantic_owner")!="ARTIKL_WHITECROW" or request.get("research_run_id") is not None:
        raise EvidenceBlocked("whitecrow_dispatch_lineage_forgery")
    if request.get("semantic_action_mode")!="CRITIQUE":
        raise EvidenceBlocked("whitecrow_semantic_action_mode_changed")

    output_root.mkdir(parents=True,exist_ok=True)
    audit_sha=_emit_unique(output_root/"review_literal_quote_audit.json",{
        "schema":"T3_F238_WHITECROW_REVIEW_QUOTE_ANTI_LAUNDERING_V1",
        "draft_sha256":draft_sha,"independent_review_sha256":trusted_review_sha,
        "exact_manuscript_line_issues":issues,
        "not_literal_source_grounded":unverified_issues,
        "source_verification_method":"exact_substring_at_claimed_1_based_line",
        "not_a_scientific_semantic_pass":True})
    report_sha=_emit_unique(output_root/"due_diligence_report.json",report)
    request_sha=_emit_unique(output_root/"research_request_pending.json",request)
    receipt={
      "schema":SCHEMA,"runtime":"REAL_WHITE_CROW_FIELDCORE_D24_CODE_INVOKED",
      "canonical_code_source":pinned,
      "question":question.strip(),"original_sha256":original_sha,
      "draft_sha256":draft_sha,"independent_review_sha256":trusted_review_sha,
      "prior_native_indago_hunt_id":hunt_id,"prior_hunt_evidence_depth":native_evidence.get("evidence_depth"),
      "old_hunt_not_a_return_to_this_new_research_request":True,
      "research_evidence_return_supplied":False,
      "report_sha256":report_sha,
      "request_sha256":request_sha,
      "research_request_id":request["research_request_id"],
      "dispatch_event_id":request["dispatch_event_id"],
      "dispatch_status":"NOT_DISPATCHED_FROM_THIS_RUN",
      "scientific_admission":report["research_readiness"],
      "coverage_status":report["coverage_status"],
      "allowed_next_operations":report["allowed_next_operations"],
      "open_research_needs_count":len(report["open_research_needs"]),
      "reviewer_concerns_preserved":len(issues)+len(unverified_issues),
      "reviewer_grounded_quotes":len(issues),
      "reviewer_unverified_quotes":len(unverified_issues),
      "reviewer_literal_audit_sha256":audit_sha,
      "source_read_depth":"NATIVE_METADATA_ONLY_0_NEW_FULL_PRIMARY",
      "source_novelty_accepted":False,
      "field_requalified_after_read":False,
      "native_whitcrow_model_opposition_executed":False,
      "author_gate":"HOLD","d25_manuscript_go":False,
      "send":False,"new_w12_routes":0,"world_mutation":False,
    }
    receipt_sha=_emit_unique(output_root/"whitecrow_stage_receipt.json",receipt)
    return {"runtime":receipt["runtime"],"report_sha256":report_sha,
            "request_sha256":request_sha,"receipt_sha256":receipt_sha,
            "request_id":request["research_request_id"],
            "dispatch_event_id":request["dispatch_event_id"],
            "research_needs":len(report["open_research_needs"]),
            "reviewer_literal_audit_sha256":audit_sha,
            "status":"D24_RESEARCH_REQUEST_PENDING_NOT_DISPATCHED",
            "author_gate":"HOLD","send":False}
