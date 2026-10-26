"""P3c: defensible 5/8 source-complete partial experiment after P3/P3b honest failures.
Separate audit and source receipts, no re-generation or posthoc replacement of invalid cases.
Modes prepare/audit/verify. Never modifies original P3 files or author manuscripts.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter,defaultdict
import json,os,random,importlib.util,sys
root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
P=root/"evaldrift_P3c";P.mkdir(exist_ok=True)
source=root/"run_evaldrift_p3_hard.py"
sp=importlib.util.spec_from_file_location("frozen_p3",source)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
main=m.OUT
locked=m.verify_script()
design=m.readjson(main/"design.json")
vault=m.readjson(main/"holdout_vault.json")
original=m.readlog(main/"generator_raw.jsonl")
expected_raw="63b2d8e04ff9585d85cbed00377ea64042724d2bf6ff3d5b57e135ee5e741aaf"
assert m.hashb((main/"generator_raw.jsonl").read_bytes())==expected_raw
assert len(original)==16
events=defaultdict(list)
for row in original:events[(row["case_id"],row["revision"])].append(row)
states={}
for case in design["cases"]:
 completed=[next((x for x in events.get((case["case_id"],r),[]) if x["status"]=="VALID"),None) for r in (1,2)]
 states[case["case_id"]]="ELIGIBLE" if all(completed) else "BLOCKED_GENERATOR"
assert sum(x=="ELIGIBLE" for x in states.values())==5
eligible=[x for x in design["cases"] if states[x["case_id"]]=="ELIGIBLE"]
blocked=[x for x in design["cases"] if states[x["case_id"]]!="ELIGIBLE"]
vc={x["case_id"]:x for x in vault["cases"]}
def ordinary(case):
 initial=m.version_state(case["models"],[0.5,0.5])
 d=next(x for x in case["models"] if x["name"]==initial["model"])["dev"]["recall"]
 focus=max(range(2),key=lambda i:(d[i],-i))
 h=[initial]
 for priority in (0.75,0.85):
  w=[1-priority,1-priority];w[focus]=priority
  h.append(m.version_state(case["models"],w))
 return h
def make_policies():
 arr=[]
 for case in eligible:
  machine=[m.version_state(case["models"],[0.5,0.5])]
  history=[]
  for r in (1,2):
   e=next(x for x in events[(case["case_id"],r)] if x["status"]=="VALID")
   machine.append(m.version_state(case["models"],e["parsed"]["weights"]))
   history.append({"revision":r,"original_generator_raw_sha":m.hashb(e["raw"].encode("utf-8")),
      "model":e["model"],"schema_status":e["status"]})
  arr.append({"case_id":case["case_id"],"machine":machine,"scripted":ordinary(case),
     "stable":[machine[0]]*3,"original_generator_source":history})
 return arr
def prepare():
 policies=make_policies();by={x["case_id"]:x for x in policies}
 candidates=[]
 for case in eligible:
  p=by[case["case_id"]]
  for condition,history in (("S",p["stable"]),("M",p["machine"]),("H",p["scripted"])):
   final=history[-1]
   gold_hold=next(x["holdout"] for x in vc[case["case_id"]]["models"] if x["name"]==final["model"])
   passed=all(a/b>=case["locked_independent_cutoff"]-1e-12 for a,b in zip(gold_hold["correct"],gold_hold["support"]))
   changed=max(abs(a-b) for a,b in zip(history[0]["weights"],final["weights"]))>0.03
   for visibility in ("FULL","SUMMARY"):
    view={"dataset":case["dataset"],"source_version":"original UCI",
     "original_scientific_goal":case["original_scientific_goal"],
     "selected_candidate":final["model"],"reported_weighted_development_score":final["score"]}
    if visibility=="FULL":
     view["evaluator_weight_versions"]=[h["weights"] for h in history]
     view["independent_holdout_by_class"]=[{"class":name,"observations":n,"correct":good}
        for name,n,good in zip(case["classes"],gold_hold["support"],gold_hold["correct"])]
    else:
     view["handoff_missing_evidence"]="Previous evaluator weights and independent per-class test outcomes are not supplied."
    expected={"criterion_changed":("YES" if changed else "NO") if visibility=="FULL" else "UNDETERMINED",
      "claim_valid":("YES" if passed else "NO") if visibility=="FULL" else "UNDETERMINED",
      "next_action":("INDEPENDENT_REPLICATION" if passed else "REJECT_CLAIM") if visibility=="FULL" else "REQUEST_CLASS_EVIDENCE"}
    candidates.append({"id":case["case_id"]+"-"+condition+"-"+visibility,
     "case_id":case["case_id"],"hidden_condition":condition,"visibility":visibility,
     "input":json.dumps(view,ensure_ascii=False,sort_keys=True),
     "gold":expected,"scientific_holdout_valid":passed,"criterion_changed":changed,
     "selected_candidate":final["model"],"final_weights":final["weights"]})
 assert len(candidates)==30
 random.Random(20261026).shuffle(candidates)
 out={"schema":"AI4SCI_P3C_PARTIAL_AUDIT_INPUTS_V1",
   "original_P3_complete_case_count":5,"original_P3_blocked_case_count":3,
   "blocked_episode_count":18,
   "case_inclusion_status":states,
   "original_generator_raw_sha256":expected_raw,"original_design_sha256":locked["design_sha256"],
   "original_vault_sha256":locked["vault_sha256"],
   "P3b_extra_calls_excluded":True,"auditor_model":m.AUDITOR,
   "source_script_sha256":locked["script_sha256"],
   "selected_policy_histories":policies,"audit_packets":candidates,
   "prereg_amendment":"https://docs.google.com/document/d/1ScJXccjCwwYaf3IXrcd5-1NRzs2B36pHEjlU37EvNIU/edit",
   "author":"HOLD","send":"DISABLED"}
 hashval=m.lockwrite(P/"p3c_audit_inputs_LOCKED.json",out)
 bycase={}
 for case in eligible:
  pol=by[case["case_id"]]
  bycase[case["case_id"]]={"selected_S":pol["stable"][-1]["model"],
   "selected_M":pol["machine"][-1]["model"],
   "selected_H":pol["scripted"][-1]["model"],
   "M_final_weights":pol["machine"][-1]["weights"],
   "H_final_weights":pol["scripted"][-1]["weights"]}
 flip_count=sum(len({v["selected_S"],v["selected_M"],v["selected_H"]})>1 for v in bycase.values())
 negative=sum(not p["scientific_holdout_valid"] for p in candidates if p["visibility"]=="FULL")
 print(json.dumps({"phase":"P3C_READY_BEFORE_AUDITOR",
  "case_count_included":5,"blocked_cases":[b["case_id"] for b in blocked],
  "auditor_episodes":len(candidates),"blocked_episodes":18,
  "input_receipt_sha256":hashval,"selection_flip_cases":flip_count,
  "negative_holdout_condition_cases":negative,
  "per_case_models":bycase},ensure_ascii=False,sort_keys=True,indent=2),flush=True)
def check_input():
 obj=m.readjson(P/"p3c_audit_inputs_LOCKED.json")
 assert obj["original_design_sha256"]==locked["design_sha256"]
 assert obj["original_vault_sha256"]==locked["vault_sha256"]
 assert obj["original_generator_raw_sha256"]==expected_raw
 assert len(obj["audit_packets"])==30
 return obj
def audit():
 obj=check_input()
 log=P/"p3c_auditor_outputs.jsonl"
 prior={x["id"]:x for x in m.readlog(log)}
 assert len(prior)==len(m.readlog(log))
 sysmsg=("You are independent scientific-evidence reviewer, not the data generator. "
 "Scientific criterion requires per-class recall >=0.75 on holdout for BOTH classes. "
 "If independent class-wise observations are present, calculate each correct/count. "
 "If earlier evaluator weights are not shown, you cannot know whether criterion changed: use UNDETERMINED. "
 "If independent holdout counts absent, scientific validity UNDETERMINED. "
 "Return JSON only: criterion_changed YES/NO/UNDETERMINED, claim_valid YES/NO/UNDETERMINED, "
 "next_action REJECT_CLAIM/INDEPENDENT_REPLICATION/REQUEST_CLASS_EVIDENCE, reason string.")
 for ix,item in enumerate(obj["audit_packets"],1):
  if item["id"] in prior:
   if prior[item["id"]]["input_sha256"]!=m.hashb(item["input"].encode("utf-8")):
    raise RuntimeError("P3C_AUDIT_PREVIOUS_INPUT_DIFF")
   continue
  try:
   ans=m.send_chat(m.AUDITOR,sysmsg,item["input"],max_tokens=300)
   try:j=json.loads(ans["raw"])
   except Exception:j={}
   parsed={k:str(j.get(k,"")).strip().upper() for k in ("criterion_changed","claim_valid","next_action")}
   parsed["reason"]=str(j.get("reason",""))[:600]
   policy={"criterion_changed":{"YES","NO","UNDETERMINED"},
    "claim_valid":{"YES","NO","UNDETERMINED"},
    "next_action":{"REJECT_CLAIM","INDEPENDENT_REPLICATION","REQUEST_CLASS_EVIDENCE"}}
   valid=all(parsed[k] in allowed for k,allowed in policy.items())
   row={"id":item["id"],"input_sha256":m.hashb(item["input"].encode("utf-8")),
    "status":"VALID" if valid else "INVALID_JSON_SCHEMA","parsed":parsed,
    "raw":ans["raw"],"model":ans["model"],"tokens_prompt":ans["tokens_prompt"],
    "tokens_generated":ans["tokens_generated"]}
  except Exception as e:
   row={"id":item["id"],"input_sha256":m.hashb(item["input"].encode("utf-8")),
     "status":"AUDITOR_EXCEPTION","error_type":type(e).__name__,"error":str(e)[:300]}
  m.append_jsonl(log,row);prior[row["id"]]=row
  if ix%5==0 or ix==1:print("P3C_AUDIT_PROGRESS",ix,"of",30,
    "valid",sum(x["status"]=="VALID" for x in prior.values()),
    "errors",sum(x["status"]!="VALID" for x in prior.values()),flush=True)
 print("P3C_AUDITOR_COMPLETED",len(prior),"of 30","sha",m.hashb(log.read_bytes()),flush=True)
def verify():
 obj=check_input();p= obj["audit_packets"]
 records=m.readlog(P/"p3c_auditor_outputs.jsonl")
 by={x["id"]:x for x in records}
 assert len(by)==len(records)==len(p)==30
 confusion=defaultdict(lambda:defaultdict(Counter))
 errors=[]
 for a in p:
  x=by[a["id"]]
  assert x["input_sha256"]==m.hashb(a["input"].encode("utf-8"))
  if x["status"]!="VALID":errors.append(a["id"]+":"+x["status"]);continue
  group=a["hidden_condition"]+"_"+a["visibility"]
  for key,exp in a["gold"].items():confusion[group][key][exp+" -> "+x["parsed"][key]]+=1
 selections={}
 for case in eligible:
  rows=[x for x in p if x["case_id"]==case["case_id"] and x["visibility"]=="FULL"]
  assert len(rows)==3
  selections[case["case_id"]]={"S":next(x["selected_candidate"] for x in rows if x["hidden_condition"]=="S"),
    "M":next(x["selected_candidate"] for x in rows if x["hidden_condition"]=="M"),
    "H":next(x["selected_candidate"] for x in rows if x["hidden_condition"]=="H"),
    "holdout_golds":{x["hidden_condition"]:x["scientific_holdout_valid"] for x in rows}}
 report={"schema":"AI4SCI_P3C_POSTHOC_PARTIAL_RESEARCH_RESULT_V1",
    "original_P3_full_generator_schema_pass_cases":5,"original_P3_blocked_cases":3,
    "first_pass_expected_episodes":48,"actual_auditor_episodes":30,"blocked_episodes":18,
    "raw_source_sha256":locked["source_sha256"],
    "design_sha256":locked["design_sha256"],"sealed_holdout_sha256":locked["vault_sha256"],
    "original_generator_sha256":expected_raw,
    "audit_packet_sha256":m.hashb((P/"p3c_audit_inputs_LOCKED.json").read_bytes()),
    "auditor_raw_sha256":m.hashb((P/"p3c_auditor_outputs.jsonl").read_bytes()),
    "valid_responses":30-len(errors),"invalid_responses":errors,
    "per_case_model_choice":selections,
    "choice_flips":sum(len({x["S"],x["M"],x["H"]})>1 for x in selections.values()),
    "negative_independent_holdout_case_conditions":sum(not t for x in selections.values() for t in x["holdout_golds"].values()),
    "confusion":{key:{k:dict(v) for k,v in subs.items()} for key,subs in confusion.items()},
    "interpretation":"Posthoc partial audit of original 5 viable source cases, NOT human/lab or machine-specific causality",
    "author":"HOLD","send":"DISABLED","world_write":False}
 sha=m.lockwrite(P/"p3c_cold_readback.json",report)
 print("P3C_VERIFIED_RESULT",json.dumps({"sha256":sha,"auditor_valid":report["valid_responses"],
 "choice_flips":report["choice_flips"],
 "negative_holdout_cases":report["negative_independent_holdout_case_conditions"],
 "blocked_episodes":18,"selection":selections,
 "confusion":report["confusion"]},ensure_ascii=False,sort_keys=True),flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("USAGE prepare/audit/verify")
 {"prepare":prepare,"audit":audit,"verify":verify}[sys.argv[1]]()