from __future__ import annotations

from pathlib import Path

import pytest

from kairoskopion.kairon_provider.fulltext import acquire_manifest_fulltexts
from kairoskopion.kairon_provider.fulltext_fallback import (
    FulltextFallbackStore,
    FulltextEvidenceReturn,
    apply_evidence_return,
    is_fallback_eligible_direct_error,
)
from kairoskopion.kairon_provider.models import CorpusArtifact, CorpusArtifactManifest


def _artifact() -> CorpusArtifact:
    return CorpusArtifact(
        source_ref="W-403",
        title="Blocked publisher article",
        authors=["A. Author"],
        year=2025,
        doi="10.1234/example.403",
        acquisition_state="fulltext_locator",
        notes=["fulltext_locator:https://publisher.example/article.pdf"],
    )


def _manifest() -> CorpusArtifactManifest:
    return CorpusArtifactManifest(
        target_id="techne",
        selection_strategy="recent_articles",
        artifacts=[_artifact()],
    )


def test_fallback_eligibility_is_access_block_specific():
    assert is_fallback_eligible_direct_error({"error_code": "http_403"})
    assert is_fallback_eligible_direct_error({"error_code": "http_401"})
    assert not is_fallback_eligible_direct_error({"error_code": "network_error"})
    assert not is_fallback_eligible_direct_error({"error_code": "download_size_over_limit"})


def test_direct_success_does_not_emit_fallback_request(tmp_path):
    manifest = _manifest()
    url = "https://publisher.example/article.pdf"
    store = FulltextFallbackStore(tmp_path)
    result = acquire_manifest_fulltexts(
        manifest,
        output_dir=tmp_path / "artifacts",
        fixtures={url: (b"%PDF-1.4\nfixture\n", "application/pdf")},
        fallback_store=store,
        target_snapshot_id="tw:techne:1",
    )
    assert result["validated"] == 1
    assert result["fallback_requests"] == []
    assert store.list_requests() == []
    assert manifest.artifacts[0].acquisition_state == "validated_artifact"


def test_direct_403_emits_durable_idempotent_fallback_request(tmp_path, monkeypatch):
    manifest = _manifest()
    store = FulltextFallbackStore(tmp_path)

    def blocked(*args, **kwargs):
        return {
            "status": "failed",
            "url": "https://publisher.example/article.pdf",
            "error_code": "http_403",
            "http_status": 403,
            "error": "HTTPError: HTTP Error 403",
        }

    monkeypatch.setattr(
        "kairoskopion.kairon_provider.fulltext.acquire_explicit_fulltext",
        blocked,
    )
    first = acquire_manifest_fulltexts(
        manifest,
        output_dir=tmp_path / "artifacts",
        fallback_store=store,
        target_snapshot_id="tw:techne:1",
        fallback_provenance_refs=["TRM-070"],
    )
    second = acquire_manifest_fulltexts(
        manifest,
        output_dir=tmp_path / "artifacts",
        fallback_store=store,
        target_snapshot_id="tw:techne:1",
        fallback_provenance_refs=["TRM-070"],
    )

    assert len(first["fallback_requests"]) == 1
    assert len(second["fallback_requests"]) == 1
    assert (
        first["fallback_requests"][0]["request_id"]
        == second["fallback_requests"][0]["request_id"]
    )
    stored = store.list_requests()
    assert len(stored) == 1
    request = stored[0]
    assert request["article_identity"]["doi"] == "10.1234/example.403"
    assert request["prior_attempts"][0]["http_status"] == 403
    assert request["requested_source_class"] == "INDAGO"
    assert manifest.artifacts[0].acquisition_state == "fallback_requested"


def test_found_location_never_becomes_readable_fulltext(tmp_path):
    manifest = _manifest()
    artifact = manifest.artifacts[0]
    store = FulltextFallbackStore(tmp_path)

    # Build one request through the public failure path.
    from kairoskopion.kairon_provider.fulltext_fallback import build_fallback_request

    request = build_fallback_request(
        target_snapshot_id="tw:techne:1",
        target_corpus_id="techne",
        artifact=artifact,
        direct_error={
            "url": "https://publisher.example/article.pdf",
            "error_code": "http_403",
            "http_status": 403,
            "error": "HTTPError: HTTP Error 403",
        },
    )
    store.put_request(request)
    stored = store.put_return(
        request.request_id,
        {
            "provider_class": "SCIHUB_CLASS",
            "provider_instance": "provider-instance",
            "provider_attempt_id": "attempt-1",
            "result_state": "FOUND_LOCATION",
            "location_ref": "provider:doi:10.1234/example.403",
            "exact_source_satisfied": True,
            "evidence_refs": ["indago:hunt:1"],
        },
    )
    evidence = FulltextEvidenceReturn(**stored)
    apply_evidence_return(artifact, evidence)

    assert artifact.acquisition_state == "fallback_location_found"
    assert artifact.local_ref is None
    assert artifact.content_hash is None
    assert any("FOUND_LOCATION" in x for x in artifact.notes)


def test_host_policy_block_is_not_not_found(tmp_path):
    artifact = _artifact()
    store = FulltextFallbackStore(tmp_path)
    from kairoskopion.kairon_provider.fulltext_fallback import build_fallback_request

    request = build_fallback_request(
        target_snapshot_id="tw:techne:1",
        target_corpus_id="techne",
        artifact=artifact,
        direct_error={
            "url": "https://publisher.example/article.pdf",
            "error_code": "http_403",
            "http_status": 403,
            "error": "HTTPError: HTTP Error 403",
        },
    )
    store.put_request(request)
    stored = store.put_return(
        request.request_id,
        {
            "provider_class": "SCIHUB_CLASS",
            "provider_attempt_id": "attempt-host-boundary",
            "result_state": "HOST_POLICY_BLOCKED",
            "failure_reason": "exact provider reached; acquisition action unavailable",
            "exact_source_satisfied": False,
        },
    )
    evidence = FulltextEvidenceReturn(**stored)
    apply_evidence_return(artifact, evidence)
    assert artifact.acquisition_state == "fallback_host_policy_blocked"
    assert artifact.local_ref is None


def test_found_artifact_requires_validation_extraction_and_registration(tmp_path):
    artifact = _artifact()
    store = FulltextFallbackStore(tmp_path)
    from kairoskopion.kairon_provider.fulltext_fallback import build_fallback_request

    request = build_fallback_request(
        target_snapshot_id="tw:techne:1",
        target_corpus_id="techne",
        artifact=artifact,
        direct_error={
            "url": "https://publisher.example/article.pdf",
            "error_code": "http_403",
            "http_status": 403,
            "error": "HTTPError: HTTP Error 403",
        },
    )
    store.put_request(request)
    with pytest.raises(ValueError, match="FOUND_ARTIFACT requires"):
        store.put_return(
            request.request_id,
            {
                "provider_class": "AUTHORIZED_ARCHIVE",
                "provider_attempt_id": "attempt-artifact",
                "result_state": "FOUND_ARTIFACT",
                "artifact_ref": "artifact:1",
            },
        )

    stored = store.put_return(
        request.request_id,
        {
            "provider_class": "AUTHORIZED_ARCHIVE",
            "provider_attempt_id": "attempt-artifact",
            "result_state": "FOUND_ARTIFACT",
            "artifact_ref": "artifact:1",
            "content_hash": "a" * 64,
            "media_type": "application/pdf",
            "byte_size": 1024,
            "validation_state": "validated",
            "extraction_state": "extracted",
            "source_registration_ref": "litops:source:artifact-1",
            "exact_source_satisfied": True,
        },
    )
    evidence = FulltextEvidenceReturn(**stored)
    apply_evidence_return(artifact, evidence)
    assert artifact.acquisition_state == "fallback_artifact_returned"
    assert artifact.content_hash == "a" * 64
    # Provider evidence is not silently converted to a local filesystem path.
    assert artifact.local_ref is None


def test_human_action_can_resume_same_request_with_later_return(tmp_path):
    artifact = _artifact()
    store = FulltextFallbackStore(tmp_path)
    from kairoskopion.kairon_provider.fulltext_fallback import build_fallback_request

    request = build_fallback_request(
        target_snapshot_id="tw:techne:1",
        target_corpus_id="techne",
        artifact=artifact,
        direct_error={
            "url": "https://publisher.example/article.pdf",
            "error_code": "http_403",
            "http_status": 403,
            "error": "HTTPError: HTTP Error 403",
        },
    )
    store.put_request(request)
    first = store.put_return(
        request.request_id,
        {
            "provider_class": "INDAGO_BROWSER",
            "provider_attempt_id": "attempt-browser-1",
            "result_state": "HUMAN_ACTION_REQUIRED",
            "human_action": {
                "kind": "challenge",
                "resume_token": "same-hunt-token",
            },
        },
    )
    second = store.put_return(
        request.request_id,
        {
            "provider_class": "INDAGO_BROWSER",
            "provider_attempt_id": "attempt-browser-1",
            "result_state": "FOUND_LOCATION",
            "location_ref": "provider:resolved-location",
            "exact_source_satisfied": True,
        },
    )
    assert first["return_id"] != second["return_id"]
    events = store.list_returns(request.request_id)
    assert [x["result_state"] for x in events] == [
        "HUMAN_ACTION_REQUIRED",
        "FOUND_LOCATION",
    ]
    assert store.get_latest_return(request.request_id).result_state == "FOUND_LOCATION"


def test_api_exposes_fulltext_fallback_routes():
    from kairoskopion.api.kairon_provider import router

    paths = {route.path for route in router.routes}
    assert "/kairon/provider/fulltext-fallback/requests" in paths
    assert "/kairon/provider/fulltext-fallback/requests/{request_id}" in paths
    methods = {
        (route.path, method)
        for route in router.routes
        for method in (route.methods or set())
    }
    assert (
        "/kairon/provider/fulltext-fallback/requests/{request_id}/return",
        "POST",
    ) in methods
