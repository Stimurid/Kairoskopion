"""Real source-only Factory intake: C01-R1/C09-R1 + source library, scientific R3, pilot P0.
Never overwrite immutable R0 Factory/W12 receipts, never author-admit an article.
"""
from pathlib import Path
from hashlib import sha256
import json,sys,os,subprocess,re
here=Path(__file__).resolve().parent
original=json.loads((here/"manifest.json").read_text(encoding="utf-8"))
assert original["case_id"]=="AI4SCI-C-20261026" and len(original["sources"])==9
rows=[
 ("C01-R2","C01","RESEARCH_SYNTHESIS","vR2","1zUYLFqYxqEz6iPVopClOS85mJTUxEfqvpW_sfPIZJGY"),
 ("C09-R2","C09","RESEARCH_SYNTHESIS","vR2","1UWWMSqxdGTEJOEvwJcApXSXON8YxfA_r6laEtuJzb-k"),
 ("SOURCE-LIB","SOURCE-LIBRARY","RESEARCH_CONTEXT","r2","1Bs98LbCtjcJp26oaPwysPA2_lPEeNEpbOnL_2N3sM88"),
 ("SCIENCE-P3D","REVIEW","EDITORIAL_COMPARISON","p3d","1VxwF0WPsJC9a3g3qUGueByGkmZ-V5RD9kOMRfPq1uKg"),
 ("P3-PROTOCOL","PILOT","RESEARCH_CONTEXT","p3b","1ScJXccjCwwYaf3IXrcd5-1NRzs2B36pHEjlU37EvNIU"),
]
manifest=json.loads(json.dumps(original))
manifest["sources"]=[s for s in manifest["sources"] if s["key"]=="C03"]
manifest["version_edges"]=[]
manifest["delta_pairs"]=[]
for key,family,kind,version,source in rows:
 manifest["sources"].append({
   "key":key,"family":family,"kind":kind,"version":version,
   "author_state":"AI_EDITORIAL_PROPOSAL_NOT_AUTHOR_APPROVAL" if key!="SOURCE-LIB" else "NOT_VERIFIED",
   "source_id":"drive:"+source,
   "source_url":"https://docs.google.com/document/d/"+source+"/edit",
   "capture_transport":"native_docs"})
assert len(manifest["sources"])==6
encoded=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
mp=here/"manifest_source_successors_vR2.json"
if mp.exists() and mp.read_bytes()!=encoded:
  raise SystemExit("PINNED_SUCCESSOR_MANIFEST_CHANGED")
if not mp.exists():mp.write_bytes(encoded)
checkout=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\r4-factory-batch128-20261024")
config=Path(r"C:\AI\llm\aiye-executor\TRM040_HOST_CLI_ADAPTER_CONFIG_20261011.json")
template=json.loads(config.read_text(encoding="utf-8"))["command_template"]
env=os.environ.copy()
env["TRIMURTI_DOCS_FETCH_COMMAND"]=json.dumps(template)
env["LITOPS_SKIP_DOTENV"]="1"
env["LITOPS_ROOT"]=str(here/"litops-successors-R2")
env["PYTHONPATH"]=os.pathsep.join([str(checkout/"src"),
 r"C:\AI\llm\aiye-executor\worktrees\jx-227ada9c6fd6",
 r"C:\projects\trimurti\whitecrow\conceptarticle",
 r"C:\projects\trimurti\whitecrow\whitecrow-skeleton"])
storage=here/"factory-SUCCESSORS-vR2"
native=here/"native-source-captures-R2"
cmd=[sys.executable,str(checkout/"scripts"/"run_factory_source_stage.py"),
 "--manifest",str(mp),"--storage-root",str(storage),
 "--native-capture-root",str(native),"--litops-root",str(here/"litops-successors-R2")]
res=subprocess.run(cmd,env=env,cwd=checkout,capture_output=True,text=True,timeout=900)
if res.returncode:
 (here/"successor_R2_capture_error.txt").write_text(res.stderr[:20000],encoding="utf-8")
 print("SUCCESSOR_FACTORY_BLOCKED",res.stderr[:1000].replace("\n"," | "))
 raise SystemExit(res.returncode)
report=json.loads(res.stdout)
# Every new article version is read from actual freshly captured native Docs projection,
# not from a synthetic paraphrase.
bindings={}
for key,family,kind,version,source in rows:
 files=list((native/"text").glob(source+"_*.txt"))
 if len(files)!=1:raise SystemExit("NATIVE_CAPTURE_NOT_UNIQUE:"+key)
 raw=files[0].read_bytes()
 txt=raw.decode("utf-8-sig")
 bindings[key]={"source_id":"drive:"+source,"version":version,"path":str(files[0]),
      "raw_projection_sha256":sha256(raw).hexdigest(),"chars":len(txt),
      "read_depth":"NATIVE_DOCS_TEXT_FULL_PROJECTION_COMMENTS_NOT_ACQUIRED"}
citation_gate={}
for key in ("C01-R2","C09-R2"):
 x=bindings[key]
 text=Path(x["path"]).read_text(encoding="utf-8-sig")
 starts=text.find("7. ПОЛНЫЕ ИСТОЧНИКИ") if key=="C01-R2" else text.find("6. ПЕРВОИСТОЧНИКИ")
 if starts<0:raise SystemExit("BIBLIOGRAPHY_SCOPE_NOT_FOUND:"+key)
 body=text[:starts]
 bib=text[starts:]
 required=[
    ("Carlile2002_in_body",("Carlile, 2002" in body or "Carlile (2002" in body)),
    ("Carlile2004_in_body",("Carlile, 2004" in body or "Carlile (2004" in body)),
    ("Carlile2002_bib_doi","10.1287/orsc.13.4.442.2953" in bib),
    ("Carlile2004_bib_doi","10.1287/orsc.1040.0094" in bib),
    ("StarGriesemer_bib_doi","10.1177/030631289019003001" in bib),
    ("SourceRegistryReference","1Bs98LbCtjcJp26oaPwysPA2_lPEeNEpbOnL_2N3sM88" in text),
 ]
 if not all(ok for _,ok in required):raise SystemExit("CITATION_GATE_FAILED:"+key+":"+str(required))
 citation_gate[key]={"checks":{name:ok for name,ok in required},
     "status":"DETERMINISTIC_PRESENCE_PASS_SEMANTIC_SCIENCE_REVIEW_STILL_REQUIRED",
     "body_chars":len(body),"bibliography_chars":len(bib),
     "projection_sha256":x["raw_projection_sha256"]}
audit={
  "schema":"AI4SCI_SUCCESSOR_SOURCE_CITATION_GATE_V1",
  "case_id":"AI4SCI-C-20261026",
  "primary_case_immutable_receipt_sha256":"8196ad7131b3b3bd74fb0e6af93c127cb93b0e9586c881aa365e0767f369ac87",
  "prior_W3_W12_immutable_batch_sha256":"0a65810f560e094f40c605c2cecb3a34cf0203aa1c618062520ae9b3918d4edc",
  "manifest_sha256":sha256(mp.read_bytes()).hexdigest(),
  "lineage":[{"from":"C01-R1","to":"C01-R2","relation":"SOURCE_BOUND_PROPOSED_VERSION_NOT_AUTHOR_ADMITTED"},
            {"from":"C09-R1","to":"C09-R2","relation":"SOURCE_BOUND_PROPOSED_VERSION_NOT_AUTHOR_ADMITTED"}],
  "source_bindings":bindings,
  "citation_gate":citation_gate,
  "stage_summary":{k:report.get(k) for k in [
    "source_snapshot_count","native_source_count","new_native_captures",
    "reused_native_captures","whitecrow_context_packs","receipt_sha256",
    "w3_proposed_unqualified_routes","article_seed_created","external_send"]},
  "source_folder":"C:\\projects\\trimurti\\_ops\\AI4SCI-C-20261026",
  "author_gate":"HOLD","world_mutation":False,"journal_send":"DISABLED"}
af=here/"successor_citation_gate_receipt_R2.json"
a_raw=(json.dumps(audit,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if af.exists() and af.read_bytes()!=a_raw:raise SystemExit("SUCCESSOR_GATE_RECEIPT_CHANGED")
if not af.exists():af.write_bytes(a_raw)
print(json.dumps({"status":"PASS","manifest_sha256":audit["manifest_sha256"],
 "source_count":len(manifest["sources"]),
 "native_captures":audit["stage_summary"],
 "citation_gates":{x:v["status"] for x,v in citation_gate.items()},
 "receipt_sha256":sha256(a_raw).hexdigest()},ensure_ascii=False,sort_keys=True,indent=2))
