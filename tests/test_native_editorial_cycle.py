"""Editorial decision belongs to Artikl, not WhiteCrow's metadata depth flag."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from kairoskopion.kairon_provider import native_editorial_cycle as e
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked

def payload(choice="REVISION_CANDIDATE"):
    return {"schema":"trimurti-artikl-editorial-decision-v1","agent_id":"artikl",
       "decision":choice,"baseline_sha256":"a"*64,
       "independent_review_sha256":"b"*64,"reason":"substantive",
       "planned_changes":["rewrite methods"],"open_research_questions":["full prior art"],
       "author_gate":"HOLD","send":False,"world_mutation":False,
       "d25_manuscript_go":False}

def test_prompt_grants_unconstrained_working_editorial_choice(tmp_path):
    m={"artikl_source_root":str(tmp_path)}
    f={k:{"path":tmp_path/(k+".md"),"sha256":("a"*64 if k=="baseline" else "b"*64)}
       for k in ("baseline","source","review","science","whitecrow")}
    s=e._decision_prompt(m,f)
    assert "REVISION_CANDIDATE" in s
    assert "MORE_RESEARCH" in s
    assert "PARK" in s
    assert "No external source-depth field authorizes or forbids" in s
    assert "revision_eligible" not in s
    assert "You independently choose" in s

def test_native_gateway_no_invalid_response_promoted():
    good={"status":"ok","result":{"payloads":[{"text":json.dumps(payload())}]}}
    assert e.parse_gateway(json.dumps(good).encode("utf8"))["decision"]=="REVISION_CANDIDATE"
    with pytest.raises(EvidenceBlocked):
        e.parse_gateway(b'{"status":"failed","result":{}}')

def test_reviewer_requires_actual_exact_line():
    review={"schema":"trimurti-independent-C04-rewrite-review-v1",
            "draft_sha256":"","issues":[{"line":2,"literal_quote":"verified","kind":"issue"}],
            "send":False,"author_gate":"HOLD"}
    assert not hasattr(e,"revision_eligible")
    # Private full-length scientific draft normally gets a source-bound review.
    # This local unit test is for quote provenance only, not semantic truth.
    text="# example\nverified passage\n## Section\n"*1100
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as root:
        p=Path(root)/"test.md"
        p.write_text(text,encoding="utf8")
        review["draft_sha256"]=e.sha256(p.read_bytes())
        e._verify_review(review,p)
        review["issues"][0]["literal_quote"]="fabricated"
        with pytest.raises(EvidenceBlocked,match="unverified"):
            e._verify_review(review,p)

def test_end_to_end_decision_never_branches_from_scientific_readiness(tmp_path,monkeypatch):
    m={"schema":e.SCHEMA,"case_id":"T3-TALK-20261019","artikl_source_root":str(tmp_path), "author_gate":"HOLD",
       "send":False,"world_mutation":False}
    for v in ("MORE_RESEARCH","PARK"):
        root=tmp_path/v
        p=tmp_path/("manifest-"+v+".json")
        p.write_text(json.dumps(m),encoding="utf8")
        def fake_preflight(manifest):
            return {k:{"sha256":h*64, "path":tmp_path/(k+".txt")} for k,h in (("source","c"),("baseline","a"),("review","b"),("science","d"),("whitecrow","e"))}
        monkeypatch.setattr(e,"preflight",fake_preflight)
        def fake_native_call(root,stage,prompt,timeout=330):
            (root/"decision.gateway.json").write_text('{"status":"ok"}',encoding="utf8")
            return payload(v)
        monkeypatch.setattr(e,"native_call",fake_native_call)
        result=e.run(p,e.sha256(p.read_bytes()),root)
        assert result["status"]=="EDITORIAL_"+v
        assert result["new_native_hunts"]==0
        assert result["new_w12_routes"]==0
        assert result["send"] is False
        assert e.run(p,e.sha256(p.read_bytes()),root)["replay"]=="IDENTICAL_NO_NEW_MODEL_CALLS"

def test_one_real_file_draft_and_independent_review_captured_from_artikl_choice(tmp_path,monkeypatch):
    m={"schema":e.SCHEMA,"case_id":"T3-TALK-20261019","artikl_source_root":str(tmp_path),
       "scientific_repo":str(tmp_path),"author_gate":"HOLD","send":False,
       "world_mutation":False}
    manifest=tmp_path/"owner_manifest.json"
    manifest.write_text(json.dumps(m),encoding="utf8")
    root=tmp_path/"single_run"
    seen=[]
    def faked_preflight(m):
        return {k:{"sha256":(x*64),"path":tmp_path/(k+".txt"),"content":b"test"}
          for k,x in (("source","c"),("baseline","a"),("review","b"),
                      ("science","d"),("whitecrow","e"))}
    monkeypatch.setattr(e,"preflight",faked_preflight)
    def mocked_native(root,stage,prompt,timeout=330):
        seen.append(stage)
        (root/(stage+".gateway.json")).write_text('{"status":"ok"}',encoding="utf8")
        if stage=="decision":return payload("REVISION_CANDIDATE")
        assert stage=="writer"
        assert "full" in prompt.lower()
        draft=root/"draft_v0_6.md"
        draft.write_text("# Новый содержательный вариант\n"+
            "".join("## Раздел {}\n{}\n".format(i,"Содержательная аргументация и исследовательская постановка. "*190)
                     for i in range(1,9)),encoding="utf8")
        return {"sha256":e.sha256(draft.read_bytes()),"author_gate":"HOLD"}
    monkeypatch.setattr(e,"native_call",mocked_native)
    def fake_ingest(*,manifest_path,input_root,output_root,
                    trusted_source_sha256,trusted_science_sha256):
        output_root.mkdir(exist_ok=True)
        (output_root/"draft-intake-receipt.json").write_text(
            '{"status":"DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED"}',encoding="utf8")
        return {"status":"DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED"}
    monkeypatch.setattr(e,"ingest",fake_ingest)
    def fake_review(root,manifest,f,draft):
        j={"schema":"trimurti-independent-C04-rewrite-review-v1",
           "draft_sha256":e.sha256(draft.read_bytes()),
           "verdict":"REVISION_REQUIRED",
           "issues":[{"line":1,"literal_quote":"# Новый содержательный вариант","kind":"note"}],
           "author_gate":"HOLD","send":False}
        (root/"review.json").write_text(json.dumps(j,ensure_ascii=False),encoding="utf8")
        return j
    monkeypatch.setattr(e,"_independent_review",fake_review)
    result=e.run(manifest,e.sha256(manifest.read_bytes()),root)
    assert seen==["decision","writer"]
    assert result["status"]=="FULL_DRAFT_AND_INDEPENDENT_REVIEW_CAPTURED_AUTHOR_HOLD"
    assert result["draft_words"]>=3100
    assert result["candidate_sha256"]==e.sha256((root/"draft_v0_6.md").read_bytes())
    assert result["independent_review_verdict"]=="REVISION_REQUIRED"
    assert result["new_w12_routes"]==0 and result["new_indago_hunts"]==0
    assert result["send"] is False
    assert e.run(manifest,e.sha256(manifest.read_bytes()),root)["replay"]=="IDENTICAL_NO_NEW_MODEL_CALLS"
    assert seen==["decision","writer"]
