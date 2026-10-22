"""T3-TALK: actual installed LitOps Source registry -> WhiteCrow read-only import.

Required operator environment:
    LITOPS_SKIP_DOTENV=1
    LITOPS_ROOT=<isolated, owner-private directory>
    PYTHONPATH=src;<installed-LitOps-code-root>;<installed-WhiteCrow-code-root>
No manuscript synthesis, external submissions or edits to production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.integrations.litops_bridge import admit_talk_context_into_installed_litops


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--litops-root", required=True, type=Path)
    parser.add_argument("--case-id", default="T3-TALK-20261019")
    args = parser.parse_args()
    try:
        result = admit_talk_context_into_installed_litops(
            args.storage_root, args.litops_root, args.case_id,
        )
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print("TRM074_LITOPS_WHITE_CROW_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
