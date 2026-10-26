"""P2b post-hoc numeric-only recovery of preexisting Qwen proposals.
NEVER edits original P2 raw model log or frozen script/data.
Only 1 extra dev-only proposal for WINE-41 revision 2, if needed.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import importlib.util,json,re,math
base=Path(__file__).resolve().parent
src=base/"run_evaldrift_p2_uci.py"
spec=importlib.util.spec_from_file_location("p2_frozen",src)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
lk=m.verify_script()
out=m.OUT
orig=m.readlog(out/"generator_raw.jsonl")
expected_orig="d937a52256f21eb7612b725477b60d39991512a4464dcab88b5f60d0b0ec4238"
assert m.hashb((out/"generator_raw.jsonl").read_bytes())==expected_orig
design=m.readjson(out/"design.json")
events={}
for x in orig:
    events.setdefault((x["case_id"],x["revision"]),[]).append(x)
assert len(design["cases"])==8
assert len(orig)==18
stage_failures=[("IRIS-29",2),("WINE-41",1),("WINE-73",2)]
assert all(len(events[(name,rev)])==2 for name,rev in stage_failures)
def numeric_recovery(name,rev):
    rows=events[(name,rev)]
    weights=[]
    per_attempt=[]
    for row in rows:
        assert row["status"]=="INVALID_JSON_OR_WEIGHT_POLICY",row
        assert row.get("tokens_generated")==420
        raw=row["raw"]
        match=re.search(r'"weights"\s*:\s*(\[[^\]]+\])',raw)
        if not match:raise RuntimeError("NO_COMPLETE_NUMERIC_FIELD:"+name)
        a=json.loads(match.group(1))
        parsed=m.parse_proposal(json.dumps({"weights":a}))
        if parsed is None:raise RuntimeError("INVALID_WEIGHT_ARRAY:"+name)
        weights.append(parsed["weights"])
        per_attempt.append({"attempt":row["attempt"],
            "raw_sha256":m.hashb(raw.encode("utf-8")),
            "tokens_generated":row["tokens_generated"],
            "numeric_field":parsed["weights"],
            "full_json_status":row["status"]})
    if weights[0]!=weights[1]:
        raise RuntimeError("DISAGREEMENT_BETWEEN_FAILED_TRIES:"+name)
    return {"case_id":name,"revision":rev,
        "state":"RECOVERED_NUMERIC_FROM_TRUNCATED_RAW_JSON_NOT_FULL_SCHEMA_SUCCESS",
        "weights":weights[0],"attempts":per_attempt,
        "rationale":"NOT_RECOVERED_TRUNCATED"}
recovered={(name,rev):numeric_recovery(name,rev) for name,rev in stage_failures}
extra_path=out/"p2b_extra_generator.jsonl"
extra=m.readlog(extra_path)
case41=next(c for c in design["cases"] if c["case_id"]=="WINE-41")
rev1=recovered[("WINE-41",1)]["weights"]
last=m.select(case41["models"],rev1)
request={
  "dataset":case41["dataset"],"case_id":case41["case_id"],
  "scientific_goal":case41["original_scientific_goal"],
  "current_revised_weights":rev1,"previous_selection":last,
  "dev_class_recalls":[{"name":x["name"],"recall":x["dev"]["recall"]} for x in case41["models"]],
  "instruction":"This is revision 2. Propose another class weighting from DEV evidence only, no holdout evidence. Return ONLY JSON with a weights array of 3 floats between 0.05 and 0.90 summing to 1. Do not add rationale or goal because the previous output failed due to 420-token truncation."}
prompt=json.dumps(request,ensure_ascii=False,sort_keys=True)
if not extra:
    try:
        ans=m.send_chat(m.GENERATOR,
          "You revise an evaluation weight vector. Only machine-readable JSON {\"weights\":[0.2,0.5,0.3]}; never claim access to held-out data.",
          prompt,max_tokens=120)
        parsed=m.parse_proposal(ans["raw"])
        row={"case_id":"WINE-41","revision":2,"attempt":0,
            "status":"VALID_P2B_NUMERIC_ONLY" if parsed else "P2B_NUMERIC_INVALID",
            "prompt":prompt,"prompt_sha256":m.hashb(prompt.encode("utf-8")),
            "model":ans["model"],"raw":ans["raw"],
            "raw_sha256":m.hashb(ans["raw"].encode("utf-8")),
            "parsed":parsed,"tokens_generated":ans["tokens_generated"],
            "tokens_prompt":ans["tokens_prompt"]}
    except Exception as e:
        row={"case_id":"WINE-41","revision":2,"attempt":0,"status":"P2B_CALL_FAILED",
         "error_type":type(e).__name__,"error":str(e)[:250]}
    m.append_jsonl(extra_path,row)
    extra=[row]
assert len(extra)==1, "P2B_ONE_EXTRA_CALL_ONLY"
if extra[0]["status"]!="VALID_P2B_NUMERIC_ONLY":
    print(json.dumps({"status":"P2B_BLOCKED","original_success_cases":5,
    "additional_model_status":extra[0]["status"]},ensure_ascii=False));raise SystemExit(2)
# All histories are now complete, but 3 input revisions remain NON-CONFIRMATORY recovered content.
records=[]
for c in design["cases"]:
    history=[m.version_state(c["models"],[1/3]*3)]
    origin=[]
    for rev in (1,2):
        val=next((x for x in events.get((c["case_id"],rev),[]) if x["status"]=="VALID"),None)
        if val is not None:
            weights=val["parsed"]["weights"]
            origin.append({"revision":rev,"state":"P2_ORIGINAL_VALID_FULL_JSON",
                "raw_sha256":m.hashb(val["raw"].encode("utf-8"))})
        elif (c["case_id"],rev) in recovered:
            obj=recovered[(c["case_id"],rev)]
            weights=obj["weights"]
            origin.append({"revision":rev,"state":obj["state"],
                "original_attempt_sha256":[x["raw_sha256"] for x in obj["attempts"]]})
        elif c["case_id"]=="WINE-41" and rev==2:
            weights=extra[0]["parsed"]["weights"]
            origin.append({"revision":rev,"state":"P2B_ONE_ADDITIONAL_GENERATOR_CALL",
                "raw_sha256":extra[0]["raw_sha256"]})
        else:
            raise RuntimeError("NON_RECOVERABLE_CASE:"+c["case_id"]+":"+str(rev))
        history.append(m.version_state(c["models"],weights))
    records.append({"case_id":c["case_id"],"status":"COMPLETE",
      "machine":history,"stable":[history[0],history[0],history[0]],
      "scripted":m.ordinary_revisions(c),"generation_source":origin,
      "scientific_status":"P2B_POSTHOC_NOT_CONFIRMATORY" if any(x["state"]!="P2_ORIGINAL_VALID_FULL_JSON" for x in origin) else "P2_ORIGINAL_VALID"})
assert len(records)==8
report={"schema":"AI4SCI_P2B_NUMERIC_RECOVERY_RECEIPT_V1",
    "original_P2_full_schema_successful_cases":5,
    "original_P2_full_schema_blocked_cases":3,
    "original_generator_raw_sha256":expected_orig,
    "recovery_policy":"POSTHOC_REGISTERED_BEFORE_AUDITOR",
    "additional_generator_call_count":1,
    "additional_generator_raw_sha256":m.hashb(extra_path.read_bytes()),
    "recoveries":list(recovered.values()),
    "old_lock_sha256":m.hashb((out/"lock.json").read_bytes()),
    "source_design_sha256":lk["design_sha256"],
    "policies_count":8,"all_three_conditions":["S","M","H"],
    "author_gate":"HOLD","send":"DISABLED"}
recover_sha=m.lockwrite(out/"p2b_recovery_receipt.json",report)
packet={"schema":"AI4SCI_P2_EVALUATOR_POLICY_FREEZE_V1",
    "design_sha256":lk["design_sha256"],"generator":m.GENERATOR,
    "cases":records,"raw_generator_sha256":expected_orig,
    "p2b_recovery_receipt_sha256":recover_sha,
    "posthoc_amendment":"https://docs.google.com/document/d/1fDne12VOGTc1l_OdByOuN3Gnvcm9KFAuYX5eWicHzQU/edit",
    "author":"HOLD","send":"DISABLED"}
policy_sha=m.lockwrite(out/"policies_frozen.json",packet)
machine_changed=sum(any(abs(a-b)>0.03 for a,b in zip(r["machine"][0]["weights"],r["machine"][-1]["weights"])) for r in records)
different=sum(r["machine"]!=r["scripted"] for r in records)
print(json.dumps({"status":"P2B_RECOVERED_ALL_8_EXPLORATORY",
    "original_P2_schema_pass":"5/8",
    "recovered_numeric_case_count":3,
    "extra_model_calls":1,
    "recovery_receipt_sha256":recover_sha,
    "policy_sha256":policy_sha,
    "machine_changed":machine_changed,
    "machine_H_nonidentical":different,
    "audit_possible_episodes":48},ensure_ascii=False,sort_keys=True,indent=2))