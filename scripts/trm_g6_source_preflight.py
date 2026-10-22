"""Reproducible G6 source pack gate: fail before spawning an empty hunt.

This is NOT an L3 journal fit or scientific novelty certification.
Run with python scripts/trm_g6_source_preflight.py in the assigned Git worktree.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib, json, sys

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"benchmarks/_operator_notes/trm_g5_operator_20261022"
INDEX=ROOT/"data/venue_evidence_packs/g5_operator_official_20261022.jsonl"
SCIENCE=PACK/"g6_scientific_currentness_brief.md"

def read_jsonl(path:Path)->list[dict]:
    return [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines()
            if row.strip()]

def preflight()->dict:
    if not INDEX.is_file() or not SCIENCE.is_file():
        raise RuntimeError("SOURCE_PACK_NOT_VISIBLE_IN_WORKTREE")
    index=read_jsonl(INDEX)
    detail=read_jsonl(PACK/"article_pages_v3.jsonl")
    witnesses=read_jsonl(PACK/"primary_pdf_witnesses.jsonl")
    analogs=read_jsonl(PACK/"indago_analog_backlog.jsonl")
    manifest=json.loads((PACK/"repo_pack_manifest.json").read_text(encoding="utf-8"))
    assert len(index)==92 and len({x["record_id"] for x in index})==92
    assert dict(Counter(x["venue"] for x in index))=={
        "VF":22,"FJ":15,"EPN":15,"LOGOS":28,"DS":12}
    assert len(detail)==63 and sum(x["status"]=="OBSERVED" for x in detail)==26
    assert len(witnesses)==12 and sum(x["page_count"] for x in witnesses)==171
    assert len(analogs)==8 and all(x["independent_novelty_verdict"]!="PASS"
                                  for x in analogs)
    assert all(not x["novelty_reviewed"] for x in witnesses)
    assert all(not x["scientific_claim_support_reviewed"] for x in witnesses)
    assert "H0 preferred" in SCIENCE.read_text(encoding="utf-8")
    assert "2017" in SCIENCE.read_text(encoding="utf-8")
    assert manifest["private_fulltext_copied_to_git"] is False
    for item in manifest["tracked_entries"]:
        f=ROOT/item["repo_path"]
        assert f.is_file(),item["repo_path"]
        assert hashlib.sha256(f.read_bytes()).hexdigest()==item["sha256"]
    return dict(status="SOURCE_PACK_VISIBLE_AND_INTACT",index=92,
                real_detail_pages=26,actual_pdf_witnesses=12,extracted_pages=171,
                analog_backlog_count=8,scientifically_qualified_pairs=0,
                private_primary_fulltexts_in_checkout=False)

if __name__=="__main__":
    try: print(json.dumps(preflight(),ensure_ascii=False,sort_keys=True))
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED_SOURCE_PACK","error":str(exc)},
                         ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
