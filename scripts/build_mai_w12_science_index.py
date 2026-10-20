"""Batch-index prior INDAGO W69 family objections against every authenticated MAI W12 route.

INDEXING is an executed deterministic retrieval over a secondary research
summary, never a new peer review, journal policy check, independent DOI read,
author approval or manuscript. Contradictory candidate claims stay on HOLD.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from typing import Any

HEAD_RE = re.compile(r"^([A-F]) / ([^\r\n]+)$",re.MULTILINE)
DOI_RE = re.compile(r"(?:DOI\s*)?(10\.\d{4,9}/[^\s;,，)]+)",re.I)
PROVENANCE_ID = "1ISWZWzWi16ZxYtUP_K4g8gVTZL8zWQ2HHlpG8TaKXcU"
CONTRACT_SCHEMA = "MAI_W12_PRIOR_RESEARCH_INDEX_V1"
UPSTREAM_SCHEMA = "MAI_W12_BATCH_RESEARCH_PACKET_v1"

def stable(value: Any) -> bytes:
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def _write(path:Path,value:Any)->None:
    raw=stable(value)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)

def extract_heads(text:str)->dict[str,dict[str,Any]]:
    matches=list(HEAD_RE.finditer(text))
    if len(matches)!=6 or [m.group(1) for m in matches]!=list("ABCDEF"):
        raise ValueError("canonical A-F header set missing, reordered or duplicated")
    decision=text.find("DECISION / RESEARCH GATES",matches[-1].end())
    if decision<0:
        raise ValueError("canonical A-F boundary to decision section missing")
    found={}
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else decision
        section=text[m.start():end].strip()
        if len(section)<100:raise ValueError("unexpectedly empty family dossier")
        dois=[]
        for match in DOI_RE.finditer(section):
            doi=match.group(1).rstrip(".)")
            if doi not in dois:dois.append(doi)
        lines=[z.strip() for z in section.splitlines() if z.strip()]
        warnings=[z for z in lines[1:] if any(s in z.lower() for s in (
            "rivals","opponents","blocker","critical","not original",
            "no experiment","no human","needs","reserve","separate",
            "not independently","not new","reject","novum","without"
        ))]
        found[m.group(1)]={
            "family":m.group(1),"heading":m.group(2),
            "char_start":m.start(),"char_end":end,
            "section_sha256":digest(section.encode("utf-8")),
            "secondary_section":section,
            "doi_candidates":dois,
            "recorded_cautions":warnings,
        }
    return found

def build(packets:Path,head_path:Path,donors_path:Path,out:Path)->dict[str,Any]:
    meta=json.loads((packets/"manifest.json").read_text(encoding="utf-8"))
    if meta.get("schema")!="MAI_W12_BATCH_OUTPUT_MANIFEST_v1":
        raise ValueError("unrecognized W12 input manifest")
    raw=head_path.read_bytes()
    text=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
    heads=extract_heads(text)
    donor=json.loads(donors_path.read_text(encoding="utf-8"))
    if donor.get("schema")!="MAI_INDAGO_DONOR_TEXT_PROJECTIONS_v1":
        raise ValueError("incorrect Indago donor catalog")
    ref=next((x for x in donor["sources"] if x.get("drive_file_id")==PROVENANCE_ID),None)
    if ref is None or Path(ref["local_path"]).resolve()!=head_path.resolve():
        raise ValueError("unmatched Indago A-F source ID/local projection")
    all_donors=donor["sources"]
    paths=sorted((packets/"routes").glob("MAI-W12-*.json"))
    if not paths or len(paths)!=meta.get("records"):
        raise ValueError("W12 source route count mismatch")
    review_cards=[]
    for path in paths:
        packet=json.loads(path.read_text(encoding="utf-8"))
        if packet.get("schema")!=UPSTREAM_SCHEMA or packet.get("source_jsonl_sha256")!=meta.get("source_jsonl_sha256"):
            raise ValueError("W12 packet schema/source authority mismatch "+path.name)
        route=packet["route"]
        rid=route["route_id"]
        fam=route["family"]
        if fam not in heads:raise ValueError("family not in prior research "+str(fam))
        h=heads[fam]
        originals=[
            {"source_id":"drive:"+x["drive_file_id"],"read_coverage":x["read_coverage"],
             "source_scope":x["source_scope"]}
            for x in all_donors if x["family"]==fam
        ]
        source_ru=route.get("abstract_ru","")
        if not source_ru.strip():raise ValueError("missing W12 abstract "+rid)
        evidence_status={
            "title_of_scientific_question":h["heading"],
            "original_claim_text_sha256":digest(source_ru.encode("utf-8")),
            "prior_indago_head_file_id":PROVENANCE_ID,
            "prior_indago_head_file_sha256":digest(raw),
            "prior_indago_head_section_sha256":h["section_sha256"],
            "prior_indago_head_normalized_text_char_span":[h["char_start"],h["char_end"]],
            "origin":"INDAGO_W69_PREVIOUSLY_AUTHORED_SECONDARY_RESEARCH",
            "content_read_scope":"RESEARCH_SYNTHESIS_NOT_PRIMARY_PUBLISHED_ARTICLES",
            "publisher_source_bytes_verification":"NOT_RUN_THIS_WAVE",
            "prior_art_doi_candidates":h["doi_candidates"],
            "doi_authority":"CITED_BY_PREVIOUS_INDAGO_RESEARCH_NOT_INDEPENDENTLY_READ_THIS_WAVE",
            "family_level_scientific_cautions":h["recorded_cautions"],
            "family_note":h["secondary_section"],
            "route_literature_url_in_W12":route.get("literature_url",""),
            "route_literature_read_depth":"NOT_READ_IN_THIS_WAVE",
            "author_source_text_projections":originals,
            "author_original_source_coverage":"PARTIAL_TEXT_PROJECTION" if originals else "NOT_INCLUDED_IN_THIS_STAGE",
        }
        blockers=[
            "INDEPENDENT_READ_OF_DECISIVE_PRIOR_ART_NOT_DONE",
            "ROUTE_SPECIFIC_CLAIM_VS_OPPONENT_NOT_ADJUDICATED",
            "VENUE_NATIVE_POLICY_NOT_CURRENTLY_VERIFIED",
            "NO_AUTONOMOUS_INDAGO_OR_ARTIKL_RESEARCH_OPERATION",
            "AUTHOR_APPROVAL_NOT_OBTAINED",
        ]
        if fam=="C":blockers.append("MAI_PARTICIPANT_AUDIO_CONSENT_AND_ORIGINAL_HOMEWORK_UNVERIFIED")
        if fam=="E":blockers.append("PROSPECTIVE_CAUSAL_EXPERIMENT_NOT_PERFORMED")
        if fam=="D":blockers.append("INDEPENDENT_ARTICLE_DISTINCTNESS_NOT_ESTABLISHED_RESERVE")
        if fam=="F":blockers.append("PRIOR_2025_AUTHOR_ARTICLE_MUST_KEEP_DISTINCT_GENEALOGY")
        packet_review={
            "schema":CONTRACT_SCHEMA,
            "route_id":rid,
            "family":fam,
            "variant":route["variant"],
            "journal":route["journal"],
            "working_title":route["title_ru"],
            "source_sheet_id":route.get("original_spreadsheet_id"),
            "source_sheet_cells":route.get("source_cell_range"),
            "source_jsonl_sha256":meta.get("source_jsonl_sha256"),
            "research_index_state":"PREEXISTING_FAMILY_OPPOSITION_INDEXED",
            "scholarly_execution_state":"HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION",
            "scientific_conclusions_accepted":False,
            "author_ready":False,
            "journal_send_authorized":False,
            "science_provenance":evidence_status,
            "blockers":blockers,
            "next_operation":"QUALIFY_ROUTE_WITH_EXISTING_RESEARCH_AND_SOURCE_NATIVE_READ",
        }
        _write(out/"routes"/(rid+".json"),packet_review)
        review_cards.append({
            "route_id":rid,"family":fam,"journal":route["journal"],
            "variant":route["variant"],
            "opponents_indexed_from_prior_indago":len(h["doi_candidates"]),
            "route_literature_listed":bool(route.get("literature_url")),
            "direct_publisher_reads_this_wave":0,
            "family_author_source_projections":len(originals),
            "research_status":packet_review["scholarly_execution_state"],
            "review_packet":f"routes/{rid}.json",
            "blockers":len(blockers),
        })
    doi_count=sum(len(h["doi_candidates"]) for h in heads.values())
    result={
        "schema":CONTRACT_SCHEMA,
        "source_indago_head_file_id":PROVENANCE_ID,
        "source_indago_head_sha256":digest(raw),
        "source_W12_sha256":meta.get("source_jsonl_sha256"),
        "route_count":len(review_cards),
        "head_count":len(heads),
        "head_doi_candidates_total":doi_count,
        "route_statuses":{"PREEXISTING_FAMILY_OPPOSITION_INDEXED":len(review_cards)},
        "real_research_operations_this_wave":0,
        "route_author_ready_count":0,
        "external_send_count":0,
        "first_class_family_warnings":"Extracted mechanically from prior INDAGO 08, NOT newly adjudicated",
        "review_cards":review_cards,
    }
    _write(out/"science_index.json",result)
    _write(out/"family_heads_index.json",heads)
    with (out/"science_index.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(review_cards[0]))
        writer.writeheader();writer.writerows(review_cards)
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--indago-head",type=Path,required=True)
    p.add_argument("--donors",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=build(a.packets,a.indago_head,a.donors,a.output)
    print(json.dumps({k:v for k,v in result.items() if k!="review_cards"},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
