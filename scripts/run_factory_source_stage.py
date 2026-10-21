"""Single explicit no-submit entry for existing Kairoskopion source/research organs.

This performs permitted local staging, not an autonomous Indago search,
WhiteCrow scientific judgment, Artikl author approval or publication send.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from kairoskopion.services.corpus_factory_entry import execute_factory_source_stage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--research-packet", type=Path, action="append", default=[],
                        help="Repeat for bounded independent W2/W3 research waves")
    parser.add_argument("--litops-root", type=Path)
    parser.add_argument("--venue-route-packet", type=Path, action="append", default=[],
                        help="Owner-private source/venue W12 research-route input; repeat for each route")
    parser.add_argument("--native-capture-root", type=Path,
                        help="Private TRM040 native Docs store for sources marked capture_transport=native_docs")
    parser.add_argument("--manual-w1-reopen", action="store_true")
    parser.add_argument("--owner-prior-research-receipt", type=Path,
                        help="Previously executed owner-private research receipt, held and verified")
    parser.add_argument("--owner-prior-graph-root", type=Path,
                        help="Exact private previous Kairon graph root, NOT a new research engine")
    args = parser.parse_args()
    if bool(args.owner_prior_research_receipt) != bool(args.owner_prior_graph_root):
        parser.error("owner prior-research receipt and graph root must be supplied together")
    try:
        receipt = execute_factory_source_stage(
            args.manifest, args.storage_root,
            research_packet_paths=args.research_packet,
            venue_route_packet_paths=args.venue_route_packet,
            litops_root=args.litops_root,
            native_capture_root=args.native_capture_root,
            manual_w1_reopen=args.manual_w1_reopen,
        )
        if args.owner_prior_research_receipt:
            from kairoskopion.services.owner_prior_research_bridge import (
                import_owner_prior_science,
            )
            owner_prior = import_owner_prior_science(
                args.owner_prior_research_receipt,
                args.owner_prior_graph_root,
                args.storage_root,
            )
            receipt["owner_prior_research"] = owner_prior
            receipt["joined_factory_research_sha256"] = sha256(
                json.dumps({
                    "factory_sha256": receipt["receipt_sha256"],
                    "owner_prior_sha256": owner_prior["receipt_sha256"],
                }, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print("FACTORY_SOURCE_STAGE_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
