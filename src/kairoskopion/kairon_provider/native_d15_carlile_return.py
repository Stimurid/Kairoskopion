"""D15 Wave 2 Carlile originals -> pinned canonical WhiteCrow FieldCore D24.

This adapter admits independently read primary passages from verified local PDFs
into the existing Factory. It is not Indago, a new hunt, or a permission to
rewrite C04. One shot, content-addressed, fail-closed.
"""
from __future__ import annotations
import json,re,sys,importlib
from pathlib import Path
from collections.abc import Mapping
from .native_whitecrow_stage import _validate_source, _emit_unique
from .publication_runner import EvidenceBlocked, sha256

SCHEMA="T3_F4_D15_CARLILE_WAVE2_WHITE_CROW_READBACK_V1"
WHITE_COMMIT="0bd96d098a65c2f6063d682e4f9e3e97c8034227"
WHITE_SHA="265216755b06926414ff09ad38f1c79de531345a5d93b397cd7468141a0401af"
OLD_REPORT_SHA="ba3dc104b580944b89514dcd14df8afe041ffecea728bdf015307a3daf64a99d"
OLD_RECEIPT_SHA="cca64ea578645fc86ee962c560433a6a08339ffb5b036a0afa4fd703e9a88e5a"
MANUSCRIPT_SHA="f5a3290780436cff2677476c49a5bd68ac8e93cc7c81a2693b0a052369e91914"
READ_ROOT=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_D15_NEAREST_WAVE2_20261104")
OLD_ROOT=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_REVIEW_RETURN_20261104\F4_D15_WHITECROW_REQUALIFIED")
SOURCE_DEFS={
 "2002":("CARLILE_2002_PRAGMATIC_KNOWLEDGE","Carlile_2002_PragmaticKnowledge_original",
         "Carlile_D15_full_primary_read"),
 "2004":("CARLILE_2004_THREE_T_FRAMEWORK","Carlile_2004_ThreeT_IntegratedFramework_original",
         "Carlile_2004_D15_full_primary_read"),
}

def _pin(path:Path,expected_sha:str)->bytes:
    if not isinstance(expected_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_sha):
        raise EvidenceBlocked("d15_wave2_missing_exact_sha")
    if not path.is_file():raise EvidenceBlocked("d15_wave2_source_missing:"+path.name)
    raw=path.read_bytes()
    if sha256(raw)!=expected_sha:
        raise EvidenceBlocked("d15_wave2_source_sha_mismatch:"+path.name)
    return raw

def _json_pinned(path:Path,sha:str)->dict:
    out=json.loads(_pin(path,sha).decode("utf-8-sig"))
    if not isinstance(out,dict):raise EvidenceBlocked("d15_wave2_not_object")
    return out

def _normalized(s:str)->str:
    import unicodedata
    s=unicodedata.normalize("NFKC",s).replace("\u00ad","").replace("\ufb01","fi").replace("\ufb02","fl")
    return " ".join(s.split()).casefold()

def _source_read(kind:str,item:dict)->tuple[list[str],list[dict],dict]:
    source_id,base,auditbase=SOURCE_DEFS[kind]
    root=READ_ROOT
    doc=_pin(root/(base+".pdf"),item["source_pdf_sha256"])
    if not doc.startswith(b"%PDF"):raise EvidenceBlocked("d15_wave2_not_pdf")
    carrier=_json_pinned(root/(base+".source_carrier.json"),item["carrier_sha256"])
    assert isinstance(carrier,dict)
    text=_pin(root/(base+".full_text.txt"),item["source_text_sha256"]).decode("utf-8")
    if (carrier["source_pdf_sha256"]!=item["source_pdf_sha256"]
        or carrier["source_extracted_sha256"]!=item["source_text_sha256"]
        or carrier["page_count"]!=14):
        raise EvidenceBlocked("d15_wave2_invalid_source_carrier")
    chunks=re.split(r"===== PDF PAGE ([0-9]+) =====",text)
    if len(chunks)!=29:raise EvidenceBlocked("d15_wave2_missing_pages")
    pages={int(chunks[i]):chunks[i+1] for i in range(1,29,2)}
    if set(pages)!=set(range(1,15)):raise EvidenceBlocked("d15_wave2_invalid_page_ids")
    audit=_json_pinned(root/(auditbase+".json"),item["audit_sha256"])
    check=_json_pinned(root/(auditbase+".anchor_verification.json"),item["check_sha256"])
    errata=_json_pinned(root/(auditbase+".quote_errata.json"),item["errata_sha256"])
    if (audit["source_id"]!=source_id or audit["manuscript_sha256"]!=MANUSCRIPT_SHA
        or audit["novelty_accepted"] is not False or audit["author_gate"]!="HOLD"
        or audit["send"] is not False or audit["world_mutation"] is not False
        or audit["d25_manuscript_go"] is not False):
        raise EvidenceBlocked("d15_wave2_model_scope_or_source_invalid")
    scope=audit.get("reading_scope") or {}
    if scope.get("pages_read")!=list(range(1,15)):
        raise EvidenceBlocked("d15_wave2_primary_full_read_not_proven")
    trace=_pin(root/(auditbase+".stderr.log"),item["stderr_sha256"]).decode("utf-8",errors="replace")
    if sum(f"===== PDF PAGE {i} =====" in trace for i in range(1,15))!=14:
        raise EvidenceBlocked("d15_wave2_real_model_trace_missing_pages")
    if _pin(root/(auditbase+".exit.txt"),item["exit_sha256"]).decode("ascii").strip()!="0":
        raise EvidenceBlocked("d15_wave2_model_nonzero_exit")
    if (check["audit_sha256"]!=item["audit_sha256"]
        or check["source_pdf_sha256"]!=item["source_pdf_sha256"]
        or check["source_text_sha256"]!=item["source_text_sha256"]):
        raise EvidenceBlocked("d15_wave2_quote_verification_lineage_invalid")
    if (errata["audit_sha256"]!=item["audit_sha256"]
        or errata["check_sha256"]!=item["check_sha256"]
        or errata["source_extracted_sha256"]!=item["source_text_sha256"]
        or errata["original_strict_count"]!=check["strict"]
        or errata["original_nonliteral_count"]!=check["compact_only"]+check["unverified"]
        or errata["corrected_exact_same_claim_count"]!=len(errata["corrections"])
        or errata["unadmitted_count"]!=len(errata["unadmitted"])):
        raise EvidenceBlocked("d15_wave2_quote_errata_lineage_or_counts_invalid")
    # Only review quotations with physical original PDF page match, after
    # any specifically pinned verified corrected fragment; original failed
    # spans never reach the scientific evidence set.
    corrected={(str(c["section"]),int(c["index"])):(int(c["pdf_page"]),str(c["corrected_quote"]))
               for c in errata.get("corrections") or []}
    if len(corrected)!=len(errata["corrections"]):
        raise EvidenceBlocked("d15_wave2_duplicate_corrected_quote_id")
    refs=[]
    ledger=[]
    for row in check.get("checks") or []:
        section=str(row["section"]);idx=int(row["index"])
        if row["status"]=="STRICT":
            page=int(row["pdf_page"]);quote=str(row["claimed_quote"])
        else:
            if (section,idx) not in corrected:
                # This review quote is not literal evidence. Keep it in the
                # error ledger, but do NOT admit it as a WhiteCrow passage.
                continue
            page,quote=corrected[(section,idx)]
        if page not in pages or _normalized(quote) not in _normalized(pages[page]):
            raise EvidenceBlocked("d15_wave2_quote_missing_from_original_pdf_page")
        ref=f"{source_id}@p{page}@sha256:{sha256(quote.encode('utf-8'))}"
        refs.append(ref)
        ledger.append({"ref":ref,"source_id":source_id,"page":page,
           "quote_sha256":sha256(quote.encode("utf-8"))})
    refs=list(dict.fromkeys(refs))
    ledger=list({x["ref"]:x for x in ledger}.values())
    if len(refs)<4 or len(refs)!=len(ledger):
        raise EvidenceBlocked("d15_wave2_insufficient_unique_primary_anchors")
    return refs,ledger,{
     "source_id":source_id,"pdf_sha256":item["source_pdf_sha256"],
     "extracted_text_sha256":item["source_text_sha256"],
     "page_count":14,"independent_report_sha256":item["audit_sha256"],
     "anchor_verification_sha256":item["check_sha256"],
     "errata_sha256":item["errata_sha256"],
     "unique_source_passages":len(refs),
     "original_unverified_quote_placements":check["compact_only"]+check["unverified"],
     "corrected_quote_placements_admitted":len(corrected),
     "unadmitted_quote_placements":errata["unadmitted_count"],
     "independent_reader_observed_all_pages":True,
     "novelty_accepted":False}

def run(*,manifest_path:Path,manifest_sha:str,whitecrow_root:Path,out:Path)->dict:
    manifest=_json_pinned(manifest_path,manifest_sha)
    if (manifest.get("schema")!="T3_F4_D15_CARLILE_WAVE2_PINNED_RETURN_MANIFEST_V1"
        or manifest.get("manuscript_sha256")!=MANUSCRIPT_SHA
        or manifest.get("author_gate")!="HOLD" or manifest.get("send") is not False
        or manifest.get("world_mutation") is not False):
        raise EvidenceBlocked("d15_wave2_manifest_invalid")
    _validate_source(whitecrow_root,WHITE_COMMIT,WHITE_SHA)
    old=_json_pinned(OLD_ROOT/"whitecrow_d24_after_verified_d15_reads.json",OLD_REPORT_SHA)
    old_receipt=_json_pinned(OLD_ROOT/"whitecrow_d15_readback_receipt.json",OLD_RECEIPT_SHA)
    if (old["coverage_status"]!="PARTIAL" or old["research_readiness"]!="BLOCKED_ON_DUE_DILIGENCE"
        or len(old["read_bodies"])!=3 or len(old["primary_passages"])<60
        or old_receipt["whitecrow_report_sha256"]!=OLD_REPORT_SHA):
        raise EvidenceBlocked("d15_wave2_previous_whitecrow_report_untrusted")
    read=list(old["read_bodies"])
    anchors=list(old["primary_passages"])
    newmeta=[]
    ledger=[]
    for kind in ("2002","2004"):
        if kind not in (manifest.get("sources") or {}):
            raise EvidenceBlocked("d15_wave2_required_primary_missing")
        refs,rows,meta=_source_read(kind,manifest["sources"][kind])
        if meta["source_id"] in read:raise EvidenceBlocked("d15_wave2_duplicate_read_source")
        read.append(meta["source_id"]);anchors.extend(refs)
        ledger.extend(rows);newmeta.append(meta)
    anchors=list(dict.fromkeys(anchors))
    if len(read)!=5 or len(anchors)<70:
        raise EvidenceBlocked("d15_wave2_partial_new_science_return")
    q=(
     "Does C04 offer a distinct reproducible organogenesis mechanism beyond "
     "vanguard-project capabilities, cross-project memory objects, pragmatic "
     "knowledge-boundary transformation and surety governance? "
     "Are L/B/M/H/U independent observations with extra predictive value?"
    )
    data={
      "question":q,"read_bodies":read,"primary_passages":anchors,
      "nearest_precedent":old["nearest_precedent"],
      "strongest_known_objection":old["strongest_known_objection"],
      "coverage_evidence":{
        "relevant_primary_works":read,
        "primary_passage_anchors":anchors,
        "positions_distinguished":[
          "recursively_generated_project_capabilities",
          "adaptable_productive_boundary_objects",
          "contractual_bonding_governance",
          "pragmatic_knowledge_translation_and_transformation",
          "C04_L_B_M_H_U_event_and_rights_qualification_proposal"],
        "control_checks":[{"check":"full_nearest_field_novelty_coverage",
                           "status":"NOT_PERFORMED"}],
        "freshness_risk":"UNKNOWN"},
      "field_saturation_class":"EVIDENCE_INSUFFICIENT",
      "known_unknowns":[
        "Davies-Brady 2000, Prencipe-Tell 2001, Hargadon-Sutton 1997 and D'Adderio 2003 have not yet been read in their full physical primary versions in this source return.",
        "Commissioning, process qualification, metrology and systems-engineering primary competitor field remains partly unread.",
        "C04 has not executed L/B/M/H/U measurements, independent successor reuse or pre-registered comparative case study.",
        "Field-wide construct novelty and causal comparative advantage remain unknown."],
      "open_research_needs":[
        "Read original Davies-Brady 2000, Prencipe-Tell 2001, Hargadon-Sutton 1997 and D'Adderio 2003 primary bodies and exact comparable sections.",
        "Disambiguate Carlile boundary-object transformation vs technical-method creation and separately qualified successor reuse.",
        "Define null rival at matched cost, retrospective vs prospective selection, and blind-coded M/H/U outcome categories.",
        "Execute authorized prospective empirical pilot and primary-competitor triangulation before field-novelty claim."],
      "negative_boundary_findings":[
        "Neither a new team, a new tool, a transferred artefact nor pragmatic transformation is enough on its own to establish C04 novelty.",
        "Even physical five-source reading does not establish full literature saturation or actual empirical causal effect."],
    }
    source_root=str(whitecrow_root.resolve())
    if source_root not in sys.path:sys.path.insert(0,source_root)
    mod=importlib.import_module("fieldcore.academic_due_diligence")
    if Path(mod.__file__).resolve()!=whitecrow_root.resolve()/"fieldcore"/"academic_due_diligence.py":
        raise EvidenceBlocked("d15_wave2_untrusted_whitecrow_import")
    report=mod.build_disciplinary_positioning_report(
        data,semantic_action_mode="CRITIQUE",
        trigger_ref="T3_F4_D15_CARLILE_WAVE2_FIVE_REAL_PRIMARY_ORIGINALS")
    if (report["read_bodies"]!=read
        or len(report["primary_passages"])!=len(anchors)
        or report["coverage_status"]=="HIGH"
        or report["research_readiness"]!="BLOCKED_ON_DUE_DILIGENCE"
        or report["semantic_action_mode"]!="CRITIQUE"
        or report["nearest_precedent_grounded"] is not True
        or report["strongest_known_objection_grounded"] is not True):
        raise EvidenceBlocked("d15_wave2_whitecrow_science_upgrade_not_justified")
    out.mkdir(parents=True,exist_ok=True)
    rsha=_emit_unique(out/"whitecrow_d24_after_five_primary_reads.json",report)
    asha=_emit_unique(out/"wave2_quote_anchor_ledger_private.json",{"anchors":ledger})
    receipt={
      "schema":SCHEMA,"whitecrow_source_commit":WHITE_COMMIT,
      "whitecrow_source_module_sha256":WHITE_SHA,
      "five_read_bodies":read,"verified_primary_passages":len(anchors),
      "new_source_proofs":newmeta,
      "prior_source_readback_receipt_sha256":OLD_RECEIPT_SHA,
      "whitecrow_source_report_sha256":rsha,
      "wave2_private_quote_ledger_sha256":asha,
      "coverage_status":report["coverage_status"],
      "research_readiness":report["research_readiness"],
      "manuscript_sha256":MANUSCRIPT_SHA,
      "field_novelty_accepted":False,"field_saturation_accepted":False,
      "new_indago_hunts":0,"new_artikl_rewrites":0,
      "author_gate":"HOLD","d25_manuscript_go":False,
      "send":False,"world_mutation":False}
    _emit_unique(out/"wave2_real_whitecrow_readback_receipt.json",receipt)
    return receipt

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True,type=Path)
    ap.add_argument("--manifest-sha",required=True)
    ap.add_argument("--out",required=True,type=Path)
    opts=ap.parse_args()
    try:
        result=run(manifest_path=opts.manifest,manifest_sha=opts.manifest_sha,
          whitecrow_root=Path(r"C:\projects\whitecrow-antonova-direct-20261019"),
          out=opts.out)
        print(json.dumps(result,ensure_ascii=False))
    except (EvidenceBlocked,ValueError,KeyError,OSError,AssertionError) as e:
        print(json.dumps({"status":"HOLD","reason":str(e)[:180],
             "d25_manuscript_go":False,"send":False,
             "world_mutation":False},ensure_ascii=False))
        raise SystemExit(2)
