"""Operator-only, offline import of the verified private W12 research archive.

No Drive OAuth in this CLI, no implicit user creation, no API write route and
no editorial submission. The owner-provided ZIP must already be on disk.
Example:
  python scripts/import_w12_private_research.py \
    --zip PRIVATE.zip --user-id user_000000000000 \
    --zip-sha256 <owner-verified-sha256> \
    --xlsx-sha256 <owner-verified-sha256>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from kairoskopion.api.auth import get_data_dir
from kairoskopion.kairon_provider.w12_private_runtime import (
    W12AdmissionError, research_stage_projection, stage_private_research,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Owner-private W12 research stage (not Article admission)")
    parser.add_argument("--zip", required=True, type=Path, help="Authorized local private research ZIP")
    parser.add_argument("--user-id", required=True, help="Existing authenticated user_<12 hex> workspace")
    parser.add_argument("--zip-sha256", required=True, help="Pinned SHA256 of authorized ZIP bytes")
    parser.add_argument("--xlsx-sha256", required=True, help="Pinned SHA256 of original W12 XLSX")
    parser.add_argument("--data-dir", type=Path, help="Override KAIROSKOPION_DATA_DIR")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"user_[a-f0-9]{12}", args.user_id):
        parser.error("existing normalized user_<12 hex> workspace id required")
    data_dir = args.data_dir or get_data_dir()
    root = data_dir / "users" / args.user_id
    if not root.is_dir() or root.is_symlink():
        parser.error("user workspace must already exist; never create an identity from a source ZIP")
    try:
        receipt = stage_private_research(
            args.zip, root,
            expected_archive_sha256=args.zip_sha256,
            expected_source_sha256=args.xlsx_sha256,
        )
        projection = research_stage_projection(root, limit=1)
    except W12AdmissionError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    # Print only hashes/counts. Private source rows and author contact fields
    # never leave the user's local storage in this operator receipt.
    print(json.dumps({
        "status": receipt["status"],
        "sourceSha256": receipt["source_sha256"],
        "archiveSha256": receipt["archive_sha256"],
        "sourceRowsStaged": projection["sourceRowsStaged"],
        "researchRouteCount": projection["researchRouteCount"],
        "editorialRoutesQualified": 0,
        "artiklArticlesAdmitted": 0,
        "externalSubmissions": 0,
        "userScoped": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
