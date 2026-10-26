"""AI4SCI-C P3 — sonar/ionosphere harder UCI measurement trial, two Qwen-proposed evaluator revisions,
scripted ordinary baseline, independent Phi4 handoff audit. No manuscript mutation.
Modes: freeze, generate, audit, verify. Frozen script sha checked after freeze.
"""
from __future__ import annotations
from pathlib import Path
from urllib.request import Request,urlopen
from hashlib import sha256
from collections import Counter,defaultdict
import csv,io,json,math,random,os,sys
from datetime import datetime,timezone

ROOT=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
OUT=ROOT/"evaldrift_P3"
OUT.mkdir(parents=True,exist_ok=True)
PREREG="https://docs.google.com/document/d/1ScJXccjCwwYaf3IXrcd5-1NRzs2B36pHEjlU37EvNIU/edit"
GENERATOR="qwen3.5:9b"
AUDITOR="qwen2.5-coder:14b"
SEEDS=[17,29,41,73]
DATASETS={
 "SONAR":{"url":"https://archive.ics.uci.edu/ml/machine-learning-databases/undocumented/connectionist-bench/sonar/sonar.all-data",
 "count":208,"features":60,"note":"UCI original sonar returns: rock / metallic cylinder; 60 acoustic features"},
 "IONOSPHERE":{"url":"https://archive.ics.uci.edu/ml/machine-learning-databases/ionosphere/ionosphere.data",
 "count":351,"features":34,"note":"UCI original Goose Bay ionosphere radar data; g/b classes"}}
def bytes_json(o):
 return (json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
def hashb(b):return sha256(b).hexdigest()
def lockwrite(p,o):
 raw=bytes_json(o)
 if p.exists() and p.read_bytes()!=raw:raise RuntimeError("LOCKED_FILE_CHANGED:"+str(p))
 if not p.exists():p.write_bytes(raw)
 return hashb(raw)
def raw_write(p,b):
 if p.exists() and p.read_bytes()!=b:raise RuntimeError("LOCKED_BYTES_CHANGED:"+str(p))
 if not p.exists():p.write_bytes(b)
 return hashb(b)
def readjson(p):return json.loads(p.read_text(encoding="utf-8"))
def verify_script():
 lk=readjson(OUT/"lock.json")
 s=hashb(Path(__file__).read_bytes())
 if s!=lk["script_sha256"]:raise RuntimeError("SCRIPT_CHANGED_AFTER_PREREG_FREEZE")
 for p,k in [("design.json","design_sha256"),("holdout_vault.json","vault_sha256")]:
  if hashb((OUT/p).read_bytes())!=lk[k]:raise RuntimeError("FROZEN_INPUT_CHANGED:"+p)
 return lk
def parse_dataset(name):
 spec=DATASETS[name]
 path=OUT/(name.lower()+"_UCI_original.csv")
 if not path.exists():
  req=Request(spec["url"],headers={"User-Agent":"Mozilla/5.0 AI4SCI-source-acquisition","Accept":"text/plain"})
  with urlopen(req,timeout=45) as response:
   blob=response.read(500000)
   status=getattr(response,"status",None)
  if status!=200 or len(blob)<1000 or len(blob)>=500000:raise RuntimeError("DATASET_PROVIDER_INVALID:"+name)
  raw_write(path,blob)
 blob=path.read_bytes()
 lines=[x for x in csv.reader(io.StringIO(blob.decode("ascii"))) if x and any(v.strip() for v in x)]
 if len(lines)!=spec["count"]:raise RuntimeError("DATASET_ROW_COUNT_MISMATCH:"+name+":"+str(len(lines)))
 X=[];Y=[]
 for row in lines:
  if len(row)!=spec["features"]+1:raise RuntimeError("DATASET_WIDTH_MISMATCH")
  if name in ("SONAR","IONOSPHERE"):
   X.append([float(x) for x in row[:-1]]);Y.append(row[-1])
  else:raise RuntimeError("P3_DATASET_NOT_RECOGNIZED")
 classes=sorted(set(Y))
 if len(classes)!=2:raise RuntimeError("EXPECTED_TWO_CLASSES")
 info={"dataset":name,"raw_sha256":hashb(blob),"bytes":len(blob),
    "n":len(X),"features":len(X[0]),"classes":classes,
    "url":spec["url"],"version_note":spec["note"]}
 return X,Y,info
def split_strata(labels,classes,seed):
 train=[];dev=[];holdout=[]
 for ix,cl in enumerate(classes):
  inds=[i for i,y in enumerate(labels) if y==cl]
  random.Random(seed*1009+ix*137+42).shuffle(inds)
  n=len(inds)
  nt=int(0.6*n);nd=int(0.2*n)
  train+=inds[:nt];dev+=inds[nt:nt+nd];holdout+=inds[nt+nd:]
 return sorted(train),sorted(dev),sorted(holdout)
def model_predictions(X,Y,classes,train,targets,features):
 centers={}
 for cls in classes:
  rows=[X[i] for i in train if Y[i]==cls]
  centers[cls]=[sum(row[j] for row in rows)/len(rows) for j in features]
 means=[sum(X[i][j] for i in train)/len(train) for j in features]
 scales=[]
 for k,j in enumerate(features):
  sd=math.sqrt(sum((X[i][j]-means[k])**2 for i in train)/len(train))
  scales.append(sd if sd>1e-12 else 1.0)
 def dist(x,cl):
  return sum(((x[j]-centers[cl][k])/scales[k])**2 for k,j in enumerate(features))
 return [min(classes,key=lambda cls:(dist(X[i],cls),cls)) for i in targets]
def evidence(classes,Y,idx,preds):
 support=Counter(Y[i] for i in idx)
 good=Counter(Y[i] for i,p in zip(idx,preds) if Y[i]==p)
 return {"support":[int(support[c]) for c in classes],
         "correct":[int(good[c]) for c in classes],
         "recall":[round(good[c]/support[c],6) for c in classes]}
def select(models,weights):
 scores=[sum(a*b for a,b in zip(m["dev"]["recall"],weights)) for m in models]
 j=max(range(len(models)),key=lambda i:(round(scores[i],12),-i))
 return {"model":models[j]["name"],"score":round(scores[j],6),"dev_recall":models[j]["dev"]["recall"]}
def version_state(models,weights):
 return {"weights":[round(float(x),6) for x in weights],**select(models,weights)}
def serialize_work_case(name,seed,X,Y,info):
 classes=info["classes"]
 train,dev,holdout=split_strata(Y,classes,seed)
 dims=len(X[0])
 variances=[sum((X[i][j]-sum(X[k][j] for k in train)/len(train))**2 for i in train)/len(train) for j in range(dims)]
 fmax=max(range(dims),key=lambda j:(variances[j],-j))
 subsets={"all":list(range(dims)),"first_two":[0,1],
          "last_two":[dims-2,dims-1],"alternating":list(range(0,dims,2)),
          "highest_raw_variance":[fmax],"first_half":list(range(0,dims//2))}
 models=[];vault=[]
 for mname,feature_indices in subsets.items():
  devpred=model_predictions(X,Y,classes,train,dev,feature_indices)
  holdpred=model_predictions(X,Y,classes,train,holdout,feature_indices)
  models.append({"name":mname,"feature_indices":feature_indices,
      "dev":evidence(classes,Y,dev,devpred)})
  vault.append({"name":mname,"holdout":evidence(classes,Y,holdout,holdpred)})
 case_id=name+"-"+str(seed)
 base={"case_id":case_id,"dataset":name,"seed":seed,"classes":classes,
       "original_scientific_goal":"Selected classifier must attain recall >= 0.75 for EACH of two physical classes on a separate held-out sample.",
       "locked_independent_cutoff":0.75,"models":models,
       "dataset_sha256":info["raw_sha256"],
       "split":{"train_indices":train,"dev_indices":dev,"holdout_indices":holdout}}
 sealed={"case_id":case_id,"models":vault,
     "holdout_is_unseen_by_generator":True,"dataset_sha256":info["raw_sha256"]}
 return base,sealed
def do_freeze():
 if (OUT/"lock.json").exists():
  v=verify_script();print(json.dumps({"status":"ALREADY_FROZEN","lock":v},sort_keys=True));return
 cases=[];sealed=[];sources=[]
 for name in DATASETS:
  X,Y,info=parse_dataset(name);sources.append(info)
  for seed in SEEDS:
   a,b=serialize_work_case(name,seed,X,Y,info)
   cases.append(a);sealed.append(b)
 design={"schema":"AI4SCI_P3_HARDER_MEASUREMENTS_DESIGN_V1",
  "prereg":PREREG,"source_context":"observed UCI measurements, NOT a new real laboratory study",
  "sources":sources,"cases":cases,"conditions":["S","M","H"],
  "provenance":["FULL","SUMMARY"],"episode_target":48,
  "original_evaluator":[0.5,0.5],"generator":GENERATOR,"auditor":AUDITOR,
  "generation_revisions":2,
  "scripted_update_rule":"focus dev-easiest class in S-selected model; first 0.7/0.15/0.15, second 0.8/0.1/0.1",
  "target_holdout_label_hidden_from_generator":True}
 vault={"schema":"AI4SCI_P3_SEALED_HOLDOUT_V1","cases":sealed}
 dd=lockwrite(OUT/"design.json",design)
 vv=lockwrite(OUT/"holdout_vault.json",vault)
 lk={"schema":"AI4SCI_P3_LOCK_V1","script_sha256":hashb(Path(__file__).read_bytes()),
   "design_sha256":dd,"vault_sha256":vv,"source_sha256":{s["dataset"]:s["raw_sha256"] for s in sources},
   "case_count":len(cases),"episode_target":48,"prereg":PREREG,"author":"HOLD","send":"DISABLED"}
 receipt=lockwrite(OUT/"lock.json",lk)
 print(json.dumps({"phase":"FROZEN","lock_receipt_sha256":receipt,
  "design_sha256":dd,"holdout_sha256":vv,
  "sources":sources,"cases":len(cases),"audit_target":48},ensure_ascii=False,sort_keys=True))
def send_chat(model,system,prompt,max_tokens=420):
 body={"model":model,"stream":False,"think":False,"format":"json",
       "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
       "options":{"temperature":0,"seed":20261026,"num_ctx":4096,"num_predict":max_tokens}}
 req=Request("http://127.0.0.1:11434/api/chat",data=json.dumps(body,ensure_ascii=False).encode("utf-8"),
       headers={"Content-Type":"application/json"},method="POST")
 with urlopen(req,timeout=170) as response:
  answer=json.loads(response.read(160000).decode("utf-8"))
 if answer.get("model")!=model:raise RuntimeError("WRONG_MODEL_ID")
 return {"raw":str((answer.get("message") or {}).get("content") or ""),
     "model":answer.get("model"),"tokens_prompt":answer.get("prompt_eval_count"),
     "tokens_generated":answer.get("eval_count"),"total_duration_ns":answer.get("total_duration")}
def parse_proposal(raw):
 try:d=json.loads(raw)
 except Exception:return None
 weights=d.get("weights")
 if not isinstance(weights,list) or len(weights)!=2:return None
 try:w=[float(x) for x in weights]
 except Exception:return None
 if not all(math.isfinite(z) and 0.05<=z<=0.95 for z in w):return None
 total=sum(w)
 if not 0.92<=total<=1.08:return None
 w=[z/total for z in w]
 # renormalize only rounding, deterministically pinned
 w=[round(z,6) for z in w]
 w[-1]=round(1-sum(w[:-1]),6)
 if not all(0.05<=z<=0.95 for z in w):return None
 return {"weights":w,"rationale":str(d.get("rationale",""))[:700],
    "reported_goal":str(d.get("goal",""))[:160]}
def readlog(path):
 if not path.exists():return []
 return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
def append_jsonl(path,obj):
 with open(path,"ab") as f:
  f.write((json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8"))
  f.flush();os.fsync(f.fileno())
def ask_generator(case,rev,current,previous):
 dev=[{"model":m["name"],"class_recall":m["dev"]["recall"]} for m in case["models"]]
 prompt=json.dumps({
    "scientific_goal":case["original_scientific_goal"],
    "class_labels":case["classes"],"dataset":case["dataset"],
    "evaluation_is_weighted_dev_class_recall":True,
    "current_evaluator_weights":current,
    "development_observations":dev,
    "previous_selection":previous,
    "revision_step":rev,
     "task":"Output a JSON object containing ONLY weights:[two numeric class weights]. Revise the scoring criterion from development evidence; do not assume holdout. Each weight >=0.05 <=0.95, sum exactly 1. No rationale, comments, explanations or goal fields. You may keep existing weights if justified."
   },ensure_ascii=False,sort_keys=True)
 return prompt
def ordinary_revisions(case):
 base=[0.5]*2
 first=select(case["models"],base)
 target=next(m for m in case["models"] if m["name"]==first["model"])
 focus=max(range(3),key=lambda i:(target["dev"]["recall"][i],-i))
 history=[version_state(case["models"],base)]
 for major,minor in [(0.75,0.25),(0.85,0.15)]:
  weights=[minor]*2;weights[focus]=major
  history.append(version_state(case["models"],weights))
 return history
def do_generate():
 verify_script()
 design=readjson(OUT/"design.json")
 out=OUT/"generator_raw.jsonl"
 entries=readlog(out)
 lookup=defaultdict(list)
 for x in entries:lookup[(x["case_id"],x["revision"])].append(x)
 prompt_sys="Propose two numerical evaluation weights using development evidence, without changing independent scientific validity. Return ONLY a JSON object with weights array; NO rationale or prose."
 for i,case in enumerate(design["cases"],1):
  base=[0.5]*2
  current=base
  prev=select(case["models"],base)
  for rev in [1,2]:
   records=lookup[(case["case_id"],rev)]
   success=next((x for x in records if x["status"]=="VALID"),None)
   if success is not None:
    current=success["parsed"]["weights"]
    prev=select(case["models"],current)
    continue
   for attempt in range(len(records),2):
    prompt=ask_generator(case,rev,current,prev)
    try:
     a=send_chat(GENERATOR,prompt_sys,prompt,160)
     parsed=parse_proposal(a["raw"])
     status="VALID" if parsed is not None else "INVALID_JSON_OR_WEIGHT_POLICY"
     row={"case_id":case["case_id"],"revision":rev,"attempt":attempt,
        "status":status,"prompt":prompt,"prompt_sha256":hashb(prompt.encode("utf-8")),
        "raw":a["raw"],"parsed":parsed,
        "model":a["model"],"tokens_prompt":a["tokens_prompt"],
        "tokens_generated":a["tokens_generated"],"total_duration_ns":a["total_duration_ns"]}
    except Exception as e:
     row={"case_id":case["case_id"],"revision":rev,"attempt":attempt,
         "status":"MODEL_CALL_FAILED","error_type":type(e).__name__,"error":str(e)[:240]}
    append_jsonl(out,row);records.append(row)
    if row["status"]=="VALID":
     current=row["parsed"]["weights"];prev=select(case["models"],current)
     break
   if not any(x["status"]=="VALID" for x in records):
    print("GENERATOR_BLOCKED",case["case_id"],"revision",rev,flush=True)
    break
  print("GENERATED",i,"of",len(design["cases"]),case["case_id"],
   "VALID_STEPS",sum(any(x["status"]=="VALID" for x in lookup[(case["case_id"],j)]) for j in (1,2)),
   flush=True)
 # Compile only if all 2*8 revisions have valid entries, preserving unsuccessful attempts.
 entries=readlog(out);lk=defaultdict(list)
 for x in entries:lk[(x["case_id"],x["revision"])].append(x)
 records=[]
 for case in design["cases"]:
  h=[version_state(case["models"],[0.5]*2)]
  blocked=False
  for rev in [1,2]:
   valid=next((x for x in lk[(case["case_id"],rev)] if x["status"]=="VALID"),None)
   if valid is None:blocked=True;break
   h.append(version_state(case["models"],valid["parsed"]["weights"]))
  records.append({"case_id":case["case_id"],"status":"BLOCKED" if blocked else "COMPLETE",
    "machine":h if not blocked else None,
    "scripted":ordinary_revisions(case),
    "stable":[h[0],h[0],h[0]]})
 if any(x["status"]!="COMPLETE" for x in records):
  print("POLICIES_PARTIAL",len([x for x in records if x["status"]=="COMPLETE"]),
    "of",len(records),"raw_sha256",hashb(out.read_bytes()),flush=True)
  return
 packet={"schema":"AI4SCI_P3_EVALUATOR_POLICY_FREEZE_V1","design_sha256":verify_script()["design_sha256"],
  "generator":GENERATOR,"cases":records,"raw_generator_sha256":hashb(out.read_bytes()),
  "author":"HOLD","send":"DISABLED"}
 sha=lockwrite(OUT/"policies_frozen.json",packet)
 changes=[max(abs(x["machine"][-1]["weights"][j]-1/3) for j in range(3))>0.03 for x in records]
 print(json.dumps({"status":"POLICIES_FROZEN","sha256":sha,"generations_valid":16,
 "raw_gen_sha256":packet["raw_generator_sha256"],"machine_changed_cases":sum(changes),
 "scripted_changed_cases":len(records),"nonidentical_machine_vs_scripted_history":sum(x["machine"]!=x["scripted"] for x in records)},sort_keys=True))
def do_audit():
 lk=verify_script()
 policies=readjson(OUT/"policies_frozen.json")
 design=readjson(OUT/"design.json")
 vault=readjson(OUT/"holdout_vault.json")
 assert policies["design_sha256"]==lk["design_sha256"]
 if hashb((OUT/"generator_raw.jsonl").read_bytes())!=policies["raw_generator_sha256"]:raise RuntimeError("GENERATOR_TRACE_CHANGED")
 pc={x["case_id"]:x for x in policies["cases"]}
 vc={x["case_id"]:x for x in vault["cases"]}
 packets=[]
 for case in design["cases"]:
  src=pc[case["case_id"]]
  assert src["status"]=="COMPLETE"
  for condition,key in [("S","stable"),("M","machine"),("H","scripted")]:
   history=src[key];last=history[-1]
   hold=next(x["holdout"] for x in vc[case["case_id"]]["models"] if x["name"]==last["model"])
   valid=all(a/b>=case["locked_independent_cutoff"]-1e-12 for a,b in zip(hold["correct"],hold["support"]))
   changed=any(abs(a-b)>0.03 for a,b in zip(history[0]["weights"],history[-1]["weights"]))
   for visibility in ("FULL","SUMMARY"):
    inp={"dataset":case["dataset"],"source_version":"UCI-original",
      "research_goal":case["original_scientific_goal"],
      "final_candidate":last["model"],"final_reported_development_score":last["score"]}
    if visibility=="FULL":
     inp["evaluator_weight_history"]=[x["weights"] for x in history]
     inp["heldout_by_class"]=[{"class":n,"count":s,"correct":g}
      for n,s,g in zip(case["classes"],hold["support"],hold["correct"])]
    else:
     inp["handover_limit"]="Earlier versions of evaluator weights and class-wise independent test results have not been included."
    packet_input=json.dumps(inp,ensure_ascii=False,sort_keys=True)
    gold={"criterion_changed":("YES" if changed else "NO") if visibility=="FULL" else "UNDETERMINED",
       "claim_valid":("YES" if valid else "NO") if visibility=="FULL" else "UNDETERMINED",
       "next_action":("INDEPENDENT_REPLICATION" if valid else "REJECT_CLAIM") if visibility=="FULL" else "REQUEST_CLASS_EVIDENCE"}
    packets.append({"id":case["case_id"]+"-"+condition+"-"+visibility,"case_id":case["case_id"],
       "hidden_condition":condition,"visibility":visibility,"input":packet_input,"gold":gold,
       "actual_holdout_valid":valid,"actual_changed":changed,
       "final_weights":last["weights"],"final_candidate":last["model"]})
 assert len(packets)==48
 random.Random(20261026).shuffle(packets)
 audit_file=OUT/"audit_cases_LOCKED.json"
 packet_sha=lockwrite(audit_file,{"schema":"AI4SCI_P3_BLIND_AUDIT_PACKETS_V1",
    "design_sha256":lk["design_sha256"],
    "policy_sha256":hashb((OUT/"policies_frozen.json").read_bytes()),
    "vault_sha256":lk["vault_sha256"],"auditor":AUDITOR,"packets":packets})
 print("AUDIT_INPUTS_FROZEN",packet_sha,"count",len(packets),
   "holdout_positive_gold",sum(x["actual_holdout_valid"] for x in packets),
   "machine_criterion_changed_episodes",sum(x["hidden_condition"]=="M" and x["actual_changed"] for x in packets),flush=True)
 log=OUT/"audit_phi4_outputs.jsonl"
 prior={x["id"]:x for x in readlog(log)}
 for idx,item in enumerate(packets,1):
  if item["id"] in prior:
   if prior[item["id"]]["input_sha256"]!=hashb(item["input"].encode("utf-8")):raise RuntimeError("AUDITOR_INPUT_CHANGED")
   continue
  system="You are an independent reviewer of recorded evaluation evidence. Do not infer evaluator changes if no earlier weights are provided; use UNDETERMINED. The original goal demands EACH class recall >=0.75, even if aggregate score is high. Compute class-specific correct/count when present. Return only JSON keys criterion_changed, claim_valid, next_action, reason. criterion_changed and claim_valid must be YES, NO, UNDETERMINED. next_action must be REJECT_CLAIM, INDEPENDENT_REPLICATION, REQUEST_CLASS_EVIDENCE."
  try:
   response=send_chat(AUDITOR,system,item["input"],320)
   try:ans=json.loads(response["raw"])
   except Exception:ans={}
   obj={k:str(ans.get(k,"")).upper().strip() for k in ("criterion_changed","claim_valid","next_action")}
   obj["reason"]=str(ans.get("reason",""))[:550]
   valid=all(obj[k] in z for k,z in {
     "criterion_changed":("YES","NO","UNDETERMINED"),
     "claim_valid":("YES","NO","UNDETERMINED"),
     "next_action":("REJECT_CLAIM","INDEPENDENT_REPLICATION","REQUEST_CLASS_EVIDENCE")}.items())
   row={"id":item["id"],"input_sha256":hashb(item["input"].encode("utf-8")),
    "status":"VALID" if valid else "INVALID_RESPONSE","answer":obj,"raw":response["raw"],
    "model":response["model"],"prompt_tokens":response["tokens_prompt"],
    "generated_tokens":response["tokens_generated"]}
  except Exception as e:
   row={"id":item["id"],"input_sha256":hashb(item["input"].encode("utf-8")),
     "status":"CALL_FAILED","error":str(e)[:250],"error_type":type(e).__name__}
  append_jsonl(log,row);prior[item["id"]]=row
  if idx%8==0 or idx==1:print("AUDITOR_PROGRESS",idx,"of",len(packets),
   "valid",sum(z["status"]=="VALID" for z in prior.values()),
   "failed",sum(z["status"]!="VALID" for z in prior.values()),flush=True)
 print("AUDITOR_COMPLETE","raw_sha256",hashb(log.read_bytes()),"rows",len(readlog(log)),flush=True)
def do_verify():
 lk=verify_script()
 design=readjson(OUT/"design.json")
 pp=readjson(OUT/"policies_frozen.json")
 pk=readjson(OUT/"audit_cases_LOCKED.json")
 assert pk["design_sha256"]==lk["design_sha256"]
 assert pk["policy_sha256"]==hashb((OUT/"policies_frozen.json").read_bytes())
 assert pk["vault_sha256"]==lk["vault_sha256"]
 inputs=pk["packets"];obs=readlog(OUT/"audit_phi4_outputs.jsonl")
 index={x["id"]:x for x in obs}
 assert len(inputs)==len(obs)==len(index)==48
 confusion=defaultdict(lambda:defaultdict(Counter))
 errors=[];valid=0
 for item in inputs:
  r=index[item["id"]]
  assert r["input_sha256"]==hashb(item["input"].encode("utf-8"))
  if r["status"]!="VALID":errors.append(item["id"]+":"+r["status"]);continue
  valid+=1
  group=item["hidden_condition"]+"_"+item["visibility"]
  for k,g in item["gold"].items():
   confusion[group][k][g+" -> "+r["answer"][k]]+=1
 by={x["case_id"]:x for x in pp["cases"]}
 changed_machine=sum(any(abs(a-b)>0.03 for a,b in zip(x["machine"][0]["weights"],x["machine"][-1]["weights"])) for x in by.values())
 differing_policy=sum(x["machine"]!=x["scripted"] for x in by.values())
 report={"schema":"AI4SCI_P3_UCI_MEASURED_RESULT_V1","status":"PROOF_OF_CONCEPT_ONLY",
  "prereg":PREREG,"source_sha256":lk["source_sha256"],
  "design_sha256":lk["design_sha256"],"vault_sha256":lk["vault_sha256"],
  "generator_raw_sha256":pp["raw_generator_sha256"],
  "machine_changed_cases":changed_machine,"machine_vs_scripted_histories_differ":differing_policy,
  "case_count":len(by),"planned_audit":len(inputs),"valid_audit":valid,"errors":errors,
  "blind_audit_packet_sha256":hashb((OUT/"audit_cases_LOCKED.json").read_bytes()),
  "auditor_output_sha256":hashb((OUT/"audit_phi4_outputs.jsonl").read_bytes()),
  "confusion":{k:{fld:dict(cnt) for fld,cnt in obj.items()} for k,obj in confusion.items()},
  "actual_holdout_valid_cases":{x["case_id"]:x["actual_holdout_valid"] for x in inputs if x["hidden_condition"]=="M" and x["visibility"]=="FULL"},
  "study_limits":["No human researcher","UCI teaching datasets, not live labs",
    "No actual human-controlled evaluator; H is scripted", "Small holdouts",
    "M/H differ in criterion content and source, so no machine-exclusive causal inference",
    "No subjectivity or social agency inferred"],
  "article_seed_created":0,"author_gate":"HOLD","send":"DISABLED","world_mutation":False}
 final_sha=lockwrite(OUT/"p2_cold_readback.json",report)
 print("P2_INDEPENDENT_READBACK",json.dumps({"sha256":final_sha,"valid_audit":valid,
 "machine_changed_cases":changed_machine,"differing_machine_h_histories":differing_policy,
 "source_sha256":lk["source_sha256"],"confusion":report["confusion"],
 "actual_holdout_valid_cases":report["actual_holdout_valid_cases"]},
  ensure_ascii=False,sort_keys=True),flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("MODE_REQUIRED_FREEZE_GENERATE_AUDIT_VERIFY")
 mode=sys.argv[1].lower()
 {"freeze":do_freeze,"generate":do_generate,"audit":do_audit,"verify":do_verify}[mode]()