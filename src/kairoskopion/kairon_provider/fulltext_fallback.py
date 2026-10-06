"""Provider-neutral full-text fallback seam for TRM-070.

This module does not implement Indago provider tactics. It gives Kairoskopion a
typed, durable request/return boundary so an explicit official/OA acquisition
failure can continue as a separate fallback attempt without source laundering.

The current Indago P0/browser body is discovery/location + challenge/human
resume infrastructure. FOUND_LOCATION is therefore deliberately distinct from
FOUND_ARTIFACT, and no return can make an artifact readable in Kairoskopion
without a separately accessible validated artifact transport.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import CorpusArtifact


RESULT_STATES = {
    "FOUND_ARTIFACT",
    "FOUND_LOCATION",
    "HUMAN_ACTION_REQUIRED",
    "HOST_POLICY_BLOCKED",
    "PROVIDER_BLOCKED",
    "NOT_FOUND",
    "TRANSIENT_FAILURE",
    "TRANSPORT_DEFECT",
    "IDENTITY_CONFLICT",
}

ACQUISITION_GOALS = {
    "LOCATE",
    "ACQUIRE_IF_RUNTIME_AUTHORIZED",
    "RESUME_HUMAN_ACTION",
}

FALLBACK_ELIGIBLE_ERROR_CODES = {
    "http_401",
    "http_403",
    "http_407",
    "http_429",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class FulltextAcquisitionRequest:
    request_id: str
    target_snapshot_id: str
    target_corpus_id: str
    source_ref: str
    article_identity: dict[str, Any] = field(default_factory=dict)
    requested_source_class: str = "INDAGO"
    source_priority: list[str] = field(default_factory=list)
    acquisition_goal: str = "ACQUIRE_IF_RUNTIME_AUTHORIZED"
    known_locations: list[str] = field(default_factory=list)
    prior_attempts: list[dict[str, Any]] = field(default_factory=list)
    current_artifact_state: str = "metadata_only"
    provenance_refs: list[str] = field(default_factory=list)
    idempotency_key: str = ""
    created_at: str = field(default_factory=_now)
    schema_version: str = "fulltext-acquisition-request-v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FulltextEvidenceReturn:
    request_id: str
    provider_class: str
    provider_attempt_id: str
    result_state: str
    provider_instance: str | None = None
    resolved_article_identity: dict[str, Any] = field(default_factory=dict)
    exact_source_satisfied: bool | None = None
    reorientation_history: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    location_ref: str | None = None
    human_action: dict[str, Any] | None = None
    artifact_ref: str | None = None
    content_hash: str | None = None
    media_type: str | None = None
    byte_size: int | None = None
    acquisition_path: str | None = None
    validation_state: str | None = None
    extraction_state: str | None = None
    source_registration_ref: str | None = None
    observed_at: str = field(default_factory=_now)
    schema_version: str = "fulltext-evidence-return-v1"
    return_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _article_identity(artifact: CorpusArtifact) -> dict[str, Any]:
    return {
        "doi": artifact.doi,
        "title": artifact.title,
        "authors": list(artifact.authors or []),
        "year": artifact.year,
        "source_ref": artifact.source_ref,
    }


def _known_locations(artifact: CorpusArtifact) -> list[str]:
    out: list[str] = []
    for note in artifact.notes or []:
        if note.startswith("fulltext_locator:"):
            value = note.split(":", 1)[1].strip()
            if value:
                out.append(value)
    return list(dict.fromkeys(out))


def is_fallback_eligible_direct_error(error: dict[str, Any]) -> bool:
    code = str(error.get("error_code") or "").strip().lower()
    return code in FALLBACK_ELIGIBLE_ERROR_CODES


def build_fallback_request(
    *,
    target_snapshot_id: str,
    target_corpus_id: str,
    artifact: CorpusArtifact,
    direct_error: dict[str, Any],
    requested_source_class: str = "INDAGO",
    acquisition_goal: str = "ACQUIRE_IF_RUNTIME_AUTHORIZED",
    provenance_refs: list[str] | None = None,
) -> FulltextAcquisitionRequest:
    if acquisition_goal not in ACQUISITION_GOALS:
        raise ValueError(f"unsupported acquisition_goal: {acquisition_goal}")

    identity = _article_identity(artifact)
    prior_attempt = {
        "provider_class": "OFFICIAL_OR_EXPLICIT_LOCATOR",
        "provider_instance": direct_error.get("url"),
        "result_state": "PROVIDER_BLOCKED",
        "error_code": direct_error.get("error_code"),
        "http_status": direct_error.get("http_status"),
        "failure_reason": direct_error.get("error"),
    }
    semantic_key = {
        "target_snapshot_id": target_snapshot_id,
        "target_corpus_id": target_corpus_id,
        "source_ref": artifact.source_ref,
        "article_identity": identity,
        "requested_source_class": requested_source_class,
        "acquisition_goal": acquisition_goal,
    }
    idem = _digest(semantic_key)
    return FulltextAcquisitionRequest(
        request_id=f"fulltextreq:{idem[:20]}",
        target_snapshot_id=target_snapshot_id,
        target_corpus_id=target_corpus_id,
        source_ref=artifact.source_ref,
        article_identity=identity,
        requested_source_class=requested_source_class,
        acquisition_goal=acquisition_goal,
        known_locations=_known_locations(artifact),
        prior_attempts=[prior_attempt],
        current_artifact_state=artifact.acquisition_state,
        provenance_refs=list(provenance_refs or []),
        idempotency_key=idem,
    )


def normalize_evidence_return(
    request: FulltextAcquisitionRequest,
    payload: dict[str, Any],
) -> FulltextEvidenceReturn:
    state = str(payload.get("result_state") or "").strip().upper()
    if state not in RESULT_STATES:
        raise ValueError(f"unsupported result_state: {state or '<empty>'}")

    provider_class = str(payload.get("provider_class") or "").strip()
    attempt_id = str(payload.get("provider_attempt_id") or "").strip()
    if not provider_class:
        raise ValueError("provider_class is required")
    if not attempt_id:
        raise ValueError("provider_attempt_id is required")

    location_ref = payload.get("location_ref")
    human_action = payload.get("human_action")
    artifact_ref = payload.get("artifact_ref")
    content_hash = payload.get("content_hash")
    validation_state = payload.get("validation_state")
    extraction_state = payload.get("extraction_state")
    source_registration_ref = payload.get("source_registration_ref")
    failure_reason = payload.get("failure_reason")

    if state == "FOUND_LOCATION" and not location_ref:
        raise ValueError("FOUND_LOCATION requires location_ref")
    if state == "HUMAN_ACTION_REQUIRED" and not isinstance(human_action, dict):
        raise ValueError("HUMAN_ACTION_REQUIRED requires human_action")
    if state == "FOUND_ARTIFACT":
        missing = [
            name for name, value in (
                ("artifact_ref", artifact_ref),
                ("content_hash", content_hash),
                ("validation_state", validation_state),
                ("extraction_state", extraction_state),
                ("source_registration_ref", source_registration_ref),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "FOUND_ARTIFACT requires " + ", ".join(missing)
            )
    if state in {
        "HOST_POLICY_BLOCKED",
        "PROVIDER_BLOCKED",
        "TRANSIENT_FAILURE",
        "TRANSPORT_DEFECT",
        "IDENTITY_CONFLICT",
    } and not failure_reason:
        raise ValueError(f"{state} requires failure_reason")

    semantic = {
        "request_id": request.request_id,
        "provider_class": provider_class,
        "provider_instance": payload.get("provider_instance"),
        "provider_attempt_id": attempt_id,
        "result_state": state,
        "resolved_article_identity": payload.get("resolved_article_identity") or {},
        "exact_source_satisfied": payload.get("exact_source_satisfied"),
        "reorientation_history": payload.get("reorientation_history") or [],
        "evidence_refs": payload.get("evidence_refs") or [],
        "failure_reason": failure_reason,
        "location_ref": location_ref,
        "human_action": human_action,
        "artifact_ref": artifact_ref,
        "content_hash": content_hash,
        "media_type": payload.get("media_type"),
        "byte_size": payload.get("byte_size"),
        "acquisition_path": payload.get("acquisition_path"),
        "validation_state": validation_state,
        "extraction_state": extraction_state,
        "source_registration_ref": source_registration_ref,
    }
    return FulltextEvidenceReturn(
        **semantic,
        return_id=f"fulltextret:{_digest(semantic)[:20]}",
    )


def apply_evidence_return(
    artifact: CorpusArtifact,
    evidence: FulltextEvidenceReturn,
) -> CorpusArtifact:
    """Apply only machine-visible acquisition state; never fabricate readability."""
    state_map = {
        "FOUND_ARTIFACT": "fallback_artifact_returned",
        "FOUND_LOCATION": "fallback_location_found",
        "HUMAN_ACTION_REQUIRED": "fallback_human_action_required",
        "HOST_POLICY_BLOCKED": "fallback_host_policy_blocked",
        "PROVIDER_BLOCKED": "fallback_provider_blocked",
        "NOT_FOUND": "fallback_not_found",
        "TRANSIENT_FAILURE": "fallback_transient_failure",
        "TRANSPORT_DEFECT": "fallback_transport_defect",
        "IDENTITY_CONFLICT": "fallback_identity_conflict",
    }
    artifact.acquisition_state = state_map[evidence.result_state]
    if evidence.result_state == "FOUND_ARTIFACT" and evidence.content_hash:
        artifact.content_hash = evidence.content_hash

    notes = list(artifact.notes or [])
    additions = [
        f"fulltext_fallback_return:{evidence.return_id}",
        f"fulltext_fallback_state:{evidence.result_state}",
        f"fulltext_fallback_provider:{evidence.provider_class}",
    ]
    if evidence.provider_instance:
        additions.append(
            f"fulltext_fallback_provider_instance:{evidence.provider_instance}"
        )
    if evidence.location_ref:
        additions.append(f"fulltext_fallback_location:{evidence.location_ref}")
    if evidence.source_registration_ref:
        additions.append(
            f"fulltext_source_registration:{evidence.source_registration_ref}"
        )
    if evidence.failure_reason:
        additions.append(f"fulltext_fallback_failure:{evidence.failure_reason}")
    artifact.notes = list(dict.fromkeys(notes + additions))
    # local_ref is intentionally untouched. A remote/provider return is not a
    # locally readable artifact until a separate artifact transport/ingest step
    # makes bytes available and validates them inside Kairoskopion.
    return artifact


class FulltextFallbackStore:
    """Append-only request/return store with idempotent event replay."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "fulltext_fallback"
        self.requests = self.root / "requests"
        self.returns = self.root / "returns"
        self.requests.mkdir(parents=True, exist_ok=True)
        self.returns.mkdir(parents=True, exist_ok=True)

    def _request_path(self, request_id: str) -> Path:
        return self.requests / f"{_safe_id(request_id)}.json"

    def _return_dir(self, request_id: str) -> Path:
        path = self.returns / _safe_id(request_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def put_request(self, request: FulltextAcquisitionRequest) -> dict[str, Any]:
        data = request.to_dict()
        path = self._request_path(request.request_id)
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("idempotency_key") != request.idempotency_key:
                raise ValueError("request id collision with different idempotency key")
            return existing
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
        return data

    def get_request(self, request_id: str) -> FulltextAcquisitionRequest | None:
        path = self._request_path(request_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("request_id") != request_id:
            return None
        return FulltextAcquisitionRequest(**data)

    def list_requests(
        self,
        *,
        target_snapshot_id: str | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for path in sorted(self.requests.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if target_snapshot_id and data.get("target_snapshot_id") != target_snapshot_id:
                continue
            request_id = data.get("request_id")
            latest = self.get_latest_return(str(request_id)) if request_id else None
            out.append({
                **data,
                "latest_return": latest.to_dict() if latest else None,
            })
        return out

    def put_return(
        self,
        request_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = self.get_request(request_id)
        if request is None:
            raise ValueError("fulltext fallback request not found")
        evidence = normalize_evidence_return(request, payload)
        root = self._return_dir(request_id)
        path = root / f"{_safe_id(evidence.return_id)}.json"
        data = evidence.to_dict()
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
        return data

    def list_returns(self, request_id: str) -> list[dict[str, Any]]:
        root = self._return_dir(request_id)
        out: list[dict[str, Any]] = []
        for path in root.glob("*.json"):
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        out.sort(key=lambda x: (x.get("observed_at") or "", x.get("return_id") or ""))
        return out

    def get_latest_return(
        self,
        request_id: str,
    ) -> FulltextEvidenceReturn | None:
        rows = self.list_returns(request_id)
        if not rows:
            return None
        return FulltextEvidenceReturn(**rows[-1])
