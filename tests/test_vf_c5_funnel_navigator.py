"""VF-C5 tests — venue_funnel_navigator: 8-layer walk + activation rule."""

from __future__ import annotations

import pytest

from kairoskopion.enums import VenueFunnelLayer, VenueSourceCategory
from kairoskopion.schema import VenueProfilePackage
from kairoskopion.services.venue_funnel_navigator import (
    LAYER_ORDER,
    LAYER_SOURCE_ALLOWLIST,
    SUBOBJECT_TO_LAYER,
    is_source_allowed_at_layer,
    validate_activation_rule,
    walk_funnel,
)
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry


# ---------------------------------------------------------------------------
# Activation rule
# ---------------------------------------------------------------------------

class TestActivationRule:
    def test_layer_order_is_8(self):
        assert len(LAYER_ORDER) == 8
        assert LAYER_ORDER[0] == VenueFunnelLayer.UNIVERSE.value
        assert LAYER_ORDER[-1] == VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value

    def test_every_layer_has_allowlist(self):
        for layer in LAYER_ORDER:
            assert layer in LAYER_SOURCE_ALLOWLIST
            assert len(LAYER_SOURCE_ALLOWLIST[layer]) > 0

    def test_corpus_layer_allows_only_d_g_h(self):
        # Canon §3: published_corpus_hull comes from D corpus + G API + H fulltext
        allowed = LAYER_SOURCE_ALLOWLIST[
            VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value
        ]
        assert VenueSourceCategory.D_CORPUS.value in allowed
        assert VenueSourceCategory.G_METADATA_API.value in allowed
        assert VenueSourceCategory.H_FULL_TEXT_RESOLVER.value in allowed
        # Categories that CANNOT populate corpus hull authoritatively
        assert VenueSourceCategory.J_TACIT_SIGNAL.value not in allowed
        assert VenueSourceCategory.A_JOURNAL_SITE.value not in allowed

    def test_editorial_board_layer_excludes_corpus_only_sources(self):
        allowed = LAYER_SOURCE_ALLOWLIST[
            VenueFunnelLayer.EDITORIAL_BOARD_CLOUD.value
        ]
        assert VenueSourceCategory.E_EDITORIAL_BOARD.value in allowed
        # H is full-text only — never authoritative for board
        assert VenueSourceCategory.H_FULL_TEXT_RESOLVER.value not in allowed

    def test_is_source_allowed_at_layer(self):
        # D corpus at PUBLISHED_CORPUS_HULL — allowed
        assert is_source_allowed_at_layer(
            VenueSourceCategory.D_CORPUS.value,
            VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value,
        ) is True
        # J tacit at PUBLISHED_CORPUS_HULL — NOT allowed
        assert is_source_allowed_at_layer(
            VenueSourceCategory.J_TACIT_SIGNAL.value,
            VenueFunnelLayer.PUBLISHED_CORPUS_HULL.value,
        ) is False

    def test_none_source_category_defaults_to_allowed(self):
        # Honest default: cannot judge unknown source; do not hard-fail
        assert is_source_allowed_at_layer(
            None, VenueFunnelLayer.UNIVERSE.value,
        ) is True

    def test_unknown_layer_forward_compat(self):
        # Unknown layer name → True (don't block forward-compat additions)
        assert is_source_allowed_at_layer(
            VenueSourceCategory.D_CORPUS.value, "future_layer_99",
        ) is True


class TestActivationRuleValidator:
    def test_clean_vpkg_no_violations(self):
        v = VenueProfilePackage(
            canonical_name="V",
            openalex_source_id="S1",
            published_corpus_hull_id="pch_1",
            editorial_board_cloud_id="ebc_1",
            completeness={
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
            },
        )
        assert validate_activation_rule(v.to_dict()) == []

    def test_corpus_hull_without_source_is_violation(self):
        v = VenueProfilePackage(
            canonical_name="V",
            completeness={"PublishedCorpusHull": "present"},
        )
        violations = validate_activation_rule(v.to_dict())
        assert len(violations) == 1
        assert "PublishedCorpusHull" in violations[0]
        assert "D/G" in violations[0]

    def test_board_cloud_without_id_is_violation(self):
        v = VenueProfilePackage(
            canonical_name="V",
            completeness={"EditorialBoardCloud": "partial"},
        )
        violations = validate_activation_rule(v.to_dict())
        assert any("EditorialBoardCloud" in vio for vio in violations)


# ---------------------------------------------------------------------------
# Funnel walk
# ---------------------------------------------------------------------------

def _make_vpkg(name, **overrides):
    # Identity is unique per name so the registry's by-name / by-ISSN
    # index does not merge two distinct test VPKGs into one record.
    name_slug = "".join(c for c in name if c.isalnum())[:8] or "X"
    base = dict(
        canonical_name=name,
        issns=overrides.pop("issns", [f"{abs(hash(name)) % 9000 + 1000}-{abs(hash(name)) % 9000 + 1000:04d}"]),
        venue_type=overrides.pop("venue_type", "journal"),
        discovery_clusters=overrides.pop("discovery_clusters", []),
        openalex_source_id=overrides.pop("openalex_source_id", f"S_{name_slug}"),
        homepage_url=overrides.pop("homepage_url", f"https://{name_slug}.example/"),
        completeness=overrides.pop("completeness", {
            "VenueIdentity": "present",
            "PublishedCorpusHull": "present",
            "EditorialBoardCloud": "present",
            "FormalSubmissionProfile": "missing",
        }),
        published_corpus_hull_id=overrides.pop(
            "published_corpus_hull_id", f"pch_{name_slug}"
        ),
        editorial_board_cloud_id=overrides.pop(
            "editorial_board_cloud_id", f"ebc_{name_slug}"
        ),
    )
    base.update(overrides)
    return VenueProfilePackage(**base)


def _mavrinsky_article():
    return {
        "disciplinary_registers": [
            "continental_philosophy",
            "philosophy_of_technology",
            "media_philosophy",
        ],
        "tribes_present": {
            "Deleuze_Guattari": "constructive",
            "Foucault": "constructive",
            "Lacan": "foil",
        },
    }


class TestFunnelWalk:
    def test_walk_emits_8_layers(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "Foucault Studies",
            discovery_clusters=["continental_philosophy", "foucault_studies"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        assert len(out["layers"]) == 8
        assert out["_layers_walked"] == LAYER_ORDER
        assert out["stopping_reason"] == "walked all 8 layers"

    def test_universe_drops_venue_without_directory_id(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        # Has identity
        reg.upsert(_make_vpkg("Real Journal",
                               discovery_clusters=["continental_philosophy"]))
        # No directory id at all
        reg.upsert(_make_vpkg(
            "Phantom Journal",
            issns=[],
            openalex_source_id=None,
            homepage_url=None,
            discovery_clusters=["continental_philosophy"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l1 = out["layers"][0]
        assert l1["candidates_in"] == 2
        assert l1["candidates_out"] == 1
        assert len(l1["candidates_dropped"]) == 1

    def test_disciplinary_filter_keeps_continental_drops_unrelated(
        self, tmp_path,
    ):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "Continental Venue",
            discovery_clusters=["continental_philosophy"],
        ))
        reg.upsert(_make_vpkg(
            "Math Venue",
            discovery_clusters=["mathematics", "number_theory"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l2 = out["layers"][1]  # DISCIPLINARY_REGIME
        # Both pass L1 (have directory id), L2 should drop Math
        assert l2["candidates_in"] == 2
        assert l2["candidates_out"] == 1

    def test_tribe_filter_drops_no_tribe_signal(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "Foucault Studies",
            discovery_clusters=["continental_philosophy", "foucault_studies"],
        ))
        reg.upsert(_make_vpkg(
            "Generic Phil Journal",
            discovery_clusters=["continental_philosophy"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l3 = out["layers"][2]  # TRIBE_SCHOOL
        # Foucault Studies has 'foucault' in clusters/name; Generic doesn't
        assert l3["candidates_in"] == 2
        # Both pass L2; L3 drops "Generic Phil Journal"
        assert l3["candidates_out"] == 1

    def test_venue_class_filter_can_drop_proceedings(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "Foucault Studies",
            discovery_clusters=["continental_philosophy", "foucault_studies"],
            venue_type="journal",
        ))
        reg.upsert(_make_vpkg(
            "Some Proceedings",
            discovery_clusters=["continental_philosophy", "foucault"],
            venue_type="proceedings",
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
            submission_scenario={"allowed_venue_types": ["journal"]},
        )
        l4 = out["layers"][3]  # VENUE_CLASS
        # Proceedings dropped
        assert any(
            "proceedings" in r.lower()
            for r in l4["drop_reasons"].values()
        ) or l4["candidates_out"] < l4["candidates_in"]

    def test_l6_section_special_issue_is_informational_not_dropping(
        self, tmp_path,
    ):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "Foucault Studies",
            discovery_clusters=["continental_philosophy", "foucault_studies"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l6 = out["layers"][5]
        # Current VPKGs don't carry section_model_ids — L6 must NOT drop
        # them; should surface as a note.
        assert l6["candidates_in"] == l6["candidates_out"]
        assert any("VF-C4" in n for n in l6["notes"])

    def test_l7_drops_vpkg_without_board_cloud(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "With Board",
            discovery_clusters=["continental_philosophy", "foucault"],
            completeness={
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
            },
        ))
        reg.upsert(_make_vpkg(
            "No Board",
            discovery_clusters=["continental_philosophy", "foucault"],
            editorial_board_cloud_id=None,
            completeness={
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "missing",
            },
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l7 = out["layers"][6]
        assert l7["candidates_in"] == 2
        assert l7["candidates_out"] == 1

    def test_l8_drops_vpkg_without_corpus_hull(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "With Corpus",
            discovery_clusters=["continental_philosophy", "foucault"],
            completeness={
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
            },
        ))
        reg.upsert(_make_vpkg(
            "No Corpus",
            discovery_clusters=["continental_philosophy", "foucault"],
            published_corpus_hull_id=None,
            completeness={
                "PublishedCorpusHull": "missing",
                "EditorialBoardCloud": "present",
            },
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        l8 = out["layers"][7]
        assert l8["candidates_in"] == 2
        assert l8["candidates_out"] == 1

    def test_funnel_floor_stops_early(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg(
            "V", discovery_clusters=["continental_philosophy", "foucault"],
        ))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
            funnel_floor=VenueFunnelLayer.JOURNAL_ENVELOPE.value,
        )
        assert len(out["layers"]) == 5  # L1..L5
        assert out["_layers_walked"][-1] == VenueFunnelLayer.JOURNAL_ENVELOPE.value
        assert "funnel_floor" in out["stopping_reason"]

    def test_final_shortlist_matches_last_layer_kept(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        v = _make_vpkg(
            "Foucault Studies",
            discovery_clusters=["continental_philosophy", "foucault_studies"],
        )
        reg.upsert(v)
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        # The one VPKG survives all 8 layers
        assert out["final_shortlist"] == [v.venue_profile_package_id]

    def test_activation_violations_surfaced(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        # VPKG claims PublishedCorpusHull=present but has no source id
        bad = VenueProfilePackage(
            canonical_name="Bad",
            issns=["1234-5678"],
            discovery_clusters=["continental_philosophy", "foucault"],
            completeness={
                "VenueIdentity": "present",
                "PublishedCorpusHull": "present",
                "EditorialBoardCloud": "present",
            },
            editorial_board_cloud_id="ebc_x",
        )
        reg.upsert(bad)
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        # Violations must show up on at least one layer
        total = sum(out["activation_summary"].values())
        assert total > 0

    def test_article_filter_constraints_recorded(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        reg.upsert(_make_vpkg("V"))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        af = out["article_filter_applied"]
        assert "continental_philosophy" in af["disciplinary_registers"]
        assert "Foucault" in af["constructive_tribes"]
        assert "Lacan" not in af["constructive_tribes"]  # foil, not constructive

    def test_empty_registry_walks_cleanly(self, tmp_path):
        reg = VenueProfileRegistry(storage_root=str(tmp_path))
        out = walk_funnel(
            article_model=_mavrinsky_article(),
            vpkg_registry=reg,
        )
        for layer in out["layers"]:
            assert layer["candidates_in"] == 0
            assert layer["candidates_out"] == 0
        assert out["final_shortlist"] == []


class TestSubobjectLayerMapping:
    def test_every_subobject_maps_to_a_known_layer(self):
        for sub, layer in SUBOBJECT_TO_LAYER.items():
            assert layer in LAYER_ORDER, \
                f"{sub} maps to unknown layer {layer}"
