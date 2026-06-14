"""Coverage and roundtrip tests for Venue Funnel v1 enums (VF-C1).

These enums are the foundation for downstream sprints VF-C2 (the
`VenueProfilePackage` dataclass) through VF-C9 (mirror gold). They
must:

- expose exactly the value counts mandated by the canon,
- carry distinct string values (no collisions across an enum),
- roundtrip through `str(value)` reconstruction (`Enum(str_value)`),
- preserve membership semantics (`value in Enum.__members__.values()`).

The canonical reference is
`docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md`; the operational rubric
is `benchmarks/golden/venue_source_layer_map.md`.
"""

from __future__ import annotations

import json

import pytest

from kairoskopion.enums import (
    CacheMissCategory,
    VenueFunnelLayer,
    VenueSourceCategory,
)


# --- Cardinality (canon mandates exact counts) ---

def test_venue_funnel_layer_has_eight_values():
    assert len(list(VenueFunnelLayer)) == 8


def test_venue_source_category_has_ten_values():
    assert len(list(VenueSourceCategory)) == 10


def test_cache_miss_category_has_four_values():
    assert len(list(CacheMissCategory)) == 4


# --- Membership: each canonical name is present ---

@pytest.mark.parametrize(
    "name",
    [
        "UNIVERSE",
        "DISCIPLINARY_REGIME",
        "TRIBE_SCHOOL",
        "VENUE_CLASS",
        "JOURNAL_ENVELOPE",
        "SECTION_SPECIAL_ISSUE",
        "EDITORIAL_BOARD_CLOUD",
        "PUBLISHED_CORPUS_HULL",
    ],
)
def test_funnel_layer_member_present(name):
    assert name in VenueFunnelLayer.__members__


@pytest.mark.parametrize(
    "name",
    [
        "A_JOURNAL_SITE",
        "B_PUBLISHER",
        "C_INDEXER_REGISTRY",
        "D_CORPUS",
        "E_EDITORIAL_BOARD",
        "F_CORPUS_AUTHORS",
        "G_METADATA_API",
        "H_FULL_TEXT_RESOLVER",
        "I_CFP_SOCIETY_CHANNEL",
        "J_TACIT_SIGNAL",
    ],
)
def test_source_category_member_present(name):
    assert name in VenueSourceCategory.__members__


@pytest.mark.parametrize(
    "name",
    ["ABSENT", "STALE", "WEAK_EVIDENCE", "FRESH_SUFFICIENT"],
)
def test_cache_miss_category_member_present(name):
    assert name in CacheMissCategory.__members__


# --- Source category A–J prefix discipline ---

def test_source_category_values_carry_alpha_prefix():
    """Canon §3 labels A–J are part of the wire format; the prefix is
    not cosmetic — it is how the rubric and the funnel cross-reference."""
    expected_prefixes = list("ABCDEFGHIJ")
    for member, expected in zip(VenueSourceCategory, expected_prefixes):
        assert member.value.startswith(f"{expected}_"), (
            f"{member.name} value {member.value!r} must start with "
            f"{expected}_ to match canon §3 labelling"
        )


# --- Uniqueness within each enum ---

@pytest.mark.parametrize(
    "enum_cls",
    [VenueFunnelLayer, VenueSourceCategory, CacheMissCategory],
)
def test_enum_values_are_unique(enum_cls):
    values = [m.value for m in enum_cls]
    assert len(values) == len(set(values)), (
        f"{enum_cls.__name__} has duplicate values"
    )


# --- String roundtrip: Enum(value) reconstructs the same member ---

@pytest.mark.parametrize(
    "enum_cls",
    [VenueFunnelLayer, VenueSourceCategory, CacheMissCategory],
)
def test_enum_string_roundtrip(enum_cls):
    for member in enum_cls:
        assert enum_cls(member.value) is member


# --- JSON roundtrip: serialise as string, deserialise via Enum(...) ---

@pytest.mark.parametrize(
    "enum_cls",
    [VenueFunnelLayer, VenueSourceCategory, CacheMissCategory],
)
def test_enum_json_roundtrip(enum_cls):
    for member in enum_cls:
        encoded = json.dumps(member.value)
        decoded = enum_cls(json.loads(encoded))
        assert decoded is member


# --- str subclass behaviour preserved (matches every other enum here) ---

@pytest.mark.parametrize(
    "enum_cls",
    [VenueFunnelLayer, VenueSourceCategory, CacheMissCategory],
)
def test_enum_is_str_subclass(enum_cls):
    """Domain enums are `str, Enum` so that they round-trip through
    JSON / dict serialisation without explicit conversion. VF-C2
    relies on this (`VenueProfilePackage.to_dict` stores the raw
    string value)."""
    for member in enum_cls:
        assert isinstance(member, str)
        assert member == member.value


# --- Negative case: unknown value raises ValueError, not silent passthrough ---

@pytest.mark.parametrize(
    "enum_cls,bad_value",
    [
        (VenueFunnelLayer, "not_a_layer"),
        (VenueSourceCategory, "K_invented_category"),
        (CacheMissCategory, "uncached"),
    ],
)
def test_enum_rejects_unknown_value(enum_cls, bad_value):
    with pytest.raises(ValueError):
        enum_cls(bad_value)


# --- Ordering of VenueFunnelLayer matches canon §1 narrowing direction ---

def test_funnel_layer_declaration_order_matches_canon_narrowing():
    """Canon §1 walks from broad (universe) to concrete (corpus hull).
    The enum declaration order is normative for any code that iterates
    layers top-down (e.g. VF-C5 navigator). Lock it here."""
    actual = [m.name for m in VenueFunnelLayer]
    expected = [
        "UNIVERSE",
        "DISCIPLINARY_REGIME",
        "TRIBE_SCHOOL",
        "VENUE_CLASS",
        "JOURNAL_ENVELOPE",
        "SECTION_SPECIAL_ISSUE",
        "EDITORIAL_BOARD_CLOUD",
        "PUBLISHED_CORPUS_HULL",
    ]
    assert actual == expected


# --- Ordering of VenueSourceCategory matches canon §3 A–J labelling ---

def test_source_category_declaration_order_matches_canon_labelling():
    actual = [m.name for m in VenueSourceCategory]
    expected = [
        "A_JOURNAL_SITE",
        "B_PUBLISHER",
        "C_INDEXER_REGISTRY",
        "D_CORPUS",
        "E_EDITORIAL_BOARD",
        "F_CORPUS_AUTHORS",
        "G_METADATA_API",
        "H_FULL_TEXT_RESOLVER",
        "I_CFP_SOCIETY_CHANNEL",
        "J_TACIT_SIGNAL",
    ]
    assert actual == expected
