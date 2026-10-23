"""Source-linked A3/A4 scholarly reading is not self-authorized by a model."""
from __future__ import annotations

from pathlib import Path
import json
import pytest

from kairoskopion.kairon_provider.w12_packets import native_scholarly_model_read_for_route,sha

def stable(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

P1="The authority to revise the evaluation rubric is not inferred from a perfect machine score."
P2="Responsibility for the failure of automatic detection remains a publicly contestable institutional question."
P3="A counterexample should distinguish performance from the legitimacy of normative rule revision."

def evidence(tmp:Path):
    native=tmp/"published"
    scientific=tmp/"science"
    route={
        "route_id":"MAI-W12-009","family":"A","variant":"A-EDUCATION",
        "journal":"Studies in Philosophy and Education",
        "title_ru":"Нормативные полномочия","abstract_ru":"A3 сохраняет норму, A4 меняет право изменить её.",
    }
    w12_sha="f"*64
    entries=[]
    for i in range(3):
        doi=f"10.1007/example-2026-article-{i}"
        url="https://link.springer.com/article/"+doi
        article=("The complete article body follows. "+P1+" "+P2+" "+P3+" ")*100
        assert len(article)>6500
        original=article.encode("utf-8")
        prefix=native/"url_capture_cache"/sha(url.encode())[:24]
        prefix.mkdir(parents=True)
        (prefix/"source.bin").write_bytes(original)
        (prefix/"visible_text.txt").write_text(article+"\n",encoding="utf-8")
        source={
            "route_id":"MAI-W12-009","doi":doi,
            "source_W12_sha256":w12_sha,
            "source_W12_scientific_claim":{"title_ru":route["title_ru"],
                                          "abstract_ru":route["abstract_ru"]},
            "original_publisher_url":url,
            "original_publisher_html_sha256":sha(original),
            "original_visible_text_sha256":sha(article.encode()),
            "publisher_readable_article_main_body":article,
            "publisher_readable_main_body_sha256":sha(article.encode()),
        }
        model_anchors=[
            {"role":"PAPER_CLAIM","exact_quote":P1,
             "inference_using_quote":"The exact publisher quotation gives an argument.",
             "quote_sha256":sha(P1.encode()),
             "publisher_main_body_offset":article.index(P1),
             "publisher_original_visible_text_sha256":sha(article.encode())},
            {"role":"PAPER_ARGUMENT","exact_quote":P2,
             "inference_using_quote":"The quote identifies the responsibility problem.",
             "quote_sha256":sha(P2.encode()),
             "publisher_main_body_offset":article.index(P2),
             "publisher_original_visible_text_sha256":sha(article.encode())},
            {"role":"BOUNDARY_OR_CONCLUSION","exact_quote":P3,
             "inference_using_quote":"The citation demands a discriminating countercase.",
             "quote_sha256":sha(P3.encode()),
             "publisher_main_body_offset":article.index(P3),
             "publisher_original_visible_text_sha256":sha(article.encode())},
        ]
        original_review={"route_id":"MAI-W12-009","doi":doi,
                         "anchors":[{k:a[k] for k in ("role","exact_quote","inference_using_quote")} for a in model_anchors]}
        verified={
            **original_review,"anchors":model_anchors,
            "source_read_depth":"PUBLISHER_HTML_MAIN_BODY_MODEL_READ",
            "science_novelty_author_accepted":False,
            "research_novelty_author_accepted":False,
            "journal_send_count":0,"author_gate":"HOLD",
            "scientific_stage":"NATIVE_SAME_JOURNAL_ARGUMENT_CRITIQUE_PROVISIONAL",
            "original_pub_html_sha256":sha(original),
            "article_body_source_sha256":sha(article.encode()),
            "strongest_source_grounded_objection":"The normative delegation is ungrounded.",
        }
        doc=scientific/"papers"/sha(doi.encode())[:20]
        doc.mkdir(parents=True)
        (doc/"source_input.json").write_bytes(stable(source))
        receipt={
            "schema":"MAI_ARTIKL_NATIVE_PUBLISHER_SCHOLARLY_CHALLENGE_v1",
            "input_key":sha(stable(source)),
            "model_response_sha256":sha(stable(original_review)),
            "scientific_adjudication":"PROVISIONAL",
            "independent_human_scholarly_peer_review":"NOT_DONE",
            "author_decision":"HOLD","external_send_count":0,
            "verified_review":verified,"model_output":original_review,
        }
        (doc/"accepted_challenge.json").write_bytes(stable(receipt))
        entries.append({"doi":doi,"title":"Scholarly original "+str(i),
                        "status":"MODEL_QUOTE_VERIFIED",
                        "source_anchor_count":3})
    summary={
        "schema":"MAI_ARTIKL_NATIVE_SCHOLARLY_READ_BATCH_v1",
        "route_id":route["route_id"],"source_w12_sha256":w12_sha,
        "author_gates_approved":0,"world_mutations_applied":0,
        "external_submission_count":0,"scientific_novelty_peer_accepted":0,
        "papers":entries,
    }
    (scientific/"native_scholarly_read_receipt.json").write_bytes(stable(summary))
    return route,w12_sha,native,scientific

def test_native_scholarly_reads_require_exact_source_sha_and_model_hold(tmp_path):
    r,s,native,model=evidence(tmp_path)
    out=tmp_path/"board"
    count=native_scholarly_model_read_for_route(r,out,s,native,model)
    assert count["status"]=="QUOTE_ATTESTED_ARTIKL_NATIVE_MACHINE_READING"
    assert count["count"]==3 and count["anchors"]==9
    assert count["independent_review_certified"]==0
    assert count["scholarly_authority"]=="HOLD"
    assert (out/count["detail"]).is_file()

def test_tampered_quote_halts_all_native_science_import(tmp_path):
    r,s,native,model=evidence(tmp_path)
    proof=next((model/"papers").glob("*/accepted_challenge.json"))
    x=json.loads(proof.read_text(encoding="utf-8"))
    x["verified_review"]["anchors"][0]["exact_quote"]="Invented text not present in full original publisher body"
    proof.write_bytes(stable(x))
    with pytest.raises(ValueError,match="false scientific publisher quote"):
        native_scholarly_model_read_for_route(r,tmp_path/"board",s,native,model)

def test_changed_html_source_halts_model_import(tmp_path):
    r,s,native,model=evidence(tmp_path)
    src=next((native/"url_capture_cache").glob("*/source.bin"))
    src.write_bytes(b"replaced source")
    with pytest.raises(ValueError,match="published article body changed"):
        native_scholarly_model_read_for_route(r,tmp_path/"board",s,native,model)

def test_author_approval_in_model_is_rejected(tmp_path):
    r,s,native,model=evidence(tmp_path)
    proof=next((model/"papers").glob("*/accepted_challenge.json"))
    x=json.loads(proof.read_text(encoding="utf-8"))
    x["verified_review"]["research_novelty_author_accepted"]=True
    proof.write_bytes(stable(x))
    with pytest.raises(ValueError,match="unsupported authority"):
        native_scholarly_model_read_for_route(r,tmp_path/"board",s,native,model)
