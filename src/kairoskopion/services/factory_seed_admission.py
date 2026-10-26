"""P3i: one fail-closed admission review at the existing Factory/Artikl boundary.

NOT a second Factory or a mutation API. Existing OpportunityGraphStore.put()
continues to reject *all* direct ArticleSeed author/science promotions. This
reviewer proves that the owner-private Factory source, original P3 holdout,
claim-level independent oracle, and two separately authenticated decisions
refer to exactly the same candidate. Passing means 'OWNER_REVIEW_ELIGIBLE',
not 'AUTHOR_APPROVED_ARTICLE', and can never send a journal submission.

The owner/author signing keys and trusted SHA pins MUST originate outside the
candidate/LLM-controlled workset. This code cannot authenticate the host itself.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import json
from pathlib import Path
from typing import Any, Mapping

from .factory_scientific_source_pin import readback_factory_scientific_source_pin
from .p3h_original_science_binding import verify_original_p3h_source_oracle_binding
from .scientific_evidence_consistency import audit_empirical_claim


_SCHEMA = "AI4SCI_FACTORY_AUTHOR_CONSENT_V1"
_MAX = 100_000


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _decode(raw: bytes | None) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX:
        raise ValueError("signed author receipt absent")
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError("duplicate signed author receipt field")
            out[k] = v
        return out
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                     parse_constant=lambda _: (_ for _ in ()).throw(
                         ValueError("nonfinite receipt number")))
    if not isinstance(obj, dict):
        raise ValueError("signed author receipt must be JSON object")
    return obj


def _consent(
    *,
    role: str,
    raw: bytes | None,
    owner_key: bytes | None,
    trusted_sha256: str | None,
    case_id: str,
    seed_id: str,
    revision: str,
    packet_sha256: str,
) -> bool:
    """HMAC validates an already-issued receipt; never issues one.

    Keys are loaded by the privileged owner runtime, not accepted from model
    output. Caller-controlled keys can pass unit tests but are NOT trust anchors.
    """
    if (not isinstance(owner_key, bytes) or len(owner_key) < 32
            or not isinstance(trusted_sha256, str)
            or len(trusted_sha256) != 64):
        return False
    if not isinstance(raw, bytes) or sha256(raw).hexdigest() != trusted_sha256:
        return False
    try:
        obj = _decode(raw)
    except (ValueError, UnicodeError, json.JSONDecodeError, TypeError):
        return False
    expected = {
        "schema": _SCHEMA,
        "case_id": case_id,
        "seed_id": seed_id,
        "revision": revision,
        "packet_sha256": packet_sha256,
        "role": role,
        "decision": "ACCEPT",
    }
    if any(obj.get(k) != v for k, v in expected.items()):
        return False
    if set(obj) != set(expected) | {"signature"}:
        return False
    signature = obj.get("signature")
    if not isinstance(signature, str) or len(signature) != 64:
        return False
    expected_signature = hmac.new(
        owner_key, _canonical(expected), "sha256"
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def assess_factory_seed_admission(
    *,
    seed_id: str,
    revision: str,
    case_id: str,
    claim_classification: str | None,
    factory_root: str | Path,
    factory_source_id: str,
    factory_source_bytes: bytes,
    owner_expected_factory_receipt_sha256: str | None,
    experiment_root: str | Path,
    owner_expected_lock_sha256: str | None,
    owner_expected_replay_oracle_sha256: str | None,
    owner_expected_numeric_oracle_sha256: str | None,
    experimental_dataset: str | None,
    scientific_packet_bytes: bytes | None,
    owner_expected_packet_sha256: str | None,
    claim_oracle_bytes: bytes | None,
    owner_expected_claim_oracle_sha256: str | None,
    model_response_bytes: bytes | None,
    author_receipt_bytes: bytes | None = None,
    coauthor_receipt_bytes: bytes | None = None,
    owner_author_receipt_sha256: str | None = None,
    owner_coauthor_receipt_sha256: str | None = None,
    owner_author_verification_key: bytes | None = None,
    owner_coauthor_verification_key: bytes | None = None,
) -> dict[str, Any]:
    """Nonmutating composition; no claim may bypass a missing classification.

    The science oracle is a *claim-level* packet in the existing
    scientific_evidence_consistency schema, distinct from the previous P3c
    aggregate oracle. Both are necessary: P3c proves original source lineage,
    claim-level oracle checks this candidate's particular conclusion.
    """
    problems = []
    source_pin = None
    p3 = None
    science = None

    if not all(isinstance(v, str) and v.strip()
               for v in (seed_id, revision, case_id, factory_source_id)):
        problems.append("CANDIDATE_IDENTITY_UNRESOLVED")
    if claim_classification != "EMPIRICAL":
        problems.append("CLAIM_CLASSIFICATION_NOT_TRUSTED_OR_NOT_EMPIRICAL")
    if not owner_expected_factory_receipt_sha256:
        problems.append("OWNER_FACTORY_RECEIPT_PIN_MISSING")
    else:
        try:
            source_pin = readback_factory_scientific_source_pin(
                factory_storage_root=factory_root,
                case_id=case_id,
                source_id=factory_source_id,
                source_bytes=factory_source_bytes,
                owner_expected_stage_receipt_sha256=owner_expected_factory_receipt_sha256,
            )
        except (OSError, ValueError, TypeError, KeyError):
            problems.append("FACTORY_SOURCE_PIN_REJECTED")
    if not all((owner_expected_lock_sha256,
                owner_expected_replay_oracle_sha256,
                owner_expected_numeric_oracle_sha256)):
        problems.append("ORIGINAL_NUMERIC_ORACLE_PINS_MISSING")
    else:
        try:
            p3 = verify_original_p3h_source_oracle_binding(
                experiment_root=experiment_root,
                owner_expected_lock_sha256=owner_expected_lock_sha256,
                owner_expected_replay_oracle_sha256=owner_expected_replay_oracle_sha256,
                owner_expected_numeric_oracle_sha256=owner_expected_numeric_oracle_sha256,
            )
        except (OSError, ValueError, TypeError, KeyError):
            problems.append("ORIGINAL_NUMERIC_ORACLE_BINDING_REJECTED")

    try:
        # The dataset selector is not an independent source witness; it merely
        # selects which already pinned original dataset this claim must match.
        if p3 is None or experimental_dataset not in ("SONAR", "IONOSPHERE"):
            raise ValueError("original dataset identity unavailable")
        data_name = experimental_dataset.lower() + "_UCI_original.csv"
        path = Path(experiment_root).resolve() / "evaldrift_P3" / data_name
        if path.is_symlink() or not path.is_file():
            raise ValueError("original source missing")
        original = path.read_bytes()
        original_sha = sha256(original).hexdigest()
        if original_sha != p3["source_hashes"][experimental_dataset]:
            raise ValueError("dataset original bytes not pinned")
        science = audit_empirical_claim(
            packet_bytes=scientific_packet_bytes,
            expected_packet_sha256=owner_expected_packet_sha256,
            source_bytes=original,
            expected_source_sha256=original_sha,
            oracle_bytes=claim_oracle_bytes,
            expected_oracle_sha256=owner_expected_claim_oracle_sha256,
            model_response_bytes=model_response_bytes,
        )
        if science["status"] != "STRUCTURED_EVIDENCE_PASSED":
            problems.append("CLAIM_LEVEL_SCIENTIFIC_WARRANT_NOT_PASSED")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        problems.append("CLAIM_LEVEL_SCIENTIFIC_WARRANT_NOT_PASSED")
    packet_sha = (sha256(scientific_packet_bytes).hexdigest()
                  if isinstance(scientific_packet_bytes, bytes) else "")
    consents = {
        "AUTHOR": _consent(
            role="AUTHOR", raw=author_receipt_bytes,
            owner_key=owner_author_verification_key,
            trusted_sha256=owner_author_receipt_sha256,
            case_id=case_id, seed_id=seed_id, revision=revision,
            packet_sha256=packet_sha,
        ),
        "COAUTHOR": _consent(
            role="COAUTHOR", raw=coauthor_receipt_bytes,
            owner_key=owner_coauthor_verification_key,
            trusted_sha256=owner_coauthor_receipt_sha256,
            case_id=case_id, seed_id=seed_id, revision=revision,
            packet_sha256=packet_sha,
        ),
    }
    for role, matched in consents.items():
        if not matched:
            problems.append(role + "_SIGNATURE_OR_DECISION_NOT_VERIFIED")
    blockers = sorted(set(problems))
    return {
        "schema": "AI4SCI_FACTORY_SEED_ADMISSION_REVIEW_V1",
        "case_id": case_id,
        "seed_id": seed_id,
        "revision": revision,
        "status": "OWNER_REVIEW_ELIGIBLE" if not blockers else "BLOCKED",
        "blockers": blockers,
        "factory_source_pin": source_pin,
        "original_p3h_oracle_bound": p3 is not None,
        "claim_level_science_status": science["status"] if science else "BLOCKED",
        "author_consent_signed": consents["AUTHOR"],
        "coauthor_consent_signed": consents["COAUTHOR"],
        "article_seed_created": False,
        "world_mutation": "NONE",
        "external_send": "DISABLED",
        "publication_authority": "NONE",
        "finalization": "OWNER_RUNTIME_ONLY",
    }
