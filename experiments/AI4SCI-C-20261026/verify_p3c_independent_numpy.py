"""Independent NumPy replay of all P3 UCI Sonar/Ionosphere candidate dev & holdout counts.
Never calls/imports the P3 model implementation or changes original locked oracle.
"""
from pathlib import Path
from hashlib import sha256
import json,csv,io
import numpy as np
h=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
p=h/"evaldrift_P3";c=h/"evaldrift_P3c"
def load(f):return json.loads(f.read_text(encoding="utf-8"))
def sha(f):return sha256(f.read_bytes()).hexdigest()
lock=load(p/"lock.json");d=load(p/"design.json");vault=load(p/"holdout_vault.json")
packet=load(c/"p3c_audit_inputs_LOCKED.json")
assert sha(p/"design.json")==lock["design_sha256"]==packet["original_design_sha256"]
assert sha(p/"holdout_vault.json")==lock["vault_sha256"]==packet["original_vault_sha256"]
sources={}
for name in ("SONAR","IONOSPHERE"):
 f=p/(name.lower()+"_UCI_original.csv")
 assert sha(f)==lock["source_sha256"][name]
 rows=[x for x in csv.reader(io.StringIO(f.read_text(encoding="ascii"))) if x]
 X=np.array([[float(v) for v in x[:-1]] for x in rows],dtype=float)
 Y=np.array([x[-1] for x in rows])
 sources[name]=(X,Y)
byvault={v["case_id"]:v for v in vault["cases"]}
count=0
for case in d["cases"]:
 X,Y=sources[case["dataset"]]
 splits=case["split"]
 train=np.array(splits["train_indices"])
 dev=np.array(splits["dev_indices"])
 hold=np.array(splits["holdout_indices"])
 assert len(set(train)&set(dev))==len(set(train)&set(hold))==len(set(dev)&set(hold))==0
 assert len(train)+len(dev)+len(hold)==len(X)
 cls=case["classes"]
 gold={v["name"]:v["holdout"] for v in byvault[case["case_id"]]["models"]}
 for model in case["models"]:
  cols=np.array(model["feature_indices"])
  trainx=X[train][:,cols]
  means=trainx.mean(axis=0)
  std=trainx.std(axis=0)
  std[std<1e-12]=1.0
  cent=np.stack([trainx[Y[train]==z].mean(axis=0) for z in cls])
  cent=(cent-means)/std
  for split,ids,ref in [("dev",dev,model["dev"]),("holdout",hold,gold[model["name"]])]:
   q=(X[ids][:,cols]-means)/std
   pred=np.asarray(cls)[np.argmin(((q[:,None,:]-cent[None,:,:])**2).sum(axis=2),axis=1)]
   actual=Y[ids]
   support=[int(np.sum(actual==label)) for label in cls]
   correct=[int(np.sum((actual==label)&(pred==label))) for label in cls]
   recalls=[round(v/n,6) for v,n in zip(correct,support)]
   assert support==ref["support"],(case["case_id"],model["name"],split,"SUPPORT")
   assert correct==ref["correct"],(case["case_id"],model["name"],split,"CORRECT")
   assert recalls==ref["recall"],(case["case_id"],model["name"],split,"RECALL")
   count+=1
assert count==96
cases=packet["selected_policy_histories"]
assert len(cases)==5
checks=[]
for case in cases:
 name=case["case_id"]
 goldcase=byvault[name]
 ref={r["name"]:r["holdout"] for r in goldcase["models"]}
 line={"case_id":name}
 for letter,key in (("S","stable"),("M","machine"),("H","scripted")):
  chosen=case[key][-1]["model"]
  z=ref[chosen]
  recall=[a/b for a,b in zip(z["correct"],z["support"])]
  passgoal=all(x>=.75-1e-12 for x in recall)
  line[letter]={"model":chosen,"recall":[round(r,3) for r in recall],
       "valid":passgoal,"final_weights":case[key][-1]["weights"]}
 checks.append(line)
negative=sum(not z[t]["valid"] for z in checks for t in ("S","M","H"))
flips=sum(len({z["S"]["model"],z["M"]["model"],z["H"]["model"]})>1 for z in checks)
report={"schema":"AI4SCI_P3C_NUMPY_INDEPENDENT_ORACLE_V1",
 "original_sources":lock["source_sha256"],
 "design_sha256":lock["design_sha256"],"vault_sha256":lock["vault_sha256"],
 "audit_packet_sha256":sha(c/"p3c_audit_inputs_LOCKED.json"),
 "original_P3_raw_generator_sha256":packet["original_generator_raw_sha256"],
 "independent_dev_holdout_recomputations":count,"cases_eligible":5,
 "negative_case_conditions":negative,"any_choice_change_cases":flips,
 "comparisons":checks,"source_code":"INDEPENDENT_NUMPY_NOT_FROZEN_P3_MODEL",
 "scientific_limit":"No human, lab or machine-specific causal effect; source/classifier computational corroboration only"}
f=c/"p3c_independent_oracle.json"
raw=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if f.exists() and f.read_bytes()!=raw:raise RuntimeError("NUMPY_INDEPENDENT_OUTPUT_CHANGED")
if not f.exists():f.write_bytes(raw)
print(json.dumps({"status":"SOURCE_RECOMPUTE_VERIFIED","sha256":sha256(raw).hexdigest(),
    "dev_holdout_checks":count,"negative_case_conditions":negative,
    "choice_change_cases":flips,"case_matrix":checks},ensure_ascii=False,sort_keys=True),flush=True)