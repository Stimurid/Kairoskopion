"""Posthoc separate field-level review of INVALID whole-response schema.
NEVER reclassify original P3c 15 invalid FULL rows as valid, no new model calls.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter,defaultdict
import json
root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026\evaldrift_P3c")
design=json.loads((root/"p3c_audit_inputs_LOCKED.json").read_text(encoding="utf-8"))
rows=[json.loads(s) for s in (root/"p3c_auditor_outputs.jsonl").read_text(encoding="utf-8").splitlines() if s]
by={r["id"]:r for r in rows}
assert len(rows)==len(by)==len(design["audit_packets"])==30
reg={"criterion_changed":{"YES","NO","UNDETERMINED"},
 "claim_valid":{"YES","NO","UNDETERMINED"},
 "next_action":{"REJECT_CLAIM","INDEPENDENT_REPLICATION","REQUEST_CLASS_EVIDENCE"}}
stats=defaultdict(lambda:{"attempts":0,"original_full_schema_valid":0,"raw_json_parseable":0,
 "raw_field_criterion_correct":0,"raw_field_claim_correct":0,"raw_field_action_correct":0,
 "raw_field_criterion_invalid":0,"raw_field_claim_invalid":0,"raw_field_action_invalid":0})
bad_examples=[]
for item in design["audit_packets"]:
 r=by[item["id"]]
 key=item["visibility"]
 x=stats[key];x["attempts"]+=1
 x["original_full_schema_valid"]+=int(r["status"]=="VALID")
 try:j=json.loads(r.get("raw") or "")
 except Exception:j=None
 if not isinstance(j,dict):continue
 x["raw_json_parseable"]+=1
 for k,statfield in (("criterion_changed","criterion"),("claim_valid","claim"),("next_action","action")):
  value=str(j.get(k,"")).strip().upper()
  if value not in reg[k]:
   x["raw_field_"+statfield+"_invalid"]+=1
  elif value==item["gold"][k]:
   x["raw_field_"+statfield+"_correct"]+=1
 if key=="FULL" and r["status"]!="VALID" and len(bad_examples)<5:
  bad_examples.append({"id":item["id"],"original_schema_status":r["status"],
     "actual_goal_valid":item["scientific_holdout_valid"],
     "gold":item["gold"],
     "auditor_parsed_but_invalid_contract":{k:j.get(k) for k in ("criterion_changed","claim_valid","next_action")},
     "verbatim_reason_excerpt":str(j.get("reason",""))[:430]})
assert stats["FULL"]["attempts"]==stats["SUMMARY"]["attempts"]==15
assert stats["FULL"]["original_full_schema_valid"]==0
assert stats["SUMMARY"]["original_full_schema_valid"]==15
assert stats["FULL"]["raw_json_parseable"]==15
assert stats["FULL"]["raw_field_action_invalid"]==15
record={"schema":"AI4SCI_P3C_POSTHOC_INVALID_RAW_FIELD_REVIEW_V1",
 "status":"INVALID_WHOLE_RESPONSE_REMAINS_INVALID",
 "source_input_sha256":sha256((root/"p3c_audit_inputs_LOCKED.json").read_bytes()).hexdigest(),
 "source_output_sha256":sha256((root/"p3c_auditor_outputs.jsonl").read_bytes()).hexdigest(),
 "blind_model":"qwen2.5-coder:14b",
 "method":"parse raw JSON only for diagnostic audit; no schema status rehabilitation, no new audit model calls",
 "counts":dict(stats),"examples":bad_examples,
 "interpretation":"FULL invalid next_action was NO_ACTION (outside frozen enum) and raw validity/criterion statements must not be promoted to accepted answers",
 "accepted_original_full_schema_responses":15,
 "invalid_original_full_schema_responses":15,
 "author":"HOLD","send":"DISABLED"}
target=root/"p3c_raw_field_analysis.json"
enc=(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if target.exists() and target.read_bytes()!=enc:raise SystemExit("POSTHOC_DIAG_ALREADY_EXISTS_DIFFERENT")
if not target.exists():target.write_bytes(enc)
print(json.dumps({"status":record["status"],"sha256":sha256(enc).hexdigest(),
 "counts":record["counts"],"example":bad_examples[0] if bad_examples else None},
 ensure_ascii=False,sort_keys=True),flush=True)
