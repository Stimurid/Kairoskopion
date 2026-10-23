"""MAI prior-art verification: retrieve source records via real Crossref/OpenAlex APIs.

Input: authenticated W12 packets & INDAGO source-linked 53 scientific HOLD dossiers.
Output: immutable cached API JSON, per-route verified DOI/abstract *read depth*
and a replayable source receipt. No autonomous philosophical judgment, novel
article admission, editorial policy certification or external manuscript send.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

DOI_RE=re.compile(r"^10\.\d{4,9}/[A-Za-z0-9_.;():+%\-~/]+$", re.I)
API_BASES={
    "crossref":"https://api.crossref.org/works/",
    "openalex":"https://api.openalex.org/works/https://doi.org/",
}
USER_AGENT="Kairoskopion-MAI-Scholarly-Source-Verification/0.1 (research index; Crossref and OpenAlex API)"
SCHEMA="MAI_PRIOR_ART_AUTHENTICATED_API_EVIDENCE_v1"
MAX_RESPONSE=1_500_000
MAX_ABSTRACT=10000

class StripHTML(HTMLParser):
    def __init__(self)->None:
        super().__init__(convert_charrefs=True)
        self.parts:list[str]=[]
    def handle_data(self,s:str)->None:
        self.parts.append(s)

def normalize_doi(s:str)->str:
    s=s.strip()
    if s.lower().startswith("https://doi.org/"):
        s=s[len("https://doi.org/"):]
    elif s.lower().startswith("http://dx.doi.org/"):
        s=s[len("http://dx.doi.org/"):]
    s=s.strip().rstrip(".,)")
    if not DOI_RE.fullmatch(s):raise ValueError("invalid DOI string: "+s[:90])
    return s.lower()

def stable(obj:Any)->bytes:
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def put(path:Path,value:Any)->None:
    content=stable(value)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(content);tmp.replace(path)

def abstract_html_to_text(source:Any)->str:
    if not isinstance(source,str):return ""
    h=StripHTML()
    try:h.feed(source)
    except Exception:return ""
    return re.sub(r"\s+"," "," ".join(h.parts)).strip()[:MAX_ABSTRACT]

def inverted_index_to_text(value:Any)->str:
    if not isinstance(value,dict) or not value:return ""
    seq={}
    for term,positions in value.items():
        if not isinstance(positions,list):continue
        for pos in positions:
            if isinstance(pos,int) and 0<=pos<10000:
                seq[pos]=term
    if not seq:return ""
    ordered=[seq.get(i,"") for i in range(max(seq)+1)]
    return re.sub(r"\s+"," "," ".join(ordered)).strip()[:MAX_ABSTRACT]

def api_url(backend:str,doi:str)->str:
    return API_BASES[backend]+quote(doi,safe="/")

def query(backend:str,doi:str,cache:Path,timeout:float=18)->dict[str,Any]:
    doi=normalize_doi(doi)
    d=cache/sha(doi.encode("utf-8"))[:20]
    path=d/(backend+".json")
    if path.exists():
        saved=json.loads(path.read_text(encoding="utf-8"))
        if saved.get("requested_doi")!=doi or saved.get("backend")!=backend:
            raise ValueError("DOI cache identity drift: "+str(path))
        # Require verified raw result SHA, not cached superficial receipt
        rawfile=d/(backend+".response.json")
        if saved.get("http_status")==200:
            if not rawfile.is_file() or sha(rawfile.read_bytes())!=saved.get("raw_response_sha256"):
                raise ValueError("cached published-source raw bytes drift "+doi)
        saved["from_cache"]=True
        return saved
    url=api_url(backend,doi)
    stamp=datetime.now(timezone.utc).isoformat()
    status=None
    error=None
    data=None
    raw=b""
    for attempt in range(3):
        try:
            req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
            with urlopen(req,timeout=timeout) as response:
                status=response.status
                raw=response.read(MAX_RESPONSE+1)
                if len(raw)>MAX_RESPONSE:raise ValueError("API response too large")
                if status==200:
                    data=json.loads(raw.decode("utf-8"))
            break
        except HTTPError as exc:
            status=exc.code
            error=str(exc)
            if status in (429,500,502,503,504) and attempt<2:
                time.sleep(1.5*(attempt+1))
                continue
            break
        except (URLError,TimeoutError,OSError,ValueError,json.JSONDecodeError) as exc:
            error=type(exc).__name__+": "+str(exc)[:180]
            if attempt<2:
                time.sleep(attempt+1)
                continue
            break
    decoded:dict[str,Any]={}
    if status==200 and isinstance(data,dict):
        work=data.get("message") if backend=="crossref" else data
        if isinstance(work,dict):
            actual=work.get("DOI" if backend=="crossref" else "doi","")
            try: verified=normalize_doi(str(actual))==doi
            except ValueError: verified=False
            titleval=work.get("title")
            if isinstance(titleval,list):title=titleval[0] if titleval else ""
            else:title=titleval if isinstance(titleval,str) else ""
            if backend=="crossref":
                abstract=abstract_html_to_text(work.get("abstract"))
                publisher=work.get("publisher") or ""
                venue=(work.get("container-title") or [""])[0]
                pubdate=work.get("published",{}).get("date-parts",[])
                link=work.get("URL") or ""
            else:
                abstract=inverted_index_to_text(work.get("abstract_inverted_index"))
                pub=work.get("primary_location") or {}
                src=(pub.get("source") or {}) if isinstance(pub,dict) else {}
                venue=src.get("display_name") or ""
                publisher=(work.get("host_venue") or {}).get("publisher") or "" if isinstance(work.get("host_venue"),dict) else ""
                pubdate=work.get("publication_date") or ""
                link=work.get("primary_location",{}).get("landing_page_url") or ""
            decoded={
                "returned_doi":actual,
                "doi_identity_match":verified,
                "title":str(title)[:500],
                "venue":str(venue)[:350],
                "publisher":str(publisher)[:350],
                "publication_date":pubdate,
                "abstract_text":abstract,
                "abstract_sha256":sha(abstract.encode("utf-8")) if abstract else None,
                "publication_url":str(link)[:700],
                "read_depth":"DATABASE_ABSTRACT" if abstract else "DATABASE_METADATA_ONLY",
                "source_is_primary_publisher_fulltext":False,
            }
            if not verified:error="RETURNED_DOI_MISMATCH"
    snap={
        "schema":"MAI_PUBLISHED_WORK_API_QUERY_v1",
        "backend":backend,"requested_doi":doi,"api_url":url,
        "http_status":status,"error":error,
        "fetched_utc":stamp,"from_cache":False,
        "raw_response_sha256":sha(raw) if status==200 else None,
        "raw_response_bytes":len(raw) if status==200 else 0,
        "parsed":decoded,
    }
    if status==200 and data is not None:
        d.mkdir(parents=True,exist_ok=True)
        (d/(backend+".response.json")).write_bytes(raw)
    put(path,snap)
    return snap

def effective_abstract(records:list[dict[str,Any]])->dict[str,Any]:
    matching=[x for x in records if x.get("http_status")==200 and (x.get("parsed") or {}).get("doi_identity_match")]
    matching.sort(key=lambda x:(bool((x.get("parsed") or {}).get("abstract_text")),x["backend"]=="crossref"),reverse=True)
    if not matching:return{"read_depth":"NOT_FOUND_OR_UNVERIFIED","abstract_text":"","provider":None}
    first=matching[0]
    detail=first["parsed"]
    return{
        "read_depth":detail["read_depth"],"abstract_text":detail["abstract_text"],
        "provider":first["backend"],"publication_title":detail.get("title",""),
        "publisher":detail.get("publisher",""),"publication_venue":detail.get("venue",""),
        "raw_response_sha256":first.get("raw_response_sha256"),
        "doi_identity_match":True,
    }

def execute(packet_root:Path,science_root:Path,output:Path,start:int=0,limit:int=10,refresh:bool=False,max_workers:int=4)->dict[str,Any]:
    if start<0 or limit<1 or limit>53 or max_workers<1 or max_workers>6:
        raise ValueError("invalid bounds")
    idx=json.loads((science_root/"science_index.json").read_text(encoding="utf-8"))
    packet_meta=json.loads((packet_root/"manifest.json").read_text(encoding="utf-8"))
    if idx.get("schema")!="MAI_W12_PRIOR_RESEARCH_INDEX_V1" or idx.get("source_W12_sha256")!=packet_meta.get("source_jsonl_sha256"):
        raise ValueError("scientific index/source W12 bytes mismatch")
    all_paths=sorted((packet_root/"routes").glob("MAI-W12-*.json"))
    if len(all_paths)!=idx.get("route_count") or not all_paths:raise ValueError("W12 route count mismatch")
    selected=all_paths[start:start+limit]
    if not selected:raise ValueError("start outside route list")
    route_inputs=[]
    doi_union:set[str]=set()
    for f in selected:
        packet=json.loads(f.read_text(encoding="utf-8"))
        rid=packet["route"]["route_id"]
        j=json.loads((science_root/"routes"/(rid+".json")).read_text(encoding="utf-8"))
        if j["family"]!=packet["route"]["family"] or j["source_jsonl_sha256"]!=idx["source_W12_sha256"]:
            raise ValueError("source/Indago family drift "+rid)
        family=[]
        errors=[]
        for raw_doi in j["science_provenance"].get("prior_art_doi_candidates",[]):
            try:family.append(normalize_doi(raw_doi))
            except ValueError:errors.append({"value":raw_doi,"role":"family_rival","reason":"INVALID_DOI"})
        listed=packet["route"].get("literature_url","")
        route_doi=None
        if listed and ("doi.org/" in listed):
            try:route_doi=normalize_doi(listed)
            except ValueError:errors.append({"value":listed,"role":"route_listed_paper","reason":"INVALID_DOI"})
        for doi in family:doi_union.add(doi)
        if route_doi:doi_union.add(route_doi)
        route_inputs.append((rid,packet,j,sorted(set(family)),route_doi,errors))
    # Cache verified publication database results; no free-form web crawling.
    results:dict[tuple[str,str],dict[str,Any]]={}
    calls=[(doi,backend) for doi in sorted(doi_union) for backend in API_BASES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures={pool.submit(query,backend,doi,output/"published_work_cache"): (doi,backend) for doi,backend in calls}
        for task in concurrent.futures.as_completed(futures):
            key=futures[task]
            try:results[key]=task.result()
            except Exception as exc:
                raise RuntimeError("cached provider result failed for "+str(key)+": "+str(exc)) from exc
    completed=[]
    indexed_by_route={}
    for rid,packet,prior,family,route_doi,errors in route_inputs:
        roles={k:["family_rival"] for k in family}
        if route_doi:
            roles.setdefault(route_doi,[])
            roles[route_doi].append("w12_route_listed")
        verified=[]
        for doi in sorted(roles):
            entries=[results[(doi,backend)] for backend in API_BASES]
            info=effective_abstract(entries)
            verified.append({
                "doi":doi,"roles":roles[doi],
                "crossref_status":results[(doi,"crossref")]["http_status"],
                "openalex_status":results[(doi,"openalex")]["http_status"],
                "source_record_digests":{
                    b:sha(stable({k:v for k,v in results[(doi,b)].items() if k!="from_cache"})) for b in API_BASES
                },
                "abstract":info,
            })
        if any(v["abstract"].get("read_depth")=="DATABASE_ABSTRACT" for v in verified):
            status="ABSTRACTS_ACQUIRED_NEEDS_SCHOLARLY_INTERPRETATION"
        elif any(v["abstract"].get("read_depth")=="DATABASE_METADATA_ONLY" for v in verified):
            status="METADATA_ACQUIRED_NEEDS_SOURCE_TEXT"
        else:status="SOURCE_READS_NOT_AVAILABLE"
        body={
            "schema":SCHEMA,"route_id":rid,
            "scientific_family":packet["route"]["family"],
            "meaning_version":packet["route"]["variant"],
            "journal":packet["route"]["journal"],
            "working_title":packet["route"]["title_ru"],
            "source_abstract_sha256":sha(packet["route"]["abstract_ru"].encode("utf-8")),
            "W12_source_sha256":idx["source_W12_sha256"],
            "prior_indago_route_sha256":sha(stable(prior)),
            "operation":"Crossref + OpenAlex API DOI identity & abstract retrieval",
            "operation_status":status,
            "published_works":verified,
            "invalid_source_identifiers":errors,
            "published_work_count":len(verified),
            "database_abstract_count":sum(z["abstract"].get("read_depth")=="DATABASE_ABSTRACT" for z in verified),
            "publisher_fulltexts_read":0,
            "independent_scholarly_claim_adjudications":0,
            "technical_user_approved":False,
            "journal_policy_verified":False,
            "science_gate":"HOLD",
            "human_author_gate":"CLOSED",
            "external_send_count":0,
            "next_operation":"CLAIM_OPPONENT_CHALLENGE_USING_DATABASE_ABSTRACTS_AND_AUTHORED_MAI_SOURCES",
        }
        put(output/"routes"/(rid+".json"),body)
        completed.append({"route_id":rid,"status":status,"published_works":len(verified),
                          "abstracts":body["database_abstract_count"],"receipt_sha256":sha(stable(body))})
        indexed_by_route[rid]=body
    manifest={
        "schema":"MAI_PUBLISHED_WORK_API_BATCH_v1",
        "route_count":len(completed),
        "start":start,"limit":limit,
        "source_W12_sha256":idx["source_W12_sha256"],
        "unique_requested_doi":len(doi_union),
        "provider_queries":len(calls),
        "cache_hits":sum(results[k]["from_cache"] for k in results),
        "non_success_provider_responses":sum(results[k]["http_status"]!=200 for k in results),
        "abstracts_retrieved_route_bindings":sum(v["abstracts"] for v in completed),
        "route_review_needed_count":len(completed),
        "scholarly_conclusions_cleared":0,
        "editorial_send_count":0,"author_gate_cleared":0,
        "per_route":completed,
    }
    put(output/"source_batch_receipt.json",manifest)
    return manifest

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packets",type=Path,required=True)
    ap.add_argument("--science",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--start",type=int,default=0)
    ap.add_argument("--limit",type=int,default=10)
    ap.add_argument("--max-workers",type=int,default=4)
    args=ap.parse_args()
    a=execute(args.packets,args.science,args.output,args.start,args.limit,max_workers=args.max_workers)
    print(json.dumps(a,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
