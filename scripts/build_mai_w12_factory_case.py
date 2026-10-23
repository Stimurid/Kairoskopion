"""Create a private TRM074 Factory source manifest from W12 packets + pinned Drive text projections.

This stage is source admission only: it does not warrant novelty, published
journal policy, author consent, field acceptance or manuscript submission.
The manifest stays PRIVATE. Input W12 dossiers must already be authenticated
and produced by the existing MAI W12 packet materializer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "TRM074_COLD_CASE_V1"
W12_SOURCE_SCOPE = "W12_SECONDARY_RESEARCH_SYNTHESIS_ONLY"
ALLOWED_KINDS = {"RESEARCH_SYNTHESIS", "CONCEPT_BASELINE", "SPEECH_SCRIPT", "RESEARCH_CONTEXT"}
ALLOWED_STATES = {"NOT_VERIFIED", "RESEARCH_RETURN_NOT_AUTHOR_APPROVAL"}
ALLOWED_COVERAGE = {"RESEARCH_SYNTHESIS_TEXT_ONLY", "TEXT_EXTRACT_ONLY"}
SHEET_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
RANGE = re.compile(r"^A([2-9]|[1-9][0-9]+):M\1$")
CASE_ID = re.compile(r"^[A-Za-z0-9_-]{3,100}$")

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def _check_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("missing/empty authorized source "+str(path))
    return path

def build_case(packet_root: Path, donor_manifest: Path, case_id: str) -> dict[str,Any]:
    if not CASE_ID.fullmatch(case_id):
        raise ValueError("invalid case_id")
    meta=load(packet_root/"manifest.json")
    if meta.get("schema")!="MAI_W12_BATCH_OUTPUT_MANIFEST_v1":
        raise ValueError("unrecognized W12 packet schema")
    packet_paths=sorted((packet_root/"routes").glob("MAI-W12-*.json"))
    if not packet_paths or len(packet_paths)!=meta.get("records"):
        raise ValueError("packet count mismatch")
    sources=[]
    ids=set()
    for path in packet_paths:
        pkt=load(path)
        if pkt.get("schema")!="MAI_W12_BATCH_RESEARCH_PACKET_v1":
            raise ValueError("unexpected W12 route packet")
        r=pkt["route"]
        source_id=str(r.get("original_spreadsheet_id") or "")
        cell=str(r.get("source_cell_range") or "")
        rid=str(r["route_id"])
        if (not SHEET_ID.fullmatch(source_id) or not RANGE.fullmatch(cell)
             or r.get("source_authority")!="LIVE_AUTHENTICATED_GOOGLE_SHEET_DERIVED"
             or r.get("not_original_xlsx_bytes") is not True
             or r.get("target_status")!="POLICY_UNVERIFIED"):
            raise ValueError("W12 sheet provenance not accepted "+rid)
        md=_check_file(packet_root/"routes"/(rid+".md"))
        # No false identity: a row is a source-within-SHEET, never a Doc.
        sid=f"w12-sheet:{source_id}:{cell}:MAI-20261020"
        if sid in ids: raise ValueError("duplicate source id")
        ids.add(sid)
        sources.append({
            "family":r["family"],"key":rid.replace("MAI-W12-","W"),
            "kind":"RESEARCH_SYNTHESIS","version":r["variant"],
            "source_id":sid,
            "source_url":f"https://docs.google.com/spreadsheets/d/{source_id}/edit#range={cell}",
            "local_path":str(md),
            "read_coverage":"RESEARCH_SYNTHESIS_TEXT_ONLY",
            "author_state":"RESEARCH_RETURN_NOT_AUTHOR_APPROVAL",
            "scope":W12_SOURCE_SCOPE,
            "title":r["journal"]+" / "+r["variant"],
            "source_mime":"text/markdown",
            "original_route_id":rid,
            "claims_read":"W12_SECONDARY_SUMMARY_NOT_VENUE_POLICY",
        })
    raw=load(donor_manifest)
    if not isinstance(raw,dict) or raw.get("schema")!="MAI_INDAGO_DONOR_TEXT_PROJECTIONS_v1":
        raise ValueError("invalid donor manifest schema")
    donors=raw.get("sources")
    if not isinstance(donors,list):
        raise ValueError("donor.sources must be a list")
    for item in donors:
        fid=str(item.get("drive_file_id") or "")
        if not DRIVE_ID.fullmatch(fid): raise ValueError("invalid donor stable Drive id")
        url="https://docs.google.com/document/d/"+fid+"/edit"
        if item.get("url")!=url: raise ValueError("Drive URL/ID mismatch")
        local=_check_file(Path(item["local_path"]))
        kind=item.get("kind")
        state=item.get("author_state")
        coverage=item.get("read_coverage")
        if kind not in ALLOWED_KINDS or state not in ALLOWED_STATES or coverage not in ALLOWED_COVERAGE:
            raise ValueError("unsupported donor kind/author/read-coverage")
        if not item.get("source_scope") or "PROJECTION" not in item["source_scope"]:
            raise ValueError("donor must be labelled as connector TEXT PROJECTION")
        if item.get("provider_original_bytes_verified") is not False:
            raise ValueError("donor projection must not claim original Drive raw-byte verification")
        sid="drive:"+fid
        if sid in ids: raise ValueError("duplicate donor source_id "+sid)
        ids.add(sid)
        sources.append({
            "family":item["family"],"key":item["key"],
            "kind":kind,"version":item["version"],
            "source_id":sid,"source_url":url,"local_path":str(local),
            "read_coverage":coverage,"author_state":state,
            "scope":item["source_scope"],"title":item.get("title",""),
            "source_mime":"text/plain",
            "provider_original_bytes_verified":False,
            "source_projection":"GOOGLE_DRIVE_CONNECTOR_TEXT_NOT_NATIVE_RAW",
        })
    return {
        "schema":SCHEMA,"case_id":case_id,"publication_send":"DISALLOWED",
        "sources":sources,"version_edges":[],"delta_pairs":[],
        "decision_events":[],"discussion_events":[],
        "missing_carriers":[
            {"family":"MAI","kind":"PRACTICES_2_TO_4_ORIGINAL_FILES",
             "status":"NOT_LOCATED_NOT_ASSUMED"},
            {"family":"MAI","kind":"CONSENT_FOR_PLAUD_PUBLICATION",
             "status":"NOT_VERIFIED_NOT_ASSUMED"},
            {"family":"B_C_F","kind":"ORIGINAL_AUTHOR_AND_EMPIRICAL_SOURCE_CARRIERS",
             "status":"NOT_INCLUDED_IN_THIS_INGEST"},
        ],
        "metadata":{
            "source_count":len(sources),
            "W12_secondary_routes":len(packet_paths),
            "indago_or_author_donors":len(donors),
            "science_qualification":"NOT_PERFORMED",
            "scope":"SOURCE_AND_CONTEXT_ADMISSION_ONLY",
            "source_09_provenance":meta.get("source_jsonl_sha256"),
        }
    }

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--donors",type=Path,required=True)
    p.add_argument("--case-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    case=build_case(a.packets,a.donors,a.case_id)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(case,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"case_id":a.case_id,"route_count":case["metadata"]["W12_secondary_routes"],
        "donor_count":case["metadata"]["indago_or_author_donors"],
        "source_count":len(case["sources"]),"output":str(a.output)},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
