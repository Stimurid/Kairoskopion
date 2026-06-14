"""Mavrinsky real venue selection v1.

Step 1: enrich the existing durable VenueProfileRegistry
  (C1 ISSN → OpenAlex identity; C3 corpus hull build for newly-resolved
  ids; homepage discovery as side-effect of OpenAlex source record).

Step 2: run the v1 selection (ArticleModel × VPKG × evidence) and
write durable artefacts under private_inputs/runs/.

NO LLM. NO broad discovery. NO new architecture. Operates on the
15 VPKGs from pass #002 plus any identity/corpus enrichment.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.services.mavrinsky_venue_selection import (  # noqa: E402
    run_selection_over_registry,
)
from kairoskopion.services.venue_profile_enricher import enrich_registry  # noqa: E402
from kairoskopion.services.venue_profile_registry import (  # noqa: E402
    VenueProfileRegistry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("selection-v1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--storage-root", default=".kairoskopion")
    ap.add_argument("--skip-enrich", action="store_true")
    ap.add_argument("--corpus-max-works", type=int, default=30)
    args = ap.parse_args()

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    reg = VenueProfileRegistry(storage_root=args.storage_root)
    log.info("Registry loaded: %d VPKGs", reg.count())

    if not args.skip_enrich:
        log.info("=== Enrichment pass (C1 identity + C3 corpus) ===")
        enrich_summary = enrich_registry(
            reg, do_identity=True, do_corpus=True,
            corpus_max_works=args.corpus_max_works,
        )
        (out / "enrich_summary.json").write_text(
            json.dumps(enrich_summary, ensure_ascii=False, indent=2,
                       default=str),
            encoding="utf-8",
        )
        log.info(
            "Enrichment: id_attached=%d ambiguous=%d corpus_built=%d",
            enrich_summary["identity_attached"],
            enrich_summary["identity_ambiguous"],
            enrich_summary["corpus_built"],
        )

    log.info("=== Selection v1 ===")
    artefacts = run_selection_over_registry(reg, output_dir=out)
    print("\n=== BUCKETS ===")
    print(json.dumps(artefacts["_meta"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
