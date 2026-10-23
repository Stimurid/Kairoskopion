"""Stage a bounded TRM-073 research packet; never create/send an article."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.services.trm073_research_stage import stage_research_packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-packet", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = stage_research_packet(args.research_packet, args.storage_root)
    except (ValueError, KeyError, OSError) as exc:
        print(f"TRM073_RESEARCH_STAGE_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
