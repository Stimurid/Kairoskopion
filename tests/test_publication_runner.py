"""Synthetic evidence only. P06/P07 labels exercise reuse, never live acceptance."""
from copy import deepcopy
import io
import json
from pathlib import Path
import zipfile

import pytest

from kairoskopion.kairon_provider.publication_runner import (
    atomic_write, main, run_import, save_json, sha256,
)
from kairoskopion.kairon_provider.submission_package_factory import (
    ARTIFACT_KINDS, DEFAULT_QA, SubmissionPackageFactoryStore, _digest,
)
from kairoskopion.kairon_provider.submission_gate import assess_submission_package
from kairoskopion.kairon_provider.target_world_catalog import TargetWorldCatalog


def write_file(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": name, "sha256": sha256(data)}


def fixture_docx(label):
    """A real ZIP/XML container holding explicitly synthetic manuscript text."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as doc:
        doc.writestr("[Content_Types].xml", '<?xml version="1.0"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '</Types>')
        doc.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                     '</Relationships>')
        doc.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                     '<w:body><w:p><w:r><w:t>FIXTURE ONLY ' + label + '</w:t></w:r></w:p></w:body></w:document>')
    return stream.getvalue()


def setup_case(tmp_path, article="P06"):
    root = tmp_path / article
    root.mkdir(parents=True)
    catalog = TargetWorldCatalog(root / "catalog")
    entry = catalog.ingest({"snapshot_id": "fixture:tw", "target_id": "fixture:venue"},
                           origin="FIXTURE_ONLY", status="PROD_ACCEPTED")
    target = catalog.get_package(entry["package_id"])
    target["catalog_status"] = entry["status"]
    source = write_file(root, "sibling.txt", b"FIXTURE ONLY immutable sibling")
    sibling = {"ref": "fixture:sibling:" + article, "revision": "r1", "sha256": source["sha256"]}
    spec = {"article_id": article, "venue_id": "fixture:venue",
            "authoritative_sibling": sibling, "target_world_package": target,
            "submission_pack": {"submission_pack_id": "fixture:pack:" + article,
                                "status": "ready_skeleton", "ready_status": "ready_for_manual_submission"},
            "policy_snapshot_refs": ["fixture:policy:r1"], "route_status": "LIVE",
            "author_fields_status": "CONFIRMED"}
    manifest = {"schema_version": "publication-import-v1", "evidence_mode": "FIXTURE",
                "spec": spec, "sibling_file": source, "artifacts": {}}
    for kind in sorted(ARTIFACT_KINDS):
        file = write_file(root, kind + ".docx", fixture_docx(article + " " + kind))
        version = {"ref": "fixture:artifact:" + article + ":" + kind,
                   "revision": "export-1", "sha256": file["sha256"]}
        row = {"file": file, "version": version, "source_sibling": sibling, "qa": {}}
        for qtype in DEFAULT_QA:
            evidence = write_file(root, kind + "-" + qtype + ".txt", b"FIXTURE ONLY QA evidence, not real QA")
            receipt = {"article_id": article, "kind": kind, "qa_type": qtype,
                       "artifact": version, "source_sibling": sibling,
                       "target_world_package_id": target["package_id"],
                       "target_world_digest": target["content_digest"],
                       "policy_snapshot_refs": spec["policy_snapshot_refs"],
                       "evidence_mode": "FIXTURE", "producer_ref": "fixture:producer",
                       "status": "PASS", "evidence_files": [evidence]}
            if qtype == "VISUAL_RENDER":
                receipt["page_count"] = 1
                evidence["page"] = 1
            row["qa"][qtype] = write_file(root, kind + "-" + qtype + ".json",
                                          json.dumps(receipt).encode())
        manifest["artifacts"][kind] = row
    args = dict(manifest_path=root / "manifest.json", approval_path=root / "approval.json",
                input_root=root, output_root=root / "output", catalog_root=root / "catalog",
                allow_fixtures=True)
    persist_case(args, manifest)
    return args, manifest, catalog


def persist_case(args, manifest):
    save_json(args["manifest_path"], manifest)
    save_json(args["approval_path"], {
        "manifest_digest": _digest(manifest), "evidence_mode": manifest["evidence_mode"],
        "decision": "APPROVED_FOR_LOCAL_DRY_RUN", "authority_ref": "fixture:human-approval",
        "valid_until": "2999-01-01T00:00:00Z",
        "approved_qa_sha256": [p["sha256"] for row in manifest["artifacts"].values()
                               for p in row["qa"].values()],
    })


def change_receipt(args, manifest, qtype, change):
    pointer = manifest["artifacts"]["manuscript_docx"]["qa"][qtype]
    path = args["input_root"] / pointer["path"]
    receipt = json.loads(path.read_text())
    change(receipt)
    data = json.dumps(receipt).encode()
    path.write_bytes(data)
    pointer["sha256"] = sha256(data)
    persist_case(args, manifest)


@pytest.mark.parametrize("article", ["P06", "P07"])
def test_fixture_import_reuse_idempotence_no_semantic_mutation(tmp_path, article, monkeypatch):
    import socket
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError("network/process actuator forbidden in offline runner")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    args, manifest, _ = setup_case(tmp_path, article)
    before = {p: p.read_bytes() for p in args["input_root"].glob("*") if p.is_file()}
    result = run_import(**args)
    assert result["status"] == "FIXTURE_DRY_RUN_COMPLETE", result
    assert result["finalization_request"] is None
    assert result["external_submit_events"] == []
    assert result["live_acceptance"] == "NOT_CLAIMED"
    assert run_import(**args) == result
    assert before == {p: p.read_bytes() for p in before}
    request = deepcopy(result["fixture_gate_request"])
    assert request.pop("target_world_package_id") == manifest["spec"]["target_world_package"]["package_id"]
    request["target_world_package"] = manifest["spec"]["target_world_package"]
    assert assess_submission_package(**request)["status"] == "READY_FOR_HUMAN_SUBMISSION"


PHASES = ["PLANNED", "QA_PENDING", "FINALIZATION_READY", "HANDED_OFF"]
PHASES += [phase + ":" + kind for kind in sorted(ARTIFACT_KINDS)
           for phase in ("MATERIALIZING", "ARTIFACT_COMPLETE")]
PHASES += [phase + ":" + kind + ":" + qa for kind in sorted(ARTIFACT_KINDS)
           for qa in DEFAULT_QA for phase in ("QA_RUNNING", "QA_COMPLETE")]


@pytest.mark.parametrize("phase", PHASES)
def test_restart_at_every_phase(tmp_path, phase):
    args, _, _ = setup_case(tmp_path)

    def interrupt(current):
        if current == phase:
            raise RuntimeError("simulated worker death")

    with pytest.raises(RuntimeError):
        run_import(**args, checkpoint=interrupt)
    result = run_import(**args, resume=True)
    assert result["status"] == "FIXTURE_DRY_RUN_COMPLETE", result
    state = SubmissionPackageFactoryStore(args["output_root"]).get(result["run_id"])
    assert len(state["qa_receipts"]) == 12 and state["qa_in_progress"] == []
    assert list(args["output_root"].rglob("recovery-*.json"))
    assert run_import(**args) == result


@pytest.mark.parametrize("qtype", DEFAULT_QA)
@pytest.mark.parametrize("failure", ["missing", "FAIL", "unapproved", "lineage", "evidence"])
def test_qa_fail_closed(tmp_path, qtype, failure):
    args, manifest, _ = setup_case(tmp_path)
    if failure == "missing":
        del manifest["artifacts"]["manuscript_docx"]["qa"][qtype]
        persist_case(args, manifest)
    elif failure == "unapproved":
        approval = json.loads(args["approval_path"].read_text())
        approval["approved_qa_sha256"] = []
        save_json(args["approval_path"], approval)
    else:
        change_receipt(args, manifest, qtype, lambda r: r.update(
            {"status": "FAIL"} if failure == "FAIL" else
            {"article_id": "wrong-article"} if failure == "lineage" else {"evidence_files": []}))
    result = run_import(**args)
    assert result["status"].startswith("BLOCKED"), result
    assert result["fixture_gate_request"] is None
    assert result["finalization_request"] is None


@pytest.mark.parametrize("field,value", [("route_status", "BLOCKED"), ("author_fields_status", "OPEN")])
def test_human_and_route_gates_preserved(tmp_path, field, value):
    args, manifest, _ = setup_case(tmp_path)
    manifest["spec"][field] = value
    persist_case(args, manifest)
    result = run_import(**args)
    assert result["status"] == "BLOCKED"
    assert any(value in b for b in result["blockers"])
    assert result["fixture_gate_request"] is None


@pytest.mark.parametrize("which", ["source", "artifact", "receipt", "catalog_digest", "catalog_status", "expiry"])
def test_revalidation_revokes_previous_deliverable(tmp_path, which):
    args, manifest, catalog = setup_case(tmp_path)
    assert run_import(**args)["status"] == "FIXTURE_DRY_RUN_COMPLETE"
    if which in {"source", "artifact", "receipt"}:
        row = manifest["artifacts"]["manuscript_docx"]
        pointer = manifest["sibling_file"] if which == "source" else row["file"] if which == "artifact" else row["qa"]["SEMANTIC_QA"]
        (args["input_root"] / pointer["path"]).write_bytes(b"changed")
    elif which == "expiry":
        approval = json.loads(args["approval_path"].read_text())
        approval["valid_until"] = "2000-01-01T00:00:00Z"
        save_json(args["approval_path"], approval)
    else:
        index = catalog._load_index()
        index["entries"][0]["status" if which == "catalog_status" else "content_digest"] = "HISTORICAL" if which == "catalog_status" else "0" * 64
        catalog._save_index(index)
    result = run_import(**args)
    assert result["status"].startswith("BLOCKED"), result
    saved = json.loads((args["output_root"] / result["execution_id"] / "result.json").read_text())
    assert saved["finalization_request"] is None and saved["fixture_gate_request"] is None


def test_no_policy_downgrade_or_fixture_promotion(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    args["allow_fixtures"] = False
    assert run_import(**args)["status"] == "BLOCKED"
    args["allow_fixtures"] = True
    manifest["spec"]["required_qa_types"] = ["SEMANTIC_QA"]
    manifest["spec"]["required_artifact_kinds"] = ["manuscript_docx"]
    manifest["evidence_mode"] = "REAL"
    persist_case(args, manifest)
    # Merely changing the manifest/approval labels cannot promote fixture receipts.
    assert run_import(**args)["status"] == "BLOCKED"


def test_missing_import_and_path_escape(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    manifest["artifacts"]["manuscript_docx"]["file"]["path"] = "missing.docx"
    persist_case(args, manifest)
    assert run_import(**args)["status"] == "BLOCKED_NEEDS_ADAPTER"
    manifest["artifacts"]["manuscript_docx"]["file"]["path"] = "../outside.docx"
    persist_case(args, manifest)
    assert run_import(**args, resume=True)["blockers"] == ["input_path_outside_workspace"]


def test_all_render_pages_required(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    change_receipt(args, manifest, "VISUAL_RENDER", lambda r: r.update(page_count=2))
    assert run_import(**args)["blockers"] == ["full_page_render_evidence_incomplete"]


@pytest.mark.parametrize("field,value", [("ref", "fixture:other"), ("revision", "r2"), ("sha256", "0" * 64)])
def test_changed_provenance_never_reuses_prior_qa(tmp_path, field, value):
    args, manifest, _ = setup_case(tmp_path)
    before = run_import(**args)
    manifest["spec"]["authoritative_sibling"][field] = value
    persist_case(args, manifest)
    result = run_import(**args)
    assert result["execution_id"] != before["execution_id"]
    assert result["status"].startswith("BLOCKED")


def test_atomic_result_failure_preserves_previous_bytes(tmp_path, monkeypatch):
    import kairoskopion.kairon_provider.publication_runner as runner
    dest = tmp_path / "result.json"
    atomic_write(dest, b"old")
    def fail(*args):
        raise OSError("interrupted rename")
    monkeypatch.setattr(runner.os, "replace", fail)
    with pytest.raises(OSError):
        atomic_write(dest, b"new")
    assert dest.read_bytes() == b"old"
    assert not list(tmp_path.glob("*.tmp"))


def test_cli_no_submit_surface(tmp_path, capsys):
    args, _, _ = setup_case(tmp_path)
    argv = []
    for key, flag in [("manifest_path", "manifest"), ("approval_path", "approval"),
                      ("input_root", "input-root"), ("output_root", "output-root"),
                      ("catalog_root", "catalog-root")]:
        argv += ["--" + flag, str(args[key])]
    assert main(argv) == 2
    assert main(argv + ["--allow-fixtures"]) == 0
    assert "FIXTURE_DRY_RUN_COMPLETE" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(argv + ["--submit"])


def test_actual_api_request_model_compatibility(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIROSKOPION_DATA_DIR", str(tmp_path / "api"))
    from kairoskopion.api.kairon_provider import SubmissionPackageFinalizeRequest
    args, _, _ = setup_case(tmp_path)
    result = run_import(**args)
    request = SubmissionPackageFinalizeRequest(**result["fixture_gate_request"])
    assert request.article_id == "P06"
    assert request.required_qa_types == sorted(DEFAULT_QA)
    assert request.required_artifact_kinds == sorted(ARTIFACT_KINDS)


def test_controls_harness_independent_reuse_and_missing_inputs(tmp_path):
    import runpy
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_publication_controls.py"
    run_controls = runpy.run_path(str(script))["run_controls"]
    args, _, _ = setup_case(tmp_path, "P06")
    receipt = run_controls(tmp_path, tmp_path / "controls", args["catalog_root"], allow_fixtures=True)
    assert [r["status"] for r in receipt["controls"]] == ["FIXTURE_DRY_RUN_COMPLETE", "BLOCKED_NEEDS_ADAPTER"]
    setup_case(tmp_path, "P07")
    receipt = run_controls(tmp_path, tmp_path / "controls", args["catalog_root"], allow_fixtures=True)
    assert all(r["status"] == "FIXTURE_DRY_RUN_COMPLETE" for r in receipt["controls"])
    assert receipt["controls"][0]["execution_id"] != receipt["controls"][1]["execution_id"]
    assert receipt["live_acceptance"] == "NOT_CLAIMED"


def test_changes_at_finalization_boundary_block(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    def change(phase):
        if phase == "FINALIZATION_READY":
            (args["input_root"] / manifest["sibling_file"]["path"]).write_bytes(b"changed")
    result = run_import(**args, checkpoint=change)
    assert result["status"] == "BLOCKED"
    assert result["fixture_gate_request"] is None


def test_resume_requires_stopped_worker_assertion(tmp_path):
    args, _, _ = setup_case(tmp_path)
    def interrupt(phase):
        if phase.startswith("MATERIALIZING:"):
            raise RuntimeError("worker died")
    with pytest.raises(RuntimeError):
        run_import(**args, checkpoint=interrupt)
    assert run_import(**args)["blockers"] == ["interrupted_worker_requires_explicit_resume"]
    assert run_import(**args, resume=True)["status"] == "FIXTURE_DRY_RUN_COMPLETE"


def test_manifest_revision_cannot_bypass_terminal_qa_immutability(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    before = run_import(**args)
    change_receipt(args, manifest, "SEMANTIC_QA", lambda r: r.update(status="FAIL"))
    after = run_import(**args)
    assert before["execution_id"] != after["execution_id"]
    assert before["run_id"] == after["run_id"]
    assert after["status"] == "BLOCKED"
    assert after["blockers"] == ["terminal QA receipt is immutable"]
    assert json.loads((args["output_root"] / "current.json").read_text())["fixture_gate_request"] is None


def test_manifest_revision_cannot_replace_completed_artifact(tmp_path):
    args, manifest, _ = setup_case(tmp_path)
    run_import(**args)
    row = manifest["artifacts"]["manuscript_docx"]
    row["version"]["revision"] = "unauthorized-reexport-2"
    persist_case(args, manifest)
    assert run_import(**args)["blockers"] == ["completed artifact version is immutable"]


def test_missing_manifest_revokes_current_handoff(tmp_path):
    args, _, _ = setup_case(tmp_path)
    run_import(**args)
    args["manifest_path"] = args["input_root"] / "missing.json"
    assert run_import(**args)["status"] == "BLOCKED_NEEDS_ADAPTER"
    current = json.loads((args["output_root"] / "current.json").read_text())
    assert current["fixture_gate_request"] is None
