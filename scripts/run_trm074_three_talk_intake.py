"""No-submit TRM-074 operator replay, backed by existing source intake."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.services.talk_corpus_intake import run_case


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_case(args.manifest, args.storage_root)
    except (ValueError, KeyError, OSError) as exc:
        print(f"TRM074_FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
