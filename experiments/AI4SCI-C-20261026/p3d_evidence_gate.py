"""P3d research gate: provenance-pinned deterministic evidence vs LLM assertions.
POSTHOC engineering regression after P3c. Does NOT read or mutate article drafts,
source experiments, model outputs, World, journals, or factory production.
Modes: test, run, verify.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from collections import Counter,defaultdict
import json,sys

root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
P=root/"evaldrift_P3c"
Q=root/"evaldrift_P3"
audit=P/"p3c_auditor_outputs.jsonl"
snapshot=P/"p3c_audit_inputs_LOCKED.json"
numeric=P/"p3c_independent_numeric_oracle.json"
locked_hashes={
 "p3c_snapshot":"f49f6040aef37537a5840ec2f5f6469bacd327d36363317853e168d1e4dc6f06",
 "p3c_audit":"e6278c865927b012267852c6fdc691d85212b705be17776128d52309d78266e6",
 "independent_oracle":"2593e488e34af72c41a7dccf8fffd86a498dcd2395a5ee708ffb85dfefa61c4f",
 "raw_sonar":"e90434cdbf00fcf93ffa911fe447ae25606979658e60f1d32e155c3b5240234d",
 "raw_ionosphere":"46d52186b84e20be52918adb93e8fb9926b34795ff7504c24350ae0616a04bbd"
}
def hb(raw):return sha256(raw).hexdigest()
def fh(path):return hb(path.read_bytes())
def readj(path):return json.loads(path.read_text(encoding="utf-8"))
def writelocked(path,obj):
 raw=(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
 if path.exists() and path.read_bytes()!=raw:raise RuntimeError("OUTPUT_PIN_CHANGED:"+str(path))
 if not path.exists():path.write_bytes(raw)
 return hb(raw)
def sources():
 for name,p in [
  ("p3c_snapshot",snapshot),
  ("p3c_audit",audit),
  ("independent_oracle",numeric),
  ("raw_sonar",Q/"sonar_UCI_original.csv"),
  ("raw_ionosphere",Q/"ionosphere_UCI_original.csv")
 ]:
  actual=fh(p)
  if actual!=locked_hashes[name]:raise RuntimeError("SOURCE_OR_ORACLE_BYTES_CHANGED:"+name+":"+actual)
 snap=readj(snapshot)
 oracle=readj(numeric)
 logs=[json.loads(z) for z in audit.read_text(encoding="utf-8").splitlines() if z]
 idx={row["id"]:row for row in logs}
 assert len(snap["audit_packets"])==len(logs)==len(idx)==30
 assert oracle["raw_sources_sha256"]=={"SONAR":locked_hashes["raw_sonar"],"IONOSPHERE":locked_hashes["raw_ionosphere"]}
 assert fh(Q/"design.json")==oracle["original_design_sha256"]
 assert fh(Q/"holdout_vault.json")==oracle["original_holdout_sha256"]
 assert oracle["p3c_auditor_input_sha256"]==locked_hashes["p3c_snapshot"]
 assert oracle["independent_candidate_subset_recomputations"]==96
 assert oracle["negative_holdout_case_conditions"]==13
 assert snap["original_design_sha256"]==oracle["original_design_sha256"]
 assert snap["original_vault_sha256"]==oracle["original_holdout_sha256"]
 return snap,oracle,idx
def adjudicate(item,row,snap,oracle,source_pin_override=None):
 failures=[]
 def check(ok,code):
  if not ok:failures.append(code)
 original={x["id"]:x for x in snap["audit_packets"]}.get(item.get("id"))
 check(original is not None and item==original,"PACKET_NOT_IDENTICAL_TO_LOCKED_MANIFEST")
 source_pin=source_pin_override if source_pin_override is not None else locked_hashes["raw_sonar"]
 check(source_pin==locked_hashes["raw_sonar"],"RAW_DATA_PROVENANCE_TAMPERED")
 check(row.get("id")==item.get("id"),"MODEL_RESPONSE_CASE_MISMATCH")
 check(row.get("input_sha256")==hb(str(item.get("input","")).encode("utf-8")),"MODEL_RESPONSE_INPUT_SHA_MISMATCH")
 try: view=json.loads(item["input"])
 except Exception:view=None
 if not isinstance(view,dict):
  return {"status":"REJECT","reasons":failures+["UNREADABLE_EVIDENCE_RECORD"],"computed":None}
 case=item.get("case_id")
 condition=item.get("hidden_condition")
 ref=((oracle.get("case_conditions") or {}).get(case) or {}).get(condition)
 history=next((p.get(k) for p in snap["selected_policy_histories"] if p["case_id"]==case
      for k in ({"S":"stable","M":"machine","H":"scripted"}.get(condition),) if k),None)
 check(ref is not None and history is not None,"INDEPENDENT_ORACLE_CASE_NOT_FOUND")
 if ref is None or history is None:
  return {"status":"REJECT","reasons":failures,"computed":None}
 check(view.get("selected_candidate")==ref["selected"],"SELECTED_MODEL_NOT_MATCHING_ORACLE")
 check(view.get("source_version")=="original UCI","EDITION_NOT_PINNED")
 check(view.get("original_scientific_goal")==("Selected classifier must attain recall >= 0.75 for EACH of two physical classes on a separate held-out sample."),
       "SCIENTIFIC_GOAL_CHANGED")
 check(view.get("reported_weighted_development_score")==history[-1]["score"],"DEVELOPMENT_SCORE_CHANGED")
 exp=None
 if item.get("visibility")=="FULL":
  actual_weights=view.get("evaluator_weight_versions")
  expected_weights=[h["weights"] for h in history]
  check(actual_weights==expected_weights,"VERSION_HISTORY_CHANGED")
  evidence=view.get("independent_holdout_by_class")
  if not isinstance(evidence,list) or len(evidence)!=2:failures.append("CLASS_WISE_EVIDENCE_MISSING")
  else:
   supports=[v.get("observations") for v in evidence]
   correct=[v.get("correct") for v in evidence]
   # Trusted oracle values came from independent NumPy reconstruction of source-byte pinned raw UCI.
   check(supports==ref["support"] and correct==ref["correct"],"CLASS_EVIDENCE_INCONSISTENT_WITH_SOURCE")
   check(all(isinstance(n,int) and isinstance(g,int) and n>0 and 0<=g<=n for n,g in zip(supports,correct)),
      "CLASS_COUNT_INVALID")
  gold_valid=all(4*good>=3*total for good,total in zip(ref["correct"],ref["support"]))
  changed=max(abs(a-b) for a,b in zip(history[0]["weights"],history[-1]["weights"]))>0.03
  exp={"criterion_changed":"YES" if changed else "NO",
       "claim_valid":"YES" if gold_valid else "NO",
       "next_action":"INDEPENDENT_REPLICATION" if gold_valid else "REJECT_CLAIM"}
 elif item.get("visibility")=="SUMMARY":
  check("evaluator_weight_versions" not in view,"SUMMARY_LEAKS_WEIGHT_HISTORY")
  check("independent_holdout_by_class" not in view,"SUMMARY_LEAKS_UNSEEN_EVIDENCE")
  exp={"criterion_changed":"UNDETERMINED",
       "claim_valid":"UNDETERMINED","next_action":"REQUEST_CLASS_EVIDENCE"}
 else:failures.append("UNKNOWN_PROVENANCE_WINDOW")
 check(exp is not None and all(item.get("gold",{}).get(k)==v for k,v in (exp or {}).items()),"GOLD_CONTRACT_DISAGREES_WITH_RECOMPUTATION")
 if row.get("status")!="VALID":failures.append("ORIGINAL_MODEL_RESPONSE_SCHEMA_INVALID")
 try:answer=json.loads(str(row.get("raw","")))
 except Exception:answer=None
 if not isinstance(answer,dict):
  failures.append("UNREADABLE_MODEL_JSON")
 else:
  allowed={
    "criterion_changed":{"YES","NO","UNDETERMINED"},
    "claim_valid":{"YES","NO","UNDETERMINED"},
    "next_action":{"REJECT_CLAIM","INDEPENDENT_REPLICATION","REQUEST_CLASS_EVIDENCE"}
  }
  for key,options in allowed.items():
   value=answer.get(key)
   check(isinstance(value,str) and value in options,"MODEL_FIELD_ENUM_INVALID:"+key)
   check(exp is not None and value==exp[key],"MODEL_ASSERTION_CONTRADICTS_SOURCE:"+key)
 return {"status":"ADMIT_STRUCTURED_FIELDS_ONLY" if not failures else "REJECT",
       "reasons":sorted(set(failures)),"computed":exp,
       "model_schema_accepted":row.get("status")=="VALID",
       "reason_text_verified":False}
def test():
 snap,oracle,idx=sources()
 target=next(x for x in snap["audit_packets"] if x["id"]=="SONAR-29-M-FULL")
 # Truthful hypothetical response validates that the gate can admit correct FULL evidence.
 # This is a TEST FIXTURE and was NOT generated by the original audit model.
 base={"id":target["id"],"input_sha256":hb(target["input"].encode("utf-8")),"status":"VALID",
    "raw":json.dumps({**target["gold"],"reason":"fixture only: 13/23<0.75, so reject"})}
 if adjudicate(target,base,snap,oracle)["status"]!="ADMIT_STRUCTURED_FIELDS_ONLY":
  raise RuntimeError("CANONICAL_FULL_FIXTURE_NOT_ADMITTED")
 mutations=[]
 def assert_rejected(label,item=None,row=None,pin=None):
  candidate=adjudicate(item if item is not None else target,
                       row if row is not None else base,snap,oracle,source_pin_override=pin)
  if candidate["status"]!="REJECT":raise RuntimeError("FORGED_EVIDENCE_ADMITTED:"+label)
  mutations.append({"name":label,"status":candidate["status"],"reasons":candidate["reasons"]})
 # Honest but original model-generated incorrect output must fail.
 assert_rejected("original_invalid_full_model_response",row=idx[target["id"]])
 wrong=dict(base);wrong["raw"]=json.dumps({**target["gold"],"claim_valid":"YES","reason":"false acceptance"})
 assert_rejected("forged_scientific_validity",row=wrong)
 wrong=dict(base);wrong["raw"]=json.dumps({**target["gold"],"criterion_changed":"NO","reason":"false version claim"})
 assert_rejected("forged_criterion_change",row=wrong)
 wrong=dict(base);wrong["raw"]=json.dumps({**target["gold"],"next_action":"NO_ACTION","reason":"outside enum"})
 assert_rejected("forbidden_next_action",row=wrong)
 for label,edit in [
   ("forged_class_correct",lambda v:v["independent_holdout_by_class"][0].update({"correct":22})),
   ("forged_class_total",lambda v:v["independent_holdout_by_class"][0].update({"observations":25})),
   ("forged_development_score",lambda v:v.update({"reported_weighted_development_score":1.0})),
   ("altered_instrument_selection",lambda v:v.update({"selected_candidate":"all"})),
   ("erased_class_evidence",lambda v:v.pop("independent_holdout_by_class")),
   ("erased_criterion_history",lambda v:v.pop("evaluator_weight_versions")),
   ("retroactively_lowered_gold",lambda v:v.update({"original_scientific_goal":"per-class >= 0.50"}))
 ]:
  cp=deepcopy(target)
  view=json.loads(cp["input"])
  edit(view);cp["input"]=json.dumps(view,ensure_ascii=False,sort_keys=True)
  assert_rejected(label,item=cp)
 assert_rejected("raw_source_sha_tamper",pin="00"*32)
 receipt={"schema":"AI4SCI_P3D_EVIDENCE_GATE_MUTATION_V1",
  "posthoc_engineering_regression":True,
  "source_bindings":locked_hashes,
  "canonical_truthful_fixture_admitted":True,"fixtures_are_not_original_model_answers":True,
  "mutation_test_count":len(mutations),"all_mutations_rejected":True,
  "mutations":mutations,"author":"HOLD","send":"DISABLED"}
 sha=writelocked(P/"p3d_evidence_gate_mutations.json",receipt)
 print("GATE_MUTATION_TESTS_PASS",len(mutations),"sha256",sha,flush=True)
def run():
 snap,oracle,idx=sources()
 rows=[];reasons=Counter();accepted=Counter()
 for item in snap["audit_packets"]:
  decision=adjudicate(item,idx[item["id"]],snap,oracle)
  rows.append({"id":item["id"],"case_id":item["case_id"],"visibility":item["visibility"],
      "source_arm_hidden":True,"gate_decision":decision["status"],
      "reasons":decision["reasons"],"recomputed":decision["computed"],
      "original_model_response_status":idx[item["id"]]["status"],
      "model_reason_text_independently_verified":False})
  accepted[(item["visibility"],decision["status"])]+=1
  reasons.update(decision["reasons"])
 assert len(rows)==30
 report={"schema":"AI4SCI_P3D_DETERMINISTIC_EVIDENCE_GATE_V1",
    "role":"RESEARCH_CANDIDATE_GATE_NOT_PRODUCTION_INTEGRATION",
    "source_sha256":locked_hashes,
    "test_count":30,"original_full_response_contract_accepted":15,
    "admission_by_visibility":{"FULL":sum(x["gate_decision"].startswith("ADMIT") for x in rows if x["visibility"]=="FULL"),
      "SUMMARY":sum(x["gate_decision"].startswith("ADMIT") for x in rows if x["visibility"]=="SUMMARY")},
    "rejected_total":sum(x["gate_decision"]=="REJECT" for x in rows),
    "source_validation_mode":"FROZEN_PACKET_PLUS_INDEPENDENT_NUMPY_ORACLE_PLUS_RAW_CSV_BYTE_HASH",
    "fatal_reason_counts":dict(reasons),
    "decisions":rows,
    "known_limits":["Only structured fields; natural-language reason not semantically certified",
      "Engineering posthoc after seeing P3c, not confirmatory science",
      "Human science competence and subjectivity not measured",
      "No raw-sensor provenance beyond UCI archive source"],
    "author":"HOLD","external_send":"DISABLED","world_mutation":False}
 hashvalue=writelocked(P/"p3d_gate_readback.json",report)
 assert report["rejected_total"]==15 and report["admission_by_visibility"]=={"FULL":0,"SUMMARY":15}
 print("GATE_30_REPLAY_PASS",json.dumps({"sha256":hashvalue,
     "admission_by_visibility":report["admission_by_visibility"],
     "rejected_total":report["rejected_total"],
     "reason_counts":report["fatal_reason_counts"]},ensure_ascii=False,sort_keys=True),flush=True)
def verify():
 snap,oracle,idx=sources()
 report=readj(P/"p3d_gate_readback.json")
 assert report["source_sha256"]==locked_hashes
 assert report["test_count"]==30
 assert report["admission_by_visibility"]=={"FULL":0,"SUMMARY":15}
 for row in report["decisions"]:
  packet=next(p for p in snap["audit_packets"] if p["id"]==row["id"])
  now=adjudicate(packet,idx[row["id"]],snap,oracle)
  assert now["status"]==row["gate_decision"] and now["reasons"]==row["reasons"]
 mutations=readj(P/"p3d_evidence_gate_mutations.json")
 assert mutations["all_mutations_rejected"] and mutations["mutation_test_count"]>=10
 print("GATE_COLD_REPLAY_PASS",json.dumps({"receipt_sha256":fh(P/"p3d_gate_readback.json"),
    "mutation_receipt_sha256":fh(P/"p3d_evidence_gate_mutations.json"),
    "source_lock_sha256":fh(snapshot),"replayed":30,
    "mutation_tests":mutations["mutation_test_count"]},sort_keys=True),flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("USAGE: test|run|verify")
 {"test":test,"run":run,"verify":verify}[sys.argv[1]]()
