"""Offline factory contracts. All writes stay in pytest's tmp_path."""

from copy import deepcopy
import json

import pytest

from kairoskopion.kairon_provider.submission_gate import assess_submission_package
from kairoskopion.kairon_provider.submission_package_factory import (
    BLOCKED, DEFAULT_QA, FINALIZATION_READY, HANDED_OFF, MATERIALIZING,
    PLANNED, QA_PENDING, SubmissionPackageFactoryStore,
)


def inputs(**overrides):
    result = {
        "article_id": "article:synthetic", "venue_id": "venue:synthetic",
        "authoritative_sibling": {"ref": "artikl:sibling:synthetic", "revision": "r1", "sha256": "a" * 64},
        "target_world_package": {
            "package_id": "targetworld:synthetic@1", "content_digest": "b" * 64,
            "status": "PROD_ACCEPTED", "snapshot": {
                "snapshot_id": "targetworld:synthetic", "target_id": "venue:synthetic",
            },
        },
        "submission_pack": {
            "submission_pack_id": "skeleton:synthetic", "status": "ready_skeleton",
            "ready_status": "ready_for_manual_submission",
            "blocking_issues": [], "missing_items": [], "unknowns": [],
        },
        "policy_snapshot_refs": ["policy:synthetic:r1"],
        "route_status": "LIVE", "author_fields_status": "CONFIRMED",
    }
    result.update(overrides)
    return result


def artifact(kind="manuscript_docx"):
    return {"ref": "artifact:synthetic:" + kind, "revision": "export-r1", "sha256": "c" * 64}


def record(store, run, kind="manuscript_docx"):
    return store.record_artifact(
        run["run_id"], kind=kind, artifact=artifact(kind),
        source_sibling=run["spec"]["authoritative_sibling"],
    )


def qa(store, run, kind="manuscript_docx", qa_type="SEMANTIC_QA", status="PASS"):
    return store.record_qa(
        run["run_id"], kind=kind, qa_type=qa_type, artifact=artifact(kind),
        status=status, evidence_ref=f"qa:synthetic:{kind}:{qa_type}",
    )


def ready(store, **overrides):
    run = store.start(**inputs(**overrides))
    for kind in run["spec"]["required_artifact_kinds"]:
        run = record(store, run, kind)
        for qtype in run["spec"]["required_qa_types"]:
            run = qa(store, run, kind, qtype)
    return run


def test_identical_start_returns_durable_current_state(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    first = store.start(**inputs())
    assert first["phase"] == PLANNED
    assert store.start(**inputs()) == first
    advanced = record(store, first)
    assert SubmissionPackageFactoryStore(tmp_path).start(**inputs()) == advanced


@pytest.mark.parametrize("field,value", [("revision", "r2"), ("sha256", "d" * 64), ("ref", "artikl:other")])
def test_sibling_identity_changes_run_id(tmp_path, field, value):
    store = SubmissionPackageFactoryStore(tmp_path)
    args = inputs()
    first = store.start(**args)
    args["authoritative_sibling"][field] = value
    assert store.start(**args)["run_id"] != first["run_id"]


@pytest.mark.parametrize("sibling", [{"ref": "sibling:1"}, {"ref": "sibling:1", "revision": " "}, {"ref": "sibling:1", "sha256": "bad"}])
def test_unversioned_or_malformed_sibling_rejected(tmp_path, sibling):
    with pytest.raises(ValueError):
        SubmissionPackageFactoryStore(tmp_path).start(**inputs(authoritative_sibling=sibling))
    assert not list(tmp_path.rglob("*.json"))


def test_no_manuscript_payload_and_no_input_mutation(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    args = inputs()
    args["submission_pack"]["cover_letter"] = "SYNTHETIC_CONTENT_NOT_TO_STORE"
    args["target_world_package"]["snapshot"]["manuscript_text"] = "SYNTHETIC_CONTENT_NOT_TO_STORE"
    original = deepcopy(args)
    run = store.start(**args)
    assert args == original
    with pytest.raises(ValueError, match="no content payload"):
        store.start(**inputs(authoritative_sibling={**args["authoritative_sibling"], "text": "payload"}))
    with pytest.raises(ValueError, match="no content payload"):
        store.record_artifact(run["run_id"], kind="manuscript_docx",
                              artifact={**artifact(), "bytes": "payload"},
                              source_sibling=args["authoritative_sibling"])
    for path in tmp_path.rglob("*.json"):
        assert "SYNTHETIC_CONTENT_NOT_TO_STORE" not in path.read_text(encoding="utf-8")
    assert run["spec"]["authoritative_sibling"] == args["authoritative_sibling"]


def test_artifact_idempotency_and_immutable_version_binding(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = record(store, store.start(**inputs()))
    assert record(store, run) == run
    with pytest.raises(ValueError, match="immutable"):
        store.record_artifact(run["run_id"], kind="manuscript_docx",
                              artifact={**artifact(), "revision": "export-r2"},
                              source_sibling=run["spec"]["authoritative_sibling"])
    with pytest.raises(ValueError, match="sibling mismatch"):
        store.record_artifact(run["run_id"], kind="manuscript_docx", artifact=artifact(),
                              source_sibling={"ref": "artikl:other", "revision": "r1"})
    assert store.get(run["run_id"]) == run


def test_qa_rejects_wrong_version_and_is_idempotent(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = record(store, store.start(**inputs()))
    with pytest.raises(ValueError, match="version mismatch"):
        store.record_qa(run["run_id"], kind="manuscript_docx", qa_type="SEMANTIC_QA",
                        artifact={**artifact(), "sha256": "d" * 64}, status="PASS", evidence_ref="qa:wrong")
    run = qa(store, run)
    assert qa(store, run) == run
    assert len(run["qa_receipts"]) == 1
    with pytest.raises(ValueError, match="immutable"):
        qa(store, run, status="FAIL")


def test_restart_recovers_claims_preserving_receipts(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = store.start(**inputs(required_artifact_kinds=["manuscript_docx", "title_page"]))
    run = record(store, run)
    run = qa(store, run)
    run = store.begin_artifact(run["run_id"], "title_page")
    assert run["phase"] == MATERIALIZING
    run = store.begin_qa(run["run_id"], kind="manuscript_docx", qa_type="VISUAL_RENDER")
    # Simulate an abandoned partial temp write. It must not replace committed JSON.
    (store.root / "interrupted.tmp").write_text('{"partial":', encoding="utf-8")
    restarted = SubmissionPackageFactoryStore(tmp_path)
    recovered = restarted.recover(run["run_id"])
    assert recovered["artifacts"]["title_page"]["status"] == "PENDING"
    assert recovered["artifacts"]["manuscript_docx"] == run["artifacts"]["manuscript_docx"]
    assert recovered["qa_receipts"] == run["qa_receipts"]
    assert recovered["qa_in_progress"] == []
    assert restarted.recover(run["run_id"]) == recovered
    recovered = record(restarted, recovered, "title_page")
    for kind in recovered["spec"]["required_artifact_kinds"]:
        for qtype in DEFAULT_QA:
            recovered = qa(restarted, recovered, kind, qtype)
    assert recovered["phase"] == FINALIZATION_READY


def test_missing_visual_render_blocks_request(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = record(store, store.start(**inputs()))
    for qtype in ("SEMANTIC_QA", "PRIVACY_SCRUB"):
        run = qa(store, run, qa_type=qtype)
    assert run["phase"] == QA_PENDING
    assert "artifact_qa_not_passed:manuscript_docx:VISUAL_RENDER" in run["blockers"]
    with pytest.raises(ValueError, match="VISUAL_RENDER"):
        store.build_finalization_request(run["run_id"])


@pytest.mark.parametrize("failed", DEFAULT_QA)
def test_failed_qa_blocks(tmp_path, failed):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = record(store, store.start(**inputs()))
    for qtype in DEFAULT_QA:
        run = qa(store, run, qa_type=qtype, status="FAIL" if qtype == failed else "PASS")
    assert run["phase"] == BLOCKED
    with pytest.raises(ValueError, match="qa_failed"):
        store.build_finalization_request(run["run_id"])


@pytest.mark.parametrize("overrides,blocker", [
    ({"author_fields_status": "OPEN"}, "author_fields_not_confirmed:OPEN"),
    ({"route_status": "BLOCKED"}, "submission_route_not_live:BLOCKED"),
    ({"route_status": "UNKNOWN"}, "submission_route_not_live:UNKNOWN"),
    ({"policy_snapshot_refs": []}, "policy_snapshot_missing"),
])
def test_external_conditions_never_promoted(tmp_path, overrides, blocker):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = ready(store, **overrides)
    assert run["phase"] == BLOCKED
    assert blocker in run["blockers"]
    with pytest.raises(ValueError):
        store.build_finalization_request(run["run_id"])


def test_all_artifacts_require_their_own_qa(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = store.start(**inputs(required_artifact_kinds=["manuscript_docx", "title_page"]))
    for kind in run["spec"]["required_artifact_kinds"]:
        run = record(store, run, kind)
    for qtype in DEFAULT_QA:
        run = qa(store, run, qa_type=qtype)
    with pytest.raises(ValueError, match="title_page"):
        store.build_finalization_request(run["run_id"])


def test_full_handoff_matches_gate_and_preserves_exact_lineage(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    kinds = ["manuscript_docx", "title_page", "cover_letter", "submission_checklist"]
    run = ready(store, required_artifact_kinds=kinds)
    assert run["phase"] == FINALIZATION_READY
    request = store.build_finalization_request(run["run_id"])
    assert json.loads(request["manuscript_revision"]) == run["spec"]["authoritative_sibling"]
    assert request["target_world_package"] == run["spec"]["target_world_package"]
    for row in request["artifacts"]:
        assert row["source_sibling"] == run["spec"]["authoritative_sibling"]
        assert {k: row[k] for k in ("ref", "revision", "sha256")} == artifact(row["kind"])
    assert len(request["qa_receipts"]) == len(kinds) * 3
    manifest = assess_submission_package(**request)
    assert manifest["status"] == "READY_FOR_HUMAN_SUBMISSION"
    assert manifest["human_gate"] == "FINAL_SUBMISSION_BY_TIMUR_ONLY"
    restarted = SubmissionPackageFactoryStore(tmp_path)
    assert restarted.build_finalization_request(run["run_id"]) == request
    assert restarted.recover(run["run_id"])["phase"] == HANDED_OFF
    assert not (tmp_path / "kairon_provider" / "submission_packages").exists()
    assert set(p.name for p in (tmp_path / "kairon_provider").iterdir()) == {"submission_package_runs"}


def test_explicit_target_qa_policy_and_order_are_deterministic(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = ready(store, required_qa_types=["SEMANTIC_QA", "PRIVACY_SCRUB"])
    assert run["phase"] == FINALIZATION_READY
    repeat = store.start(**inputs(required_qa_types=["PRIVACY_SCRUB", "SEMANTIC_QA", "SEMANTIC_QA"]))
    assert repeat == run
    assert store.build_finalization_request(run["run_id"])["required_qa_types"] == ["PRIVACY_SCRUB", "SEMANTIC_QA"]
    with pytest.raises(ValueError):
        store.start(**inputs(required_qa_types=[]))


@pytest.mark.parametrize("field", ["blocking_issues", "missing_items", "unknowns"])
def test_skeleton_debt_remains_blocking(tmp_path, field):
    store = SubmissionPackageFactoryStore(tmp_path)
    skeleton = inputs()["submission_pack"]
    skeleton[field] = ["synthetic unresolved item"]
    run = ready(store, submission_pack=skeleton)
    assert run["phase"] == BLOCKED
    with pytest.raises(ValueError, match="skeleton:"):
        store.build_finalization_request(run["run_id"])


def test_target_world_status_and_identity_fail_closed(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    target = inputs()["target_world_package"]
    target["status"] = "PROVIDER_OBSERVED"
    run = ready(store, target_world_package=target)
    assert run["phase"] == BLOCKED
    target["snapshot"]["target_id"] = "venue:other"
    with pytest.raises(ValueError, match="target_id"):
        store.start(**inputs(target_world_package=target))


def test_interrupted_atomic_replace_keeps_last_committed_receipts(tmp_path, monkeypatch):
    from kairoskopion.kairon_provider import submission_package_factory as factory

    store = SubmissionPackageFactoryStore(tmp_path)
    committed = qa(store, record(store, store.start(**inputs())))

    def interrupt_replace(source, destination):
        raise OSError("synthetic interruption before commit")

    with monkeypatch.context() as patch:
        patch.setattr(factory.os, "replace", interrupt_replace)
        with pytest.raises(OSError, match="synthetic interruption"):
            qa(store, committed, qa_type="PRIVACY_SCRUB")
    restarted = SubmissionPackageFactoryStore(tmp_path)
    assert restarted.get(committed["run_id"]) == committed
    retried = qa(restarted, committed, qa_type="PRIVACY_SCRUB")
    assert len(retried["qa_receipts"]) == 2
    assert qa(restarted, retried, qa_type="PRIVACY_SCRUB") == retried


@pytest.mark.parametrize("version", [{"revision": "r1"}, {"sha256": "a" * 64}])
def test_revision_only_and_hash_only_siblings_supported(tmp_path, version):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = ready(store, authoritative_sibling={"ref": "sibling:synthetic", **version})
    request = store.build_finalization_request(run["run_id"])
    assert json.loads(request["manuscript_revision"])["ref"] == "sibling:synthetic"
    assert assess_submission_package(**request)["status"] == "READY_FOR_HUMAN_SUBMISSION"


def test_returned_state_cannot_mutate_persisted_lineage(tmp_path):
    store = SubmissionPackageFactoryStore(tmp_path)
    run = store.start(**inputs())
    run_id = run["run_id"]
    run["spec"]["authoritative_sibling"]["revision"] = "uncommitted"
    assert store.get(run_id)["spec"]["authoritative_sibling"]["revision"] == "r1"
