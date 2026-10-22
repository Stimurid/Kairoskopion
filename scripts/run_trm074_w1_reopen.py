"""Replay previously sourced W1 manual objections as author-gated Kairon events."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.services.talk_corpus_reopen import propose_w1_return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--case-id", default="T3-TALK-20261019")
    args = parser.parse_args()
    try:
        receipt = propose_w1_return(args.storage_root, args.case_id)
    except (ValueError, KeyError, OSError) as exc:
        print(f"TRM074_W1_REOPEN_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
