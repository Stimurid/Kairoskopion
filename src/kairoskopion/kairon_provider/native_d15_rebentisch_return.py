"""F4 D15 / six-primary-body canonical WhiteCrow return for Carlile-Rebentisch 2003.

This is the existing Factory's D15 return path, not a new service. Admission
requires actual independent full original reading + quote registry page match.
Every report is source- and content-pinned. Never authorizes rewrite or SEND.
"""
from __future__ import annotations
import importlib,sys,json,re
from pathlib import Path
from .native_whitecrow_stage import _validate_source,_emit_unique
from .publication_runner import EvidenceBlocked,sha256

WHITE_COMMIT="0bd96d098a65c2f6063d682e4f9e3e97c8034227"
WHITE_MODULE_SHA="265216755b06926414ff09ad38f1c79de531345a5d93b397cd7468141a0401af"
SCIENCE=Path(r"C:\projects\trimurti-t3-articles")
OPS=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_D15_NEAREST_WAVE3_20261104")
SOURCE_ID="CARLILE_REBENTISCH_2003_KNOWLEDGE_TRANSFORMATION_CYCLE"
BASE="Carlile_Rebentisch_2003_Knowledge_Transformation_Cycle"
PREVIOUS_REPORT=SCIENCE/"runs"/"T3-Factory"/"F4_D15_whitecrow_d24_five_primary_reads.json"
PREVIOUS_REPORT_SHA="44b810caae3ed31a6a6d2b337c45de160b15ad769a5fd6f1d0c610e05b2d15c6"
PREVIOUS_RECEIPT=SCIENCE/"runs"/"T3-Factory"/"F4_D15_whitecrow_five_primary_read_receipt.json"
PREVIOUS_RECEIPT_SHA="f2bb9d26a8875d7295b40ebb4fe23a2d575a4b7cbcb951be05b1eae4d58845cc"
MANUSCRIPT_SHA="f5a3290780436cff2677476c49a5bd68ac8e93cc7c81a2693b0a052369e91914"
SOURCE_PDF_SHA="4dd74f1e309aab570c4cd32427d9765d68d1a748638a15aa429728fe15b1c77b"
SOURCE_FULLTEXT_SHA="91e5288b616a1dc468ac9ee669163b73693f96d6f2e96e38a57cfd3da0f7c8e3"
SOURCE_CARRIER_SHA="ecc69bbfee29d756f6d9e2c71a4cd1cf4dd5bc2d9be78a288a763d09b60025d3"
SOURCE_REGISTRY_SHA="0a5fe1873601c623a4accba5c60248106c6ca403579f3d4320dca67968066020"

def _expect(path:Path,sha:str)->bytes:
    if not re.fullmatch("[0-9a-f]{64}",str(sha)):
        raise EvidenceBlocked("d15_wave3_unsafe_sha_request")
    if not path.is_file():
        raise EvidenceBlocked("d15_wave3_missing_pinned_input:"+path.name)
    b=path.read_bytes()
    if sha256(b)!=sha:
        raise EvidenceBlocked("d15_wave3_source_sha_mismatch:"+path.name)
    return b

def _load(path:Path,sha:str)->dict:
    data=json.loads(_expect(path,sha).decode("utf-8-sig"))
    if not isinstance(data,dict):
        raise EvidenceBlocked("d15_wave3_untrusted_json_body")
    return data

def read_primary_with_pins(manifest:dict)->tuple[list[str],dict]:
    pins=manifest.get("pins")
    if not isinstance(pins,dict):
        raise EvidenceBlocked("d15_wave3_source_manifest_missing")
    for fn,expect_hash in [
       (BASE+".pdf",SOURCE_PDF_SHA),
       (BASE+".full_text.txt",SOURCE_FULLTEXT_SHA),
       ("Carlile_Rebentisch_2003_source_carrier.json",SOURCE_CARRIER_SHA),
       ("Carlile_Rebentisch_2003_exact_quote_candidates.json",SOURCE_REGISTRY_SHA)]:
        _expect(OPS/fn,expect_hash)
    carrier=_load(OPS/"Carlile_Rebentisch_2003_source_carrier.json",SOURCE_CARRIER_SHA)
    assert carrier["pdf_pages"]==16 and carrier["pdf_sha256"]==SOURCE_PDF_SHA
    assert carrier["text_sha256"]==SOURCE_FULLTEXT_SHA
    audit=_load(OPS/"Carlile_Rebentisch_2003_independent_full_read.json",pins["audit_sha256"])
    verify=_load(OPS/"Carlile_Rebentisch_2003_source_readback.json",pins["readback_sha256"])
    if (verify["independent_source_audit_sha256"]!=pins["audit_sha256"]
        or verify["source_id"]!=SOURCE_ID
        or verify["source_pages"]!=16
        or verify["source_pages_in_actual_independent_trace"]!=16
        or verify["source_id"]!=audit["source_id"]
        or verify["selected_exact_quote_count"]<12):
        raise EvidenceBlocked("d15_wave3_independent_primary_read_unsubstantiated")
    if (audit["manuscript_sha256"]!=MANUSCRIPT_SHA
        or audit.get("publication_field_novelty_accepted") is not False
        or audit.get("empirical_C04_demonstrated") is not False
        or audit.get("author_gate")!="HOLD"
        or audit.get("send") is not False
        or audit.get("world_mutation") is not False):
        raise EvidenceBlocked("d15_wave3_model_claimed_authority")
    if (audit["reading_scope"]["pages_read"]!=list(range(1,17))
        or verify["selected_exact_quote_count"]!=len(audit["selected_original_passage_ids"])):
        raise EvidenceBlocked("d15_wave3_missing_page_read")
    # physical provenance readback not self certification: the real source audit
    # helper verified literal registry IDs on original extracted PDF pages.
    full=_expect(OPS/(BASE+".full_text.txt"),SOURCE_FULLTEXT_SHA).decode("utf-8")
    chunks=re.split("===== PDF PAGE ([0-9]+) =====",full)
    if len(chunks)!=33:
        raise EvidenceBlocked("d15_wave3_missing_original_page_slices")
    pages={int(chunks[i]):chunks[i+1] for i in range(1,len(chunks),2)}
    registry=_load(OPS/"Carlile_Rebentisch_2003_exact_quote_candidates.json",SOURCE_REGISTRY_SHA)
    lookup={x["id"]:x for x in registry["anchors"]}
    if (len(set(audit["selected_original_passage_ids"]))!=len(audit["selected_original_passage_ids"])
        or len(lookup)!=len(registry["anchors"])):
        raise EvidenceBlocked("d15_wave3_duplicate_quotation_ids")
    out=[]
    for row in verify["checked_source_quotes"]:
        rid=row["id"]
        if (rid not in lookup or rid not in audit["selected_original_passage_ids"]
            or row.get("verified_direct_source_page") is not True):
            raise EvidenceBlocked("d15_wave3_reference_not_independent_quote")
        source=lookup[rid]
        if (source["pdf_page"]!=row["pdf_page"]
            or source["quote_sha256"]!=row["quote_sha256"]
            or source["exact_quote"] not in " ".join(pages[row["pdf_page"]].split())):
            raise EvidenceBlocked("d15_wave3_source_quote_page_mismatch")
        sha=source["quote_sha256"]
        out.append(f"{SOURCE_ID}@p{row['pdf_page']}@sha256:{sha}")
    refs=list(dict.fromkeys(out))
    if len(refs)<12:
        raise EvidenceBlocked("d15_wave3_insufficient_source_quote_anchors")
    return refs,{
      "source_id":SOURCE_ID,
      "original_pdf_sha256":SOURCE_PDF_SHA,
      "original_text_sha256":SOURCE_FULLTEXT_SHA,
      "original_source_carrier_sha256":SOURCE_CARRIER_SHA,
      "quote_registry_sha256":SOURCE_REGISTRY_SHA,
      "independent_audit_sha256":pins["audit_sha256"],
      "source_readback_sha256":pins["readback_sha256"],
      "primary_pdf_pages":16,
      "verbatim_page_anchored_passages":len(refs),
      "independent_fulltext_read_observed":True,
      "novelty_accepted":False}

def run(manifest_path:Path,manifest_sha:str,whitecrow_root:Path,out:Path)->dict:
    manifest=_load(manifest_path,manifest_sha)
    if (manifest.get("schema")!="T3_F4_D15_CARLILE_REBENTISCH_2003_RETURN_MANIFEST_V1"
        or manifest.get("manuscript_sha256")!=MANUSCRIPT_SHA
        or manifest.get("author_gate")!="HOLD"
        or manifest.get("send") is not False
        or manifest.get("world_mutation") is not False):
        raise EvidenceBlocked("d15_wave3_bad_source_pinning_manifest")
    _validate_source(whitecrow_root,WHITE_COMMIT,WHITE_MODULE_SHA)
    prev=_load(PREVIOUS_REPORT,PREVIOUS_REPORT_SHA)
    previous_receipt=_load(PREVIOUS_RECEIPT,PREVIOUS_RECEIPT_SHA)
    if (len(prev["read_bodies"])!=5
        or len(prev["primary_passages"])!=83
        or prev["coverage_status"]!="PARTIAL"
        or prev["research_readiness"]!="BLOCKED_ON_DUE_DILIGENCE"
        or previous_receipt["whitecrow_source_report_sha256"]!=PREVIOUS_REPORT_SHA
        or SOURCE_ID in prev["read_bodies"]):
        raise EvidenceBlocked("d15_wave3_previous_whitecrow_report_not_admitted")
    source_refs,source_proof=read_primary_with_pins(manifest)
    bodies=list(prev["read_bodies"])+[SOURCE_ID]
    anchors=list(dict.fromkeys(prev["primary_passages"]+source_refs))
    if len(bodies)!=6 or len(anchors)<95:
        raise EvidenceBlocked("d15_wave3_original_coverage_incomplete")
    data={
      "question":"Does C04's prospectively instituted L/B/M/H/U qualification-and-succession mechanism predict events beyond the path-dependent knowledge transformation cycle and its two observed transfer/design cases?",
      "read_bodies":bodies,
      "primary_passages":anchors,
      "nearest_precedent":prev["nearest_precedent"],
      "strongest_known_objection":prev["strongest_known_objection"],
      "coverage_evidence":{
        "relevant_primary_works":bodies,
        "primary_passage_anchors":anchors,
        "positions_distinguished":[
           "project_capability_generation_and_reuse",
           "productive_cross_project_memory_objects",
           "performance_bonding_contractual_governance",
           "pragmatic_boundaries_and_tool_creation",
           "knowledge_transformation_storage_retrieval_and_reconfiguration",
           "C04_L_B_M_H_U_proposed_qualifying_successor_mechanism"],
        "control_checks":[{"check":"field_wide_nearest_neighbor_original_fulltext_saturation",
                           "status":"NOT_PERFORMED"}],
        "freshness_risk":"UNKNOWN"},
      "field_saturation_class":"EVIDENCE_INSUFFICIENT",
      "known_unknowns":[
        "Prencipe-Tell 2001, Davies-Brady 2000, Hargadon-Sutton 1997 and D'Adderio 2003 not yet all independently read from exact physical primary PDF in this return.",
        "Independent process qualification and commissioned successor operation primary field underread.",
        "The original six studies do not establish a prospective C04 cohort or a distinct positive M/H/U effect.",
        "Candidate registry passage-ID literal provenance does not itself verify every reviewer interpretation."],
      "open_research_needs":[
        "Complete finite nearest precedent comparisons to original inter-project inheritance and technology-brokering case studies.",
        "Specify an intervention whose predicted successor outcomes differ under matched information, training, rights and resources from the strong Carlile-Rebentisch rival.",
        "Pre-register independent qualification M, handoff H and successor reproduction U; retain unavailable-opportunity and failed-use cases separately.",
        "Assess construct novelty and measurement validity independently before any rewrite or D25 release."],
      "negative_boundary_findings":[
        "Carlile-Rebentisch 2003 already describes the cycle from stored knowledge to retrieval, contextual transformation, and new transferable solutions.",
        "Creation of new boundary objects under novel demands is not, alone, a C04 causal mechanism."
      ] }
    root=str(whitecrow_root.resolve())
    if root not in sys.path:sys.path.insert(0,root)
    module=importlib.import_module("fieldcore.academic_due_diligence")
    if Path(module.__file__).resolve()!=whitecrow_root.resolve()/"fieldcore"/"academic_due_diligence.py":
        raise EvidenceBlocked("d15_wave3_wrong_whitecrow_source_module")
    report=module.build_disciplinary_positioning_report(
        data,semantic_action_mode="CRITIQUE",
        trigger_ref="T3_F4_D15_ORIGINAL_CARLILE_REBENTISCH_2003_WAVE3")
    if (report.get("read_bodies")!=bodies
        or len(report.get("primary_passages") or [])!=len(anchors)
        or report.get("coverage_status")=="HIGH"
        or report.get("research_readiness")!="BLOCKED_ON_DUE_DILIGENCE"
        or report.get("semantic_action_mode")!="CRITIQUE"
        or report.get("nearest_precedent_grounded") is not True
        or report.get("strongest_known_objection_grounded") is not True):
        raise EvidenceBlocked("d15_wave3_whitecrow_unjustified_science_go")
    out.mkdir(parents=True,exist_ok=True)
    rsha=_emit_unique(out/"whitecrow_d24_after_six_primary_reads.json",report)
    receipt={
      "schema":"T3_F4_D15_SIX_PRIMARY_WHITE_CROW_RECEIPT_V1",
      "whitecrow_exact_git_commit":WHITE_COMMIT,
      "whitecrow_exact_module_sha256":WHITE_MODULE_SHA,
      "source_proof":source_proof,
      "independent_read_source_count":6,
      "read_bodies":bodies,"verified_unique_primary_passages":len(anchors),
      "whitecrow_report_sha256":rsha,
      "previous_whitecrow_report_sha256":PREVIOUS_REPORT_SHA,
      "manuscript_sha256":MANUSCRIPT_SHA,
      "whitecrow_research_readiness":report["research_readiness"],
      "whitecrow_coverage_status":report["coverage_status"],
      "field_science_novelty_accepted":False,
      "field_saturation_accepted":False,
      "independent_C04_empirical_program_completed":False,
      "new_indago_hunts":0,"new_artikl_rewrites":0,
      "author_gate":"HOLD","d25_manuscript_go":False,
      "send":False,"world_mutation":False}
    _emit_unique(out/"six_primary_whitecrow_return_receipt.json",receipt)
    return receipt

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--manifest-sha",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:
        print(json.dumps(run(args.manifest,args.manifest_sha,
                              Path(r"C:\projects\whitecrow-antonova-direct-20261019"),
                              args.out),ensure_ascii=False))
    except (EvidenceBlocked,ValueError,KeyError,OSError,AssertionError) as e:
        print(json.dumps({"status":"HOLD","reason":str(e),
                          "author_gate":"HOLD","d25_manuscript_go":False,
                          "send":False,"world_mutation":False},ensure_ascii=False))
        raise SystemExit(2)
