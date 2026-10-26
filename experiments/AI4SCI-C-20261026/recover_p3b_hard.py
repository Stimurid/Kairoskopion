"""POSTHOC P3b recovery: preserve original 5/8 result, repair source class-count bug
in a separate script and conduct development-only new Qwen calls on 3 failed cases.
No original P3 frozen file, model attempts, original raw data or holdout overwritten.
"""
from pathlib import Path
import importlib.util,json
from hashlib import sha256
root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
code=root/"run_evaldrift_p3_hard.py"
spec=importlib.util.spec_from_file_location("p3_frozen",code)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
locked=m.verify_script()
out=m.OUT
original_path=out/"generator_raw.jsonl"
original_sha="63b2d8e04ff9585d85cbed00377ea64042724d2bf6ff3d5b57e135ee5e741aaf"
assert m.hashb(original_path.read_bytes())==original_sha
cases=m.readjson(out/"design.json")["cases"]
assert len(cases)==8
allrows=m.readlog(original_path)
assert len(allrows)==16
by={}
for x in allrows:
 by.setdefault((x["case_id"],x["revision"]),[]).append(x)
blocked=("SONAR-41","SONAR-73","IONOSPHERE-73")
assert all(len(by[(t,1)])==2 and all(x["status"]=="INVALID_JSON_OR_WEIGHT_POLICY" for x in by[(t,1)]) for t in blocked)
def scripted(case):
 first=m.version_state(case["models"],[0.5,0.5])
 selected=next(x for x in case["models"] if x["name"]==first["model"])
 focus=max(range(2),key=lambda i:(selected["dev"]["recall"][i],-i))
 h=[first]
 for focusw in [0.75,0.85]:
  w=[1-focusw,1-focusw];w[focus]=focusw
  h.append(m.version_state(case["models"],w))
 return h
allowed=[0.25,0.35,0.45,0.55,0.65,0.75]
sysmsg="You are updating a 2-class evaluator. Return ONLY JSON with two weights. The first weight MUST be chosen from 0.25, 0.35, 0.45, 0.55, 0.65, 0.75 and second MUST be exactly its complement to sum 1. This is a scoring priority, NOT the observed recall numbers. NO prose, no explanation, no additional fields."
extra_path=out/"p3b_extra_generator.jsonl"
existing=m.readlog(extra_path)
index={(x["case_id"],x["revision"]):x for x in existing}
assert len(existing)==len(index),"NO_DUPLICATE_EXTRA_CALLS"
new_count=0
for case in cases:
 if case["case_id"] not in blocked:continue
 current=[0.5,0.5]
 previous=m.select(case["models"],current)
 for rev in (1,2):
  key=(case["case_id"],rev)
  old=index.get(key)
  if old is None:
   prompt=json.dumps({
    "dataset":case["dataset"],"case_id":case["case_id"],"version":rev,
    "scientific_goal":case["original_scientific_goal"],
    "current_weights":current,"previous_candidate":previous,
    "dev_class_recall_by_candidate":[{"candidate":x["name"],"two_class_recall":x["dev"]["recall"]} for x in case["models"]],
    "required_output":"JSON {weights:[w,1-w]} where w is one of 0.25,0.35,0.45,0.55,0.65,0.75; no rationale, never return recall values as weights."
    },ensure_ascii=False,sort_keys=True)
   try:
    response=m.send_chat("qwen3.5:9b",sysmsg,prompt,max_tokens=120)
    obj=json.loads(response["raw"])
    ww=obj.get("weights")
    if isinstance(ww,list) and len(ww)==2:
     vals=[float(z) for z in ww]
     mathematically_valid=all(abs(vals[0]-v)<1e-5 for v in allowed) and abs(vals[0]+vals[1]-1)<1e-5
     parsed=m.parse_proposal(response["raw"]) if mathematically_valid else None
    else:parsed=None
    status="VALID_NEW_P3B_WEIGHT_POLICY" if parsed else "INVALID_NEW_P3B_POLICY"
    old={"case_id":case["case_id"],"revision":rev,"status":status,
      "raw":response["raw"],"raw_sha256":m.hashb(response["raw"].encode("utf-8")),
      "parsed":parsed,"model":response["model"],"tokens_generated":response["tokens_generated"],
      "prompt":prompt,"prompt_sha256":m.hashb(prompt.encode("utf-8"))}
   except Exception as exc:
    old={"case_id":case["case_id"],"revision":rev,"status":"P3B_CALL_ERROR",
       "error_type":type(exc).__name__,"error":str(exc)[:260]}
   m.append_jsonl(extra_path,old);index[key]=old;new_count+=1
  if old["status"]!="VALID_NEW_P3B_WEIGHT_POLICY":
   print("P3B_INCOMPLETE",case["case_id"],"revision",rev,"status",old["status"],flush=True)
   break
  current=old["parsed"]["weights"];previous=m.select(case["models"],current)
 print("P3B_SOURCE",case["case_id"],"completed_steps",sum(index.get((case["case_id"],rev),{}).get("status")=="VALID_NEW_P3B_WEIGHT_POLICY" for rev in (1,2)),flush=True)
records=[]
for case in cases:
 cur=[m.version_state(case["models"],[0.5,0.5])]
 provenance=[]
 state="COMPLETE"
 for rev in (1,2):
  valid=next((x for x in by.get((case["case_id"],rev),[]) if x["status"]=="VALID"),None)
  if valid:
   weights=valid["parsed"]["weights"]
   provenance.append({"revision":rev,"type":"ORIGINAL_P3_VALID_FULL_JSON",
        "raw_sha256":m.hashb(valid["raw"].encode("utf-8"))})
  else:
   repl=index.get((case["case_id"],rev))
   if not repl or repl["status"]!="VALID_NEW_P3B_WEIGHT_POLICY":
    state="BLOCKED";break
   weights=repl["parsed"]["weights"]
   provenance.append({"revision":rev,"type":"POSTHOC_NEW_P3B_MODEL_CALL",
     "raw_sha256":repl["raw_sha256"]})
  cur.append(m.version_state(case["models"],weights))
 rec={"case_id":case["case_id"],"status":state,
      "machine":cur if state=="COMPLETE" else None,
      "stable":[cur[0]]*3,"scripted":scripted(case),
      "revision_provenance":provenance,
      "source_status":"ORIGINAL_P3_VALID" if case["case_id"] not in blocked else "P3B_EXPLORATORY_REPAIR"}
 records.append(rec)
receipt={"schema":"AI4SCI_P3B_POSTHOC_REPAIR_RECEIPT_V1",
    "original_P3_generator_full_valid_task_cases":5,
    "original_P3_generator_blocked_task_cases":3,
    "original_P3_source_assembly_bug":"range(3) on two-class scripted evaluator; original code frozen",
    "original_P3_raw_generator_sha256":original_sha,
    "P3B_extra_model_calls_actual":len(index),
    "P3B_extra_calls_this_execution":new_count,
    "P3B_extra_log_sha256":m.hashb(extra_path.read_bytes()),
    "P3B_scoring_rule":"fixed prereg H: first .75/.25, then .85/.15 favor the easier dev class",
    "cases":records,
    "source_design_sha256":locked["design_sha256"],
    "old_source_script_sha256":locked["script_sha256"],
    "posthoc_exploratory":True,
    "author":"HOLD","world_write":False,"send":"DISABLED"}
sha=m.lockwrite(out/"p3b_recovery_receipt.json",receipt)
complete=sum(x["status"]=="COMPLETE" for x in records)
if complete<8:
 print(json.dumps({"status":"P3B_PARTIAL","complete":complete,
    "original_P3":5,"extra_model_calls":len(index),"receipt_sha256":sha},
   ensure_ascii=False,sort_keys=True));raise SystemExit(2)
policy={"schema":"AI4SCI_P3_EVALUATOR_POLICY_FREEZE_V1",
 "design_sha256":locked["design_sha256"],"generator":"qwen3.5:9b",
 "cases":records,"raw_generator_sha256":original_sha,
 "P3B_recovery_receipt_sha256":sha,"posthoc_exploratory":True,
 "author":"HOLD","send":"DISABLED"}
polsha=m.lockwrite(out/"policies_frozen.json",policy)
flip_count=0
changed=0
for c in records:
 if any(abs(a-b)>0.03 for a,b in zip(c["machine"][0]["weights"],c["machine"][-1]["weights"])):changed+=1
 if c["machine"][-1]["model"]!=c["stable"][-1]["model"] or c["machine"][-1]["model"]!=c["scripted"][-1]["model"]:flip_count+=1
print(json.dumps({"status":"P3B_EXPLORATORY_POLICIES_FROZEN",
 "original_P3_full_schema_complete":5,"P3B_complete":complete,
 "P3B_extra_calls":len(index),"recovery_sha256":sha,"policy_sha256":polsha,
 "machine_weights_changed_cases":changed,"decision_flip_cases":flip_count,
 "blind_audit_target":48},ensure_ascii=False,sort_keys=True,indent=2))