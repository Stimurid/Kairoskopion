"""Upgrade corpus artifacts from locator state to acquired/validated files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.venue.fulltext_fetch import acquire_explicit_fulltext
from .models import CorpusArtifactManifest


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
) -> dict[str, Any]:
    fixtures = fixtures or {}
    attempted = acquired = validated = 0
    errors: list[dict[str, Any]] = []

    for artifact in manifest.artifacts:
        if attempted >= max_files:
            break
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
        if result.get("status") in ("validated", "acquired_unvalidated"):
            acquired += 1
            artifact.local_ref = result.get("path")
            artifact.content_hash = result.get("sha256")
            artifact.acquisition_state = (
                "validated_artifact" if result.get("status") == "validated"
                else "acquired_unvalidated"
            )
            artifact.notes.append(f"transport_size_bytes:{result.get('size_bytes')}")
            if result.get("status") == "validated":
                validated += 1
        else:
            artifact.notes.append(f"fulltext_acquisition_failed:{result.get('error')}")
            errors.append({"source_ref": artifact.source_ref, **result})

    return {
        "manifest": manifest,
        "attempted": attempted,
        "acquired": acquired,
        "validated": validated,
        "errors": errors,
        "complete": attempted > 0 and acquired == attempted,
    }
