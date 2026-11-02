"""Real-worker bounded cycle tests; fake tests cannot certify scientific quality."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pytest
from kairoskopion.kairon_provider.manuscript_cycle_runner import (
    WORKER, run_cycle,
)
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fixture(tmp_path):
    inp=tmp_path/"input"
    inp.mkdir()
    repo=tmp_path/"repo"
    repo.mkdir()
    baseline=("# Baseline\n\n## Core\n"+"Important author's thesis " * 35).encode()
    source=("Actual source text: capacity, obligation and guarantee. "*25).encode()
    science=json.dumps({"author_gate":"HOLD","external_send":False,
                        "W12_added":0,"original_research":["Costa"]}).encode()+b" "*650
    prior=json.dumps({"editorial_gate":"REVISION_REQUIRED",
                      "candidate_sha256":sha(baseline),"findings":["methods"]}).encode()+b" "*150
    tasks=json.dumps({"native_indago_execution":"NOT_INVOKED_IN_THIS_PASS",
                      "trigger":{"draft_sha256":sha(baseline)}}).encode()
    files={"source":source,"science":science,"baseline":baseline,"review":prior,"research_tasks":tasks}
    artifacts={}
    for name, content in files.items():
        (inp/(name+".txt" if name != "baseline" else "baseline.md")).write_bytes(content)
        path = name+".txt" if name!="baseline" else "baseline.md"
        artifacts[name]={"path":path,"sha256":sha(content)}
    manifest={"schema":"trimurti-manuscript-cycle-v1","case_id":"T3-TALK",
              "claim_id":"C04-GUARMEAS","route_id":"C-GUARMEAS",
              "worker":WORKER,"evidence_mode":"REAL","author_gate":"HOLD",
              "article_seed_accepted":False,"submit":False,
              "max_writer_calls":1,"max_review_calls":1,"artifacts":artifacts}
    p=inp/"cycle.json"
    p.write_text(json.dumps(manifest),encoding="utf-8")
    kw={"manifest_path":p,"input_root":inp,"output_root":tmp_path/"output",
        "scientific_repo":repo,"trusted_source_sha":sha(source),
        "trusted_science_sha":sha(science),"trusted_baseline_sha":sha(baseline),
        "trusted_review_sha":sha(prior)}
    return kw


def fake_worker(seen):
    def f(stage,prompt,output,cwd,timeout_seconds):
        seen.append(stage)
        if stage=="scholar":
            result={"schema":"T3_M105_SOURCE_CRITICAL_SCOUT_V1",
                    "source_sha256":seen.expected_source,
                    "science_sha256":seen.expected_science,
                    "status":"SCOPED_RESEARCH_NOT_FULL_ACCEPTANCE",
                    "evaluations":[{"task_id":x,"read_depth":"ABSTRACT_ONLY"}
                      for x in ("M105-CONSTRUCT-VALIDITY","M105-CONTRACT-GUARANTEE-PRIOR",
                                "M105-SELECTIVE-LABELS")],
                    "novelty_accepted":False,"author_gate":"HOLD","send":False}
            output.write_text(json.dumps(result),encoding="utf-8")
        elif stage=="writer":
            output.write_text("# New manuscript\n\n## Theory\n"+("Original scholarly text " * 1500)
                              +"\n## Method\n"+"Method detail " * 1000+
                              "\n## Critique\n## Discussion\n## Findings\n## Conclusions\n## References",
                              encoding="utf-8")
        else:
            result={"schema":"T3_MANUSCRIPT_REAL_WORKER_REVIEW_V1",
                    "candidate_sha256":sha((output.parent/"writer.txt").read_bytes()),
                    "gate":"REVISION_REQUIRED","substantive_findings":[{"why":"missing field work"}],
                    "novelty_accepted":False,"author_approved":False,"send":False}
            output.write_text(json.dumps(result),encoding="utf-8")
        return {"model_cli":"mock_test_only","exit_code":0}
    return f


class Steps(list):
    expected_source: str
    expected_science: str


def setup(tmp_path):
    kw=fixture(tmp_path)
    seen=Steps()
    seen.expected_source=kw["trusted_source_sha"]
    seen.expected_science=kw["trusted_science_sha"]
    return kw,seen,fake_worker(seen)


def test_real_stage_seams_one_command_replay_zero_provider_calls(tmp_path):
    kw,seen,worker=setup(tmp_path)
    first=run_cycle(**kw,worker=worker)
    second=run_cycle(**kw,worker=worker)
    assert seen==["scholar","writer","reviewer"]
    assert first==second
    assert first["status"]=="RESEARCH_EVIDENCE_REENTRY"
    assert first["send"] is False and first["new_w12_routes"]==0
    assert (kw["output_root"]/first["cycle_id"]/"intake"/"draft-intake-receipt.json").exists()


def test_original_sha_external_mismatch_rejects_before_providers(tmp_path):
    kw,seen,worker=setup(tmp_path)
    kw["trusted_source_sha"]="0"*64
    with pytest.raises(EvidenceBlocked,match="trusted_source"):
        run_cycle(**kw,worker=worker)
    assert not seen


def test_manifest_self_cert_source_forgery_is_rejected(tmp_path):
    kw,seen,worker=setup(tmp_path)
    m=json.loads(kw["manifest_path"].read_text(encoding="utf-8"))
    fake=b"Attacker changes author's data and self-certified hashes "*40
    p=kw["input_root"]/"source.txt"
    p.write_bytes(fake)
    m["artifacts"]["source"]["sha256"]=sha(fake)
    kw["manifest_path"].write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="trusted_source_sha256_mismatch"):
        run_cycle(**kw,worker=worker)
    assert not seen


def test_replayed_worker_output_tamper_detected(tmp_path):
    kw,seen,worker=setup(tmp_path)
    first=run_cycle(**kw,worker=worker)
    p=kw["output_root"]/first["cycle_id"]/"writer.txt"
    p.write_text(p.read_text()+"malicious",encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="previous_worker_output_tampered_writer"):
        run_cycle(**kw,worker=worker)
    assert seen==["scholar","writer","reviewer"]


def test_crash_after_scholar_has_idempotent_resume(tmp_path):
    kw,seen,good_worker=setup(tmp_path)
    def crash(stage,prompt,output,cwd,timeout_seconds):
        if stage=="writer":
            raise EvidenceBlocked("test_worker_failure")
        return good_worker(stage,prompt,output,cwd,timeout_seconds)
    with pytest.raises(EvidenceBlocked,match="test_worker_failure"):
        run_cycle(**kw,worker=crash)
    final=run_cycle(**kw,worker=good_worker)
    assert final["status"]=="RESEARCH_EVIDENCE_REENTRY"
    assert seen==["scholar","writer","reviewer"]


def test_agent_fake_owner_approval_rejected(tmp_path):
    kw,seen,good=setup(tmp_path)
    def forged(stage,prompt,output,cwd,timeout_seconds):
        meta=good(stage,prompt,output,cwd,timeout_seconds)
        if stage=="reviewer":
            j=json.loads(output.read_text())
            j["author_approved"]=True
            output.write_text(json.dumps(j))
        return meta
    with pytest.raises(EvidenceBlocked,match="agent_claims_owner_approval"):
        run_cycle(**kw,worker=forged)


def test_untracked_orphan_is_not_silently_accepted(tmp_path):
    kw,seen,good=setup(tmp_path)
    def orphan(stage,prompt,output,cwd,timeout_seconds):
        if stage=="scholar":
            output.write_text("orphan on crash")
            raise EvidenceBlocked("killed_after_file_before_receipt")
        return good(stage,prompt,output,cwd,timeout_seconds)
    with pytest.raises(EvidenceBlocked,match="killed_after_file"):
        run_cycle(**kw,worker=orphan)
    with pytest.raises(EvidenceBlocked,match="orphan_unverified_worker_output_scholar"):
        run_cycle(**kw,worker=good)

def test_parallel_or_stale_worker_lock_fails_closed(tmp_path):
    kw,seen,worker=setup(tmp_path)
    kw["output_root"].mkdir(parents=True)
    lock=kw["output_root"]/".trimurti_cycle_worker.lock"
    lock.write_text("other run")
    with pytest.raises(EvidenceBlocked,match="concurrent_or_stale_cycle_lock"):
        run_cycle(**kw,worker=worker)
    assert lock.exists() and not seen
