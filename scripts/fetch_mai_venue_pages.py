"""Capture real public journal-world web evidence for MAI W12 / Kairon.

This is a URL/HTTP/text acquisition stage, NOT verification of journal CFP,
current deadline, rights, AI policy, editorial fit or acceptance. Blocks (403,
TLS, robots/JS shells, missing URLs) are retained as explicit negative evidence.

Page bytes and SHA256 stay on owner-authorized machine; only code/tests in Git.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime,timezone
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from typing import Any

SCHEMA="MAI_KAIRON_OFFICIAL_VENUE_WEB_CAPTURE_v1"
MAX_BYTES=850_000
AGENT="Kairoskopion-MAI-Kairon-SourceAcquisition/0.1 (editorial research, no journal submission)"

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()
def stable(data:Any)->bytes:
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
def write(path:Path,data:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(stable(data))
    tmp.replace(path)
def load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def valid_url(value:str)->bool:
    try:
        uri=urlparse(value)
        if uri.scheme!="https" or not uri.hostname or uri.username or uri.password:
            return False
        host=uri.hostname.lower()
        if host in ("localhost","localhost.localdomain") or host.endswith((".local",".internal",".localhost")):
            return False
        try:
            ipaddress.ip_address(host)
            return False  # Domain-only public bibliographic/journal URLs
        except ValueError:
            pass
        return "." in host and not any(x in value for x in ("\r","\n","\x00"))
    except Exception:
        return False

class ExternalRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not valid_url(newurl):
            raise ValueError("UNSAFE_REDIRECT")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _request(url:str,timeout:float):
    req=Request(url,headers={"User-Agent":AGENT,"Accept":"text/html,application/xhtml+xml,text/plain,application/pdf"})
    return build_opener(ExternalRedirect).open(req,timeout=timeout)

class VisibleText(HTMLParser):
    def __init__(self)->None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth=0
        self.content:list[str]=[]
        self.title:list[str]=[]
        self.in_title=False
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg","template"):
            self.hidden_depth+=1
        if tag=="title":self.in_title=True
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg","template"):
            self.hidden_depth=max(0,self.hidden_depth-1)
        if tag=="title":self.in_title=False
    def handle_data(self,text):
        if self.hidden_depth:return
        if self.in_title:self.title.append(text)
        else:self.content.append(text)

def parse_text(raw:bytes,content_type:str)->tuple[str,str]:
    charset="utf-8"
    m=re.search(r"charset\s*=\s*([a-zA-Z0-9._-]+)",content_type or "",re.I)
    if m:charset=m.group(1)
    try:decoded=raw.decode(charset,errors="replace")
    except LookupError:decoded=raw.decode("utf-8",errors="replace")
    if "html" not in (content_type or "").lower():
        return re.sub(r"\s+"," ",decoded).strip()[:80000],""
    parser=VisibleText()
    try:parser.feed(decoded)
    except Exception:return "", ""
    return (
        re.sub(r"\s+"," "," ".join(parser.content)).strip()[:80000],
        re.sub(r"\s+"," "," ".join(parser.title)).strip()[:500],
    )

def obtain(url:str,cache:Path,*,refresh:bool=False,timeout:float=15)->dict[str,Any]:
    if not valid_url(url):
        return {"schema":"MAI_VENUE_WEB_SOURCE_v1","requested_url":url,
                "status":"URL_DISALLOWED_OR_INVALID","http_status":None,"cached":False,
                "raw_sha256":None,"read_depth":"NOT_READ"}
    root=cache/sha(url.encode("utf-8"))[:24]
    record=root/"capture.json"
    if record.exists() and not refresh:
        item=load(record)
        if item.get("requested_url")!=url:
            raise ValueError("URL cache identity drift")
        content=root/"source.bin"
        if item.get("raw_sha256") and (not content.is_file() or sha(content.read_bytes())!=item["raw_sha256"]):
            raise ValueError("URL cache raw byte hash mismatch "+url)
        item["cached"]=True
        return item
    now=datetime.now(timezone.utc).isoformat()
    state="NETWORK_FAILURE";status=None;ctype="";final=url;raw=b"";err=None
    try:
        with _request(url,timeout) as res:
            status=res.status
            ctype=res.headers.get("Content-Type","")
            final=res.geturl()
            if not valid_url(final):raise ValueError("UNSAFE_FINAL_URL")
            raw=res.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                state="RESPONSE_TOO_LARGE_OR_TRUNCATED"
                raw=raw[:MAX_BYTES]
            elif status!=200:
                state="HTTP_NON_200"
            elif "html" in ctype.lower() or "text/plain" in ctype.lower():
                state="FETCHED_TEXT"
            elif "pdf" in ctype.lower():
                state="FETCHED_PDF_NO_TEXT"
            else:
                state="UNSUPPORTED_CONTENT_TYPE"
    except HTTPError as exc:
        status=exc.code
        state="HTTP_REJECTED"
        err=str(exc)[:180]
    except (URLError,OSError,TimeoutError,ValueError) as exc:
        err=type(exc).__name__+": "+str(exc)[:240]
        state="TLS_OR_NETWORK_BLOCKED"
    text="";title=""
    if state=="FETCHED_TEXT":
        text,title=parse_text(raw,ctype)
        if len(text)<300:
            state="HTML_NO_USEFUL_POLICY_TEXT"
    digest=sha(raw) if raw else None
    root.mkdir(parents=True,exist_ok=True)
    if raw:
        (root/"source.bin").write_bytes(raw)
    if text:
        (root/"visible_text.txt").write_text(text+"\n",encoding="utf-8")
    body={
        "schema":"MAI_VENUE_WEB_SOURCE_v1",
        "requested_url":url,"final_url":final,
        "requested_host":urlparse(url).hostname,
        "final_host":urlparse(final).hostname,
        "http_status":status,"content_type":ctype,
        "status":state,"error":err,
        "retrieved_utc":now,"cached":False,
        "raw_sha256":digest,"raw_bytes":len(raw),
        "visible_text_sha256":sha(text.encode("utf-8")) if text else None,
        "visible_chars":len(text),"title_from_html":title,
        "read_depth":"WEB_HTML_TEXT_EXTRACT" if text else
                     "WEB_PDF_UNREAD" if state=="FETCHED_PDF_NO_TEXT" else "NOT_READ",
        "official_publisher_status_verified":False,
        "submission_policy_verified":False,
        "cfp_deadline_verified":False,
        "ai_authorship_policy_verified":False,
    }
    write(record,body)
    return body

def capture(packet_root:Path,output:Path,*,limit:int=53,start:int=0,
            workers:int=4,refresh:bool=False)->dict[str,Any]:
    if not (1<=limit<=53 and 1<=workers<=6 and start>=0):
        raise ValueError("invalid batch bounds")
    source=load(packet_root/"manifest.json")
    if source.get("schema")!="MAI_W12_BATCH_OUTPUT_MANIFEST_v1":
        raise ValueError("W12 source packet schema not registered")
    paths=sorted((packet_root/"routes").glob("MAI-W12-*.json"))
    if len(paths)!=source.get("records"):
        raise ValueError("missing W12 source rows")
    selected=paths[start:start+limit]
    if not selected:raise ValueError("start beyond source")
    records=[load(path) for path in selected]
    urls=sorted(set(str(rec["route"].get("official_url") or "").strip() for rec in records))
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(obtain,url,output/"url_capture_cache",refresh=refresh):url for url in urls}
        for job in concurrent.futures.as_completed(futures):
            url=futures[job]
            results[url]=job.result()
    summary=[]
    for source_record in records:
        r=source_record["route"]
        rid=r["route_id"]
        if source_record.get("source_jsonl_sha256")!=source.get("source_jsonl_sha256"):
            raise ValueError("different W12 source lineage "+rid)
        url=str(r.get("official_url") or "").strip()
        evidence=results[url]
        # Cache-hit is runtime scheduling metadata. Keep the durable route
        # artifact byte-identical across first run and cold replay.
        frozen_evidence={k:v for k,v in evidence.items() if k!="cached"}
        detail={
            "schema":SCHEMA,
            "route_id":rid,"W12_source_sha256":source["source_jsonl_sha256"],
            "source_sheet_row":r["source_cell_range"],
            "journal":r["journal"],"family":r["family"],"variant":r["variant"],
            "w12_listed_official_url":url,
            "w12_original_deadline_unverified":r.get("deadline_raw",""),
            "web_source":frozen_evidence,
            "web_source_receipt_sha256":sha(stable(frozen_evidence)),
            "source_read_state":evidence["status"],
            "next_kairon_operation":"EXTRACT_CFP_AND_AUTHOR_GUIDELINES_ONLY_IF_VISUAL_TEXT_SUFFICIENT",
            "venue_page_domain_alone_is_not_policy_acceptance":True,
            "official_rules_acceptance":"HOLD",
            "policy_freshness_verified":False,
            "publisher_fulltext_verified":False,
            "author_gate":"CLOSED",
            "send_count":0,
        }
        write(output/"routes"/(rid+".json"),detail)
        summary.append({
            "route_id":rid,"state":evidence["status"],
            "w12_listed_domain":evidence.get("requested_host"),
            "http_status":evidence.get("http_status"),
            "visible_chars":evidence.get("visible_chars",0),
            "cached":evidence.get("cached",False),
            "receipt_sha256":sha(stable(detail)),
        })
    counts={state:sum(row["state"]==state for row in summary) for state in sorted(set(x["state"] for x in summary))}
    manifest={
        "schema":"MAI_KAIRON_VENUE_WEB_ACQUISITION_BATCH_v1",
        "source_W12_sha256":source["source_jsonl_sha256"],
        "routes_requested":len(selected),
        "unique_w12_urls":len(urls),
        "routes_by_http_status":counts,
        "cached_route_count":sum(x["cached"] for x in summary),
        "route_receipts":summary,
        "policies_certified":0,"cfp_deadlines_verified":0,"author_gate_ready":0,
        "external_submissions":0,
        "read_depth":"BOUNDED_HTML_VISIBLE_TEXT_OR_BLOCKED",
    }
    write(output/"venue_acquisition_receipt.json",manifest)
    return manifest

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--limit",type=int,default=53)
    p.add_argument("--start",type=int,default=0)
    p.add_argument("--workers",type=int,default=4)
    p.add_argument("--refresh",action="store_true")
    a=p.parse_args()
    result=capture(a.packets,a.output,limit=a.limit,start=a.start,
        workers=a.workers,refresh=a.refresh)
    print(json.dumps({k:v for k,v in result.items() if k!="route_receipts"},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
