"""P3c independent source-byte numerical oracle: independently recompute all 96
UCI train-only centroid candidate dev/holdout class counters; verify all P3c
evaluator selections and validation gold. No import of P3 generating module.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import numpy as np
import csv,io,json

h=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
root=h/"evaldrift_P3"; cdir=h/"evaldrift_P3c"
def readj(p):return json.loads(p.read_text(encoding="utf-8"))
def hb(p):return sha256(p.read_bytes()).hexdigest()
lock=readj(root/"lock.json")
design=readj(root/"design.json")
vault=readj(root/"holdout_vault.json")
snap=readj(cdir/"p3c_audit_inputs_LOCKED.json")
assert hb(root/"design.json")==lock["design_sha256"]
assert hb(root/"holdout_vault.json")==lock["vault_sha256"]
assert snap["original_design_sha256"]==lock["design_sha256"]
assert snap["original_vault_sha256"]==lock["vault_sha256"]
data={}
for name in ("SONAR","IONOSPHERE"):
 p=root/(name.lower()+"_UCI_original.csv")
 assert hb(p)==lock["source_sha256"][name]
 rows=[r for r in csv.reader(io.StringIO(p.read_text(encoding="ascii"))) if r]
 x=np.array([[float(v) for v in row[:-1]] for row in rows],dtype=float)
 y=np.array([row[-1] for row in rows])
 assert len(x)==(208 if name=="SONAR" else 351) and x.shape[1]==(60 if name=="SONAR" else 34)
 data[name]=(x,y)
vv={x["case_id"]:x for x in vault["cases"]}
original_cases={x["case_id"]:x for x in design["cases"]}
pols={x["case_id"]:x for x in snap["selected_policy_histories"]}
assert len(pols)==5 and len(design["cases"])==8
checks=0
recomputed={}
for case in design["cases"]:
 name=case["case_id"];X,Y=data[case["dataset"]]
 train=np.array(case["split"]["train_indices"],dtype=int)
 dev=np.array(case["split"]["dev_indices"],dtype=int)
 hold=np.array(case["split"]["holdout_indices"],dtype=int)
 assert len(set(train)&set(dev))==0
 assert len(set(train)&set(hold))==0
 assert len(set(dev)&set(hold))==0
 assert len(train)+len(dev)+len(hold)==len(X)
 labels=case["classes"]
 reference={m["name"]:m["holdout"] for m in vv[name]["models"]}
 model_results={}
 for model in case["models"]:
  cols=np.array(model["feature_indices"],dtype=int)
  tx=X[train][:,cols]
  center=np.stack([tx[Y[train]==cl].mean(axis=0) for cl in labels])
  mu=tx.mean(axis=0);sigma=tx.std(axis=0)
  sigma[sigma<1e-12]=1.0
  def predict(indices):
   z=(X[indices][:,cols]-mu)/sigma
   zcent=(center-mu)/sigma
   sq=((z[:,None,:]-zcent[None,:,:])**2).sum(axis=2)
   return np.asarray(labels)[np.argmin(sq,axis=1)]
  result={}
  for tag,idx,ref in [("dev",dev,model["dev"]),("holdout",hold,reference[model["name"]])]:
   pred=predict(idx)
   actual=Y[idx]
   counts=[int(np.sum(actual==cl)) for cl in labels]
   good=[int(np.sum((actual==cl)&(pred==cl))) for cl in labels]
   rates=[round(a/b,6) for a,b in zip(good,counts)]
   assert counts==ref["support"],(name,model["name"],tag,"SUPPORT",counts,ref)
   assert good==ref["correct"],(name,model["name"],tag,"CORRECT",good,ref)
   assert rates==ref["recall"],(name,model["name"],tag,"RATE",rates,ref)
   result[tag]={"support":counts,"correct":good,"recall":rates}
   checks+=1
  model_results[model["name"]]=result
 recomputed[name]=model_results
assert checks==96
bycase={}
for case in pols.values():
 name=case["case_id"];parent=original_cases[name]
 out={}
 for condition,key in [("S","stable"),("M","machine"),("H","scripted")]:
  last=case[key][-1]
  hold=recomputed[name][last["model"]]["holdout"]
  goodness=all(v>=0.75-1e-12 for v in hold["recall"])
  out[condition]={"selected":last["model"],"final_weights":last["weights"],
     "support":hold["support"],"correct":hold["correct"],"recall":hold["recall"],
     "gold_claim_valid":goodness}
 bycase[name]=out
for x in snap["audit_packets"]:
 if x["visibility"]!="FULL":continue
 truth=bycase[x["case_id"]][x["hidden_condition"]]["gold_claim_valid"]
 assert x["scientific_holdout_valid"]==truth,(x["id"],truth)
 assert x["gold"]["claim_valid"]==("YES" if truth else "NO")
assert sum(sum(x[c]["gold_claim_valid"] for c in ("S","M","H")) for x in bycase.values())==2
assert sum(len(set(x[c]["selected"] for c in ("S","M","H")))>1 for x in bycase.values())==3
out={"schema":"AI4SCI_P3C_NUMPY_INDEPENDENT_ORACLE_V1",
 "status":"ALL_SOURCE_AND_EVALUATOR_OUTCOMES_MATCH",
 "raw_sources_sha256":lock["source_sha256"],
 "original_design_sha256":lock["design_sha256"],
 "original_holdout_sha256":lock["vault_sha256"],
 "p3c_auditor_input_sha256":hb(cdir/"p3c_audit_inputs_LOCKED.json"),
 "independent_code":"NUMPY_MATRIX_NEAREST_CENTROID_NOT_IMPORTING_P3_OR_P3C",
 "original_cases":8,"included_cases":5,"blocked_cases":3,"blocked_episodes":18,
 "independent_candidate_subset_recomputations":checks,
 "case_conditions":bycase,
 "negative_holdout_case_conditions":13,
 "selected_model_flip_cases_any_arm":3,
 "machine_vs_stable_decision_flip_cases":sum(x["M"]["selected"]!=x["S"]["selected"] for x in bycase.values()),
 "next":"Store as negative/positive case evidence, no novelty/admission claim",
 "author":"HOLD","send":"DISABLED"}
dest=cdir/"p3c_independent_numeric_oracle.json"
raw=(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if dest.exists() and dest.read_bytes()!=raw:raise SystemExit("INDEPENDENT_ORACLE_OUTPUT_DIFF")
if not dest.exists():dest.write_bytes(raw)
print(json.dumps({"status":out["status"],"sha256":sha256(raw).hexdigest(),
 "checks":checks,"negative":out["negative_holdout_case_conditions"],
 "flips_any_arm":out["selected_model_flip_cases_any_arm"],
 "flips_machine_vs_stable":out["machine_vs_stable_decision_flip_cases"],
 "results":bycase},ensure_ascii=False,sort_keys=True),flush=True)
