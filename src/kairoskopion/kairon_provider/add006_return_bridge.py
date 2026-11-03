"""F240: canonical WhiteCrow D24 return of genuine Indago ADD-006 one-shot.

NO fake full-text evidence, model acceptance, journal SEND, or World mutation.
Runs in the *existing* Kairoskopion package and calls real pinned WhiteCrow
integrate_research_evidence_return + positioning report. Only an actual
completed/partial ADD-006 EvidenceReturn with exact original lineage passes
the semantic ingress. Blocked provider results remain durable HOLDs.
"""
from __future__ import annotations
import argparse
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

from .publication_runner import EvidenceBlocked, atomic_write, sha256
from .native_whitecrow_stage import _validate_source, WHITE_CROW_SOURCE

SCHEMA="trimurti-add006-whitecrow-evidence-bridge-v1"
INPUT_SCHEMA="indago.add006.evidence_return.v1"

def _read(path:Path)->dict:
    d=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(d,dict):
        raise EvidenceBlocked("expected_json_object")
    return d

def _write_once(path:Path,obj:dict)->str:
    b=(json.dumps(obj,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    if path.exists():
        if path.read_bytes()!=b:
            raise EvidenceBlocked("add006_bridge_immutable_receipt_conflict")
    else:
        atomic_write(path,b)
    return sha256(b)

def _admit(evidence:dict, request:dict, transport_sha:str)->None:
    if evidence.get("schema")!=INPUT_SCHEMA:
        raise EvidenceBlocked("untrusted_native_add006_schema")
    if evidence.get("research_request_id")!=request.get("research_request_id"):
        raise EvidenceBlocked("add006_request_id_conflict")
    if evidence.get("dispatch_event_id")!=request.get("dispatch_event_id"):
        raise EvidenceBlocked("add006_dispatch_id_conflict")
    if evidence.get("transport_sha256")!=transport_sha:
        raise EvidenceBlocked("add006_transport_sha_conflict")
    if evidence.get("semantic_action_mode")!="CRITIQUE" or request.get("semantic_action_mode")!="CRITIQUE":
        raise EvidenceBlocked("add006_semantic_escalation_forbidden")
    if evidence.get("author_gate")!="HOLD" or evidence.get("send") is not False:
        raise EvidenceBlocked("add006_author_publication_policy_conflict")
    if evidence.get("world_mutation") is not False or evidence.get("article_seed") is not False:
        raise EvidenceBlocked("add006_world_or_seed_mutation_forbidden")
    run_id=evidence.get("research_run_id")
    if not isinstance(run_id,str) or not re.fullmatch(r"INDAGO:RUN:[a-f0-9]{16}:[A-Za-z0-9_-]{3,100}",run_id):
        raise EvidenceBlocked("add006_run_lineage_invalid")
    if evidence.get("execution_mode")!="ONE_SHOT_RESEARCH_REQUEST" or evidence.get("writeback_destination")!="INDAGO_HUNT_LEDGER_AND_HUNT_HISTORY":
        raise EvidenceBlocked("add006_execution_contract_changed")
    if evidence.get("claim_state") not in {"COMPLETED","BLOCKED","CLAIMED","RUNNING"}:
        raise EvidenceBlocked("add006_claim_state_invalid")
    if not isinstance(evidence.get("provider_calls"),int) or evidence["provider_calls"]<0:
        raise EvidenceBlocked("add006_provider_call_count_invalid")
    if evidence.get("run_status") not in {"PASS","PARTIAL","BLOCKED","LIVE_HUNT_BLOCKED","NOOP_COMPLETED","NOOP_IN_FLIGHT"}:
        raise EvidenceBlocked("add006_native_run_status_invalid")
    if evidence.get("run_status") in {"PASS","PARTIAL"}:
        h=evidence.get("hunt")
        if not isinstance(h,dict) or not h.get("hunt_id"):
            raise EvidenceBlocked("add006_no_real_hunt_witness")
        if "m108" in str(h["hunt_id"]).lower():
            raise EvidenceBlocked("add006_old_hunt_splice_forbidden")
        if evidence.get("claim_state")!="COMPLETED":
            raise EvidenceBlocked("add006_incomplete_claim_cannot_return_science")
    else:
        if evidence.get("provider_calls",0)>0 and evidence.get("hunt") is None:
            # May be an interrupted provider turn, not reusable evidence.
            raise EvidenceBlocked("add006_interrupted_nonzero_provider_requires_triage")

def bridge(*,evidence_path:Path,request_path:Path,transport_path:Path,
           whitecrow_root:Path,trusted_whitecrow_commit:str,
           trusted_whitecrow_module_sha:str,expected_evidence_sha:str,
           expected_request_sha:str,expected_transport_sha:str,
           baseline_path:Path,stage_receipt_path:Path,expected_stage_receipt_sha:str,
           native_claim_path:Path,expected_native_claim_sha:str,
           native_ledger_path:Path,expected_native_ledger_sha:str,output_root:Path)->dict:
    for p,s in [(evidence_path,expected_evidence_sha),(request_path,expected_request_sha),
                (transport_path,expected_transport_sha)]:
        if not re.fullmatch(r"[0-9a-f]{64}",s) or not p.is_file() or sha256(p.read_bytes())!=s:
            raise EvidenceBlocked("add006_external_source_hash_mismatch:"+p.name)
    request=_read(request_path)
    evidence=_read(evidence_path)
    baseline=_read(baseline_path)
    if (not re.fullmatch(r"[0-9a-f]{64}",expected_stage_receipt_sha)
        or not stage_receipt_path.is_file()
        or sha256(stage_receipt_path.read_bytes())!=expected_stage_receipt_sha):
        raise EvidenceBlocked("whitecrow_original_stage_receipt_unpinned")
    stage=_read(stage_receipt_path)
    if (stage.get("research_request_id")!=request.get("research_request_id")
        or stage.get("dispatch_event_id")!=request.get("dispatch_event_id")
        or stage.get("request_sha256")!=expected_request_sha
        or stage.get("dispatch_status")!="NOT_DISPATCHED_FROM_THIS_RUN"):
        raise EvidenceBlocked("whitecrow_original_dispatch_identity_mismatch")
    # This F238 receipt pins the ResearchRequest; F237 separately serialised
    # the transport. Ensure the actual hashed transport repeats the same typed
    # ADD-006 dispatch identity and does not expand the CRITIQUE authority.
    t=transport_path.read_text(encoding="utf-8-sig").splitlines()
    for key,value in (
        ("research_request_id",request["research_request_id"]),
        ("dispatch_event_id",request["dispatch_event_id"]),
        ("idempotency_key",request["dispatch_event_id"]),
        ("semantic_action_mode","CRITIQUE"),
        ("execution_mode","ONE_SHOT_RESEARCH_REQUEST"),
        ("transport_activation","REQUIRES_EXPLICIT_ONE_SHOT_CONSUMER"),
    ):
        if t.count(key+": "+value)!=1:
            raise EvidenceBlocked("transport_field_unbound_to_original_dispatch:"+key)
    _admit(evidence,request,expected_transport_sha)
    # A typed model-shaped EvidenceReturn is not by itself proof of a hunt.
    # Reconcile it against host-owned O_EXCL claim and append-only native
    # runtime ledger, pinned independently of this returned JSON.
    for p,sha in ((native_claim_path,expected_native_claim_sha),
                  (native_ledger_path,expected_native_ledger_sha)):
        if not re.fullmatch(r"[0-9a-f]{64}",sha) or not p.is_file() or sha256(p.read_bytes())!=sha:
            raise EvidenceBlocked("native_claim_ledger_hash_or_file_mismatch")
    if native_claim_path.resolve().parent != evidence_path.resolve().parent:
        raise EvidenceBlocked("native_evidence_not_in_claim_directory")
    claim=_read(native_claim_path)
    if (claim.get("research_request_id")!=request["research_request_id"]
        or claim.get("dispatch_event_id")!=request["dispatch_event_id"]
        or claim.get("research_run_id")!=evidence["research_run_id"]
        or claim.get("transport_sha256")!=expected_transport_sha):
        raise EvidenceBlocked("native_claim_not_bound_to_original_dispatch")
    events=[]
    for line in native_ledger_path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("[INDAGO_RUNTIME] "):
            try: obj=json.loads(line[len("[INDAGO_RUNTIME] "):])
            except ValueError:continue
            if obj.get("dispatch_event_id")==request["dispatch_event_id"] and obj.get("research_run_id")==evidence["research_run_id"]:
                events.append(obj)
    complete=evidence["run_status"] in {"PASS","PARTIAL"}
    if complete:
        actual=(evidence.get("hunt") or {}).get("hunt_id")
        if (claim.get("state")!="COMPLETED" or claim.get("native_hunt_id")!=actual
            or not any(x.get("kind")=="direct_hunt_completed"
                and x.get("native_hunt_id")==actual for x in events)):
            raise EvidenceBlocked("native_completed_hunt_receipt_not_proven")
    elif not any(x.get("kind") in {"direct_hunt_failed","direct_hunt_unsupported"} for x in events):
        raise EvidenceBlocked("native_blocked_hunt_receipt_not_proven")
    pinned=_validate_source(whitecrow_root,trusted_whitecrow_commit,trusted_whitecrow_module_sha)
    source_root=str(whitecrow_root.resolve())
    if source_root not in sys.path:
        sys.path.insert(0,source_root)
    mod=importlib.import_module("fieldcore.academic_due_diligence")
    if Path(mod.__file__).resolve()!=(whitecrow_root.resolve()/WHITE_CROW_SOURCE).resolve():
        raise EvidenceBlocked("whitecrow_import_not_pinned")
    output_root.mkdir(parents=True,exist_ok=True)
    run_status=evidence["run_status"]
    scientific_return_possible=run_status in {"PASS","PARTIAL"} and evidence["claim_state"]=="COMPLETED"
    if scientific_return_possible:
        # Native Indago candidates/DOIs are LOCATORS only; absent independently
        # verified complete source bytes and passage anchors, use PARTIAL,
        # never canonical COMPLETED or saturated.
        derivative={
          "research_request_id":request["research_request_id"],
          "dispatch_event_id":request["dispatch_event_id"],
          "research_run_id":evidence["research_run_id"],
          "run_status":"PARTIAL",
          "read_bodies":[],
          "primary_passages":[],
          "discussion_genealogy":[],
          "negative_boundary_findings":evidence.get("negative_trails") or [],
          "known_unknowns":[
              "ADD006_NATIVE_LOCATORS_NOT_FULL_PRIMARY_D15_VERIFIED",
              "Hunt PASS/PARTIAL does not prove C04 conceptual novelty",
          ],
          "source_reliability_currentness":[{
              "source":"INDAGO_ADD006_REAL_NATIVE",
              "research_run_id":evidence["research_run_id"],
              "hunt_id":evidence["hunt"]["hunt_id"],
              "reported_read_depth":evidence.get("read_depth"),
              "trust_status":"LOCATOR_OR_METADATA_ONLY_UNTIL_D15_SOURCE_BYTE_ANCHORS"
          }],
          "remaining_research_needs":baseline.get("open_research_needs") or [],
          "stop_reason":"NATIVE_SOURCE_READ_DEPTH_NOT_INDEPENDENTLY_FULL_ATTESTED",
          "evidence_cards":[],
          "coverage_evidence":{},
        }
        merged=mod.integrate_research_evidence_return(baseline,request,derivative)
        report=mod.build_disciplinary_positioning_report(
            merged,semantic_action_mode="CRITIQUE",
            trigger_ref="ADD006:"+evidence["research_run_id"])
        if report.get("research_readiness")!="BLOCKED_ON_DUE_DILIGENCE":
            raise EvidenceBlocked("whitecrow_false_science_ready_from_metadata")
        state="REQUALIFIED_RESEARCH_MORE_D15_HOLD"
        rsha=_write_once(output_root/"whitecrow_d24_after_add006.json",report)
        merged_sha=_write_once(output_root/"whitecrow_merged_evidence.json",merged)
    else:
        state="NATIVE_HUNT_BLOCKED_NOT_A_SCIENCE_RETURN"
        rsha=None
        merged_sha=None
    receipt={
      "schema":SCHEMA,"status":state,
      "research_request_id":request["research_request_id"],
      "dispatch_event_id":request["dispatch_event_id"],
      "research_run_id":evidence["research_run_id"],
      "indago_native_run_status":run_status,
      "indago_native_evidence_sha256":expected_evidence_sha,
      "indago_claim_sha256":expected_native_claim_sha,
      "indago_runtime_ledger_sha256":expected_native_ledger_sha,
      "native_completion_attested_by_ledger":complete,
      "whitecrow_source":pinned,
      "whitecrow_admission":"REAL_FIELDCORE_D24" if scientific_return_possible else "NOT_ADMITTED_HUNT_BLOCKED",
      "whitecrow_merged_sha256":merged_sha,
      "whitecrow_report_sha256":rsha,
      "requires_artikl_science_decision":True,
      "independent_primary_read_verified":False,
      "scientific_novelty_accepted":False,
      "d25_manuscript_go":False,"author_gate":"HOLD",
      "send":False,"world_mutation":False,"new_w12_routes":0,
    }
    _write_once(output_root/"add006_whitecrow_bridge_receipt.json",receipt)
    return receipt

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser()
    for arg in ["evidence","request","transport","whitecrow-root","baseline","stage-receipt","native-claim","native-ledger","out"]:
        p.add_argument("--"+arg,type=Path,required=True)
    for arg in ["expected-stage-receipt-sha","expected-native-claim-sha","expected-native-ledger-sha","trusted-whitecrow-commit","trusted-whitecrow-module-sha",
                "expected-evidence-sha","expected-request-sha","expected-transport-sha"]:
        p.add_argument("--"+arg,required=True)
    a=p.parse_args(argv)
    try:
        res=bridge(evidence_path=a.evidence,request_path=a.request,transport_path=a.transport,
                   whitecrow_root=a.whitecrow_root,trusted_whitecrow_commit=a.trusted_whitecrow_commit,
                   trusted_whitecrow_module_sha=a.trusted_whitecrow_module_sha,
                   expected_evidence_sha=a.expected_evidence_sha,
                   expected_request_sha=a.expected_request_sha,
                   expected_transport_sha=a.expected_transport_sha,
                   baseline_path=a.baseline,stage_receipt_path=a.stage_receipt,
                   expected_stage_receipt_sha=a.expected_stage_receipt_sha,
                   native_claim_path=a.native_claim,expected_native_claim_sha=a.expected_native_claim_sha,
                   native_ledger_path=a.native_ledger,expected_native_ledger_sha=a.expected_native_ledger_sha,output_root=a.out)
    except (ValueError,KeyError,OSError,EvidenceBlocked) as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e),"author_gate":"HOLD","send":False}))
        return 2
    print(json.dumps(res,ensure_ascii=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
