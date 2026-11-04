"""F4: propagate independently read, source-pinned D15 originals into real WhiteCrow D24.

Only exact immutable research files on AORUS. No model self-certifies source
breadth; all claims must match original bytes, independent Codex trace and
postreview quote readbacks. Returns partial due diligence, not novelty or GO.
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

from .native_whitecrow_stage import _validate_source, _emit_unique
from .publication_runner import EvidenceBlocked, sha256

F4=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_REVIEW_RETURN_20261104")
F241=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F241_ONE_BOUNDED_CYCLE")
NEAR=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_D15_NEAREST_20261104")
SCHEMA="T3_F4_D15_REAL_WHITECROW_POST_PRIMARY_READING_V1"
MANUSCRIPT="f5a3290780436cff2677476c49a5bd68ac8e93cc7c81a2693b0a052369e91914"
WC_COMMIT="0bd96d098a65c2f6063d682e4f9e3e97c8034227"
WC_MODULE_SHA="265216755b06926414ff09ad38f1c79de531345a5d93b397cd7468141a0401af"
SOURCES=(
 dict(id="GIUFFRIDA_ROVIGATTI_2022",root=F4,
      source_root=F241/"source_bytes",
      source="GIUFFRIDA_ROVIGATTI_2022",
      audit="F4_D15_Giuffrida_original_source_audit.json",
      audit_sha="ec3410f6232f01be76a885f49ee27d48b96e06d0a3ce625525a94c33e75c8eca",
      check="F4_D15_Giuffrida_evidence_anchor_verification.json",
      check_sha="4ef8a405aa5566ec9851cabde89194de5c55f4654055298915484805251bf740",
      errata="F4_D15_Giuffrida_quote_errata.json",
      errata_sha="88cd7de86d42599d1b2d57cb867bb2ad2464c819e90e9a853abc802f6d067be7",
      pdf_sha="b4e61b2460aac8166b9814984f8c6fbf1d318666f55b3627e27bb70125e86601",
      text_sha="fdb7ebfece840517319947fc77cf566bea506d94fa2aeba1f09a51f8418516d7",
      pages=41,log=F4/"F4_D15_Giuffrida_original_source_audit.stderr.log",
      exit=F4/"F4_D15_Giuffrida_original_source_audit.exit.txt"),
 dict(id="CACCIATORI_2008_MEMORY_OBJECTS",root=NEAR,source_root=NEAR,
      source="Cacciatori_2008_MemoryObjects_ACCEPTED_VERSION",
      audit="Cacciatori_D15_primary_source_audit.json",
      audit_sha="2c1f63efd0e6f89ec7b76250856f4e0c0da15364e36331da6f6cf7e7d4703250",
      check="Cacciatori_D15_primary_source_audit.anchor_verification.json",
      check_sha="7be8d6c80a19877c20247ac0017aea847dfe57c91523bb6603ee6a84d7d03b3c",
      errata="Cacciatori_D15_primary_source_audit.quote_errata.json",
      errata_sha="d9a053b576d97de0de76e920d0f82c0fd9600c7dcf721183615b022750e24889",
      pdf_sha="176f182779ada522ed8da403cd1bad0d9effcc6f3766ba50f132f7db1a13c1fb",
      text_sha="2e98b87e23565154dca65147fb8c82270513625d4ae6e83ae6994607587b134f",
      pages=36,log=NEAR/"Cacciatori_D15_primary_source_audit.stderr.log",
      exit=NEAR/"Cacciatori_D15_primary_source_audit.exit.txt"),
 dict(id="DAVIES_BRADY_2016_PROJECT_CAPABILITIES",root=NEAR,source_root=NEAR,
      source="Davies_Brady_2016_Project_Capabilities_ACCEPTED",
      audit="Davies_Brady_D15_primary_source_audit.json",
      audit_sha="40497c1f279982c13f5b77887a3985a16c61ebde8700173d0c4c3360586fdb54",
      check="Davies_Brady_D15_primary_source_audit.anchor_verification.json",
      check_sha="9803b47acb17e63f6cd2578910f4b873130c7a9fe9845644f84077e5a1e52a0b",
      errata="Davies_Brady_D15_primary_source_audit.quote_errata.json",
      errata_sha="f177eb67abac3f0f628eb8c279763081178337f8c82c6853b2edf3baee08a809",
      pdf_sha="83747e42d3dd63b836278bfa2119e6f5b31bf6a8d3efeb8d1b388a5321b5f442",
      text_sha="2f99689a8fcea1e6a5e71338f20ae924d2f4048d5d99cdcc0f4078a21f3fd191",
      pages=36,log=NEAR/"Davies_Brady_D15_primary_source_audit.stderr.log",
      exit=NEAR/"Davies_Brady_D15_primary_source_audit.exit.txt"),
)

def _read_pinned(p:Path,expected_sha:str)->dict:
    if not p.is_file() or sha256(p.read_bytes())!=expected_sha:
        raise EvidenceBlocked("d15_original_readback_source_sha_mismatch:"+p.name)
    obj=json.loads(p.read_text(encoding="utf-8-sig"))
    if not isinstance(obj,dict):raise EvidenceBlocked("d15_expected_json_object")
    return obj

def _physical_anchor_pages(text:str,count:int)->dict[int,str]:
    marker=r"===== PDF PAGE ([0-9]+) =====" if count==36 else r"===== PAGE ([0-9]+) ====="
    parts=re.split(marker,text)
    if len(parts)!=1+count*2:
        raise EvidenceBlocked("d15_source_page_markers_do_not_match")
    pages={int(parts[i]):parts[i+1] for i in range(1,len(parts),2)}
    if set(pages)!=set(range(1,count+1)):
        raise EvidenceBlocked("d15_pages_incomplete")
    return pages

def _normalize(text:str)->str:
    import unicodedata
    return " ".join(unicodedata.normalize("NFKC",text).replace("\u00ad","").split()).casefold()

def _run_source(spec:dict)->tuple[list[str],list[dict],dict]:
    root=spec["root"]
    pdf=spec["source_root"]/(spec["source"]+".pdf")
    textfile=spec["source_root"]/(spec["source"]+".full_text.txt")
    for path,key in ((pdf,"pdf_sha"),(textfile,"text_sha")):
        if not path.is_file() or sha256(path.read_bytes())!=spec[key]:
            raise EvidenceBlocked("d15_primary_original_bytes_mismatch:"+spec["id"])
    pages=_physical_anchor_pages(textfile.read_text(encoding="utf-8"),spec["pages"])
    report=_read_pinned(root/spec["audit"],spec["audit_sha"])
    checks=_read_pinned(root/spec["check"],spec["check_sha"])
    err=_read_pinned(root/spec["errata"],spec["errata_sha"])
    novelty_unaccepted=(report.get("scientific_novelty_accepted") is False
        or (spec["pages"]==41
            and report.get("novelty_conclusion")=="NOT_ASSESSED_ACROSS_FIELD"))
    if (report.get("manuscript_sha256")!=MANUSCRIPT
        or not novelty_unaccepted
        or report.get("d25_manuscript_go") is not False
        or report.get("author_gate")!="HOLD"
        or report.get("send") is not False
        or report.get("world_mutation") is not False):
        raise EvidenceBlocked("d15_model_review_authority_boundary_invalid")
    scope=report.get("reading_scope") or {}
    if (scope.get("pages_read")!=list(range(1,spec["pages"]+1))
        or not (scope.get("all_41_extracted_pages_read") is True or scope.get("pdf_page_count")==36)):
        raise EvidenceBlocked("d15_full_independent_read_not_attested")
    if not spec["exit"].is_file() or spec["exit"].read_text(encoding="utf-8-sig").strip()!="0":
        raise EvidenceBlocked("d15_independent_model_terminal_receipt_absent")
    if not spec["log"].is_file():
        raise EvidenceBlocked("d15_independent_read_trace_absent")
    log=spec["log"].read_text(encoding="utf-8",errors="replace")
    marker_prefix="===== PAGE " if spec["pages"]==41 else "===== PDF PAGE "
    if any(marker_prefix+str(i)+" =====" not in log for i in range(1,spec["pages"]+1)):
        raise EvidenceBlocked("d15_independent_read_missing_real_page_observation")
    if spec["pages"]==41:
        if (checks.get("strict_quote_matches")!=17
            or checks.get("evidence_quote_total")!=18
            or err.get("verified_all_18_with_explicit_single_quote_erratum") is not True):
            raise EvidenceBlocked("d15_giuffrida_anchored_quote_repair_not_proven")
        correct=[(int(x["pdf_page"]),str(x["literal_quote"])) for x in report["evidence_passages"][1:]]
        correct.extend((int(x["pdf_page"]),str(x["quote"]))
            for x in err.get("corrected_quote_replacements") or [])
        correct.extend((int(x["pdf_page"]),str(x["quote"]))
            for x in err.get("corrected_numerical_quote_fragments") or [])
        # Corrected numerical math symbols remain byte-pinned; all claims
        # are treated as original-quote fragments, not independent effect estimates.
    else:
        if (err.get("original_independent_review_sha256")!=spec["audit_sha"]
            or err.get("verifier_sha256")!=spec["check_sha"]
            or err.get("failed_spans_remaining")!=0
            or err.get("spans_now_supported_by_exact_page_fragment")!=err.get("quoted_spans_total")):
            raise EvidenceBlocked("d15_nearest_quote_errata_not_pinned")
        correct=[(int(x["page"]),str(x["quote"])) for x in checks["quote_checks"] if x["status"]=="PASS"]
        correct.extend((int(x["corrected_pdf_page"]),str(x["source_literal_replacement"]))
                       for x in err["corrections"])
    if not correct:
        raise EvidenceBlocked("d15_no_verified_passages")
    anchor_refs=[]
    anchor_ledger=[]
    for number,quote in correct:
        if number not in pages or _normalize(quote) not in _normalize(pages[number]):
            raise EvidenceBlocked("d15_source_anchor_not_on_claimed_page:"+spec["id"]+":"+str(number))
        qhash=sha256(quote.encode("utf-8"))
        ref=f"{spec['id']}@p{number}@sha256:{qhash}"
        anchor_refs.append(ref)
        anchor_ledger.append({"ref":ref,"page":number,"quote_sha256":qhash})
    return anchor_refs,anchor_ledger,{
       "source_id":spec["id"],"pdf_sha256":spec["pdf_sha"],
       "full_text_sha256":spec["text_sha"],"source_pages":spec["pages"],
       "verified_quote_count":len(correct),
       "independent_audit_sha256":spec["audit_sha"],
       "quote_verifier_sha256":spec["check_sha"],
       "quote_errata_sha256":spec["errata_sha"],
       "independent_source_read":"ACTUAL_CODEX_SOURCE_TRACE_ALL_PAGES",
       "novelty_accepted":False}

def requalify(whitecrow_root:Path,output_root:Path)->dict:
    _validate_source(whitecrow_root,WC_COMMIT,WC_MODULE_SHA)
    sources=[]
    anchors=[]
    ledger=[]
    for s in SOURCES:
        refs,rows,meta=_run_source(s)
        sources.append(meta)
        anchors.extend(refs)
        ledger.extend(rows)
    read_bodies=[s["source_id"] for s in sources]
    # Multiple independent review sections may cite the identical original
    # sentence. They count as two review placements but only one primary
    # passage. Preserve the first byte-pinned source anchor, never inflate.
    anchors=list(dict.fromkeys(anchors))
    ledger=list({row["ref"]:row for row in ledger}.values())
    if (len(read_bodies)!=3 or len(anchors)<60
        or len(anchors)!=len(ledger)
        or len(set(anchors))!=len(anchors)):
        raise EvidenceBlocked("d15_primary_source_cardinality_incomplete")
    question=("Does C04 organogenesis offer a distinct, prospectively testable "
              "mechanism beyond project-capability building, cross-project memory "
              "objects and performance-bonded governance?")
    payload={
      "question":question,
      "read_bodies":read_bodies,
      "primary_passages":anchors,
      "coverage_evidence":{
         "relevant_primary_works":read_bodies,
         "primary_passage_anchors":anchors,
         "positions_distinguished":[
            "performance_bonding_governance",
            "cross_project_artifact_memory",
            "recursive_vanguard_project_capabilities",
            "C04_proposed_L_M_H_U_prospective_qualification"],
         "control_checks":[{"check":"field_wide_fulltext_nearest_neighbor_saturation",
                            "status":"NOT_PERFORMED"}],
         "freshness_risk":"UNKNOWN"},
      "nearest_precedent":{
          "source_ref":"DAVIES_BRADY_2016_PROJECT_CAPABILITIES",
          "reason":"Vanguard projects generate, codify, transfer and recursively redeploy capabilities."},
      "strongest_known_objection":{
          "source_ref":"CACCIATORI_2008_MEMORY_OBJECTS",
          "reason":"Productive Excel workbooks and boundary objects are already created, adapted and reused across projects."},
      "known_unknowns":[
          "Full nearest-competitor coverage in commissioning, metrology, process validation, systems engineering and technology transfer not read.",
          "No empirical C04 pilot, blind coders or prospective cohort.",
          "No controlled prediction or causal comparison for L/M/H/U with existing project capability theories.",
          "No independent scientific novelty review across full scholarly neighborhood."],
      "open_research_needs":[
          "Independently read and compare commissioning, process qualification, metrology and systems engineering primary texts.",
          "Establish closest scholarly antecedent and strongest field-wide objection beyond the three read bodies.",
          "Implement prospective cases with blind coding, preregistered L/M/H/U variables and independent successor reuse.",
          "Independently assess discriminating causal predictions and construct validity after source saturation."],
      "field_saturation_class":"EVIDENCE_INSUFFICIENT",
      "source_reliability_currentness":sources,
      "negative_boundary_findings":[
          "Neither performance-bonding reduced-form evidence nor project-memory/capability theory alone proves C04 novelty.",
          "The C04 draft has no executed empirical outcome and cannot claim qualification or SEND."],
    }
    source_root=str(whitecrow_root.resolve())
    if source_root not in sys.path:sys.path.insert(0,source_root)
    mod=importlib.import_module("fieldcore.academic_due_diligence")
    if Path(mod.__file__).resolve()!=(whitecrow_root.resolve()/"fieldcore"/"academic_due_diligence.py"):
        raise EvidenceBlocked("d15_wrong_whitecrow_runtime_module")
    report=mod.build_disciplinary_positioning_report(
        payload,semantic_action_mode="CRITIQUE",trigger_ref="T3_F4_D15_3_INDEPENDENT_PRIMARY_READS")
    if (report.get("read_bodies")!=read_bodies
        or len(report.get("primary_passages") or [])!=len(anchors)
        or report.get("nearest_precedent_grounded") is not True
        or report.get("strongest_known_objection_grounded") is not True
        or report.get("research_readiness")!="BLOCKED_ON_DUE_DILIGENCE"
        or report.get("coverage_status")=="HIGH"
        or report.get("semantic_action_mode")!="CRITIQUE"):
        raise EvidenceBlocked("d15_whitecrow_unjustified_requalification_result")
    output_root.mkdir(parents=True,exist_ok=True)
    report_path=output_root/"whitecrow_d24_after_verified_d15_reads.json"
    ledger_path=output_root/"source_anchor_ledger_private.json"
    report_sha=_emit_unique(report_path,report)
    ledger_sha=_emit_unique(ledger_path,{"anchors":ledger,"read_bodies":read_bodies})
    receipt={
       "schema":SCHEMA,"case_id":"T3-TALK-20261019",
       "whitecrow_code_commit":WC_COMMIT,"whitecrow_code_sha256":WC_MODULE_SHA,
       "manuscript_sha256":MANUSCRIPT,
       "read_bodies":read_bodies,
       "source_proofs":sources,"verified_primary_passages":len(anchors),
       "whitecrow_actual_module_invoked":True,
       "whitecrow_report_sha256":report_sha,
       "source_anchor_ledger_private_sha256":ledger_sha,
       "new_source_read_count":3,
       "whitecrow_coverage_status":report["coverage_status"],
       "whitecrow_research_readiness":report["research_readiness"],
       "nearest_precedent_grounded":True,"strongest_objection_grounded":True,
       "field_wide_novelty_accepted":False,
       "field_saturation_accepted":False,
       "empirical_program_executed":False,
       "author_gate":"HOLD","d25_manuscript_go":False,
       "send":False,"world_mutation":False,
       "new_indago_hunts":0,"new_artikl_rewrites":0,
    }
    _emit_unique(output_root/"whitecrow_d15_readback_receipt.json",receipt)
    return receipt

if __name__=="__main__":
    root=Path(r"C:\projects\whitecrow-antonova-direct-20261019")
    out=F4/"F4_D15_WHITECROW_REQUALIFIED"
    try:
        print(json.dumps(requalify(root,out),ensure_ascii=False))
    except (EvidenceBlocked,ValueError,KeyError,OSError) as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc),"author_gate":"HOLD",
                          "d25_manuscript_go":False,"send":False,"world_mutation":False}))
        raise SystemExit(2)
