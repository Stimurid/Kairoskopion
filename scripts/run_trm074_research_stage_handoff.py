"""No-submit TRM-074 corpus evidence -> existing Kairon OpportunityGraphStore."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.services.talk_corpus_research_bridge import export_talk_research_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default="T3-TALK-20261019")
    parser.add_argument("--storage-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export_talk_research_evidence(args.storage_root, args.case_id)
    except (ValueError, KeyError, OSError) as exc:
        print(f"TRM074_RESEARCH_BRIDGE_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
