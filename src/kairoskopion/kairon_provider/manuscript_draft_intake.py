"""TRM-074: fail-closed import of *actually produced* manuscript text.

This module is NOT a manuscript writer, scientific reviewer, acceptance authority,
or submission actuator. It attaches externally produced draft bytes to the
existing publication Factory's evidence identity discipline. Outputs HOLD only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .publication_runner import EvidenceBlocked, atomic_write, read_bound, sha256


SCHEMA = "trimurti-manuscript-draft-intake-v1"
STATUS = "DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED"


def _required(data: dict, name: str, expected_type: type) -> object:
    value = data.get(name)
    if not isinstance(value, expected_type) or not value:
        raise EvidenceBlocked(f"missing_or_invalid_{name}")
    return value


def ingest(*, manifest_path: Path, input_root: Path, output_root: Path,
           trusted_source_sha256: str, trusted_science_sha256: str) -> dict:
    """Every replay re-reads all three bound artifacts before accepting a receipt.

    The input root is a private case workspace, not the public source repository.
    No source content is included in emitted receipts.
    """
    if not manifest_path.is_file():
        raise EvidenceBlocked("manifest_missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise EvidenceBlocked("wrong_intake_schema")
    if manifest.get("evidence_mode") != "REAL":
        raise EvidenceBlocked("real_source_binding_required")
    if manifest.get("author_gate") != "HOLD":
        raise EvidenceBlocked("author_gate_must_be_HOLD")
    if manifest.get("submission_enabled") is not False:
        raise EvidenceBlocked("submission_must_be_disabled")
    if manifest.get("scientific_novelty_accepted") is not False:
        raise EvidenceBlocked("novelty_approval_not_accepted_from_intake")
    if manifest.get("article_seed_author_approved") is not False:
        raise EvidenceBlocked("article_seed_not_approved_from_intake")
    case_id = _required(manifest, "case_id", str)
    claim_id = _required(manifest, "claim_id", str)
    producer = _required(manifest, "producer_ref", str)
    route = _required(manifest, "route_id", str)
    objects = manifest.get("artifacts")
    if not isinstance(objects, dict) or set(objects) != {"source", "science", "draft"}:
        raise EvidenceBlocked("exact_source_science_draft_required")
    for kind in ("source", "science", "draft"):
        row = objects[kind]
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise EvidenceBlocked(f"invalid_{kind}_artifact")
    source = read_bound(input_root, objects["source"])
    science = read_bound(input_root, objects["science"])
    draft = read_bound(input_root, objects["draft"])
    # These operator-pinned digests are supplied separately from the producer's manifest.
    # A matching model-authored manifest never constitutes source authority.
    for label, expected, actual in (("source", trusted_source_sha256, sha256(source)),
                                    ("science", trusted_science_sha256, sha256(science))):
        if not isinstance(expected, str) or len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise EvidenceBlocked("trusted_" + label + "_sha256_invalid")
        if expected != actual:
            raise EvidenceBlocked("trusted_" + label + "_sha256_mismatch")
    if len(source) < 500 or len(science) < 500 or len(draft) < 4000:
        raise EvidenceBlocked("source_science_or_draft_too_small")
    try:
        text = draft.decode("utf-8")
        science_record = json.loads(science.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as err:
        raise EvidenceBlocked("draft_or_science_decode_failed") from err
    if any(s not in text for s in ("# ", "## ", "## ")):
        raise EvidenceBlocked("draft_markdown_structure_missing")
    if "W12_added" in science_record and science_record["W12_added"] != 0:
        raise EvidenceBlocked("science_packet_illicit_route_promotion")
    if science_record.get("author_gate") != "HOLD":
        raise EvidenceBlocked("science_packet_author_gate_mismatch")
    if science_record.get("external_send") is not False:
        raise EvidenceBlocked("science_packet_external_send_mismatch")
    if manifest.get("source_original_sha256") != sha256(source):
        raise EvidenceBlocked("original_author_source_sha_mismatch")
    # Claim identity and author approval never flow from the model-generated draft.
    receipt = {
        "schema": "trimurti-manuscript-draft-receipt-v1",
        "case_id": case_id,
        "claim_id": claim_id,
        "route_id": route,
        "producer_ref": producer,
        "source_sha256": sha256(source),
        "science_sha256": sha256(science),
        "draft_sha256": sha256(draft),
        "draft_bytes": len(draft),
        "draft_utf8_word_count": len(text.split()),
        "manifest_sha256": sha256(manifest_path.read_bytes()),
        "status": STATUS,
        "scientific_qa": "NOT_PERFORMED_BY_INTAKE",
        "editorial_qa": "NOT_PERFORMED_BY_INTAKE",
        "source_provenance_claim": "HASH_MATCH_ONLY",
        "independent_scientific_novelty_accepted": False,
        "article_seed_author_approved": False,
        "manuscript_go": False,
        "author_gate": "HOLD",
        "external_send": False,
        "world_mutated": False,
        "new_w12_routes": 0,
        "production_deployed": False,
    }
    payload = json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "draft-intake-receipt.json"
    if path.is_file():
        previous = path.read_bytes()
        if previous != payload:
            raise EvidenceBlocked("immutable_existing_draft_receipt_conflict")
    else:
        atomic_write(path, payload)
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser(description="Import a produced draft into Trimurti under HOLD")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--trusted-source-sha256", required=True,
                    help="Expected SHA from external authoritative source registry, not this manifest")
    ap.add_argument("--trusted-science-sha256", required=True,
                    help="Expected SHA from independently pinned scientific registry")
    args = ap.parse_args()
    try:
        result = ingest(manifest_path=args.manifest, input_root=args.input_root,
                        output_root=args.output_root,
                        trusted_source_sha256=args.trusted_source_sha256,
                        trusted_science_sha256=args.trusted_science_sha256)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (EvidenceBlocked, ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "external_send": False, "article_seed_author_approved": False},
                         ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
