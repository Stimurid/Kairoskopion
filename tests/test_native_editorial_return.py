"""F4: actual Artikl independent review-return is not a D15 permission request."""
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider import native_editorial_return as r
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked


def inputs(tmp_path):
    mf = tmp_path/"manifest.json"
    m = {"schema": r.SCHEMA, "case_id": "T3-TALK-20261019",
         "artikl_source_root": str(tmp_path), "scientific_repo": str(tmp_path),
         "author_gate": "HOLD", "send": False, "world_mutation": False}
    mf.write_text(json.dumps(m), encoding="utf-8")
    f = {name: {"sha256": chr(97 + idx)*64,
                "path": tmp_path/(name+".txt"), "bytes": b"fixture"}
         for idx,name in enumerate(("source", "baseline", "review", "science", "whitecrow", "m117_provenance"))}
    return mf, m, f


def decision(f, choice):
    return {
      "schema": "trimurti-artikl-review-return-decision-v1",
      "agent_id": "artikl", "current_release": "ARTIKL 1.0.0-rc9",
      "baseline_sha256": f["baseline"]["sha256"],
      "independent_review_sha256": f["review"]["sha256"],
      "decision": choice,
      "reason": "Scientific reason with separate source, author and review distinctions",
      "planned_changes": ["revise conceptual exposition"],
      "research_needs": ["check prior work"],
      "review_findings_used": ["NEAREST_COMPETITOR_FULLTEXT_GAP"],
      "author_gate": "HOLD", "send": False, "world_mutation": False,
      "d25_manuscript_go": False,
    }


def test_decision_prompt_preserves_artikl_authority_no_external_veto(tmp_path):
    _, m, f = inputs(tmp_path)
    prompt = r._decision_prompt(m, f)
    assert "Freely choose" in prompt
    assert "REVISION_CANDIDATE" in prompt and "MORE_RESEARCH" in prompt
    assert "KEEP_WORKING_DRAFT" in prompt and "PARK" in prompt
    assert "NOT as permission" in prompt
    assert "Do not fabricate empirical validation" in prompt
    assert "D27 is only a candidate" in prompt
    assert "NO TOOL CALLS" in prompt
    assert "=== BEGIN COMPLETE BASELINE MANUSCRIPT" in prompt
    assert "=== END M117 REVIEW; BEGIN PREVIOUS SCIENCE PACKET ===" in prompt


@pytest.mark.parametrize("choice",["MORE_RESEARCH", "KEEP_WORKING_DRAFT", "PARK"])
def test_native_decision_only_exits_with_proper_durable_hold(tmp_path, monkeypatch, choice):
    mf,m,f=inputs(tmp_path)
    monkeypatch.setattr(r,"preflight",lambda _m:f)
    stages=[]
    def call(root,stage,prompt,timeout=330):
        stages.append(stage)
        (root/(stage+".gateway.json")).write_text('{"status":"ok"}')
        return decision(f,choice)
    monkeypatch.setattr(r,"native_call",call)
    root=tmp_path/"run"
    sha=r.sha256(mf.read_bytes())
    result=r.run(mf,sha,root)
    assert result["status"]=="REVIEW_RETURN_"+choice+"_AUTHOR_HOLD"
    assert result["new_manuscripts"]==0
    assert result["send"] is False and result["new_indago_hunts"]==0
    assert result["new_w12_routes"]==0 and stages==["return_decision"]
    assert r.run(mf,sha,root)["replay"]=="IDENTICAL_NO_NEW_MODEL_CALLS"
    assert stages==["return_decision"]


def test_real_draft_and_separate_review_follow_only_actual_artikl_revision(tmp_path, monkeypatch):
    mf,m,f=inputs(tmp_path)
    monkeypatch.setattr(r,"preflight",lambda _m:f)
    stages=[]
    root=tmp_path/"run"
    def call(root,stage,prompt,timeout=330):
        stages.append(stage)
        (root/(stage+".gateway.json")).write_text('{"status":"ok"}')
        if stage=="return_decision":
            return decision(f,"REVISION_CANDIDATE")
        assert stage=="return_writer"
        lines=["# C04 original proposed new working argument"]
        for j in range(8):
            lines.append("## Section "+str(j))
            lines += ["A substantial argument about production capability and the temporary organ, without invented data. "*65]
        path=root/"draft_v0_7.md"
        path.write_text("\n".join(lines)+"\n",encoding="utf-8")
        return {"sha256":r.sha256(path.read_bytes()),"author_gate":"HOLD","send":False}
    monkeypatch.setattr(r,"native_call",call)
    monkeypatch.setattr(r,"_intake",lambda root,f,target:"4"*64)
    def review(root,m,f,target):
        body={"schema":"trimurti-independent-C04-rewrite-review-v1",
              "draft_sha256":r.sha256(target.read_bytes()),
              "reviewer":"CODEX_DISTINCT_PROCESS","verdict":"REVISION_REQUIRED",
              "author_gate":"HOLD","send":False,
              "issues":[{"kind":"issue","line":1,
                         "literal_quote":"C04 original proposed",
                         "explanation":"Specific scientific criticism","action":"Clarify"}]}
        (root/"review.json").write_text(json.dumps(body),encoding="utf-8")
        return body
    monkeypatch.setattr(r,"_independent_next_review",review)
    sha=r.sha256(mf.read_bytes())
    result=r.run(mf,sha,root)
    assert stages==["return_decision","return_writer"]
    assert result["status"]=="REVIEW_RETURN_FULL_REVISION_AND_REVIEW_AUTHOR_HOLD"
    assert result["candidate_words"]>=3100
    assert result["independent_review_verdict"]=="REVISION_REQUIRED"
    assert result["new_manuscripts"]==1 and result["independent_reviews"]==1
    assert result["author_gate"]=="HOLD" and result["send"] is False
    assert r.run(mf,sha,root)["replay"]=="IDENTICAL_NO_NEW_MODEL_CALLS"
    assert stages==["return_decision","return_writer"]
    with (root/"draft_v0_7.md").open("a",encoding="utf8") as fp:
        fp.write("\ntampered")
    with pytest.raises(EvidenceBlocked,match="draft_changed"):
        r.run(mf,sha,root)


def test_invalid_artikl_decision_is_not_promoted(tmp_path,monkeypatch):
    mf,m,f=inputs(tmp_path)
    monkeypatch.setattr(r,"preflight",lambda _m:f)
    def call(root,stage,prompt,timeout=330):
        (root/(stage+".gateway.json")).write_text('{"status":"ok"}')
        value=decision(f,"REVISION_CANDIDATE")
        value["author_gate"]="ACCEPTED"
        return value
    monkeypatch.setattr(r,"native_call",call)
    with pytest.raises(EvidenceBlocked,match="choice_invalid"):
        r.run(mf,r.sha256(mf.read_bytes()),tmp_path/"run")
    assert not (tmp_path/"run"/"review_return_receipt.json").exists()


def test_native_timeout_cannot_reuse_foreign_or_unverified_written_file(tmp_path):
    root=tmp_path
    (root/"return_writer.started").write_text("NATIVE_ARTIKL_CALL sid-1\n",encoding="ascii")
    file=root/"draft_v0_7.md"
    file.write_text("# Working draft\n"+"\n".join(
       "## Part "+str(i)+"\n"+("Meaningful discussion of production organs. "*200)
       for i in range(8)),encoding="utf8")
    outer={"status":"timeout","timeoutPhase":"provider","providerStarted":True,
           "runId":"run-1","result":{"meta":{"agentMeta":{
              "sessionId":"other-session",
              "terminalReceipt":{"runId":"run-1","sessionId":"other-session",
                                 "successfulToolNames":["read","write"]}}}}}
    (root/"return_writer.gateway.json").write_text(json.dumps(outer),encoding="utf8")
    with pytest.raises(EvidenceBlocked,match="not_attested"):
        r._writer_file_after_gateway_timeout(root,file)


def test_handoff_requires_a_real_completed_native_more_research_decision(tmp_path,monkeypatch):
    mf,m,f=inputs(tmp_path)
    monkeypatch.setattr(r,"preflight",lambda _m:f)
    with pytest.raises(EvidenceBlocked,match="no_completed_native_review_return_decision"):
        r.prepare_more_research_handoff(
            manifest=mf,expected_manifest_sha=r.sha256(mf.read_bytes()),
            root=tmp_path/"run",whitecrow_root=tmp_path,
            trusted_whitecrow_commit="a"*40,
            trusted_whitecrow_module_sha="b"*64)


def test_handoff_cannot_redirect_a_native_park_to_indago(tmp_path,monkeypatch):
    mf,m,f=inputs(tmp_path)
    monkeypatch.setattr(r,"preflight",lambda _m:f)
    root=tmp_path/"run"
    root.mkdir()
    choice=decision(f,"PARK")
    (root/"decision.json").write_text(json.dumps(choice),encoding="utf-8")
    state={
        "status":"REVIEW_RETURN_PARK_AUTHOR_HOLD",
        "decision":"PARK",
        "decision_sha256":r.sha256((root/"decision.json").read_bytes()),
        "manifest_sha256":r.sha256(mf.read_bytes()),
        "M117_review_sha256":f["review"]["sha256"],
        "baseline_sha256":f["baseline"]["sha256"],
        "author_gate":"HOLD",
    }
    (root/"review_return_receipt.json").write_text(json.dumps(state),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="native_artikl_research_choice_not_authorized"):
        r.prepare_more_research_handoff(
            manifest=mf,expected_manifest_sha=r.sha256(mf.read_bytes()),
            root=root,whitecrow_root=tmp_path,
            trusted_whitecrow_commit="a"*40,
            trusted_whitecrow_module_sha="b"*64)
