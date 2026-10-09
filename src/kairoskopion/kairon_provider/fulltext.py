"""Upgrade corpus artifacts from locator state to acquired/validated files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.venue.fulltext_fetch import acquire_explicit_fulltext
from .models import CorpusArtifactManifest
from .fulltext_fallback import (
    FulltextFallbackStore,
    build_fallback_request,
    is_fallback_eligible_direct_error,
)


def _locator(notes: list[str]) -> str | None:
    for note in notes:
        if note.startswith("fulltext_locator:"):
            return note.split(":", 1)[1]
    return None


def acquire_manifest_fulltexts(
    manifest: CorpusArtifactManifest,
    *,
    output_dir: str | Path,
    max_files: int = 10,
    max_bytes_per_file: int = 25 * 1024 * 1024,
    fixtures: dict[str, tuple[bytes, str | None]] | None = None,
    fallback_store: FulltextFallbackStore | None = None,
    target_snapshot_id: str | None = None,
    fallback_provenance_refs: list[str] | None = None,
) -> dict[str, Any]:
    fixtures = fixtures or {}
    attempted = acquired = validated = 0
    errors: list[dict[str, Any]] = []
    fallback_requests: list[dict[str, Any]] = []

    for artifact in manifest.artifacts:
        if attempted >= max_files:
            break

        # Reuse already-proven local full text. A validated artifact with a
        # durable local file and content hash is terminal for this acquisition
        # pass; reacquiring it wastes the bounded budget and can overwrite
        # evidence used by a frozen/descendant TargetWorld lineage.
        if (
            artifact.acquisition_state == "validated_artifact"
            and artifact.local_ref
            and artifact.content_hash
            and Path(artifact.local_ref).is_file()
        ):
            continue

        url = _locator(artifact.notes)
        if not url:
            continue
        attempted += 1
        fx = fixtures.get(url)
        result = acquire_explicit_fulltext(
            url,
            output_dir=output_dir,
            max_bytes=max_bytes_per_file,
            fixture_bytes=fx[0] if fx else None,
            fixture_content_type=fx[1] if fx else None,
        )
        status = str(result.get("status") or "")
        if status in ("validated", "acquired_unvalidated"):
            acquired += 1
            artifact.local_ref = result.get("path")
            artifact.content_hash = result.get("sha256")
            artifact.acquisition_state = (
                "validated_artifact"
                if status == "validated"
                else "acquired_unvalidated"
            )
            artifact.notes.append(
                f"transport_size_bytes:{result.get('size_bytes')}"
            )
            if status == "validated":
                validated += 1
                continue

            validation = result.get("validation") or {}
            validation_reason = str(
                validation.get("reason") or "unvalidated_artifact"
            )
            error = {
                "source_ref": artifact.source_ref,
                "doi": artifact.doi,
                **result,
                "error_code": validation_reason,
                "error": f"validation_failed:{validation_reason}",
            }
            errors.append(error)
        else:
            artifact.notes.append(
                f"fulltext_acquisition_failed:{result.get('error')}"
            )
            error = {
                "source_ref": artifact.source_ref,
                "doi": artifact.doi,
                **result,
            }
            errors.append(error)

        if (
            fallback_store is not None
            and target_snapshot_id
            and is_fallback_eligible_direct_error(error)
        ):
            request = build_fallback_request(
                target_snapshot_id=target_snapshot_id,
                target_corpus_id=manifest.target_id,
                artifact=artifact,
                direct_error=error,
                provenance_refs=fallback_provenance_refs,
            )
            stored = fallback_store.put_request(request)
            artifact.acquisition_state = "fallback_requested"
            artifact.notes.append(
                f"fulltext_fallback_request:{stored['request_id']}"
            )
            artifact.notes.append(
                f"fulltext_fallback_trigger:{error.get('error_code')}"
            )
            fallback_requests.append(stored)

    return {
        "manifest": manifest,
        "attempted": attempted,
        "acquired": acquired,
        "validated": validated,
        "errors": errors,
        "fallback_requests": fallback_requests,
        "complete": attempted > 0 and validated == attempted,
    }
