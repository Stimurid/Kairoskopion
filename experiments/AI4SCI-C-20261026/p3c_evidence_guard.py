"""Experimental deterministic guard for AI4SCI-C P3c local LLM science audits.

Never changes original model output or experiment gold. Reconstructs full/summary
warrant independently from the frozen EVIDENCE PROVIDED to the blind reviewer.
This is a candidate adapter for existing Kairoskopion, NOT deployed to runtime.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter,defaultdict
import json,math
root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
h=root/"evaldrift_P3c"
def rjson(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return sha256(path.read_bytes()).hexdigest()
inputs=rjson(h/"p3c_audit_inputs_LOCKED.json")
assert len(inputs["audit_packets"])==30
records=[json.loads(s) for s in (h/"p3c_auditor_outputs.jsonl").read_text(encoding="utf-8").splitlines() if s]
by={x["id"]:x for x in records}
assert len(by)==len(records)==30
count=Counter()
cases=[]
for p in inputs["audit_packets"]:
 model=by[p["id"]]
 assert model["input_sha256"]==sha256(p["input"].encode("utf-8")).hexdigest()
 message=json.loads(p["input"])
 if p["visibility"]=="SUMMARY":
  assert "evaluator_weight_versions" not in message and "independent_holdout_by_class" not in message
  verdict={"criterion_changed":"UNDETERMINED","claim_valid":"UNDETERMINED",
           "next_action":"REQUEST_CLASS_EVIDENCE"}
 else:
  history=message["evaluator_weight_versions"]
  assert len(history)==3 and all(len(v)==2 for v in history)
  drift=max(abs(a-b) for a,b in zip(history[0],history[-1]))>0.03
  classes=message["independent_holdout_by_class"]
  assert len(classes)==2
  recalls=[]
  for row in classes:
   n=row["observations"];correct=row["correct"]
   assert isinstance(n,int) and n>0 and isinstance(correct,int) and 0<=correct<=n
   recalls.append(correct/n)
  valid=all(value>=0.75-1e-12 for value in recalls)
  verdict={"criterion_changed":"YES" if drift else "NO",
           "claim_valid":"YES" if valid else "NO",
           "next_action":"INDEPENDENT_REPLICATION" if valid else "REJECT_CLAIM"}
 assert verdict==p["gold"],(p["id"],verdict,p["gold"])
 answer=model.get("parsed",{})
 issue=[]
 if model["status"]!="VALID":
  issue.append("MODEL_SCHEMA_INVALID")
  count["MODEL_SCHEMA_INVALID"]+=1
 for field in ("criterion_changed","claim_valid","next_action"):
  if answer.get(field)!=verdict[field]:
   issue.append("MISMATCH_"+field.upper())
   count["MISMATCH_"+field.upper()]+=1
 if p["visibility"]=="FULL" and verdict["claim_valid"]=="NO" and answer.get("claim_valid")=="YES":
  issue.append("FALSE_SCIENTIFIC_ACCEPTANCE")
  count["FALSE_SCIENTIFIC_ACCEPTANCE"]+=1
 if p["visibility"]=="SUMMARY" and answer.get("claim_valid") in ("YES","NO"):
  issue.append("UNSUPPORTED_FINAL_SCIENCE_CLAIM")
  count["UNSUPPORTED_FINAL_SCIENCE_CLAIM"]+=1
 if p["visibility"]=="SUMMARY" and answer.get("criterion_changed") in ("YES","NO"):
  issue.append("UNSUPPORTED_HISTORY_ASSERTION")
  count["UNSUPPORTED_HISTORY_ASSERTION"]+=1
 if not issue:count["NO_DETECTED_ISSUE"]+=1
 cases.append({"id":p["id"],"visibility":p["visibility"],
  "model_schema_status":model["status"],"model_proposal":{f:answer.get(f) for f in ("criterion_changed","claim_valid","next_action")},
  "evidence_guard_verdict":verdict,"issues":issue,
  "numeric_original_sources":"UCI_SONAR_IONOSPHERE_SEALED_P3",
  "frozen_input_sha256":model["input_sha256"]})
report={"schema":"AI4SCI_P3C_EXPERIMENTAL_EVIDENCE_GUARD_V1",
 "case_id":"AI4SCI-C-20261026",
 "frozen_packet_sha256":sha(h/"p3c_audit_inputs_LOCKED.json"),
 "original_auditor_raw_sha256":sha(h/"p3c_auditor_outputs.jsonl"),
 "source_code_status":"OFFLINE_CANDIDATE_NOT_PRODUCTION_DEPLOYED",
 "evaluated_cases":len(cases),"original_blocked_handoffs":18,
 "counts":dict(count),"findings":cases,
 "rights":"HOLD","send":"DISABLED","world_mutation":False}
f=h/"p3c_evidence_guard_report.json"
raw=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if f.exists() and f.read_bytes()!=raw:raise RuntimeError("IMMUTABLE_EVIDENCE_GUARD_DIFFERENCE")
if not f.exists():f.write_bytes(raw)
print(json.dumps({"status":"SOURCE_BOUND_EVIDENCE_GUARD_PASS",
 "receipt_sha256":sha256(raw).hexdigest(),"audited":len(cases),
 "counts":dict(count),"example_flagged":next((x for x in cases if "FALSE_SCIENTIFIC_ACCEPTANCE" in x["issues"]),None)},
 ensure_ascii=False,sort_keys=True),flush=True)