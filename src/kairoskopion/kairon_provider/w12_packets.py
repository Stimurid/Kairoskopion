"""Materialize *existing* MAI W12 editorial route research into durable packets.

This is a pure, offline, no-submit projection from an authenticated source
snapshot, not a scholarly quality gate. It cannot invent bibliography,
editorial acceptance or article identity.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import csv
from typing import Any

SCHEMA = "MAI_W12_BATCH_RESEARCH_PACKET_v1"
COLS = (
    "number", "journal", "family", "variant", "title_ru", "abstract_ru",
    "route_raw", "deadline_raw", "official_url", "literature_url",
    "editorial_note", "priority", "contact_raw",
)
OUTREACH = {
    "RECEIPT_CONFIRMED", "SENT_UNCONFIRMED", "DRAFT",
    "FORM_PREPARE", "NONE",
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def jsdata(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

def read_records(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    rows = []
    for idx, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if line.strip():
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"line {idx}: not a JSON object")
            rows.append(data)
    if not rows:
        raise ValueError("no source records")
    return rows, sha(raw)

def extract_rows(records: list[dict[str, Any]], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    header = list(snapshot.get("headers") or [])
    rows = list(snapshot.get("rows") or [])
    if len(rows) != len(records):
        raise ValueError(f"source snapshot length mismatch: {len(rows)} vs {len(records)}")
    if len(header) < 13:
        raise ValueError("expected original W12 A:M columns")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, record in enumerate(records):
        row = rows[idx]
        if not isinstance(row, list):
            raise ValueError(f"snapshot row {idx+2}: not an array")
        data = {key: str((row[pos] if pos < len(row) else "") or "").strip() for pos,key in enumerate(COLS)}
        source_fields = record.get("source_fields") or {}
        for pos,label in enumerate(header[:13]):
            text = str((row[pos] if pos < len(row) else "") or "").strip()
            if str(source_fields.get(label, "")).strip() != text:
                raise ValueError(f"source field mismatch in row {idx+2} column {label}")
        if str(record.get("source_row_index")) != str(idx+2):
            raise ValueError(f"source row index mismatch {idx+2}")
        if data["family"] != str(record.get("seed_family")):
            raise ValueError(f"family mismatch {idx+2}")
        if data["variant"] != str(record.get("meaning_version")):
            raise ValueError(f"version mismatch {idx+2}")
        if not data["number"] or not data["journal"]:
            raise ValueError(f"row {idx+2} missing number/journal")
        rid = f"MAI-W12-{int(data['number']):03d}"
        if rid in seen:
            raise ValueError("duplicate route id "+rid)
        seen.add(rid)
        data.update({
            "route_id": rid,
            "original_spreadsheet_id": snapshot.get("source_id"),
            "source_sheet": snapshot.get("source_name"),
            "source_cell_range": f"A{idx+2}:M{idx+2}",
            "source_authority": "LIVE_AUTHENTICATED_GOOGLE_SHEET_DERIVED",
            "not_original_xlsx_bytes": True,
            "target_status": "POLICY_UNVERIFIED",
            "scholarly_state": "SOURCE_DRAFT_ONLY",
            "editorial_packet_type": "SOURCE_ABSTRACT_RU",
            "notes": record.get("notes", []),
        })
        out.append(data)
    return out

def load_outreach(path: Path | None) -> tuple[list[dict[str, Any]], str | None]:
    if path is None:
        return [], None
    b=path.read_bytes()
    raw=json.loads(b.decode("utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("outreach events must be a JSON list")
    seen: set[tuple[str,str]] = set()
    for event in raw:
        if not isinstance(event,dict):
            raise ValueError("invalid outreach event")
        if str(event.get("status") or "") not in OUTREACH - {"NONE"}:
            raise ValueError("invalid outreach status")
        if not event.get("route_id"):
            raise ValueError("missing route_id")
        key=(str(event["route_id"]),str(event.get("event_id","")))
        if key in seen:
            raise ValueError("duplicate event")
        seen.add(key)
    return raw,sha(b)

def load_science_index(path: Path | None, expected_source_sha: str, expected_routes: set[str]) -> tuple[dict[str,dict[str,Any]],str | None]:
    if path is None:
        return {},None
    raw=path.read_bytes()
    body=json.loads(raw.decode("utf-8"))
    if (body.get("schema")!="MAI_W12_PRIOR_RESEARCH_INDEX_V1"
            or body.get("source_W12_sha256")!=expected_source_sha
            or body.get("real_research_operations_this_wave")!=0
            or body.get("route_author_ready_count")!=0
            or body.get("external_send_count")!=0):
        raise ValueError("science index cannot promote unverified research")
    cards=body.get("review_cards") or []
    if not isinstance(cards,list) or len(cards)!=len(expected_routes):
        raise ValueError("science index route count mismatch")
    indexed={c["route_id"]:c for c in cards}
    if len(indexed)!=len(cards) or indexed.keys()!=expected_routes:
        raise ValueError("science index route IDs mismatch")
    return indexed,sha(raw)

def publication_evidence_for_route(
    route: dict[str, Any], output: Path, source_sha: str,
    publisher_root: Path | None, model_root: Path | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    rid=route["route_id"]
    published={"status":"NOT_RUN","abstracts":0,"works":0,"detail":""}
    model={"status":"AWAITING_CRITIQUE","detail":"","cited_anchor":""}
    source_work=None
    if publisher_root is not None:
        rawpath=publisher_root/"routes"/(rid+".json")
        if rawpath.exists():
            raw=rawpath.read_bytes()
            q=json.loads(raw.decode("utf-8"))
            if (q.get("schema")!="MAI_PRIOR_ART_AUTHENTICATED_API_EVIDENCE_v1"
                    or q.get("route_id")!=rid or q.get("W12_source_sha256")!=source_sha
                    or q.get("scientific_family")!=route["family"]
                    or q.get("science_gate")!="HOLD"
                    or q.get("human_author_gate")!="CLOSED"
                    or q.get("external_send_count")!=0
                    or q.get("publisher_fulltexts_read")!=0):
                raise ValueError("published source artifact cannot promote route "+rid)
            outpath=output/"published"/(rid+".json")
            outpath.parent.mkdir(parents=True,exist_ok=True)
            outpath.write_bytes(raw)
            source_work=q
            published={
                "status":q["operation_status"],
                "works":q["published_work_count"],
                "abstracts":q["database_abstract_count"],
                "detail":"published/"+rid+".json",
                "receipt_sha256":sha(raw),
                "read_depth":"CROSSREF_OPENALEX_DATABASE_ABSTRACT_NOT_PUBLISHER_FULLTEXT",
            }
    if model_root is not None:
        path=model_root/"routes"/(rid+".json")
        if path.exists():
            raw=path.read_bytes()
            q=json.loads(raw.decode("utf-8"))
            review=q.get("review") or {}
            passage=review.get("source_passage")
            if (q.get("schema")!="MAI_W12_SOURCE_LINKED_PROVISIONAL_SCHOLARLY_CHALLENGE_v1"
                    or q.get("route_id")!=rid
                    or review.get("route_id")!=rid
                    or q.get("human_gate")!="HOLD"
                    or q.get("journal_send_count")!=0
                    or q.get("published_fulltext_read") is not False
                    or review.get("scientific_claim_accepted") is not False
                    or q.get("scientific_stage")!="PROVISIONAL_MODEL_ABSTRACT_CHALLENGE"):
                raise ValueError("model review cannot promote scholarly route "+rid)
            if passage:
                if source_work is None:
                    raise ValueError("model review must have independently held published source "+rid)
                works=source_work.get("published_works") or []
                matched=next((w for w in works if w.get("doi")==passage.get("doi")),None)
                if (matched is None or
                        review.get("source_anchor_id")!=passage.get("passage_id") or
                        passage.get("text") not in matched.get("abstract",{}).get("abstract_text","")):
                    raise ValueError("model review cited unverified abstract anchor "+rid)
            elif review.get("status")!="INSUFFICIENT_ABSTRACT":
                raise ValueError("model without anchor cannot claim sourced critique "+rid)
            outpath=output/"reviews"/(rid+".json")
            outpath.parent.mkdir(parents=True,exist_ok=True)
            outpath.write_bytes(raw)
            model={
                "status":"ABSTRACT_LINKED_PROVISIONAL_CRITIQUE" if passage else "ABSTAINED_NOT_ENOUGH_SOURCE",
                "detail":"reviews/"+rid+".json",
                "cited_anchor":review.get("source_anchor_id",""),
                "receipt_sha256":sha(raw),
                "semantic_authority":"PROVISIONAL_LLM_CRITICISM_NOT_VALIDATED_BY_AUTHOR",
            }
    return published,model

def venue_web_source_for_route(route: dict[str, Any], output: Path, source_sha: str,
                               venue_root: Path | None) -> dict[str, Any]:
    if venue_root is None:
        return {"status":"NOT_CAPTURED","receipt":"","text":"","http_status":None}
    rid=route["route_id"]
    path=venue_root/"routes"/(rid+".json")
    if not path.is_file():
        return {"status":"NOT_CAPTURED","receipt":"","text":"","http_status":None}
    raw=path.read_bytes()
    item=json.loads(raw.decode("utf-8"))
    source=item.get("web_source") or {}
    frozen_digest=sha((json.dumps(source,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
    if (item.get("schema")!="MAI_KAIRON_OFFICIAL_VENUE_WEB_CAPTURE_v1"
            or item.get("route_id")!=rid or item.get("W12_source_sha256")!=source_sha
            or item.get("family")!=route["family"]
            or item.get("variant")!=route["variant"]
            or item.get("journal")!=route["journal"]
            or item.get("w12_listed_official_url")!=route.get("official_url","")
            or item.get("official_rules_acceptance")!="HOLD"
            or item.get("author_gate")!="CLOSED" or item.get("send_count")!=0
            or item.get("venue_page_domain_alone_is_not_policy_acceptance") is not True
            or item.get("policy_freshness_verified") is not False
            or item.get("web_source_receipt_sha256")!=frozen_digest
            or any(source.get(k) is not False for k in (
                "submission_policy_verified","cfp_deadline_verified",
                "ai_authorship_policy_verified","official_publisher_status_verified"))):
        raise ValueError("untrusted venue web source attempting publisher policy promotion "+rid)
    dest=output/"venues"/(rid+".json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(raw)
    link=""
    url=item["w12_listed_official_url"]
    source_text=venue_root/"url_capture_cache"/sha(url.encode("utf-8"))[:24]/"visible_text.txt"
    if source.get("visible_text_sha256"):
        if not source_text.is_file():
            raise ValueError("venue web text missing from published source capture "+rid)
        data=source_text.read_bytes()
        visible=data.decode("utf-8").rstrip("\r\n")
        if sha(visible.encode("utf-8"))!=source["visible_text_sha256"]:
            raise ValueError("venue source text raw passage SHA mismatch "+rid)
        text_dest=output/"venue_text"/(rid+".txt")
        text_dest.parent.mkdir(parents=True,exist_ok=True)
        text_dest.write_bytes(data)
        link="venue_text/"+rid+".txt"
    return {
        "status":item["source_read_state"],
        "receipt":"venues/"+rid+".json",
        "text":link,
        "http_status":source.get("http_status"),
        "visible_chars":source.get("visible_chars",0),
        "venue_policy_gate":"HOLD",
        "receipt_sha256":sha(raw),
    }

def materialize(source: Path, snapshot_path: Path, output: Path, outreach_path: Path | None = None, analysis_root: Path | None = None, science_index_path: Path | None = None, publisher_root: Path | None = None, model_root: Path | None = None, venue_web_root: Path | None = None) -> dict[str, Any]:
    records,source_hash=read_records(source)
    snapshot_bytes=snapshot_path.read_bytes()
    snapshot=json.loads(snapshot_bytes.decode("utf-8-sig"))
    sheet_id = str(snapshot.get("source_id") or "")
    if not sheet_id or any(str(r.get("source_spreadsheet_id") or "") != sheet_id for r in records):
        raise ValueError("W12 snapshot does not match authenticated source identity")
    routes=extract_rows(records,snapshot)
    events,events_sha=load_outreach(outreach_path)
    eventmap: dict[str,list[dict[str,Any]]]={}
    for e in events:
        eventmap.setdefault(str(e["route_id"]),[]).append(e)
    known={r["route_id"] for r in routes}
    for rid in eventmap:
        if rid not in known:
            raise ValueError("orphan outreach route id "+rid)
    science_cards,science_sha=load_science_index(science_index_path,source_hash,known)
    route_dir=output/"routes"
    route_dir.mkdir(parents=True,exist_ok=True)
    index=[]
    for r in routes:
        related=eventmap.get(r["route_id"],[])
        # Explicit evidence-based statuses only; selected last event is recorded
        # with full event history, never inferred from message subject.
        last=related[-1] if related else None
        status=last["status"] if last else "SOURCE_ROUTE_EXTRACTED"
        science={"status":"NOT_INDEXED","opponents":0,"review_packet":""}
        if science_index_path is not None:
            rid=r["route_id"]
            candidate=science_cards[rid]
            sciencefile=science_index_path.parent/"routes"/(rid+".json")
            source_review=json.loads(sciencefile.read_text(encoding="utf-8"))
            if (source_review.get("route_id")!=rid
                    or source_review.get("family")!=r["family"]
                    or source_review.get("source_jsonl_sha256")!=source_hash
                    or source_review.get("author_ready") is not False
                    or source_review.get("journal_send_authorized") is not False
                    or source_review.get("scholarly_execution_state")!="HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION"
                    or candidate.get("research_status")!="HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION"):
                raise ValueError("science route requires unverified research HOLD "+rid)
            raw_review=sciencefile.read_bytes()
            science_dest=output/"science"/(rid+".json")
            science_dest.parent.mkdir(parents=True,exist_ok=True)
            science_dest.write_bytes(raw_review)
            science={
                "status":"PREEXISTING_FAMILY_OPPOSITION_INDEXED",
                "opponents":candidate.get("opponents_indexed_from_prior_indago",0),
                "review_packet":"science/"+rid+".json",
                "review_sha256":sha(raw_review),
                "read_depth":"SECONDARY_INDAGO_RESEARCH_NOT_INDEPENDENT_PUBLISHER_READ",
            }
        analysis={"status":"NOT_RUN"}
        if analysis_root is not None:
            rpath=analysis_root/r["route_id"]/"receipt.json"
            if rpath.exists():
                candidate=json.loads(rpath.read_text(encoding="utf-8"))
                if candidate.get("route_id") != r["route_id"] or candidate.get("real_source_snapshot") != source_hash:
                    raise ValueError("local pipeline receipt/source mismatch "+r["route_id"])
                if candidate.get("outbound_send_count") != 0 or candidate.get("author_gate") != "CLOSED":
                    raise ValueError("unexpected local pipeline authority claim "+r["route_id"])
                analysis={"status":candidate.get("status","UNKNOWN"),"receipt_path":str(rpath),"receipt_sha256":sha(rpath.read_bytes()),"adapter_mode":candidate.get("adapter_mode"),"scientific_qa_status":candidate.get("scientific_qa_status")}
                stdoutpath=analysis_root/r["route_id"]/"stdout.log"
                if stdoutpath.exists():
                    m=re.search(r"Overall label:\s*([^\r\n]+)",stdoutpath.read_text(encoding="utf-8"))
                    if m:
                        analysis["fit_label"]=m.group(1).strip()
        published,model=publication_evidence_for_route(
            r,output,source_hash,publisher_root,model_root)
        venue=venue_web_source_for_route(r,output,source_hash,venue_web_root)
        packet={
            "schema":SCHEMA,"source_jsonl_sha256":source_hash,
            "snapshot_sha256":sha(snapshot_bytes),"outreach_sha256":events_sha,
            "route":r,"outreach_events":related,
            "local_analysis":analysis,
            "science_index":science,
            "published_source_evidence":published,
            "model_scientific_critique":model,
            "venue_web_evidence":venue,
            "editorial_status":status,
            "scientific_state":"SOURCE_DRAFT_ONLY",
            "quality_receipts":{},
            "ready_for_author_rework":False,
            "ready_for_human_send":False,
            "missing_gates":[
                "INDEPENDENT_SCHOLARLY_CHALLENGE",
                "VENUE_NATIVE_READ_EVIDENCE",
                "CURRENT_OFFICIAL_EDITORIAL_POLICY",
                "TARGET_VARIANT_AUTHORSHIP_AND_OVERLAP",
                "FORMAL_QA_WITH_REAL_ARTIFACTS",
            ],
            "next_automated_operation":"QUALIFY_RESEARCH_AND_VENUE",
        }
        body=json.dumps(packet,ensure_ascii=False,indent=2)+"\n"
        target=route_dir/(r["route_id"]+".json")
        target.write_text(body,encoding="utf-8")
        abstract=route_dir/(r["route_id"]+".md")
        abstract.write_text(
            "# "+r["journal"]+" — "+r["variant"]+"\n\n"+
            "**Рабочая тема:** "+r["title_ru"]+"\n\n"+
            "## Авторский исходный текст W12 (русский)\n\n"+r["abstract_ru"]+"\n\n"+
            "## Редакционный маршрут в W12\n\n"+r["route_raw"]+"\n\n"+
            "**Дедлайн из W12:** "+r["deadline_raw"]+"\n\n"+
            "**Страница:** "+r["official_url"]+"\n\n"+
            "**Научный ориентир:** "+r["literature_url"]+"\n\n"+
            "**Права, условия и публикационный допуск:** НЕ ПРОВЕРЕНЫ в этом пакетном переносе.\n\n"+
            "**Статус:** "+status+"; авторский гейт закрыт до выполненных научных и издательских проверок.\n",
            encoding="utf-8"
        )
        index.append({
            "id":r["route_id"],"journal":r["journal"],"family":r["family"],
            "variant":r["variant"],"title":r["title_ru"],"deadline":r["deadline_raw"],
            "route":r["route_raw"],"editorial_status":status,
            "analysis_status":analysis.get("status","NOT_RUN"),
            "fit_label":analysis.get("fit_label",""),
            "science_index_status":science["status"],
            "science_opponents":science["opponents"],
            "science_packet":science["review_packet"],
            "published_status":published["status"],
            "published_works":published["works"],
            "published_abstracts":published["abstracts"],
            "published_packet":published["detail"],
            "model_critique_status":model["status"],
            "model_critique_packet":model["detail"],
            "venue_web_status":venue["status"],
            "venue_web_receipt":venue["receipt"],
            "venue_web_text":venue["text"],
            "venue_http_status":venue["http_status"],
            "scientific_status":"PRIOR_ART_INDEXED_ON_HOLD" if science["review_packet"] else "SOURCE_DRAFT_ONLY",
            "packet":f"routes/{r['route_id']}.json",
            "abstract":f"routes/{r['route_id']}.md",
            "source_page":r["official_url"],
        })
    stats={}
    for card in index:
        k=card["editorial_status"]
        stats[k]=stats.get(k,0)+1
    manifest={
        "schema":"MAI_W12_BATCH_OUTPUT_MANIFEST_v1",
        "source_jsonl":str(source),"source_jsonl_sha256":source_hash,
        "snapshot_path":str(snapshot_path),"snapshot_sha256":sha(snapshot_bytes),
        "outreach_snapshot":str(outreach_path) if outreach_path else None,
        "outreach_sha256":events_sha,
        "records":len(index),
        "seed_families":sorted(set(r["family"] for r in routes)),
        "meaning_versions":len(set(r["variant"] for r in routes)),
        "status_counts":stats,
        "analysis_counts":{key:sum(x["analysis_status"]==key for x in index) for key in sorted(set(x["analysis_status"] for x in index))},
        "science_index_sha256":science_sha,
        "science_indexed_count":sum(bool(x["science_packet"]) for x in index),
        "published_source_indexed_count":sum(bool(x["published_packet"]) for x in index),
        "provisional_model_critique_count":sum(bool(x["model_critique_packet"]) for x in index),
        "venue_pages_acquired_count":sum(bool(x["venue_web_receipt"]) for x in index),
        "venue_web_text_readable_count":sum(bool(x["venue_web_text"]) for x in index),
        "venue_web_blocked_count":sum(x["venue_web_status"]=="HTTP_REJECTED" for x in index),
        "venue_policies_certified_count":0,
        "ready_for_human_send":0,
        "ready_for_author_rework":0,
        "source_note":"53 authentic W12 source route drafts; not independent article count, venue policy, or completed scholarly QA.",
        "external_actions_performed":0,
        "proof":{"packet_count":len(list(route_dir.glob("MAI-W12-*.json")))}
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output/"kanban.json").write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (output/"kanban.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(index[0].keys()))
        writer.writeheader()
        writer.writerows(index)
    (output/"index.html").write_text(render_board(index,manifest),encoding="utf-8")
    return manifest

def render_board(cards: list[dict[str,Any]], manifest: dict[str,Any]) -> str:
    payload=jsdata(cards)
    n=len(cards)
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>МАИ · Тримурти · Публикационный портфель</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f6f7f9;color:#202431}
body{margin:0;padding:24px;max-width:1700px;margin:auto}
h1{font-size:25px;margin:0 0 8px}small,.sub{color:#5b667a}
nav{display:flex;gap:10px;align-items:center;margin:20px 0;flex-wrap:wrap}
input,select{padding:10px 13px;border-radius:9px;border:1px solid #cdd2da;background:white;font-size:14px}
input{min-width:310px}
.stat{background:white;padding:13px 18px;border-radius:10px;border:1px solid #e0e4ea}
.board{display:grid;grid-template-columns:repeat(4,minmax(230px,1fr));gap:13px;align-items:start}
.column{border:1px solid #e3e6ed;background:#eceff3;border-radius:12px;padding:12px;min-height:100px}
.column h2{font-size:15px;margin:2px 5px 13px}.count{float:right;color:#687486}
.article{background:#fff;border:1px solid #dfe3e9;border-radius:9px;padding:13px;margin:9px 0}
.article h3{font-size:14px;margin:0 0 7px;line-height:1.35}
.meta{font-size:12px;color:#687486;line-height:1.5}
a{color:#185c9e;text-decoration:none}a:hover{text-decoration:underline}
hr{border:0;border-top:1px solid #e5e8ee}
.warning{background:#fff8e5;padding:12px 15px;border-radius:9px;font-size:13px}
@media(max-width:1100px){.board{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.board{grid-template-columns:1fr}input{min-width:180px}}
</style></head><body>
<h1>Публикационный фронт МАИ · Тримурти</h1>
<div class="sub">""" +str(n)+""" маршрута · исходная карта W12 · восстанавливаемая пакетная обработка</div>
<p class="warning">Карточки содержат исходные W12-аннотации. Научная проверка, журнал и авторские права ещё требуют самостоятельных квитанций. Доска не отправляет писем и рукописей.</p>
<nav>
<div class="stat"><strong>"""+str(n)+"""</strong> маршрута</div>
<div class="stat"><strong>"""+str(manifest["meaning_versions"])+"""</strong> научных версий</div>
<div class="stat"><strong>0</strong> готовых к подаче по подтверждённому QA</div>
<input id="search" placeholder="Поиск по журналу, теме, версии">
<select id="family"><option value="">Все семейства</option><option>A</option><option>B</option><option>C</option><option>D</option><option>E</option><option>F</option></select>
</nav>
<div id="board" class="board"></div>
<script>const CARDS=""" +payload+""";
const COLUMNS=[
{title:"Получено / отправлено",values:["RECEIPT_CONFIRMED","SENT_UNCONFIRMED"]},
{title:"Письма и формы",values:["DRAFT","FORM_PREPARE"]},
{title:"Исходные маршруты",values:["SOURCE_ROUTE_EXTRACTED"]},
{title:"Проверка / удержание",values:["HOLD","REJECTED","POLICY_UNVERIFIED"]}
];
function el(tag,txt,cls){const x=document.createElement(tag);if(cls)x.className=cls;if(txt!==undefined)x.textContent=txt;return x}
function render(){
const q=document.getElementById("search").value.toLowerCase();
const family=document.getElementById("family").value;
const cards=CARDS.filter(c=>(!family||c.family===family)&&
(c.journal+" "+c.title+" "+c.variant+" "+c.deadline).toLowerCase().includes(q));
const board=document.getElementById("board");board.replaceChildren();
for(const col of COLUMNS){
const items=cards.filter(c=>col.values.includes(c.editorial_status));
const node=el("section",undefined,"column");
const h=el("h2",col.title+" — "+items.length);
node.append(h);
for(const item of items){const c=el("article",undefined,"article");
c.append(el("h3",item.journal));
c.append(el("div",item.family+" · "+item.variant+" · "+item.id,"meta"));
c.append(el("p",item.title));
c.append(el("div","Дедлайн W12: "+(item.deadline||"не указан"),"meta"));
c.append(el("div","Технический прогон: "+item.analysis_status+(item.fit_label?" · fit "+item.fit_label:""),"meta"));
c.append(el("div","Индаго: "+item.science_index_status+" · научные ориентиры "+item.science_opponents+" · HUMAN GATE CLOSED","meta"));
c.append(el("div","Научные базы: "+item.published_abstracts+" аннотаций; "+item.published_status,"meta"));
c.append(el("div","Критика: "+item.model_critique_status+" · авторский допуск ЗАКРЫТ","meta"));
c.append(el("div","Кайрон / веб-страница: "+item.venue_web_status+" · правила журнала НЕ ПОДТВЕРЖДЕНЫ","meta"));
const a=el("a","Исходный пакет ↗");a.href=item.packet;
c.append(a);if(item.science_packet){const v=el("a"," · Научные возражения Индаго W69 ↗");v.href=item.science_packet;c.append(v)}
if(item.published_packet){const v=el("a"," · Crossref/OpenAlex ↗");v.href=item.published_packet;c.append(v)}
if(item.model_critique_packet){const v=el("a"," · Критика ↗");v.href=item.model_critique_packet;c.append(v)}
if(item.venue_web_receipt){const v=el("a"," · Кайрон / ответ сайта ↗");v.href=item.venue_web_receipt;c.append(v)}
if(item.venue_web_text){const v=el("a"," · Текст сайта ↗");v.href=item.venue_web_text;c.append(v)}
node.append(c)}
board.append(node)}
}
document.getElementById("search").addEventListener("input",render);
document.getElementById("family").addEventListener("change",render);
render();
</script></body></html>"""

def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--snapshot",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--outreach",type=Path)
    parser.add_argument("--analysis-root",type=Path)
    parser.add_argument("--science-index",type=Path)
    parser.add_argument("--published-sources",type=Path)
    parser.add_argument("--model-challenges",type=Path)
    parser.add_argument("--venue-web",type=Path)
    args=parser.parse_args(argv)
    manifest=materialize(args.source,args.snapshot,args.output,args.outreach,args.analysis_root,args.science_index,args.published_sources,args.model_challenges,args.venue_web)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())
