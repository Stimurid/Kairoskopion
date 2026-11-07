"""F236 native WhiteCrow D24 continuity and safety contracts (no science fixtures promoted)."""
import hashlib
import json
from pathlib import Path

import pytest
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked
from kairoskopion.kairon_provider import native_whitecrow_stage as w
from kairoskopion.kairon_provider.native_factory_cycle import preflight_inputs

H="a"*64
HUNT="h-20261103T093402Z-trimurti_m108_c04_20261103-e65d8a"
QUESTION=("What exact prospective measurement distinguishes creation of an absent "
          "productive ability in a temporary organ from conventional underwriting?")

def fixtures(tmp_path):
    draft=tmp_path/"draft.md"
    draft.write_text("# Synthetic C04\nAn exact synthetic claim about organ formation.\n",encoding="utf-8")
    draft_sha=hashlib.sha256(draft.read_bytes()).hexdigest()
    rev={"candidate_sha256":draft_sha,"author_gate":"HOLD",
         "final_verdict":"REVISION_REQUIRED",
         "new_major_issues":[{"issue":"Circular organ definition",
                              "candidate_line":2,
                              "literal_quote":"An exact synthetic claim about organ formation.",
                              "problem":"ex post bias"}]}
    p=tmp_path/"review.json"
    b=(json.dumps(rev)+"\n").encode()
    p.write_bytes(b)
    receipt={"native_hunt_id":HUNT,"native_status":"PARTIAL",
             "original_sha256":H,"manuscript_sha256":draft_sha,
             "counts":{"provider_calls":8,"new_verified":0},
             "evidence_depth":"NATIVE_PROVIDER_RETURNS_NOT_INDEPENDENT_FULL_PRIMARY_READ"}
    return p,hashlib.sha256(b).hexdigest(),receipt,draft,draft_sha

def args(tmp_path):
    p,review_sha,evidence,draft,draft_sha=fixtures(tmp_path)
    return dict(whitecrow_root=tmp_path,trusted_git_commit="f"*40,
                trusted_module_sha="f"*64,review_file=p,trusted_review_sha=review_sha,
                draft_file=draft,original_sha=H,draft_sha=draft_sha,native_evidence=evidence,
                question=QUESTION,output_root=tmp_path/"out")

def test_wrong_new_hunt_lineage_does_not_qualify_as_prior_source(tmp_path):
    a=args(tmp_path)
    a["native_evidence"]["manuscript_sha256"]="b"*64
    with pytest.raises(EvidenceBlocked,match="source_mismatch"):
        w.qualify(**a)

def test_unverified_reviewer_cannot_create_dispatch(tmp_path):
    a=args(tmp_path)
    a["trusted_review_sha"]="1"*64
    with pytest.raises(EvidenceBlocked,match="review_sha_mismatch"):
        w.qualify(**a)
    assert not (tmp_path/"out").exists()

def test_empty_or_truncated_whitecrow_question_fails_before_dispatch(tmp_path):
    a=args(tmp_path)
    a["question"]="A?"
    with pytest.raises(EvidenceBlocked,match="exact_research_question"):
        w.qualify(**a)

def test_nonqualifying_native_hunt_rejected(tmp_path):
    a=args(tmp_path)
    a["native_evidence"]["native_status"]="BLOCKED"
    with pytest.raises(EvidenceBlocked,match="no_admissible_native"):
        w.qualify(**a)

def test_empty_review_issue_cannot_start_whitecrow_request():
    with pytest.raises(EvidenceBlocked,match="no_actual_issues"):
        w._normalize_issues({"new_major_issues":[]},"# synthetic")

def test_emit_same_request_idempotent_and_detects_rewrite(tmp_path):
    p=tmp_path/"pending.json"
    digest=w._emit_unique(p,{"status":"READY_FOR_RESEARCH"})
    assert digest==w._emit_unique(p,{"status":"READY_FOR_RESEARCH"})
    with pytest.raises(EvidenceBlocked,match="receipt_mutated"):
        w._emit_unique(p,{"status":"COMPLETED"})

def test_continuity_request_never_claims_old_hunt_is_new_evidence():
    assert "whitecrow" in w.SCHEMA
    assert w.WHITE_CROW_SOURCE=="fieldcore/academic_due_diligence.py"


def test_misquoted_review_cannot_be_grounded_as_manuscript_issue(tmp_path):
    a=args(tmp_path)
    review=json.loads(a["review_file"].read_text(encoding="utf-8"))
    review["new_major_issues"][0]["literal_quote"]="This assertion does not appear in the document"
    b=(json.dumps(review)+"\n").encode("utf-8")
    a["review_file"].write_bytes(b)
    a["trusted_review_sha"]=hashlib.sha256(b).hexdigest()
    with pytest.raises(EvidenceBlocked,match="whitecrow_no_literal_grounded_review_issues"):
        w._normalize_issues(review,a["draft_file"].read_text(encoding="utf-8"))
    assert not a["output_root"].exists()

def test_mixed_review_keeps_unverified_as_unknown_not_grounded(tmp_path):
    draft="# Synthetic\nExact claim is on line two.\n"
    review={"new_major_issues":[
        {"issue":"Supported defect","candidate_line":2,"literal_quote":"Exact claim","problem":"..." },
        {"issue":"Reviewer invented this sentence","candidate_line":2,
         "literal_quote":"NOT IN DRAFT","problem":"..."}
    ]}
    grounded,unverified=w._normalize_issues(review,draft)
    assert len(grounded)==1 and len(unverified)==1
    assert grounded[0]["status"]=="EXACT_MANUSCRIPT_LINE"
    assert unverified[0]["status"]=="UNVERIFIED_REVIEW_QUOTE_NOT_ADMITTED"
