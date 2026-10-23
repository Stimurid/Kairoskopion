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

def kairon_policy_candidates_for_route(
    route: dict[str, Any], output: Path, source_sha: str,
    venue_source_root: Path | None,
    venue_policy_root: Path | None,
) -> dict[str, Any]:
    """Copy *provisional* source-anchored model claims. Never approve a venue policy."""
    empty={"status":"NOT_ANALYZED","claims":0,"detail":"","route_type":"UNKNOWN",
           "deadline_hint":"","channel_hint":"","currentness":"NOT_VERIFIED"}
    if venue_policy_root is None:return empty
    rid=route["route_id"]
    if venue_source_root is None:
        raise ValueError("venue policy model depends on separately captured actual publisher HTML")
    srcfile=venue_source_root/"routes"/(rid+".json")
    policy=venue_policy_root/"routes"/(rid+".json")
    if not policy.is_file():return empty
    if not srcfile.is_file():
        raise ValueError("policy claim has no independent web receipt "+rid)
    raw=policy.read_bytes()
    item=json.loads(raw.decode("utf-8"))
    pub=json.loads(srcfile.read_text(encoding="utf-8"))
    web=pub.get("web_source") or {}
    if (item.get("schema")!="MAI_KAIRON_QUOTE_ANCHORED_POLICY_CANDIDATE_v1"
            or item.get("route_id")!=rid
            or item.get("source_W12_sha256")!=source_sha
            or item.get("captured_web_receipt_sha256")!=sha((
                json.dumps(pub,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
            or item.get("web_source_state")!=web.get("status")
            or item.get("official_publisher_policy_accepted") is not False
            or item.get("web_page_currentness_accepted") is not False
            or item.get("human_author_gate")!="HOLD"
            or item.get("journal_send_count")!=0):
        raise ValueError("policy candidate attempts authority promotion "+rid)
    status=item.get("status")
    if status=="SOURCE_WEB_READ_BLOCKED":
        if item.get("cited_claims") or web.get("status")=="FETCHED_TEXT":
            raise ValueError("blocked policy source cannot cite publisher text "+rid)
        claims=[]
    elif status=="QUOTED_POLICY_CANDIDATES_PROVISIONAL":
        if web.get("status")!="FETCHED_TEXT":
            raise ValueError("policy claim needs publisher text not blocked source "+rid)
        if not item.get("model_operation_input_digest"):
            raise ValueError("policy claim has no model operation digest "+rid)
        candidates=[
            f for f in (venue_policy_root/"chunks").glob("*/accepted.json")
            if (sha(f.read_bytes())==item.get("model_operation_receipt_sha256")
                and json.loads(f.read_text(encoding="utf-8")).get("input_digest")==item["model_operation_input_digest"])
        ]
        if len(candidates)!=1:
            raise ValueError("policy claim model operation missing or duplicated "+rid)
        proof=json.loads(candidates[0].read_text(encoding="utf-8"))
        if (sha(candidates[0].read_bytes())!=item.get("model_operation_receipt_sha256")
                or proof.get("schema")!="MAI_KAIRON_POLICY_OPERATION_RECEIPT_v1"
                or proof.get("all_policy_authority_gates")!="HOLD"
                or proof.get("external_submission_count")!=0
                or proof.get("human_author_gate")!="HOLD"):
            raise ValueError("unattested policy model operation "+rid)
        cited=[v for v in proof.get("verified_policy_claims",[]) if v.get("route_id")==rid]
        if (len(cited)!=1 or cited[0].get("cited_claims")!=item.get("cited_claims")
                or cited[0].get("route_type_candidate")!=item.get("route_type_candidate")):
            raise ValueError("policy citations disagree with producer evidence "+rid)
        text_file=venue_source_root/"url_capture_cache"/sha(route["official_url"].encode("utf-8"))[:24]/"visible_text.txt"
        if not text_file.is_file():raise ValueError("source web text is missing "+rid)
        txt=text_file.read_text(encoding="utf-8").rstrip("\r\n")
        if sha(txt.encode("utf-8"))!=web.get("visible_text_sha256"):
            raise ValueError("source web text was altered after policy extraction "+rid)
        claims=item.get("cited_claims") or []
        for claim in claims:
            exact=claim.get("exact_quote","")
            if (exact not in txt or
                    claim.get("passage_id")!=rid+"#"+sha(exact.encode("utf-8"))[:16] or
                    claim.get("quote_offset")!=txt.find(exact)):
                raise ValueError("policy evidence quote or byte anchor drift "+rid)
    else:
        raise ValueError("unknown policy candidate stage "+rid)
    target=output/"policies"/(rid+".json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
    hints={kind:next((c["value"] for c in claims if c["kind"]==kind),"") for kind in (
        "ABSTRACT_DEADLINE","MANUSCRIPT_DEADLINE","ABSTRACT_CHANNEL","MANUSCRIPT_CHANNEL")}
    return {
        "status":status,"claims":len(claims),
        "detail":"policies/"+rid+".json",
        "route_type":item.get("route_type_candidate","UNKNOWN"),
        "deadline_hint":hints["ABSTRACT_DEADLINE"] or hints["MANUSCRIPT_DEADLINE"],
        "channel_hint":hints["ABSTRACT_CHANNEL"] or hints["MANUSCRIPT_CHANNEL"],
        "currentness":"NOT_VERIFIED",
        "receipt_sha256":sha(raw),
        "authority_gate":"HOLD",
    }

def kairon_native_publisher_sources_for_route(
    route:dict[str,Any],output:Path,source_sha:str,native_root:Path|None
)->dict[str,Any]:
    if native_root is None:return {"count":0,"detail":"","native_metadata_matches":0}
    rid=route["route_id"]
    rows=[]
    for path in sorted((native_root/"routes"/rid).glob("*.json")):
        record=json.loads(path.read_text(encoding="utf-8"))
        doi=record.get("DOI","")
        provider_file=(native_root/"doi_provider_cache"/sha(doi.encode("utf-8"))[:20]/"crossref.json")
        publisher_root=(native_root/"url_capture_cache"/sha(record.get("original_publisher_url","").encode("utf-8"))[:24])
        capture_file=publisher_root/"capture.json"
        if (record.get("schema")!="MAI_KAIRON_NATIVE_PUBLISHER_WORK_SOURCE_v1"
                or record.get("route_id")!=rid
                or record.get("source_W12_sha256")!=source_sha
                or record.get("W12_venue")!=route["journal"]
                or record.get("W12_meaning_version")!=route["variant"]
                or record.get("crossref_DOI_identity_match") is not True
                or record.get("is_native_in_target_journal_by_Crossref") is not True
                or record.get("publisher_host_observed_same") is not True
                or record.get("genre_peer_research_verified") is not False
                or record.get("research_claims_evaluated") is not False
                or record.get("venue_current_policy_verified") is not False
                or record.get("artikl_author_decision")!="HOLD"
                or record.get("journal_submission_actions")!=0
                or record.get("read_depth")!="PUBLISHER_VISIBLE_HTML_TEXT_CAPTURED_NOT_SCHOLARLY_FULL_READ"
                or not provider_file.is_file() or not capture_file.is_file()):
            raise ValueError("Kairon native publication record cannot promote source to approved research "+rid)
        provider=json.loads(provider_file.read_text(encoding="utf-8"))
        pub=json.loads(capture_file.read_text(encoding="utf-8"))
        if (record.get("crossref_source_receipt_sha256")!=sha((
                  json.dumps({k:v for k,v in provider.items() if k!="from_cache"},
                             ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
                or provider.get("parsed",{}).get("doi_identity_match") is not True
                or provider.get("parsed",{}).get("venue")!=route["journal"]
                or provider.get("requested_doi")!=doi
                or pub.get("raw_sha256")!=record.get("publisher_html_raw_sha256")
                or pub.get("status")!="FETCHED_TEXT"):
            raise ValueError("Kairon venue-native paper metadata/source receipt mismatch "+rid)
        original=publisher_root/"source.bin"
        if not original.is_file() or sha(original.read_bytes())!=record["publisher_html_raw_sha256"]:
            raise ValueError("Kairon publisher original HTML byte digest missing "+rid)
        copy=output/"venue_native"/rid/path.name
        copy.parent.mkdir(parents=True,exist_ok=True)
        copy.write_bytes(path.read_bytes())
        rows.append({
            "doi":doi,"title":record["title"],
            "publication_url":record["original_publisher_url"],
            "evidence_record":"venue_native/"+rid+"/"+path.name,
            "read_depth":record["read_depth"],
            "publisher_html_raw_sha256":record["publisher_html_raw_sha256"],
        })
    if not rows:return {"count":0,"detail":"","native_metadata_matches":0}
    index=output/"venue_native"/rid/"index.json"
    index.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {
        "count":len(rows),
        "detail":"venue_native/"+rid+"/index.json",
        "native_metadata_matches":len(rows),
        "scholarly_full_texts_accepted":0,
        "editorial_world_qualified":False,
    }

def native_scholarly_model_read_for_route(
    route:dict[str,Any],output:Path,source_sha:str,
    work_root:Path|None,review_root:Path|None,
)->dict[str,Any]:
    """Read back original publisher HTML and every model-cited passage."""
    empty={"status":"NOT_RUN","count":0,"anchors":0,"detail":"",
           "scholarly_authority":"HOLD"}
    if review_root is None:return empty
    if work_root is None:
        raise ValueError("scholarly model reading requires original publisher source corpus")
    rid=route["route_id"]
    if rid!="MAI-W12-009":
        return empty  # narrow real-science pilot; do not promote other routes
    read_receipt=review_root/"native_scholarly_read_receipt.json"
    if not read_receipt.is_file():
        raise ValueError("native scholarly model reading receipt not written")
    result=json.loads(read_receipt.read_text(encoding="utf-8"))
    if (result.get("schema")!="MAI_ARTIKL_NATIVE_SCHOLARLY_READ_BATCH_v1"
            or result.get("route_id")!=rid
            or result.get("source_w12_sha256")!=source_sha
            or result.get("author_gates_approved")!=0
            or result.get("world_mutations_applied")!=0
            or result.get("external_submission_count")!=0
            or result.get("scientific_novelty_peer_accepted")!=0):
        raise ValueError("scientific model attempted author/World promotion "+rid)
    entries=result.get("papers") or []
    if len(entries)!=3:
        raise ValueError("three original same-journal works required for current pilot")
    admitted=[]
    for rec in entries:
        doi=rec.get("doi","")
        root=review_root/"papers"/sha(doi.encode("utf-8"))[:20]
        proof_file=root/"accepted_challenge.json"
        source_file=root/"source_input.json"
        if not proof_file.is_file() or not source_file.is_file():
            raise ValueError("scientific model missing real published-source proof "+doi)
        proof=json.loads(proof_file.read_text(encoding="utf-8"))
        src=json.loads(source_file.read_text(encoding="utf-8"))
        model=proof.get("verified_review") or {}
        original=proof.get("model_output") or {}
        if (proof.get("schema")!="MAI_ARTIKL_NATIVE_PUBLISHER_SCHOLARLY_CHALLENGE_v1"
                or proof.get("input_key")!=sha((
                    json.dumps(src,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
                or proof.get("model_response_sha256")!=sha((
                    json.dumps(original,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
                or proof.get("scientific_adjudication")!="PROVISIONAL"
                or proof.get("independent_human_scholarly_peer_review")!="NOT_DONE"
                or proof.get("author_decision")!="HOLD"
                or proof.get("external_send_count")!=0
                or src.get("source_W12_sha256")!=source_sha
                or src.get("route_id")!=rid
                or src.get("doi")!=doi
                or src.get("source_W12_scientific_claim",{}).get("title_ru")!=route["title_ru"]
                or src.get("source_W12_scientific_claim",{}).get("abstract_ru")!=route["abstract_ru"]
                or model.get("doi")!=doi
                or model.get("route_id")!=rid
                or model.get("source_read_depth")!="PUBLISHER_HTML_MAIN_BODY_MODEL_READ"
                or model.get("science_novelty_author_accepted") is not False
                or model.get("research_novelty_author_accepted") is not False
                or model.get("journal_send_count")!=0
                or model.get("author_gate")!="HOLD"
                or model.get("scientific_stage")!="NATIVE_SAME_JOURNAL_ARGUMENT_CRITIQUE_PROVISIONAL"):
            raise ValueError("scholarly model report has unsupported authority/source "+doi)
        url=src["original_publisher_url"]
        native_path=work_root/"url_capture_cache"/sha(url.encode("utf-8"))[:24]
        raw=(native_path/"source.bin")
        visible=(native_path/"visible_text.txt")
        article=src.get("publisher_readable_article_main_body","")
        if (not raw.is_file() or not visible.is_file()
                or sha(raw.read_bytes())!=src.get("original_publisher_html_sha256")
                or sha(raw.read_bytes())!=model.get("original_pub_html_sha256")
                or sha(visible.read_text(encoding="utf-8").rstrip("\r\n").encode("utf-8"))!=src.get("original_visible_text_sha256")
                or not visible.read_text(encoding="utf-8").lstrip().startswith(article)
                or len(article)<6500
                or sha(article.encode("utf-8"))!=src.get("publisher_readable_main_body_sha256")
                or sha(article.encode("utf-8"))!=model.get("article_body_source_sha256")):
            raise ValueError("published article body changed after model reading "+doi)
        # Validate the model's provenance and quote offsets against the original text.
        if (model.get("anchors") is None or len(model["anchors"])<3
                or len(model["anchors"])!=rec.get("source_anchor_count")
                or rec.get("status") not in ("CACHED","MODEL_QUOTE_VERIFIED","RECOVERED_QUOTE_REVALIDATED")):
            raise ValueError("insufficient independent publisher main body citations "+doi)
        orig_anchors=original.get("anchors") or []
        for idx,quote in enumerate(model["anchors"]):
            text=quote.get("exact_quote","")
            if (not isinstance(text,str) or not 25<=len(text)<=290
                    or not text in article
                    or text!=orig_anchors[idx].get("exact_quote")
                    or quote.get("quote_sha256")!=sha(text.encode("utf-8"))
                    or quote.get("publisher_main_body_offset")!=article.index(text)
                    or quote.get("publisher_original_visible_text_sha256")!=src["original_visible_text_sha256"]):
                raise ValueError("false scientific publisher quote/offset "+doi)
        dest=output/"native_scholarly"/rid/(sha(doi.encode("utf-8"))[:20]+".json")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(proof_file.read_bytes())
        admitted.append({
            "doi":doi,
            "title":rec.get("title",""),
            "source_read_depth":"PUBLISHER_HTML_MAIN_BODY_MODEL_READ",
            "review_receipt":"native_scholarly/"+rid+"/"+dest.name,
            "quote_anchors":len(model["anchors"]),
            "argument_objection":model.get("strongest_source_grounded_objection","")[:380],
            "science_admission":"PROVISIONAL_REQUIRES_HUMAN",
        })
    index=output/"native_scholarly"/rid/"index.json"
    index.write_text(json.dumps(admitted,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {
        "status":"QUOTE_ATTESTED_ARTIKL_NATIVE_MACHINE_READING",
        "count":len(admitted),
        "anchors":sum(x["quote_anchors"] for x in admitted),
        "detail":"native_scholarly/"+rid+"/index.json",
        "scholarly_authority":"HOLD",
        "independent_review_certified":0,
    }

def scientific_field_reopen_candidate_for_route(
    route:dict[str,Any],output:Path,source_sha:str,
    native_scholarly_root:Path|None,field_root:Path|None
)->dict[str,Any]:
    """Artikl's citation-linked cross-paper World return is ALWAYS only proposed."""
    empty={"status":"NOT_PROPOSED","detail":"","competing_papers":0,
           "source_anchors":0,"world_mutation_applied":False,
           "author_decision":"HOLD"}
    if field_root is None:return empty
    if native_scholarly_root is None:
        raise ValueError("field return depends on actual verified scholarly model reading")
    rid=route["route_id"]
    if rid!="MAI-W12-009":return empty
    receipt_file=field_root/"field_reopen_proposal.json"
    data_file=field_root/"source_input.json"
    model_file=field_root/"model_output.json"
    if not (receipt_file.is_file() and data_file.is_file() and model_file.is_file()):
        raise ValueError("field reopen is missing actual scholarly producer output")
    raw=receipt_file.read_bytes()
    receipt=json.loads(raw.decode("utf-8"))
    content=json.loads(data_file.read_text(encoding="utf-8"))
    model=json.loads(model_file.read_text(encoding="utf-8"))
    proposal=receipt.get("verified_proposal") or {}
    if (receipt.get("schema")!="MAI_ARTIKL_A3A4_NATIVE_FIELD_REOPEN_RECEIPT_v1"
            or receipt.get("source_input_sha256")!=sha((
                json.dumps(content,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
            or receipt.get("original_scholarship_model_output_sha256")!=sha((
                json.dumps(model,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"))
            or receipt.get("author_decision")!="HOLD"
            or receipt.get("world_mutations")!=0
            or receipt.get("journal_send_count")!=0
            or receipt.get("human_scientific_evaluation")!="REQUIRED"
            or content.get("route_id")!=rid
            or content.get("source_W12_sha256")!=source_sha
            or content.get("owner_original_W12_title_ru")!=route["title_ru"]
            or content.get("owner_original_W12_abstract_ru")!=route["abstract_ru"]
            or content.get("author_source_mutation_authorized") is not False
            or proposal.get("schema")!="MAI_ARTIKL_A3A4_NATIVE_FIELD_REOPEN_CANDIDATE_v1"
            or proposal.get("field_reopen_proposal_kind")!="FIELD_REOPEN_PROPOSAL"
            or proposal.get("route_id")!=rid
            or proposal.get("source_W12_sha256")!=source_sha
            or proposal.get("author_world_change_approved") is not False
            or proposal.get("author_draft_rewritten") is not False
            or proposal.get("author_publication_identity_accepted") is not False
            or proposal.get("journal_venue_policy_certified") is not False
            or proposal.get("external_send_count")!=0
            or proposal.get("downstream_gate")!="HUMAN_SCHOLARLY_ADJUDICATION_PENDING"):
        raise ValueError("field-return source authority/author-gate contradiction")
    evidence=content.get("three_published_native_paper_evidence") or []
    if len(evidence)!=3:
        raise ValueError("field reopen must be triangulated by three real publisher works")
    allowed={record.get("doi"):record for record in evidence}
    if len(allowed)!=3 or any(record.get("paper_review_receipt_sha256")!=sha((
            native_scholarly_root/"papers"/sha(record["doi"].encode("utf-8"))[:20]/"accepted_challenge.json").read_bytes()
                                     ) for record in evidence):
        raise ValueError("field reopen depends on altered or missing paper model evidence")
    paper_anchors={doi:{x["quote_sha256"] for x in source.get("source_anchors",[])}
                   for doi,source in allowed.items()}
    backlinks=proposal.get("source_anchor_ids") or []
    if (not 3<=len(backlinks)<=8
            or {x.get("doi") for x in backlinks}!=set(allowed)):
        raise ValueError("World return lacks coverage of three unique DOI sources")
    for link in backlinks:
        if link.get("quote_sha256") not in paper_anchors[link["doi"]]:
            raise ValueError("World return claims a nonexistent published-source anchor")
        if (link.get("quote_source_type")!="ACTUAL_SAME_JOURNAL_PUBLISHER_MAIN_BODY"
                or link.get("published_article_original_url")!=allowed[link["doi"]]["article_original_url"]):
            raise ValueError("World return citation source/role mismatch")
    target=output/"world_return"/rid/"field_reopen_proposal.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
    return {
        "status":"NATIVE_THREE_PAPER_FIELD_REOPEN_PROPOSED",
        "detail":"world_return/"+rid+"/field_reopen_proposal.json",
        "competing_papers":len(evidence),
        "source_anchors":len(backlinks),
        "world_mutation_applied":False,
        "author_decision":"HOLD",
        "decision_candidate":proposal.get("decision_candidate",""),
    }

def native_kairon_graph_world_return_for_route(
    route:dict[str,Any],output:Path,source_sha:str,
    field_root:Path|None,graph_root:Path|None,
)->dict[str,Any]:
    """Verify actual Kairon graph events, not a duplicate invented graph status."""
    empty={"status":"NOT_GRAPH_RECORDED","detail":"",
           "pinned_evidence_count":0,"world_mutations":0,
           "author_gate":"HOLD"}
    if graph_root is None:return empty
    if field_root is None:
        raise ValueError("native graph events require the cited scientific FieldReopen receipt")
    rid=route["route_id"]
    if rid!="MAI-W12-009":return empty
    return_file=graph_root/"MAI_A_EDUCATION_A3A4_GRAPH_WORLD_RETURN_RECEIPT.json"
    original_field=field_root/"field_reopen_proposal.json"
    if not return_file.is_file() or not original_field.is_file():
        raise ValueError("native source/World graph return receipts not created")
    raw=return_file.read_bytes()
    rec=json.loads(raw.decode("utf-8"))
    pins=rec.get("source_evidence_pins") or []
    if (rec.get("schema")!="MAI_ARTIKL_A3A4_NATIVE_GRAPH_REOPEN_EVENT_IMPORT_v1"
            or rec.get("source_route_id")!=rid
            or rec.get("source_W12_sha256")!=source_sha
            or rec.get("case_publisher_original_work_count")!=3
            or rec.get("science_anchor_count",0)<3
            or rec.get("human_gate")!="AUTHOR_REVIEW_REQUIRED"
            or rec.get("world_mutations")!=0
            or rec.get("outbound_submissions")!=0
            or rec.get("article_seeds_automatically_created")!=0
            or rec.get("implementation")!="EXISTING_OPPORTUNITY_GRAPH_STORE"
            or rec.get("source_original_reopen_sha256")!=sha(original_field.read_bytes())
            or len(pins)!=3
            or len({x.get("doi") for x in pins})!=3):
        raise ValueError("graph World-return evidence or owner authority mismatch")
    graph=graph_root/"kairon_provider"/"opportunity_graph"
    def path_of(name:Any,kind:str)->Path:
        token=sha(json.dumps(name,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
        return graph/kind/(token+".json")
    eid=rec["research_negative_event_id"]
    pid=rec["research_field_reopen_event_id"]
    negative_file=path_of(eid,"events")
    reopen_file=path_of(pid,"events")
    if not negative_file.is_file() or not reopen_file.is_file():
        raise ValueError("native OpportunityGraphStore events lost")
    negative=json.loads(negative_file.read_text(encoding="utf-8"))
    reopen=json.loads(reopen_file.read_text(encoding="utf-8"))
    if (negative.get("kind")!="HUNT_RESULT"
            or negative.get("event_id")!=eid
            or negative.get("subject_id")!=rid
            or not str(negative.get("result","")).startswith("REJECT_")
            or negative.get("author_decision")!="HOLD"
            or negative.get("world_mutation")!="NONE"
            or negative.get("external_send")!="DISABLED"
            or negative.get("source_evidence_pins")!=pins
            or negative.get("synthesis_receipt_sha256")!=sha(original_field.read_bytes())
            or reopen.get("kind")!="FIELD_REOPEN_PROPOSAL"
            or reopen.get("event_id")!=pid
            or reopen.get("source_event_id")!=eid
            or reopen.get("subject_id")!=rid
            or reopen.get("author_gate")!="AUTHOR_REVIEW_REQUIRED"
            or reopen.get("semantic_mutation")!="NONE"):
        raise ValueError("existing graph event source or author gate mismatch")
    for pin in pins:
        doi=pin["doi"]
        source_id=pin["id"]
        rev=pin["revision"]
        source_file=path_of(["Evidence",source_id,rev],"records")
        if not source_file.is_file():
            raise ValueError("graph source evidence missing "+doi)
        evidence=json.loads(source_file.read_text(encoding="utf-8"))
        if (evidence.get("kind")!="Evidence"
                or evidence.get("id")!=source_id
                or evidence.get("revision")!=rev
                or evidence.get("source_doi")!=doi
                or evidence.get("source_ref")!=pin["source_url"]
                or evidence.get("source_content_sha256")!=pin["sha256"]
                or evidence.get("read_depth")!="SECTIONS"
                or evidence.get("qualified_for_article") is not False
                or evidence.get("author_approved") is not False
                or evidence.get("author_gate")!="HOLD"
                or not evidence.get("passage_anchors")):
            raise ValueError("graph published-source Evidence authority/anchor drift "+doi)
    dest=output/"graph_events"/rid
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"graph_import_receipt.json").write_bytes(raw)
    (dest/"HUNT_RESULT.json").write_bytes(negative_file.read_bytes())
    (dest/"FIELD_REOPEN_PROPOSAL.json").write_bytes(reopen_file.read_bytes())
    return {
        "status":"EXISTING_KAIRON_GRAPH_EVENTS_SOURCE_ATTESTED",
        "detail":"graph_events/"+rid+"/graph_import_receipt.json",
        "event_link":"graph_events/"+rid+"/FIELD_REOPEN_PROPOSAL.json",
        "pinned_evidence_count":len(pins),
        "world_mutations":0,
        "author_gate":"HOLD",
    }

def materialize(source: Path, snapshot_path: Path, output: Path, outreach_path: Path | None = None, analysis_root: Path | None = None, science_index_path: Path | None = None, publisher_root: Path | None = None, model_root: Path | None = None, venue_web_root: Path | None = None, venue_policy_root: Path | None = None, venue_native_root: Path | None = None, native_scholarly_root: Path | None = None, field_reopen_root: Path | None = None, field_graph_root: Path | None = None) -> dict[str, Any]:
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
        policy=kairon_policy_candidates_for_route(
            r,output,source_hash,venue_web_root,venue_policy_root)
        native=kairon_native_publisher_sources_for_route(
            r,output,source_hash,venue_native_root)
        scholarly=native_scholarly_model_read_for_route(
            r,output,source_hash,venue_native_root,native_scholarly_root)
        reopen=scientific_field_reopen_candidate_for_route(
            r,output,source_hash,native_scholarly_root,field_reopen_root)
        graphreturn=native_kairon_graph_world_return_for_route(
            r,output,source_hash,field_reopen_root,field_graph_root)
        packet={
            "schema":SCHEMA,"source_jsonl_sha256":source_hash,
            "snapshot_sha256":sha(snapshot_bytes),"outreach_sha256":events_sha,
            "route":r,"outreach_events":related,
            "local_analysis":analysis,
            "science_index":science,
            "published_source_evidence":published,
            "model_scientific_critique":model,
            "venue_web_evidence":venue,
            "venue_policy_candidates":policy,
            "venue_native_publisher_sources":native,
            "native_scholarly_model_read":scholarly,
            "scientific_field_reopen_proposal":reopen,
            "native_existing_graph_world_return":graphreturn,
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
            "venue_policy_claims":policy["claims"],
            "venue_policy_status":policy["status"],
            "venue_policy_detail":policy["detail"],
            "venue_policy_route_candidate":policy["route_type"],
            "venue_policy_deadline_hint":policy["deadline_hint"],
            "venue_policy_channel_hint":policy["channel_hint"],
            "venue_native_publication_sources":native["count"],
            "venue_native_publication_index":native["detail"],
            "native_scholarly_read_status":scholarly["status"],
            "native_scholarly_read_count":scholarly["count"],
            "native_scholarly_read_anchors":scholarly["anchors"],
            "native_scholarly_read_detail":scholarly["detail"],
            "field_reopen_proposal_status":reopen["status"],
            "field_reopen_proposal_detail":reopen["detail"],
            "field_reopen_source_anchors":reopen["source_anchors"],
            "native_graph_field_reopen_status":graphreturn["status"],
            "native_graph_field_reopen_detail":graphreturn["detail"],
            "native_graph_field_reopen_event":graphreturn.get("event_link",""),
            "native_graph_original_evidence_count":graphreturn["pinned_evidence_count"],
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
        "venue_policy_candidate_count":sum(bool(x["venue_policy_detail"]) for x in index),
        "venue_policy_cited_claim_count":sum(x["venue_policy_claims"] for x in index),
        "venue_native_publication_source_count":sum(x["venue_native_publication_sources"] for x in index),
        "venue_native_scholarly_full_texts_certified":0,
        "native_scholarly_model_reads_count":sum(x["native_scholarly_read_count"] for x in index),
        "native_scholarly_model_read_anchors":sum(x["native_scholarly_read_anchors"] for x in index),
        "native_scholarly_independent_scholarly_acceptance":0,
        "scientific_field_reopen_proposal_count":sum(bool(x["field_reopen_proposal_detail"]) for x in index),
        "scientific_field_reopen_world_mutations":0,
        "native_kairon_graph_field_reopens":sum(bool(x["native_graph_field_reopen_event"]) for x in index),
        "native_kairon_graph_original_evidence_count":sum(x["native_graph_original_evidence_count"] for x in index),
        "native_kairon_graph_author_approvals":0,
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
c.append(el("div","Требования из страницы: "+item.venue_policy_claims+" цитат · "+item.venue_policy_route_candidate+" · КВАЛИФИКАЦИЯ HOLD","meta"));
if(item.venue_policy_deadline_hint){c.append(el("div","Срок из цитаты: "+item.venue_policy_deadline_hint+" (ещё не утверждён)","meta"))}
if(item.venue_policy_channel_hint){c.append(el("div","Канал из цитаты: "+item.venue_policy_channel_hint+" (ещё не утверждён)","meta"))}
const a=el("a","Исходный пакет ↗");a.href=item.packet;
c.append(a);if(item.science_packet){const v=el("a"," · Научные возражения Индаго W69 ↗");v.href=item.science_packet;c.append(v)}
if(item.published_packet){const v=el("a"," · Crossref/OpenAlex ↗");v.href=item.published_packet;c.append(v)}
if(item.model_critique_packet){const v=el("a"," · Критика ↗");v.href=item.model_critique_packet;c.append(v)}
if(item.venue_web_receipt){const v=el("a"," · Кайрон / ответ сайта ↗");v.href=item.venue_web_receipt;c.append(v)}
if(item.venue_web_text){const v=el("a"," · Текст сайта ↗");v.href=item.venue_web_text;c.append(v)}
if(item.venue_policy_detail){const v=el("a"," · Цитаты и требования ↗");v.href=item.venue_policy_detail;c.append(v)}
if(item.venue_native_publication_index){const z=el("a"," | Native journal works: "+item.venue_native_publication_sources);z.href=item.venue_native_publication_index;c.append(z)}
if(item.native_scholarly_read_detail){const z=el("a"," | Artikl: исходные аргументы и оппоненты ("+item.native_scholarly_read_count+")");z.href=item.native_scholarly_read_detail;c.append(z)}
if(item.field_reopen_proposal_detail){const v=el("a"," | Возврат к исходному тезису (научный HOLD)");v.href=item.field_reopen_proposal_detail;c.append(v)}
if(item.native_graph_field_reopen_event){const v=el("a"," | Kairon Graph: научный возврат ↗");v.href=item.native_graph_field_reopen_event;c.append(v)}
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
    parser.add_argument("--venue-policy",type=Path)
    parser.add_argument("--venue-native",type=Path)
    parser.add_argument("--native-scholarly",type=Path)
    parser.add_argument("--field-reopen",type=Path)
    parser.add_argument("--field-graph-root",type=Path)
    args=parser.parse_args(argv)
    manifest=materialize(args.source,args.snapshot,args.output,args.outreach,args.analysis_root,args.science_index,args.published_sources,args.model_challenges,args.venue_web,args.venue_policy,args.venue_native,args.native_scholarly,args.field_reopen,args.field_graph_root)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())
