"""ARTIKL scientific publisher reading proves citations and never self-certifies originality."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_mai_native_scholarly_read as stage
from tests.test_mai_w12_indago_bind import prepare

EXCERPT="The decision to delegate education's normative power does not follow from predictive performance. "
P1="The role of a teacher as a norm-sensitive agent involves a responsibility for public reasons and contestable judgments."
P2="There are conditions in which an AI tutor can optimize learning scores but cannot establish who is entitled to contest criteria."
P3="A philosophy of education must distinguish reliable computation from the institutional warrant to alter the meaning of correctness."

def fixture(tmp:Path):
    packets,_,_=prepare(tmp)
    root=tmp/"native"
    original=stage.load(packets/"routes"/"MAI-W12-001.json")
    route=original["route"]
    route["route_id"]="MAI-W12-009"
    route["journal"]="Studies in Philosophy and Education"
    route["variant"]="A-EDUCATION"
    route["family"]="A"
    route["title_ru"]="Нормативная компетентность и изменение правила"
    route["abstract_ru"]="A3 согласует правила внутри полномочий. A4 распределяет права на их пересмотр."
    original["route"]=route
    stage.write(packets/"routes"/"MAI-W12-009.json",original)
    book=tmp/"owner_book.json"
    stage.write(book,{
        "schema":"MAI_W12_ARTIKL_AUTHOR_BOOK_DRIVE_EXCERPTS_V1",
        "source_file_id":"1epciMw-Vs0imoekL5fmmqLinPAWBzfsk",
        "source_name":"Original MAI author research reconstruction",
        "source_is_W0_W69_RECONSTRUCTION_NOT_NATIVE_A3_A4_FULL_TRANSCRIPT":True,
        "source_author_approval":False,
        "excerpts":[{"label":str(i),"begin_char_offset":i,"text":"A3 and A4: "+EXCERPT}
                    for i in range(4)],
    })
    schema=stage.load(packets/"manifest.json")
    works=[
       "10.1007/s11217-026-10051-w",
       "10.1007/s11217-026-10100-4",
       "10.1007/s11217-026-10097-w",
    ]
    for doi in works:
        url="https://link.springer.com/article/"+doi
        text=("Publisher page. Abstract. "+P1+" Main body: "+
              (EXCERPT*300)+" "+P2+" "+EXCERPT*300+" "+P3+
              " References Bibliography tail")
        raw=("<html>"+text+"</html>").encode("utf-8")
        text_home=root/"url_capture_cache"/stage.sha(url.encode())[:24]
        text_home.mkdir(parents=True)
        (text_home/"source.bin").write_bytes(raw)
        (text_home/"visible_text.txt").write_text(text+"\n",encoding="utf-8")
        stage.write(text_home/"capture.json",{"status":"FETCHED_TEXT"})
        stage.write(root/"routes"/"MAI-W12-009"/(stage.sha(doi.encode())[:16]+".json"),{
            "route_id":"MAI-W12-009",
            "DOI":doi,"original_publisher_url":url,
            "source_W12_sha256":schema["source_jsonl_sha256"],
            "crossref_DOI_identity_match":True,
            "is_native_in_target_journal_by_Crossref":True,
            "publisher_host_observed_same":True,
            "genre_peer_research_verified":False,
            "artikl_author_decision":"HOLD",
            "journal_submission_actions":0,
            "read_depth":"PUBLISHER_VISIBLE_HTML_TEXT_CAPTURED_NOT_SCHOLARLY_FULL_READ",
            "publisher_html_raw_sha256":stage.sha(raw),
            "publisher_html_visible_text_sha256":stage.sha(text.encode("utf-8")),
            "title":"Publisher same-journal original research",
        })
    return packets,root,book

def review(src):
    return {
        "route_id":src["route_id"],"doi":src["doi"],
        "comparison_label":"ADVERSARIAL_PRESSURE",
        **{key:"A3 retains the institution that warrants revising a norm whereas A4 reallocates it; "
                 "this published argument changes the philosophical burden of proof."
           for key in stage.FIELDS},
        "anchors":[
            {"role":"PAPER_CLAIM","exact_quote":P1,
             "inference_using_quote":"The author develops the claim about warrants and publicly contestable judgments."},
            {"role":"PAPER_ARGUMENT","exact_quote":P2,
             "inference_using_quote":"The case separates the tool's achieved score from normative entitlement."},
            {"role":"BOUNDARY_OR_CONCLUSION","exact_quote":P3,
             "inference_using_quote":"The conclusion sets conditions under which revising criteria is defensible."},
        ],
    }

def test_readable_originals_differ_from_abstract_only_and_cache_is_real(tmp_path,monkeypatch):
    packets,root,book=fixture(tmp_path)
    sources=stage.paper_inputs(packets,root,book)
    assert len(sources)==3
    assert all(s["main_body_chars"]>6500 for s in sources)
    assert all("source_excerpts" in s["author_book"] for s in sources)
    called=[]
    def provide(prompt,schema_file,out,**kwargs):
        text=prompt.split("UNTRUSTED SCHOLARLY MATERIAL:",1)[1].strip()
        x=json.loads(text)
        called.append(x["doi"])
        return review(x),"claude CLI"
    monkeypatch.setattr(stage,"request",provide)
    output=tmp_path/"review"
    first=stage.run(packets,root,book,output,limit=3)
    assert first["machine_source_grounded_papers_reviewed"]==3
    assert first["quoted_argument_anchors"]==9
    assert first["new_model_calls"]==3
    assert first["author_gates_approved"]==0
    assert first["world_mutations_applied"]==0
    assert first["external_submission_count"]==0
    marker=[(p,p.read_bytes()) for p in (output/"papers").glob("*/accepted_challenge.json")]
    second=stage.run(packets,root,book,output,limit=3)
    assert second["new_model_calls"]==0
    assert second["machine_source_grounded_papers_reviewed"]==3
    assert len(called)==3
    assert all(p.read_bytes()==old for p,old in marker)

def test_forged_original_quote_refused(tmp_path):
    packets,root,book=fixture(tmp_path)
    src=stage.paper_inputs(packets,root,book)[0]
    fake=review(src)
    fake["anchors"][0]["exact_quote"]="An invented publisher passage pretending article says all automated judgments are always authorized"
    with pytest.raises(ValueError,match="fabricated"):
        stage.validate(fake,src)

def test_perturbed_original_publisher_html_refused(tmp_path):
    packets,root,book=fixture(tmp_path)
    src=stage.paper_inputs(packets,root,book)[0]
    path=root/"url_capture_cache"/stage.sha(src["original_publisher_url"].encode())[:24]/"source.bin"
    path.write_text("FORGED HTML",encoding="utf-8")
    with pytest.raises(ValueError,match="publisher DOI, original HTML"):
        stage.paper_inputs(packets,root,book)

def test_source_book_cannot_claim_native_exercise_approval(tmp_path):
    packets,root,book=fixture(tmp_path)
    data=stage.load(book)
    data["source_author_approval"]=True
    stage.write(book,data)
    with pytest.raises(ValueError,match="author book context"):
        stage.paper_inputs(packets,root,book)
