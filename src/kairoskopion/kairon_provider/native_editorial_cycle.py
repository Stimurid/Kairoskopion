"""Trimurti Factory: existing native ARTIKL chooses -> writes -> independent review.

This is a thin editorial lane of manuscript_cycle_runner, not another research
engine or journal system. Uses already completed real F241 EvidenceReturn,
current v0.5 + M116 and the existing native draft intake. Preserves author HOLD.
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
from .manuscript_draft_intake import ingest

SCHEMA="trimurti-native-artikl-editorial-cycle-v1"

def read(path:Path)->dict:
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict):raise EvidenceBlocked("json_object_required:"+path.name)
    return data

def readsha(path:Path,expected:str)->bytes:
    b=path.read_bytes()
    if sha256(b)!=expected:raise EvidenceBlocked("source_digest_changed:"+path.name)
    return b

def save(path:Path,b:bytes)->None:
    if path.exists():
        if path.read_bytes()!=b:raise EvidenceBlocked("existing_stage_bytes_conflict:"+path.name)
    else:atomic_write(path,b)

def emit(path:Path,obj:dict)->str:
    b=(json.dumps(obj,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    save(path,b)
    return sha256(b)

def cli_app(name:str)->str:
    executable=shutil.which(name+".cmd") or shutil.which(name)
    if not executable:raise EvidenceBlocked("required_model_cli_not_installed:"+name)
    return executable

def parse_gateway(blob:bytes)->dict:
    try:
        try:outer=json.loads(blob.decode("utf-8-sig"))
        except (UnicodeError,ValueError):outer=json.loads(blob.decode("utf-16"))
        if outer.get("status")!="ok":raise EvidenceBlocked("registered_artikl_gateway_failed")
        text=(outer["result"]["payloads"][0]["text"]).strip()
        return json.loads(text)
    except (KeyError,ValueError,IndexError,TypeError) as e:
        raise EvidenceBlocked("registered_artikl_response_not_exact_JSON") from e

def native_call(root:Path,stage:str,prompt:str,timeout:int=330)->dict:
    # One real native call per stage; a failed started stage is never silently
    # retried at another token cost.
    data=root/(stage+".gateway.json")
    begun=root/(stage+".started")
    if not data.exists():
        if begun.exists():raise EvidenceBlocked("unreceipted_native_model_call:"+stage)
        save(root/(stage+".prompt.txt"),prompt.encode("utf-8"))
        session=str(uuid.uuid5(uuid.NAMESPACE_URL,sha256(prompt.encode("utf-8"))))
        save(begun,("NATIVE_ARTIKL_CALL "+session+"\n").encode("ascii"))
        try:
            cp=subprocess.run([cli_app("openclaw"),"agent","--agent","artikl",
                  "--json","--session-id",session,"--timeout",str(timeout),
                  "--message-file",str(root/(stage+".prompt.txt"))],
                  capture_output=True,timeout=timeout+80,check=False)
        except subprocess.TimeoutExpired as e:
            raise EvidenceBlocked("native_artikl_timeout_stage:"+stage) from e
        save(root/(stage+".stderr"),cp.stderr)
        save(data,cp.stdout)
        if cp.returncode:
            raise EvidenceBlocked("native_artikl_exit_"+stage+"_"+str(cp.returncode))
    val=parse_gateway(data.read_bytes())
    return val

def _native_stage_attestation(root:Path,stage:str)->dict:
    b=(root/(stage+".gateway.json")).read_bytes()
    try:outer=json.loads(b.decode("utf-8-sig"))
    except (ValueError,UnicodeError):outer=json.loads(b.decode("utf-16"))
    meta=((outer.get("result") or {}).get("meta") or {})
    return {"agent":"artikl","gateway_run_id":outer.get("runId"),
            "gateway_sha256":sha256(b),"tool_summary":meta.get("toolSummary"),
            "native_call_started":(root/(stage+".started")).is_file()}

def preflight(m:dict)->dict:
    if m.get("schema")!=SCHEMA or m.get("case_id")!="T3-TALK-20261019":
        raise EvidenceBlocked("native_editorial_manifest_invalid")
    if m.get("author_gate")!="HOLD" or m.get("send") is not False or m.get("world_mutation") is not False:
        raise EvidenceBlocked("editorial_owner_state_invalid")
    files={}
    for tag in ("source","baseline","review","science","whitecrow"):
        row=m.get(tag) or {}
        path=Path(row.get("path") or "")
        want=row.get("sha256") or ""
        if not re.fullmatch(r"[0-9a-f]{64}",want):
            raise EvidenceBlocked("invalid_source_pin:"+tag)
        files[tag]={"path":path,"sha256":want,"content":readsha(path,want)}
    base=files["baseline"];rv=read(files["review"]["path"]);science=read(files["science"]["path"])
    if base["sha256"]!="0a1cbd31fd5c53b062bd019e382e3a14e9f16ef671318147400d4adbe6fbb34e":
        raise EvidenceBlocked("unexpected_current_C04_baseline")
    if rv.get("candidate_sha256")!=base["sha256"] or rv.get("final_verdict")!="REVISION_REQUIRED":
        raise EvidenceBlocked("review_baseline_not_current")
    if (science.get("author_gate")!="HOLD" or science.get("external_send") is not False
        or science.get("original_source_sha256")!=files["source"]["sha256"]):
        raise EvidenceBlocked("science_source_parent_conflict")
    source_root=Path(m.get("artikl_source_root") or "")
    for name in ("ENTRY_MANIFEST.md","RELEASE_MANIFEST.md","BASE_COLD_REENTER.md",
                 "GATEWAY.md","LIVE_CORE.md","CAPABILITY_REGISTRY.md"):
        p=source_root/name
        if not p.is_file() or p.stat().st_size<900:raise EvidenceBlocked("canonical_artikl_body_missing:"+name)
    entry=(source_root/"ENTRY_MANIFEST.md").read_text(encoding="utf-8-sig")
    release=(source_root/"RELEASE_MANIFEST.md").read_text(encoding="utf-8-sig")
    if "CURRENT_RELEASE = ARTIKL 1.0.0-rc9" not in entry or "ARTIKL 1.0.0-rc9" not in release:
        raise EvidenceBlocked("stale_artikl_release")
    return files

def _decision_prompt(m:dict,f:dict)->str:
    return (
       "TRIMURTI / ARTIKL 1.0.0-rc9. You are the registered ARTIKL editorial organ. "
       "This is a NEW decision, not replay of the previously pre-conditioned F241 verdict. "
       "Read current six SOURCE_ARTIKL files in working order from "+m["artikl_source_root"]+". "
       "Read COMPLETE C04 manuscript "+str(f["baseline"]["path"])+" SHA "+f["baseline"]["sha256"]+". "
       "Read COMPLETE independent M116 review "+str(f["review"]["path"])+" SHA "+f["review"]["sha256"]+". "
       "Read science packet "+str(f["science"]["path"])+" and original author source "+str(f["source"]["path"])+". "
       "Read latest WhiteCrow return "+str(f["whitecrow"]["path"])+" only as evidence/scope information, "
       "not as a gate granting permission to write. Already collected full PDF source carriers "
       "are retained in the case's F241 owner-private folder; do not launch a new hunt. "
       "You independently choose the next EDITORIAL operation for this working paper: "
       "REVISION_CANDIDATE (rewrite now as a fully provisional working manuscript, "
       "keeping unresolved evidence tagged), MORE_RESEARCH (do not write until a specified "
       "unresolved question), or PARK (stop for a substantive reason). "
       "No external source-depth field authorizes or forbids a working manuscript. "
       "The review names concrete defects (organogenesis circularity/time zero, W mixed axes, "
       "evidence taxonomy, time-varying design, composite Y and strongest prior rivals); "
       "you may repair conceptual/methodological exposition without fabricating data. "
       "Preserve five named strong conceptual nuclei from M116, not empty risk prose. "
       "You may describe provisional designs as designs, not established empirical results. "
       "Choose freely and give content reasons, do not obey any expectation that the positive "
       "choice must pass. Do not write, send, launch tools beyond reading, or change WORLD yet. "
       "Output JSON only: {\"schema\":\"trimurti-artikl-editorial-decision-v1\","
       "\"agent_id\":\"artikl\",\"current_release\":\"ARTIKL 1.0.0-rc9\","
       "\"baseline_sha256\":\""+f["baseline"]["sha256"]+"\","
       "\"independent_review_sha256\":\""+f["review"]["sha256"]+"\","
       "\"decision\":\"REVISION_CANDIDATE|MORE_RESEARCH|PARK\","
       "\"reason\":\"substantive\", \"planned_changes\":[\"...\"],"
       "\"open_research_questions\":[\"...\"],\"author_gate\":\"HOLD\","
       "\"send\":false,\"world_mutation\":false,\"d25_manuscript_go\":false}."
    )

def _write_prompt(m:dict,f:dict,choice:dict,target:Path)->str:
    return (
      "TRIMURTI ARTIKL rc9 / ACTUAL FULL MANUSCRIPT EDITORIAL REWRITE. "
      "You have already independently selected REVISION_CANDIDATE in the exact "
      "decision "+str(target.parent/"decision.gateway.json")+". "
      "Read the entire manuscript "+str(f["baseline"]["path"])+" and M116 review "
      +str(f["review"]["path"])+"; read the original owner source "+str(f["source"]["path"])+
      ", the independent science packet "+str(f["science"]["path"])+
      " and selected primary pages already held in owner-private F241/source_bytes "
      " if substantively needed. The original v0.5 is approximately 3512 words. "
      "Produce a COMPLETE new, substantive Russian scholarly working manuscript, at "
      "least 3100 words, with all existing scientific sections, no ellipses, no summary "
      "in place of text, source attribution and five protected conceptual nuclei intact. "
      "Do REAL repairs of M116: ex ante organ eligibility vs time varying realization vs ex "
      "post success; disaggregate W (authority/terms/remedies/enforceability) without "
      "pseudo-ordinal monotonicity; separate evidence source/independence/directness/"
      "reproducibility; coherent prospective time-zero/time-varying risk sets; primary Y "
      "and its technical/time/acceptance decomposition. Nearest rivals: contractor surety, "
      "project commissioning, temporary organizing, process validation; distinguish named "
      "full-text read versus open research questions. Keep a strong, generative, compelling "
      "organogenesis hypothesis, not a compliance disclaimer essay. Do not invent data, "
      "empirical improvements, references or quotes. "
      "Use tool execution to write UTF-8 Markdown EXACTLY to this private destination: "
      +str(target)+". Do not write outside this single output file, and NEVER change "
      "existing source/manuscript files, Git, WORLD, or Google Drive. "
      "Write once, then read back the file and compute its SHA256. "
      "Return JSON only with schema trimurti-artikl-native-writer-v1, "
      "file_path, sha256, approximate_words, sections_written, critical_repairs, "
      "remaining_science_debt, author_gate:HOLD, send:false. "
      "Your response alone is not the manuscript: the actual on-disk full file is required."
    )

def _independent_review(root:Path,manifest:dict,f:dict,draft:Path)->dict:
    target=root/"review.json"
    if target.exists():return read(target)
    begun=root/"review.started"
    if begun.exists():raise EvidenceBlocked("unreceipted_independent_review")
    instructions=(
      "INDEPENDENT FULL-TEXT MANUSCRIPT REVIEW, read only. The original C04 v0.5 is "+
      str(f["baseline"]["path"])+", the NEW complete draft is "+str(draft)+
      " SHA256 "+sha256(draft.read_bytes())+" and original M116 critique is "+
      str(f["review"]["path"])+". Read all THREE files COMPLETELY. "
      "Check actual M116 six defects, preserve conceptual core, source accuracy, "
      "modeling clarity, W and evidence axes, time zero, Y, nearest competitors. "
      "Report anchored before/after fixes ONLY when literally present, including "
      "candidate line numbers/short exact quotes. No fake empirical science. "
      "Return ONLY JSON with schema trimurti-independent-C04-rewrite-review-v1; "
      "draft_sha256:"+sha256(draft.read_bytes())+
      "; reviewer:CODEX_DISTINCT_PROCESS; verdict:REVISION_REQUIRED|SCOPED_PASS|PARK; "
      "issues:list of {kind,line,literal_quote,explanation,action}; "
      "six_M116_items:list of {issue,status,delta}; "
      "protected_core_status:list; next_action; author_gate:HOLD; send:false."
    )
    save(root/"review.prompt.txt",instructions.encode("utf-8"))
    save(begun,b"ONE_CODEX_INDEPENDENT_REVIEW\n")
    cmd=[cli_app("codex"),"exec","-C",str(Path(manifest["scientific_repo"])),
         "--sandbox","read-only","-o",str(target),"-"]
    try:
        cp=subprocess.run(cmd,input=instructions,encoding="utf-8",errors="replace",
                 capture_output=True,cwd=Path(manifest["scientific_repo"]),timeout=600,check=False,
                 env={**os.environ,"PYTHONUTF8":"1","PYTHONIOENCODING":"utf-8"})
    except subprocess.TimeoutExpired as e:
        raise EvidenceBlocked("reviewer_timeout_no_retry") from e
    save(root/"review.stdout.log",cp.stdout.encode("utf-8"))
    save(root/"review.stderr.log",cp.stderr.encode("utf-8"))
    if cp.returncode or not target.is_file():raise EvidenceBlocked("independent_reviewer_no_accepted_file")
    return read(target)

def _verify_review(review:dict,draft:Path)->None:
    if review.get("schema")!="trimurti-independent-C04-rewrite-review-v1" or review.get("draft_sha256")!=sha256(draft.read_bytes()):
        raise EvidenceBlocked("independent_review_wrong_draft")
    lines=draft.read_text(encoding="utf-8").splitlines()
    items=review.get("issues") or []
    if not isinstance(items,list):raise EvidenceBlocked("review_issues_malformed")
    for issue in items:
        line=issue.get("line")
        quote=issue.get("literal_quote","")
        if not isinstance(line,int) or not 1<=line<=len(lines) or not quote or quote not in lines[line-1]:
            raise EvidenceBlocked("review_unverified_exact_line_quote")
    if review.get("send") is not False or review.get("author_gate")!="HOLD":
        raise EvidenceBlocked("review_false_author_acceptance")

def run(manifest:Path,expected_manifest_sha:str,root:Path)->dict:
    readsha(manifest,expected_manifest_sha)
    m=read(manifest)
    f=preflight(m)
    root.mkdir(parents=True,exist_ok=True)
    state=root/"editorial_cycle_receipt.json"
    if state.exists():
        saved=read(state)
        if saved.get("manifest_sha256")!=expected_manifest_sha or saved.get("author_gate")!="HOLD":
            raise EvidenceBlocked("previous_cycle_identity_conflict")
        if saved.get("candidate_sha256"):
            expected=saved["candidate_sha256"]
            if sha256((root/"draft_v0_6.md").read_bytes())!=expected:raise EvidenceBlocked("saved_manuscript_changed")
        return {**saved,"replay":"IDENTICAL_NO_NEW_MODEL_CALLS"}
    lock=root/"editorial_cycle.lock"
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise EvidenceBlocked("same_cycle_already_running_or_interrupted")
    try:
        with os.fdopen(fd,"w") as fh:fh.write("RUNNING\n")
        choice=native_call(root,"decision",_decision_prompt(m,f))
        if (choice.get("schema")!="trimurti-artikl-editorial-decision-v1"
          or choice.get("decision") not in ("REVISION_CANDIDATE","MORE_RESEARCH","PARK")
          or choice.get("baseline_sha256")!=f["baseline"]["sha256"]
          or choice.get("independent_review_sha256")!=f["review"]["sha256"]
          or choice.get("agent_id")!="artikl"
          or choice.get("author_gate")!="HOLD" or choice.get("send") is not False):
            raise EvidenceBlocked("native_artikl_editorial_choice_invalid")
        emit(root/"decision.json",choice)
        if choice["decision"]!="REVISION_CANDIDATE":
            out={"schema":SCHEMA,"status":"EDITORIAL_"+choice["decision"],
                 "manifest_sha256":expected_manifest_sha,"decision":choice["decision"],
                 "decision_gateway_sha256":sha256((root/"decision.gateway.json").read_bytes()),
                 "new_research_requests":0,"new_native_hunts":0,"new_w12_routes":0,
                 "author_gate":"HOLD","send":False,"world_mutation":False}
            emit(state,out);return out
        target=root/"draft_v0_6.md"
        writer=native_call(root,"writer",_write_prompt(m,f,choice,target),timeout=480)
        if not target.is_file():raise EvidenceBlocked("native_artikl_did_not_write_full_manuscript")
        bytes_=target.read_bytes()
        text=bytes_.decode("utf-8")
        if (len(text.split())<3100 or len(text.split())>10500 or text.count("\n## ")<7
            or len(text)<20000 or not text.startswith("# ")):
            raise EvidenceBlocked("native_artikl_output_not_complete_manuscript")
        if writer.get("sha256")!=sha256(bytes_) or writer.get("author_gate")!="HOLD":
            raise EvidenceBlocked("native_artikl_writer_draft_digest_invalid")
        # Reuse native Factory intake on original author source and pinned
        # existing science, without promoting it to a scientific finding.
        intake_inputs=root/"draft_intake_inputs"
        intake_inputs.mkdir(exist_ok=True)
        for tag,body in (("source",f["source"]["content"]),("science",f["science"]["content"]),("draft",bytes_)):
            save(intake_inputs/(tag+".txt"),body)
        entries={k:{"path":k+".txt","sha256":sha256((intake_inputs/(k+".txt")).read_bytes())} for k in ("source","science","draft")}
        import_manifest={
            "schema":"trimurti-manuscript-draft-intake-v1",
            "evidence_mode":"REAL","case_id":m["case_id"],
            "claim_id":"KC-C04-GUARMEAS-JIBE-CRESTI",
            "route_id":"C-GUARMEAS-JIBE-CRESTI",
            "producer_ref":"NATIVE_ARTIKL_1.0.0_RC9_EDITORIAL_WRITER",
            "author_gate":"HOLD","submission_enabled":False,
            "scientific_novelty_accepted":False,"article_seed_author_approved":False,
            "source_original_sha256":f["source"]["sha256"],
            "artifacts":entries
        }
        emit(intake_inputs/"intake_manifest.json",import_manifest)
        intake=ingest(manifest_path=intake_inputs/"intake_manifest.json",
            input_root=intake_inputs,output_root=root/"native_factory_intake",
            trusted_source_sha256=f["source"]["sha256"],
            trusted_science_sha256=f["science"]["sha256"])
        review=_independent_review(root,m,f,target)
        _verify_review(review,target)
        # No automatic second rewrite, no imposed source-depth veto.
        out={"schema":SCHEMA,"status":"FULL_DRAFT_AND_INDEPENDENT_REVIEW_CAPTURED_AUTHOR_HOLD",
            "manifest_sha256":expected_manifest_sha,"source_sha256":f["source"]["sha256"],
            "baseline_sha256":f["baseline"]["sha256"],"M116_sha256":f["review"]["sha256"],
            "science_sha256":f["science"]["sha256"],
            "decision":"REVISION_CANDIDATE",
            "decision_gateway_sha256":sha256((root/"decision.gateway.json").read_bytes()),
            "writer_gateway_sha256":sha256((root/"writer.gateway.json").read_bytes()),
            "draft_path":str(target),"candidate_sha256":sha256(bytes_),
            "draft_words":len(text.split()),
            "intake_sha256":sha256((root/"native_factory_intake/draft-intake-receipt.json").read_bytes()),
            "independent_review_sha256":sha256((root/"review.json").read_bytes()),
            "independent_review_verdict":review.get("verdict"),
            "D27_canonical_mounted":False,
            "source_reread":True,"author_gate":"HOLD","send":False,
            "world_mutation":False,"new_w12_routes":0,"new_indago_hunts":0,
            "publication_ready":False}
        emit(state,out)
        return out
    finally:
        lock.unlink(missing_ok=True)

def main(argv:list[str]|None=None)->int:
    a=argparse.ArgumentParser(prog="manuscript_cycle_runner editorial")
    a.add_argument("--manifest",required=True,type=Path)
    a.add_argument("--expected-manifest-sha",required=True)
    a.add_argument("--output-root",required=True,type=Path)
    opts=a.parse_args(argv)
    try:output=run(opts.manifest,opts.expected_manifest_sha,opts.output_root)
    except (OSError,ValueError,KeyError,EvidenceBlocked,subprocess.TimeoutExpired) as e:
        print(json.dumps({"status":"HOLD_RUNTIME_OR_EDITORIAL","reason":str(e)[:280],
                  "author_gate":"HOLD","send":False,"new_w12_routes":0},ensure_ascii=False));return 2
    print(json.dumps(output,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
