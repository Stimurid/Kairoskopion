"""Operator-seeded canonical venues for Mavrinsky-class articles.

This is NOT discovery. The list below is operator-curated, bounded,
and explicitly tagged as `OPERATOR_SEED_CANONICAL` so a future audit
can tell at a glance:

    > "this VPKG entered the registry as an operator seed, not as a
    > DOAJ-keyword discovery result"

Rules followed:
  - canonical_name + venue_type are always set;
  - ISSN is included ONLY when the operator has high confidence the
    pair (canonical_name, ISSN) is correct; otherwise omitted and the
    enricher resolves OpenAlex source by title;
  - publisher / languages / discovery_clusters are populated where
    high-confidence; missing fields stay `UNKNOWN_NOT_SEEDED`;
  - no editor names, no impact factors, no Q-tier claims;
  - no homepage URLs are seeded — those come from OpenAlex Sources
    during enrichment, where they carry `evidence_status:
    metadata_api_openalex`.

After seeding, the standard enricher
(`services.venue_profile_enricher.enrich_registry`) attaches OpenAlex
ids and corpus hulls.
"""

from __future__ import annotations

import logging
from typing import Any

from ..schema import VenueProfilePackage

logger = logging.getLogger(__name__)


SEED_ORIGIN = "OPERATOR_SEED_CANONICAL"


# Each entry: high-confidence canonical_name + structural metadata only.
# `issns` ONLY when the operator vouches for the (name, ISSN) pairing.
# Cluster tags drive token-detection in the selector.
CANONICAL_SEEDS: list[dict[str, Any]] = [
    # --- Core philosophy / technology / AI ---
    {
        "canonical_name": "Philosophy & Technology",
        "publisher": "Springer",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["2210-5433", "2210-5441"],
        "discovery_clusters": [
            "philosophy_of_technology", "philtech_canon",
            "continental_adjacent",
        ],
    },
    {
        "canonical_name": "AI and Ethics",
        "publisher": "Springer",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["2730-5953"],
        "discovery_clusters": [
            "philosophy_of_technology", "applied_ethics", "ai_ethics",
        ],
    },
    {
        "canonical_name": "Ethics and Information Technology",
        "publisher": "Springer",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["1388-1957", "1572-8439"],
        "discovery_clusters": [
            "philosophy_of_technology", "applied_ethics", "information_ethics",
        ],
    },
    {
        "canonical_name": "Techné: Research in Philosophy and Technology",
        "publisher": "Philosophy Documentation Center",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["1091-8264"],
        "discovery_clusters": [
            "philosophy_of_technology", "philtech_canon",
            "postphenomenology", "continental_adjacent",
        ],
    },
    {
        "canonical_name": "Minds and Machines",
        "publisher": "Springer",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["0924-6495", "1572-8641"],
        "discovery_clusters": [
            "philosophy_of_mind", "philosophy_of_ai", "analytic_adjacent",
        ],
    },
    # --- STS / society / digital ---
    {
        "canonical_name": "Big Data & Society",
        "publisher": "SAGE",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["2053-9517"],
        "discovery_clusters": [
            "sts", "critical_data_studies", "platform_studies",
        ],
    },
    {
        "canonical_name": "Science, Technology, & Human Values",
        "publisher": "SAGE",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["0162-2439", "1552-8251"],
        "discovery_clusters": ["sts", "sociotechnical"],
    },
    {
        "canonical_name": "Social Studies of Science",
        "publisher": "SAGE",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["0306-3127", "1460-3659"],
        "discovery_clusters": ["sts", "actor_network"],
    },
    {
        "canonical_name": "Engaging Science, Technology, and Society",
        "publisher": "Society for Social Studies of Science",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["2413-8053"],
        "discovery_clusters": ["sts", "engaged_sts"],
    },
    {
        "canonical_name": "Digital Humanities Quarterly",
        "publisher": "Alliance of Digital Humanities Organizations",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["1938-4122"],
        "discovery_clusters": [
            "digital_humanities", "media_studies_adjacent",
        ],
    },
    # --- Continental / critical / theory-adjacent ---
    {
        "canonical_name": "Foucault Studies",
        "publisher": "University of Copenhagen",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["1832-5203"],
        "discovery_clusters": [
            "continental_philosophy", "foucault_studies", "critical_theory",
        ],
    },
    {
        "canonical_name": "Theory, Culture & Society",
        "publisher": "SAGE",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["0263-2764", "1460-3616"],
        "discovery_clusters": [
            "critical_theory", "continental_adjacent", "social_theory",
        ],
    },
    {
        "canonical_name": "New Media & Society",
        "publisher": "SAGE",
        "languages": ["en"],
        "venue_type": "journal",
        "issns": ["1461-4448", "1461-7315"],
        "discovery_clusters": [
            "media_studies", "platform_studies", "digital_society",
        ],
    },
    # --- Russian-language / regional philosophy candidates ---
    # ISSNs included only where high-confidence; otherwise enricher resolves.
    {
        "canonical_name": "Логос",
        "publisher": "Институт Гайдара",
        "languages": ["ru"],
        "venue_type": "journal",
        "issns": ["0869-5377"],
        "discovery_clusters": [
            "ru_philosophy", "continental_philosophy_ru",
            "critical_theory_ru",
        ],
    },
    {
        "canonical_name": "Вопросы философии",
        "publisher": "Российская академия наук",
        "languages": ["ru"],
        "venue_type": "journal",
        "issns": ["0042-8744"],
        "discovery_clusters": [
            "ru_philosophy", "core_ru_philosophy", "vak_perechen_candidate",
        ],
    },
    {
        "canonical_name": "Эпистемология и философия науки",
        "publisher": "Институт философии РАН",
        "languages": ["ru"],
        "venue_type": "journal",
        "issns": ["1811-833X"],
        "discovery_clusters": [
            "ru_philosophy", "philosophy_of_science_ru",
            "vak_perechen_candidate",
        ],
    },
    {
        "canonical_name": "Философские науки",
        "publisher": "Гуманитарий",
        "languages": ["ru"],
        "venue_type": "journal",
        "issns": ["0235-1188"],
        "discovery_clusters": [
            "ru_philosophy", "philosophical_sciences_ru",
            "vak_perechen_candidate",
        ],
    },
    {
        "canonical_name": "Социология власти",
        "publisher": "РАНХиГС",
        "languages": ["ru"],
        "venue_type": "journal",
        "issns": ["2074-0492", "2413-144X"],
        "discovery_clusters": [
            "ru_sociology", "critical_theory_ru", "continental_adjacent_ru",
        ],
    },
    {
        "canonical_name": "Galactica Media: Journal of Media Studies",
        "publisher": "Volga Region Scientific Center",
        "languages": ["ru", "en"],
        "venue_type": "journal",
        "issns": ["2658-7734"],
        "discovery_clusters": [
            "media_studies_ru", "digital_humanities_ru",
            "continental_adjacent_ru",
        ],
    },
    # Russian Journal of Philosophical Sciences — distinct or same as
    # Философские науки? Not pinned. Mark UNKNOWN.
    {
        "canonical_name": "Russian Journal of Philosophical Sciences",
        "publisher": None,
        "languages": ["en"],
        "venue_type": "journal",
        "issns": [],
        "discovery_clusters": [
            "ru_philosophy", "philosophical_sciences_ru",
        ],
        "unknowns": [
            "may resolve to same source as Философские науки; "
            "enricher must check via title",
        ],
    },
]


def build_seed_vpkg(seed: dict[str, Any]) -> VenueProfilePackage:
    """Turn one seed dict into a VPKG with origin tagging.

    Origin lives in two places:
      - `discovery_sources` carries the OPERATOR_SEED_CANONICAL marker;
      - `evidence_status` is `operator_seed_canonical` to differentiate
        from `external_claim` (DOAJ keyword discovery) and from
        `metadata_api_openalex` (post-enrichment).
    """
    base_unknowns = [
        "homepage_url: not seeded — resolver may attach from OpenAlex Sources",
        "EditorialBoardCloud: not seeded — requires board-page discovery sprint",
        "FormalSubmissionProfile: not seeded — requires guidelines-URL discovery",
        "publication_regime: not seeded",
    ]
    if seed.get("unknowns"):
        base_unknowns = base_unknowns + list(seed["unknowns"])

    initial_completeness = {
        "VenueIdentity": "partial",
        "VenueFieldPosition": "missing",
        "PublishedCorpusHull": "missing",
        "EditorialBoardCloud": "missing",
        "FormalSubmissionProfile": "missing",
        "CitationExpectationProfile": "missing",
        "SourceEvidencePacket": "partial",
    }

    return VenueProfilePackage(
        canonical_name=seed["canonical_name"],
        issns=list(seed.get("issns") or []),
        publisher=seed.get("publisher"),
        languages=list(seed.get("languages") or []),
        venue_type=seed.get("venue_type", "journal"),
        discovery_sources=[SEED_ORIGIN],
        discovery_clusters=list(seed.get("discovery_clusters") or []),
        completeness=initial_completeness,
        confidence="medium",
        evidence_status="operator_seed_canonical",
        unknowns=base_unknowns,
        warnings=[],
    )


def seed_canonical_venues_into_registry(registry) -> dict[str, Any]:
    """Upsert all canonical seeds into the registry.

    Idempotent: if a VPKG already exists under the same canonical_name
    or ISSN, the upsert merges and preserves the existing id. The
    `OPERATOR_SEED_CANONICAL` marker is appended to `discovery_sources`
    rather than overwritten.
    """
    summary: dict[str, Any] = {
        "total_seeds": len(CANONICAL_SEEDS),
        "newly_inserted": 0,
        "merged_into_existing": 0,
        "per_seed": [],
    }
    for seed in CANONICAL_SEEDS:
        pre_existing = registry.find(
            canonical_name=seed["canonical_name"],
            issn=next(iter(seed.get("issns") or []), None),
        )
        vpkg = build_seed_vpkg(seed)
        result = registry.upsert(vpkg)
        rec = {
            "canonical_name": seed["canonical_name"],
            "venue_profile_package_id": result.venue_profile_package_id,
            "merged_into_existing": bool(pre_existing),
            "had_seeded_issns": bool(seed.get("issns")),
        }
        summary["per_seed"].append(rec)
        if pre_existing:
            summary["merged_into_existing"] += 1
        else:
            summary["newly_inserted"] += 1
    return summary
