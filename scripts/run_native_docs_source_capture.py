"""Use installed TRM040 read-only Native Docs transport to capture one Drive ID.

Host operator supplies TRIMURTI_DOCS_FETCH_COMMAND or an already authorized
read-only Docs token. Output is a source-receipt fragment, never source text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from kairoskopion.integrations.native_docs_capture import capture_native_doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--owner-capture-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = capture_native_doc(
            args.source_id, args.source_url, args.owner_capture_root,
        )
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print("TRM074_NATIVE_DOCS_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    # No source bytes, OAuth tokens, tab text or external file content printed.
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
