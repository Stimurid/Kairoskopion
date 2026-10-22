"""Artikl/WhiteCrow: three-source-anchored A3/A4 FieldReopenProposal candidate.

Consumes actual verified main-body machine scholarly reviews from three
independent articles in the SAME target journal. Produces a versioned proposal
for author-visible return to World with explicit truth/novelty obligations.

NEVER modifies World or author material, never author-admits scholarship or
sends proposals to external journals. Run-local evidence is owner-private.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import subprocess
from typing import Any

from fetch_mai_venue_pages import load,sha,stable,write
from run_mai_native_scholarly_read import paper_inputs,validate

SCHEMA="MAI_ARTIKL_A3A4_NATIVE_FIELD_REOPEN_CANDIDATE_v1"
FIELDS=(
  "strongest_cross_paper_opposition",
  "what_was_already_done_in_published_work",
  "residual_MAI_normative_object",
  "original_A3A4_difference_proven_to_be_testable",
  "proposed_revised_claim_v1",
  "test_case_high_performance_without_rights",
  "test_case_formal_rights_low_performance",
  "competing_explanation_to_rule_out",
  "procedure_and_primary_discriminating_variable",
  "what_would_defeat_the_revised_claim",
  "additional_source_or_evidence_debt",
  "why_not_ready_for_submission",
  "author_adoption_question",
)
LABELS=("REVISE_SOURCE_CANDIDATE","RESEARCH_HOLD","NOVELTY_OVERLAP_WARNING","REJECT_CANDIDATE")
SCHEMA_JSON={
 "type":"object","additionalProperties":False,
 "properties":{
  "route_id":{"type":"string"},
  "decision_candidate":{"type":"string","enum":list(LABELS)},
  "three_source_distinctions":{"type":"array","minItems":3,"maxItems":3,
    "items":{"type":"object","additionalProperties":False,
      "properties":{
       "doi":{"type":"string"},
       "role_against_A3A4":{"type":"string"},
       "retained_MAI_difference_if_any":{"type":"string"}
      },"required":["doi","role_against_A3A4","retained_MAI_difference_if_any"]
    }},
  **{name:{"type":"string"} for name in FIELDS},
  "source_anchor_ids":{"type":"array","minItems":3,"maxItems":8,
    "items":{"type":"object","additionalProperties":False,
      "properties":{
        "doi":{"type":"string"},"quote_sha256":{"type":"string"},
        "why_this_proves_the_claim":{"type":"string"},
      },"required":["doi","quote_sha256","why_this_proves_the_claim"]
  }},
 },
 "required":["route_id","decision_candidate","three_source_distinctions",*FIELDS,"source_anchor_ids"],
}
PROMPT="""АРТИКЛЬ / WHITECROW / FIELD REOPEN — РЕАЛЬНОЕ НАУЧНОЕ УТОЧНЕНИЕ.
Задание: имея три отдельно проверенных МАШИННЫХ чтения ОРИГИНАЛЬНЫХ научных
работ того же журнала, сопоставь их аргументы с собственным A3/A4 МАИ.
Материал уже привязан к буквальным цитатам и DOI; не требуй их повторного
поиска, но не превращай авторский тезис в доказанный.

Тебе необходимо провести синтез С РИСКОМ ДЛЯ ГИПОТЕЗЫ:
1. Назови, что каждая опубликованная работа реально сделала и чего не сделала.
2. Найди общий научный долг, не спасай авторскую новизну искусственно.
3. Сформулируй единственное минимальное содержательное изменение тезиса v1,
   если остаётся реально самостоятельная проблема. Если доказательств нет,
   ставь HOLD/REJECT в decision_candidate.
4. Поставь два обязательных различающих философских контрслучая A3/A4:
   (a) технически блестящая система без права изменять норму;
   (b) формально уполномоченный орган, который плохо справляется с задачей.
5. Сформулируй контрольную переменную/операцию:
   кто может зарегистрировать ошибку? кто полномочен пересмотреть сам критерий?
   каким наблюдаемым решением санкционирован пересмотр? что изменилось в праве?
   какой исход опровергает заявленную новизну? Не писать “нужен эксперимент”
   без измеримого действия/условий.
6. Привяжи три независимых статьи к min 3 max 8 SOURCE ANCHOR ID:
   doi + quote_sha256 из разрешённого массива; НЕ выдумывай новые DOI.
7. Не выдавай придуманный вариант за сообщение автора. Не изменяй World.
   Не редактируй в этом шаге ни одну статью, не создавай отправки, не
   принимай рукопись, не сертифицируй актуальный CFP журнала.
8. Запиши, какой следующий настоящий источник способен опровергнуть
   критериальную новизну A3/A4 и где нынешняя охота не закончена.
Формат JSON по schema. Содержательная точность важнее самопрезентации.

UNTRUSTED SOURCED RESEARCH MATERIAL:
"""

def build_input(packets:Path,native_root:Path,book:Path,reads:Path)->dict[str,Any]:
    native=paper_inputs(packets,native_root,book)
    summary=load(reads/"native_scholarly_read_receipt.json")
    if (summary.get("schema")!="MAI_ARTIKL_NATIVE_SCHOLARLY_READ_BATCH_v1"
            or summary.get("route_id")!="MAI-W12-009"
            or summary.get("source_w12_sha256")!=native[0]["source_W12_sha256"]
            or summary.get("machine_source_grounded_papers_reviewed")!=3
            or summary.get("author_gates_approved")!=0
            or summary.get("world_mutations_applied")!=0
            or summary.get("external_submission_count")!=0
            or summary.get("scientific_novelty_peer_accepted")!=0):
        raise ValueError("unaccepted or missing exact native three-work scientific review")
    items=[]
    for src in native:
        doi=src["doi"]
        proof_file=reads/"papers"/sha(doi.encode("utf-8"))[:20]/"accepted_challenge.json"
        raw=proof_file.read_bytes()
        proof=load(proof_file)
        if (proof.get("schema")!="MAI_ARTIKL_NATIVE_PUBLISHER_SCHOLARLY_CHALLENGE_v1"
                or proof.get("input_key")!=sha(stable(src))
                or proof.get("model_response_sha256")!=sha(stable(proof.get("model_output")))
                or proof.get("scientific_adjudication")!="PROVISIONAL"
                or proof.get("author_decision")!="HOLD"
                or proof.get("external_send_count")!=0
                or proof.get("independent_human_scholarly_peer_review")!="NOT_DONE"):
            raise ValueError("source/model review provenance drift "+doi)
        validated=validate(proof["model_output"],src)
        if validated!=proof.get("verified_review"):
            raise ValueError("native published work quote provenance altered "+doi)
        quotes=[
            {"quote_sha256":q["quote_sha256"],"role":q["role"],
             "exact_quote":q["exact_quote"],"inference_using_quote":q["inference_using_quote"]}
            for q in validated["anchors"]
        ]
        items.append({
            "doi":doi,"publication_title":src["article_title"],
            "article_original_url":src["original_publisher_url"],
            "publisher_main_body_sha256":src["publisher_readable_main_body_sha256"],
            "paper_review_receipt_sha256":sha(raw),
            "position":validated["comparison_label"],
            "paper_thesis":validated["paper_thesis"],
            "mechanism":validated["argument_reconstruction"],
            "strongest_objection_to_MAI":validated["strongest_source_grounded_objection"],
            "limited_residual_MAI_claim":validated["original_MAI_difference_if_any"],
            "next_scientific_question":validated["revised_research_question_candidate"],
            "discriminating_countercase":validated["crucial_discriminating_countercase"],
            "novelty_disclosure":validated["reason_not_to_claim_novelty_yet"],
            "source_anchors":quotes,
        })
    return {
        "schema":"MAI_A3A4_FIELD_REOPEN_MODEL_INPUT_v1",
        "route_id":"MAI-W12-009",
        "source_W12_sha256":native[0]["source_W12_sha256"],
        "owner_original_W12_title_ru":native[0]["source_W12_scientific_claim"]["title_ru"],
        "owner_original_W12_abstract_ru":native[0]["source_W12_scientific_claim"]["abstract_ru"],
        "owner_reconstruction_doc_id":native[0]["author_book"]["source_doc_id"],
        "owner_reconstruction_excerpts":native[0]["author_book"]["source_excerpts"],
        "three_published_native_paper_evidence":items,
        "article_count_not_divisible_into_three_by_default":True,
        "author_source_mutation_authorized":False,
    }

def validate_synthesis(model:Any,data:dict[str,Any])->dict[str,Any]:
    wanted=set(SCHEMA_JSON["required"])
    if not isinstance(model,dict) or set(model)!=wanted:
        raise ValueError("world return synthesis schema not satisfied")
    if model.get("route_id")!=data["route_id"] or model.get("decision_candidate") not in LABELS:
        raise ValueError("world reopen proposal unrelated to real MAI case")
    for field in FIELDS:
        value=model.get(field)
        if not isinstance(value,str) or not 70<=len(value.strip())<=3100:
            raise ValueError("critical philosophical field missing or overlong "+field)
    papers=data["three_published_native_paper_evidence"]
    allowed={r["doi"]:{a["quote_sha256"]:a for a in r["source_anchors"]} for r in papers}
    distinctions=model["three_source_distinctions"]
    if (not isinstance(distinctions,list) or len(distinctions)!=3 or
            {r.get("doi") for r in distinctions}!=set(allowed)):
        raise ValueError("one or more authentic same-journal sources absent")
    for x in distinctions:
        if (set(x)!={"doi","role_against_A3A4","retained_MAI_difference_if_any"}
                or any(not isinstance(x[k],str) or len(x[k])<50
                       for k in ("role_against_A3A4","retained_MAI_difference_if_any"))):
            raise ValueError("fake source difference/diffuse opponent summary")
    refs=model.get("source_anchor_ids")
    if not isinstance(refs,list) or not 3<=len(refs)<=8:
        raise ValueError("source anchor counts invalid")
    linked=[];seen=set()
    for item in refs:
        if (not isinstance(item,dict)
                or set(item)!={"doi","quote_sha256","why_this_proves_the_claim"}
                or item["doi"] not in allowed
                or item["quote_sha256"] not in allowed[item["doi"]]
                or not isinstance(item["why_this_proves_the_claim"],str)
                or len(item["why_this_proves_the_claim"])<50):
            raise ValueError("invented cross-paper citation or inference")
        tup=(item["doi"],item["quote_sha256"])
        if tup in seen:raise ValueError("repeated paper passage trying to inflate science")
        seen.add(tup)
        a=allowed[item["doi"]][item["quote_sha256"]]
        linked.append({
            **item,
            "published_article_original_url":next(p["article_original_url"] for p in papers if p["doi"]==item["doi"]),
            "exact_publisher_quote":a["exact_quote"],
            "quote_source_type":"ACTUAL_SAME_JOURNAL_PUBLISHER_MAIN_BODY",
        })
    if {x["doi"] for x in linked}!=set(allowed):
        raise ValueError("cross-paper argument has no source from one competitor")
    return {
        "schema":SCHEMA,"route_id":data["route_id"],
        "source_W12_sha256":data["source_W12_sha256"],
        "field_reopen_proposal_kind":"FIELD_REOPEN_PROPOSAL",
        "decision_candidate":model["decision_candidate"],
        "literature_covered_original_articles":len(allowed),
        "source_anchor_count":len(linked),
        "source_read_depth":"THREE_PUBLISHER_MAIN_BODIES_MACHINE_READ_SOURCE_QUOTED",
        "model_proposal":{k:v for k,v in model.items() if k!="source_anchor_ids"},
        "source_anchor_ids":linked,
        "source_ontology_object_original_intact":True,
        "author_draft_rewritten":False,
        "author_world_change_approved":False,
        "author_publication_identity_accepted":False,
        "journal_venue_policy_certified":False,
        "external_send_count":0,
        "downstream_gate":"HUMAN_SCHOLARLY_ADJUDICATION_PENDING",
    }

def call_provider(prompt:str,schema_file:Path,output:Path,*,timeout:int=680)->dict[str,Any]:
    cmd=["claude","--print","--output-format","json","--json-schema",
         json.dumps(SCHEMA_JSON,ensure_ascii=False,separators=(",",":")),
         "--model","sonnet","--effort","medium","--no-session-persistence",
         "--max-turns","6","--tools",""]
    result=subprocess.run(cmd,input=prompt,encoding="utf-8",errors="replace",
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          cwd=str(output),timeout=timeout)
    (output/"model_stdout.log").write_text(result.stdout,encoding="utf-8")
    (output/"model_stderr.log").write_text(result.stderr,encoding="utf-8")
    if result.returncode!=0:
        raise RuntimeError("scholarly synthesis model rejected/failed "+str(result.returncode))
    response=json.loads(result.stdout)
    if response.get("is_error") or not isinstance(response.get("structured_output"),dict):
        raise RuntimeError("publisher-source synthesis did not produce a structured review")
    model=response["structured_output"]
    write(output/"model_output.json",model)
    write(output/"model_usage.json",{
        "modelUsage":response.get("modelUsage",{}),"total_cost_usd":response.get("total_cost_usd"),
        "duration_api_ms":response.get("duration_api_ms"),
    })
    return model

def execute(packet_root:Path,native_root:Path,book:Path,read_root:Path,output:Path)->dict[str,Any]:
    input=build_input(packet_root,native_root,book,read_root)
    key=sha(stable(input))
    target=output/"field_reopen_proposal.json"
    if target.is_file():
        saved=load(target)
        if saved.get("source_input_sha256")!=key:
            raise ValueError("unchanged World/source identity required for field reopen replay")
        model=load(output/"model_output.json")
        verified=validate_synthesis(model,input)
        if saved.get("verified_proposal")!=verified:
            raise ValueError("model synthesis cache/actual source discrepancy")
        return {"state":"CACHED","model_calls":0,"source_articles":3,
                "proposal":verified,"receipt":"field_reopen_proposal.json"}
    output.mkdir(parents=True,exist_ok=True)
    write(output/"source_input.json",input)
    write(output/"model_output_schema.json",SCHEMA_JSON)
    prompt=PROMPT+json.dumps(input,ensure_ascii=False,indent=2)
    (output/"prompt.txt").write_text(prompt,encoding="utf-8")
    raw=output/"model_output.json"
    # A CLI delivery timeout must not force an identical source read and
    # another billed provider call merely because the receipt was interrupted.
    existing_model_response=raw.is_file() and (output/"model_stdout.log").is_file()
    if existing_model_response:
        model=load(raw)
    else:
        model=call_provider(prompt,output/"model_output_schema.json",output)
    verified=validate_synthesis(model,input)
    write(target,{
        "schema":"MAI_ARTIKL_A3A4_NATIVE_FIELD_REOPEN_RECEIPT_v1",
        "source_input_sha256":key,
        "original_scholarship_model_output_sha256":sha(stable(model)),
        "verified_proposal":verified,
        "author_decision":"HOLD","world_mutations":0,
        "journal_send_count":0,
        "human_scientific_evaluation":"REQUIRED",
    })
    return {"state":"MODEL_SOURCE_ANCHOR_VERIFIED","model_calls":0 if existing_model_response else 1,
            "source_articles":3,"proposal":verified,"receipt":"field_reopen_proposal.json"}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--native-root",type=Path,required=True)
    p.add_argument("--author-book",type=Path,required=True)
    p.add_argument("--reads",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=execute(a.packets,a.native_root,a.author_book,a.reads,a.output)
    print(json.dumps({k:v for k,v in result.items() if k!="proposal"},ensure_ascii=False,indent=2))
    print("MODEL_DECISION_CANDIDATE",result["proposal"]["decision_candidate"])
    print("DOI_COUNT",result["proposal"]["literature_covered_original_articles"],
          "QUOTE_ANCHORS",result["proposal"]["source_anchor_count"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
