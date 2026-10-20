"""Bounded bridge: fetch real publisher HTML for a W12 route's scope,
submission-policy and published-opponent evidence through the EXISTING
``acquire_explicit_fulltext`` adapter, and write the capture_manifest JSON
that ``--venue-route-packet`` (trm073_w12_route_stage) expects.

This does not search the web, does not bypass access controls, and does
not certify a route: it only replaces manual curl-and-hash curation of
three pinned URLs with one reproducible command. A blocked or failed
capture is reported as such, never silently marked validated.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kairoskopion.services.w12_capture_manifest_builder import build_capture_manifest


def _parse_target(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"--target must be KEY=URL, got {spec!r}")
    key, url = spec.split("=", 1)
    return key.strip(), url.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", action="append", default=[], required=True,
        help="Repeat as KEY=URL, e.g. --target SCOPE=https://... "
             "--target GUIDELINES=https://... --target OPPONENT=https://...",
    )
    parser.add_argument("--output-dir", type=Path, required=True,
                         help="Owner-private root to store acquired HTML artifacts")
    parser.add_argument("--manifest-out", type=Path, required=True,
                         help="Path to write the capture_manifest JSON")
    args = parser.parse_args()
    try:
        targets = {}
        for spec in args.target:
            key, url = _parse_target(spec)
            if key in targets:
                raise ValueError(f"duplicate --target key: {key}")
            targets[key] = url
        report = build_capture_manifest(
            targets, output_dir=args.output_dir, manifest_path=args.manifest_out,
        )
    except (ValueError, OSError) as exc:
        print("W12_CAPTURE_MANIFEST_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if not report["all_validated"]:
        blocked = {
            k: v for k, v in report["captures"].items() if v["status"] != "validated"
        }
        print(
            "W12_CAPTURE_MANIFEST_PARTIAL: "
            + json.dumps(blocked, ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
