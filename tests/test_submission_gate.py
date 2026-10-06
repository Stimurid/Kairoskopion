from kairoskopion.kairon_provider.submission_gate import (
    BLOCKED,
    READY_FOR_HUMAN_SUBMISSION,
    SubmissionPackageStore,
    assess_submission_package,
)


def _target_world(status="PROD_ACCEPTED"):
    return {
        "schema_version": "targetworld-exchange-v1",
        "package_id": "targetworld:pt:prod@abc123",
        "content_digest": "abc123",
        "status": status,
        "snapshot": {
            "snapshot_id": "targetworld:pt:prod",
            "target_id": "philosophy_technology",
        },
    }


def _skeleton(**overrides):
    value = {
        "submission_pack_id": "sp_p06_pt",
        "ready_status": "ready_for_manual_submission",
        "status": "ready_skeleton",
        "blocking_issues": [],
        "missing_items": [],
        "unknowns": [],
    }
    value.update(overrides)
    return value


def _artifacts():
    return [
        {
            "kind": "manuscript_docx",
            "ref": "gdrive:1p06docx",
            "sha256": "deadbeef",
        },
        {
            "kind": "title_page",
            "ref": "gdoc:1title",
            "revision": "rev-title-1",
        },
    ]


def _qa():
    return [
        {
            "qa_type": "SEMANTIC_QA",
            "status": "PASS",
            "artifact_ref": "gdrive:1p06docx",
            "evidence_ref": "gdoc:semantic-pass",
        },
        {
            "qa_type": "PRIVACY_SCRUB",
            "status": "PASS",
            "artifact_ref": "gdrive:1p06docx",
            "evidence_ref": "gdoc:privacy-pass",
        },
        {
            "qa_type": "VISUAL_RENDER",
            "status": "PASS",
            "artifact_ref": "gdrive:1p06docx",
            "evidence_ref": "gdoc:render-pass",
        },
    ]


def _assess(**overrides):
    args = {
        "article_id": "P06",
        "manuscript_revision": "p06-pt-v0.2",
        "venue_id": "philosophy_technology",
        "submission_pack": _skeleton(),
        "target_world_package": _target_world(),
        "artifacts": _artifacts(),
        "qa_receipts": _qa(),
        "route_status": "LIVE",
        "author_fields_status": "CONFIRMED",
        "policy_snapshot_refs": ["official:pt-guidelines:2026-10-06"],
    }
    args.update(overrides)
    return assess_submission_package(**args)


def test_finalization_happy_path_reaches_human_gate():
    manifest = _assess()
    assert manifest["status"] == READY_FOR_HUMAN_SUBMISSION
    assert manifest["blockers"] == []
    assert manifest["human_gate"] == "FINAL_SUBMISSION_BY_TIMUR_ONLY"
    assert manifest["target_world"]["content_digest"] == "abc123"


def test_manifest_id_is_deterministic_over_semantic_inputs():
    first = _assess()
    second = _assess()
    assert first["manifest_id"] == second["manifest_id"]
    assert first["content_digest"] == second["content_digest"]
    assert first["assessed_at"] != second["assessed_at"] or first["assessed_at"]


def test_store_repeat_is_idempotent(tmp_path):
    store = SubmissionPackageStore(tmp_path)
    first = store.put(_assess())
    second = store.put(_assess())
    assert second == first
    assert store.get(first["manifest_id"]) == first


def test_missing_visual_render_blocks_finalization():
    qa = [x for x in _qa() if x["qa_type"] != "VISUAL_RENDER"]
    manifest = _assess(qa_receipts=qa)
    assert manifest["status"] == BLOCKED
    assert "required_qa_not_passed:VISUAL_RENDER" in manifest["blockers"]


def test_failed_qa_blocks_even_if_other_pass_exists():
    qa = _qa() + [
        {
            "qa_type": "VISUAL_RENDER",
            "status": "FAIL",
            "artifact_ref": "gdrive:1p06docx",
            "evidence_ref": "gdoc:failed-render",
        }
    ]
    manifest = _assess(qa_receipts=qa)
    assert manifest["status"] == BLOCKED
    assert "qa_failed:VISUAL_RENDER" in manifest["blockers"]


def test_non_live_route_blocks_finalization():
    manifest = _assess(route_status="BLOCKED")
    assert manifest["status"] == BLOCKED
    assert "submission_route_not_live:BLOCKED" in manifest["blockers"]


def test_open_author_fields_block_finalization():
    manifest = _assess(author_fields_status="OPEN")
    assert manifest["status"] == BLOCKED
    assert "author_fields_not_confirmed:OPEN" in manifest["blockers"]


def test_missing_required_artifact_blocks_finalization():
    manifest = _assess(
        artifacts=[],
        required_artifact_kinds=["manuscript_docx"],
    )
    assert manifest["status"] == BLOCKED
    assert "required_artifact_missing:manuscript_docx" in manifest["blockers"]


def test_unversioned_artifact_blocks_finalization():
    artifacts = [
        {
            "kind": "manuscript_docx",
            "ref": "gdrive:1p06docx",
        }
    ]
    manifest = _assess(artifacts=artifacts)
    assert manifest["status"] == BLOCKED
    assert "artifact_unversioned:manuscript_docx" in manifest["blockers"]


def test_skeleton_debt_is_not_erased_by_artifact_qa():
    manifest = _assess(
        submission_pack=_skeleton(
            missing_items=["current AI policy unknown"],
            unknowns=["live route not verified by skeleton"],
        )
    )
    assert manifest["status"] == BLOCKED
    assert "skeleton:missing:current AI policy unknown" in manifest["blockers"]
    assert "skeleton:unknown:live route not verified by skeleton" in manifest["blockers"]


def test_nonproduction_target_world_cannot_finalize():
    for status in ("QUALIFIED_DEV", "PROVIDER_OBSERVED", "STAGING", "PROVISIONAL"):
        manifest = _assess(target_world_package=_target_world(status))
        assert manifest["status"] == BLOCKED
        assert (
            f"target_world_status_not_finalizable:{status}"
            in manifest["blockers"]
        )


def test_current_catalog_promotion_can_finalize_frozen_older_package():
    package = _target_world("PROVIDER_OBSERVED")
    package["catalog_status"] = "PROD_ACCEPTED"
    manifest = _assess(target_world_package=package)
    assert manifest["status"] == READY_FOR_HUMAN_SUBMISSION
    assert manifest["target_world"]["status"] == "PROD_ACCEPTED"
    assert manifest["target_world"]["package_status"] == "PROVIDER_OBSERVED"



def test_upstream_submission_pack_identity_is_digest_bound():
    first = _assess()
    second_skeleton = _skeleton()
    second_skeleton["submission_pack_id"] = "sp_p06_pt_other"
    second = _assess(submission_pack=second_skeleton)
    assert first["manifest_id"] != second["manifest_id"]


def test_missing_submission_pack_id_blocks_finalization():
    skeleton = _skeleton()
    skeleton["submission_pack_id"] = None
    manifest = _assess(submission_pack=skeleton)
    assert manifest["status"] == BLOCKED
    assert "submission_pack_id_missing" in manifest["blockers"]


def test_missing_policy_snapshot_blocks():
    manifest = _assess(policy_snapshot_refs=[])
    assert manifest["status"] == BLOCKED
    assert "policy_snapshot_missing" in manifest["blockers"]
