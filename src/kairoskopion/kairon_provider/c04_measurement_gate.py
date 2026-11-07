"""C04 M114: fail-closed *structural* pre-award measurement snapshot validation.

This is not a validated scientific instrument, author decision, or D25 gate.
It prevents mixing substantive state with evidence quality, leaking outcome
information, and silently reusing post-t0 witnesses. No fabricated real cases.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .publication_runner import EvidenceBlocked, atomic_write, sha256

SCHEMA="trimurti-c04-measurement-snapshot-v1"
RECEIPT_SCHEMA="trimurti-c04-snapshot-structural-check-v1"
AXES=("K","A","Q","T","W")
TOP_KEYS={"schema","operation_id","specification_sha256","t0_utc","coder_id",
          "dimensions","measurement_charter_sha256"}
DIM_KEYS={"state","evidence_quality","observed_utc","witness_sha256","rationale",
          "not_applicable_reason"}
STATE_SPECIAL={"UNKNOWN","NOT_APPLICABLE"}
LEVELS={"E0","E1","E2","E3"}
MAX_INPUT=128_000
CHARter_HASH="afb8ae10d7cdd83790153446227a4e5e3b85e708e16f0e36e1ff03c522ad85b7"

def _digest(value):
    return isinstance(value,str) and bool(re.fullmatch(r"[a-f0-9]{64}",value))

def _stamp(text):
    if not isinstance(text,str):
        raise EvidenceBlocked("timestamp_required")
    try:
        t=datetime.fromisoformat(text.replace("Z","+00:00"))
    except ValueError as e:
        raise EvidenceBlocked("invalid_timestamp") from e
    if t.tzinfo is None or t.utcoffset() is None:
        raise EvidenceBlocked("timezone_offset_required")
    return t.astimezone(timezone.utc)

def validate(row:dict,*,raw_bytes:bytes,expected_charter_sha256:str)->dict:
    if not isinstance(row,dict) or set(row)!=TOP_KEYS:
        raise EvidenceBlocked("snapshot_schema_or_keys_invalid")
    if row["schema"]!=SCHEMA or not isinstance(row["operation_id"],str) or not (1<=len(row["operation_id"])<=120):
        raise EvidenceBlocked("operation_identity_invalid")
    if not _digest(row["specification_sha256"]):
        raise EvidenceBlocked("exact_specification_sha_required")
    if not _digest(expected_charter_sha256) or expected_charter_sha256!=CHARter_HASH or row["measurement_charter_sha256"]!=expected_charter_sha256:
        raise EvidenceBlocked("untrusted_or_stale_charter_sha")
    if not isinstance(row["coder_id"],str) or not (1<=len(row["coder_id"])<=120):
        raise EvidenceBlocked("coder_identity_missing")
    cutoff=_stamp(row["t0_utc"])
    dims=row["dimensions"]
    if not isinstance(dims,dict) or set(dims)!=set(AXES):
        raise EvidenceBlocked("all_five_individual_dimensions_required")
    statuses={}
    for axis in AXES:
        v=dims[axis]
        if not isinstance(v,dict) or set(v)!=DIM_KEYS:
            raise EvidenceBlocked("dimension_schema_invalid:"+axis)
        state=v["state"]
        if not ((type(state) is int and state in (0,1,2,3))
                or (isinstance(state,str) and state in STATE_SPECIAL)):
            raise EvidenceBlocked("substantive_state_invalid:"+axis)
        e=v["evidence_quality"]
        if not isinstance(e,str) or e not in LEVELS:
            raise EvidenceBlocked("evidence_quality_invalid:"+axis)
        w=v["witness_sha256"]
        if w is not None and not _digest(w):
            raise EvidenceBlocked("witness_sha_invalid:"+axis)
        when=v["observed_utc"]
        if when is not None and _stamp(when)>cutoff:
            raise EvidenceBlocked("post_t0_witness_leakage:"+axis)
        reason=v["rationale"]
        if not isinstance(reason,str) or not (10<=len(reason.strip())<=2000):
            raise EvidenceBlocked("substantive_rationale_missing:"+axis)
        if e=="E0":
            if state!="UNKNOWN" or w is not None or when is not None:
                raise EvidenceBlocked("zero_evidence_cannot_assert_state:"+axis)
        elif e in {"E2","E3"}:
            if not _digest(w) or when is None:
                raise EvidenceBlocked("high_evidence_requires_dated_witness:"+axis)
        if state=="NOT_APPLICABLE":
            na=v["not_applicable_reason"]
            if not isinstance(na,str) or len(na.strip())<15 or e not in {"E2","E3"}:
                raise EvidenceBlocked("na_requires_supported_exemption:"+axis)
        elif v["not_applicable_reason"] not in (None,""):
            raise EvidenceBlocked("na_reason_with_non_na_state:"+axis)
        if state!="UNKNOWN" and e=="E0":
            raise EvidenceBlocked("known_state_without_evidence:"+axis)
        statuses[axis]={"substantive_state":state,"evidence_quality":e,
                        "witness_byte_pin_present":bool(w),
                        "observed_at_or_before_t0":when is None or _stamp(when)<=cutoff}
    return {"schema":RECEIPT_SCHEMA,
       "operation_id":row["operation_id"],"coder_id":row["coder_id"],
       "input_sha256":sha256(raw_bytes),
       "specification_sha256":row["specification_sha256"],
       "charter_sha256":expected_charter_sha256,
       "t0_utc":cutoff.isoformat(),
       "dimensions":statuses,
       "gate":"STRUCTURE_ONLY_VALID",
       "validates_truth_of_witness":False,"construct_validity_established":False,
       "interrater_reliability_established":False,
       "outcome_Y_included":False,"author_gate":"HOLD","scientific_status":"UNVALIDATED_PROPOSED_CODEBOOK",
       "d25_manuscript_go":False,"accepted_article_seed":False,
       "new_w12_routes":0,"send":False,"world_mutated":False}

def readback(*,input_path:Path,charter_path:Path,output_path:Path)->dict:
    if not input_path.is_file() or input_path.stat().st_size>MAX_INPUT:
        raise EvidenceBlocked("snapshot_missing_or_oversized")
    charter=charter_path.read_bytes()
    ch=sha256(charter)
    raw=input_path.read_bytes()
    try:
        obj=json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError,ValueError) as e:
        raise EvidenceBlocked("snapshot_unreadable_json") from e
    receipt=validate(obj,raw_bytes=raw,expected_charter_sha256=ch)
    content=(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    if output_path.exists():
        if output_path.read_bytes()!=content:
            raise EvidenceBlocked("structural_receipt_conflict")
    else:
        atomic_write(output_path,content)
    return receipt

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--charter",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    try:
        receipt=readback(input_path=a.input,charter_path=a.charter,output_path=a.out)
    except (OSError,EvidenceBlocked) as e:
        print(json.dumps({"gate":"BLOCKED","reason":str(e),"send":False}))
        return 2
    print(json.dumps(receipt,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
