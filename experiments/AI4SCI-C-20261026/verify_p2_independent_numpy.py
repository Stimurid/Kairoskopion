"""Independent NumPy recomputation of P2 UCI holdout evidence from byte-pinned raw CSV.
Does not import the generating module or trust its reported per-class scores.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import numpy as np
import csv,io,json
root=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026\evaldrift_P2")
def readjson(p):return json.loads(p.read_text(encoding="utf-8"))
def h(p):return sha256(p.read_bytes()).hexdigest()
design=readjson(root/"design.json")
vault=readjson(root/"holdout_vault.json")
locked=readjson(root/"lock.json")
policies=readjson(root/"policies_frozen.json")
assert h(root/"design.json")==locked["design_sha256"]
assert h(root/"holdout_vault.json")==locked["vault_sha256"]
sources={}
for name in ("IRIS","WINE"):
 p=root/(name.lower()+"_UCI_original.csv")
 assert h(p)==locked["source_sha256"][name]
 rows=[x for x in csv.reader(io.StringIO(p.read_text(encoding="ascii"))) if x]
 if name=="IRIS":X=np.array([[float(s) for s in row[:4]] for row in rows],dtype=float);Y=np.array([row[4] for row in rows])
 else:X=np.array([[float(s) for s in row[1:]] for row in rows],dtype=float);Y=np.array(["class_"+row[0] for row in rows])
 sources[name]=(X,Y)
case_vault={r["case_id"]:r for r in vault["cases"]}
case_policies={r["case_id"]:r for r in policies["cases"]}
checks=0
matrix=[]
for case in design["cases"]:
 X,Y=sources[case["dataset"]]
 train=np.asarray(case["split"]["train_indices"],dtype=int)
 dev=np.asarray(case["split"]["dev_indices"],dtype=int)
 hold=np.asarray(case["split"]["holdout_indices"],dtype=int)
 assert not set(train)&set(dev) and not set(train)&set(hold) and not set(dev)&set(hold)
 assert len(train)+len(dev)+len(hold)==len(X)
 labels=case["classes"]
 expected={r["name"]:r["holdout"] for r in case_vault[case["case_id"]]["models"]}
 for candidate in case["models"]:
  cols=np.asarray(candidate["feature_indices"],dtype=int)
  train_x=X[train][:,cols]
  mean=train_x.mean(axis=0)
  scales=train_x.std(axis=0)
  scales[scales<1e-12]=1.0
  classcenters=np.stack([train_x[Y[train]==cl].mean(axis=0) for cl in labels])
  def predict(ix):
   z=(X[ix][:,cols]-mean)/scales
   cent=(classcenters-mean)/scales
   distances=((z[:,None,:]-cent[None,:,:])**2).sum(axis=2)
   return np.asarray(labels)[np.argmin(distances,axis=1)]
  for subset,ix,reference in [("dev",dev,candidate["dev"]),("holdout",hold,expected[candidate["name"]])]:
   pred=predict(ix)
   truth=Y[ix]
   support=[int(np.sum(truth==cl)) for cl in labels]
   correct=[int(np.sum((truth==cl)&(pred==cl))) for cl in labels]
   recall=[round(a/b,6) for a,b in zip(correct,support)]
   assert support==reference["support"],(case["case_id"],candidate["name"],subset,"SUPPORT",support,reference["support"])
   assert correct==reference["correct"],(case["case_id"],candidate["name"],subset,"CORRECT",correct,reference["correct"])
   assert recall==reference["recall"],(case["case_id"],candidate["name"],subset,"RECALL",recall,reference["recall"])
   checks+=1
 policy=case_policies[case["case_id"]]
 row={"case_id":case["case_id"],"dataset":case["dataset"],
     "source_sha256":locked["source_sha256"][case["dataset"]],
     "n_dev":len(dev),"n_holdout":len(hold)}
 for kind,key in [("S","stable"),("M","machine"),("H","scripted")]:
  end=policy[key][-1]
  hold=expected[end["model"]]
  class_recall=[a/b for a,b in zip(hold["correct"],hold["support"])]
  passed=all(v>=0.80-1e-12 for v in class_recall)
  row[kind]={"model":end["model"],"final_weights":end["weights"],
      "dev_score":end["score"],"holdout_recalls":[round(z,3) for z in class_recall],
      "all_class_threshold_pass":passed}
 matrix.append(row)
assert checks==80
assert len(matrix)==8
output={"schema":"AI4SCI_P2_NUMPY_INDEPENDENT_ORACLE_V1","status":"ALL_80_SOURCE_SUBSET_COUNTERS_MATCH",
 "independent_implementation":"NUMPY_VECTOR_CENTROIDS_NOT_IMPORTING_P2_GENERATOR",
 "source_sha256":locked["source_sha256"],"design_sha256":locked["design_sha256"],
 "vault_sha256":locked["vault_sha256"],"policy_sha256":h(root/"policies_frozen.json"),
 "auditor_raw_sha256":h(root/"audit_phi4_outputs.jsonl"),
 "cases":matrix,"independent_dev_holdout_recomputations":checks,
 "all_holdouts_meet_original_recall_constraint":all(row[t]["all_class_threshold_pass"] for row in matrix for t in ("S","M","H")),
 "n_case_condition_pass":sum(row[t]["all_class_threshold_pass"] for row in matrix for t in ("S","M","H")),
 "n_case_condition_total":24,
 "scientific_scope":"Teaching datasets and deterministic centroid classifiers; no live lab, humans or original method novelty",
 "rights":"OWNER_HOLD","send":"DISABLED"}
out=root/"p2_independent_numeric_oracle.json"
raw=(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if out.exists() and out.read_bytes()!=raw:raise RuntimeError("INDEPENDENT_RESULT_DIFFERENCE")
if not out.exists():out.write_bytes(raw)
print(json.dumps({"status":output["status"],"sha256":sha256(raw).hexdigest(),
    "recomputations":checks,"n_case_condition_pass":output["n_case_condition_pass"],
    "matrix":matrix},ensure_ascii=False,sort_keys=True),flush=True)