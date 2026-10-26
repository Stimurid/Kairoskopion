"""Cold source-stage acceptance for C01-R2/C09-R2, without generating articles or changing World."""
from pathlib import Path
from hashlib import sha256
import json
h=Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
def digest(p):return sha256(p.read_bytes()).hexdigest()
p=h/"successor_citation_gate_receipt_R2.json"
m=h/"manifest_source_successors_vR2.json"
b=json.loads(p.read_text(encoding="utf-8"))
orig=json.loads(m.read_text(encoding="utf-8"))
assert b["schema"]=="AI4SCI_SUCCESSOR_SOURCE_CITATION_GATE_V1"
assert b["case_id"]=="AI4SCI-C-20261026"
assert b["author_gate"]=="HOLD" and b["journal_send"]=="DISABLED" and not b["world_mutation"]
assert digest(p)=="f38dd3e790cf5b9ff2574c08ea1252a32e7b4dac410bc8f0dbe0002d9018eb62"
assert digest(m)=="659513b19dc8e2eb4d1c0a8aada3270ad689f65fb5ab90685fdf5c29ce68dd18"
assert len(orig["sources"])==6 and len(b["source_bindings"])==5
assert b["stage_summary"]["new_native_captures"]==6
assert b["stage_summary"]["whitecrow_context_packs"]==6
assert b["stage_summary"]["article_seed_created"]==0
assert b["stage_summary"]["external_send"]=="DISABLED"
expected={"C01-R2":"1zUYLFqYxqEz6iPVopClOS85mJTUxEfqvpW_sfPIZJGY",
          "C09-R2":"1UWWMSqxdGTEJOEvwJcApXSXON8YxfA_r6laEtuJzb-k"}
for k,id in expected.items():
 bound=b["source_bindings"][k]
 assert bound["source_id"]=="drive:"+id
 source=Path(bound["path"])
 assert source.is_file() and digest(source)==bound["raw_projection_sha256"]
 text=source.read_text(encoding="utf-8-sig")
 assert "Carlile (2002" in text and "Carlile (2004" in text
 assert "10.1287/orsc.13.4.442.2953" in text and "10.1287/orsc.1040.0094" in text
 assert "10.1177/030631289019003001" in text
 assert "1Bs98LbCtjcJp26oaPwysPA2_lPEeNEpbOnL_2N3sM88" in text
 assert b["citation_gate"][k]["status"]=="DETERMINISTIC_PRESENCE_PASS_SEMANTIC_SCIENCE_REVIEW_STILL_REQUIRED"
for k,bound in b["source_bindings"].items():
 assert digest(Path(bound["path"]))==bound["raw_projection_sha256"]
original=h/"successor_citation_gate_receipt_R1c.json"
assert original.is_file()
assert digest(original)=="53ec3ca82f198b20061928c52cda420fa06a461496f2b24370482ff44293cfdb"
# An independent disk search for the exact native Factory receipt, not a copied script assertion.
factory=h/"factory-SUCCESSORS-vR2"
hits=[]
for z in factory.rglob("*.json"):
 try:
  if digest(z)=="e42655c0d0e335b1ca03e075a83acbf4e604299d0eb00bb85bb87add4d0b60d9":
   hits.append(str(z))
 except OSError:pass
assert len(hits)==1,("NATIVE_FACTORY_RECEIPT_NOT_LOCATED",hits)
report={"schema":"AI4SCI_C01_C09_R2_INDEPENDENT_SOURCE_READBACK_V1",
 "case_id":"AI4SCI-C-20261026",
 "manifest_sha256":digest(m),
 "source_gate_receipt_sha256":digest(p),
 "native_factory_receipt_sha256":"e42655c0d0e335b1ca03e075a83acbf4e604299d0eb00bb85bb87add4d0b60d9",
 "native_factory_receipt_path":hits[0],
 "source_count":6,"native_captures":6,"whitecrow_context_packs":6,
 "citation_gate":{"C01-R2":"PASS_PRESENCE_NOT_SCIENCE","C09-R2":"PASS_PRESENCE_NOT_SCIENCE"},
 "R1c_receipt_sha256":digest(original),
 "author_approved_article_seeds":0,"external_send":"DISABLED","world_mutations":False,
 "scientific_novelty":"UNVERIFIED","next":"INDEPENDENT_SCIENCE_REVIEW_AND_AUTHOR_CONSENT"}
out=h/"successor_R2_cold_readback.json"
raw=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if out.exists() and out.read_bytes()!=raw:raise SystemExit("R2_COLD_READBACK_DIFFERENT")
if not out.exists():out.write_bytes(raw)
print(json.dumps({"status":"R2_COLD_VERIFIED","receipt_sha256":sha256(raw).hexdigest(),
 "factory_receipt":hits[0],"manifest":digest(m),
 "citation_gates":report["citation_gate"],"sources":6},ensure_ascii=False,sort_keys=True),flush=True)
