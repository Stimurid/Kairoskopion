"""FieldPositionModel extraction prompt families.

Two prompt families:
1. ARTICLE_FIELD_POSITION — extract article coordinates from ArticleModel + text
2. VENUE_FIELD_POSITION — extract venue coordinates from VenueModel + corpus data
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE


# ---------------------------------------------------------------------------
# Shared axis definitions (used in both prompts)
# ---------------------------------------------------------------------------

_AXES_REFERENCE = """\
## Axis definitions

### Group 1: Disciplinary positioning
- **discipline_vector**: dict of discipline names → float (0.0–1.0).
  Not one discipline — a weighted membership across several.
  Use the most specific label the text supports. Prefer narrow sub-fields
  over broad umbrella terms.
- **subdiscipline_address**: {primary, niche, working_area} — hierarchical
  address within the primary discipline.

### Group 2: Epistemic framework affiliation
- **framework_affiliation_vector**: dict of framework/lineage names → float
  (0.0–1.0). Epistemic frameworks the article affiliates with, as
  evidenced in the text. Derive from evidence, not from a fixed list.
  May be empty if not applicable.
- **citation_network_signature**: {expected_references, typically_cite,
  never_cite, notable_omissions, bridge_frameworks, self_citation_norm}.
  "expected_references" = key works or authors the text's positioning implies
  should appear. "notable_omissions" = references that the stated positioning
  would normally entail but are absent — absence may or may not be
  significant depending on field norms.
- **opponents_and_foils**: {explicit_opponents, implicit_foils,
  published_polemics, avoided_polemics}.

### Group 3: Argument profile
- **argument_move_vector**: dict of move types → float (0.0–1.0).
  Weighted presence of argument moves used in the text: how the article
  structures its contribution (e.g. problem statement, model building,
  comparative analysis, critique, synthesis, systematic review).
- **novelty_mode**: {mode, novelty_claim_strength (0.0–1.0),
  builds_on_or_opposes}.
  How the article positions its novelty contribution.
- **evidence_type_profile**: dict of evidence types → float (0.0–1.0).
  Weighted distribution of evidence kinds used in the text (e.g.
  theoretical argument, case study, quantitative data, experimental,
  archival, computational, mixed methods).

### Group 4: Methodological register
- **method_stance**: {explicit_method (bool), method_family (str),
  method_specificity (low/medium/high), empirical_component (bool)}.
  For venues add: requires_explicit_method, accepted_method_families,
  rejected_method_families.
- **formalization_level**: float (0.0–1.0).
  0.0 = free-form prose, 1.0 = fully formal/axiomatic structure.

### Group 5: Audience & Register
- **audience_level**: {expertise_required (general/educated/specialist/
  deep_specialist), presupposed_knowledge (list), accessibility_index (0.0–1.0)}.
- **language_register**: {language, register (academic_formal/academic_accessible/
  semi_popular/popular), jargon_density (0.0–1.0),
  expected_word_count_min, expected_word_count_max}.
- **genre_position**: {genre, genre_formality (0.0–1.0), sections_expected (list)}.

### Group 6: Geopolitics & Institutional context
- **geographic_affinity**: {author_region, framework_origin_region,
  target_audience_region, language_of_publication}.
  For venues add: editorial_board_regions (dict str→float),
  author_regions_published (dict str→float),
  anglophone_hegemony_index (0.0–1.0).
- **institutional_signals**: Prestige and ranking are per-database, per-year,
  per-category. Do not assign a single prestige tier. Instead populate:
  {indexing (list), open_access (str), apc_range_usd_min, apc_range_usd_max,
  review_model, typical_decision_weeks}.

### Group 7: Temporal
- **temporal_position**: {recency_of_core_references (classic/mixed/recent/
  cutting_edge), median_reference_year, reference_time_depth_years,
  field_maturity (nascent/growing/established/declining/reviving)}.
"""


# ---------------------------------------------------------------------------
# Article prompt family
# ---------------------------------------------------------------------------

ARTICLE_FIELD_POSITION_SYSTEM = """\
You are Field Position Analyst — a specialized role within Kairoskopion, \
an evidence-first publication-positioning system.

""" + _OPEN_FIELD_DOCTRINE + """

Your task: given an ArticleModel and manuscript text, produce coordinate \
values for every axis of the FieldPositionModel. The article is a POINT \
(or compact region) in academic disciplinary space.

""" + _AXES_REFERENCE + """

### Article-specific axis
- **article_readiness**: {manuscript_stage (idea/draft/presubmission/submitted/
  revision/accepted), completeness (0.0–1.0), word_count, has_abstract,
  has_bibliography, has_methods_section, formal_compliance_score (0.0–1.0)}.

## Rules

1. Every vector (discipline, framework_affiliation, argument_move, evidence_type)
   must have at least 2 components where applicable. Float values must be 0.0–1.0.
   framework_affiliation_vector may be empty if the field has no framework
   structure.
2. citation_network_signature: list expected_references the article's positioning
   implies; note notable_omissions where positioning suggests references that
   are absent.
3. Do NOT guess. If you cannot determine a value, use null and add to unknowns.
4. Be specific in naming disciplines and frameworks — generic labels are useless.
5. Vectors should sum to roughly 1.0 (soft constraint).
6. formalization_level, jargon_density, accessibility_index, novelty_claim_strength,
   genre_formality, completeness, formal_compliance_score are all 0.0–1.0.
"""

ARTICLE_FIELD_POSITION_USER_TEMPLATE = """\
Build FieldPositionModel coordinates for this article.

## ArticleModel
```json
{article_json}
```

## Manuscript text (first 8000 chars)
{manuscript_text}

Return a JSON object with all axis groups populated.
"""

ARTICLE_FIELD_POSITION_OUTPUT_SCHEMA: dict = {
    "title": "ArticleFieldPosition",
    "type": "object",
    "properties": {
        "discipline_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "subdiscipline_address": {
            "type": "object",
            "properties": {
                "primary": {"type": ["string", "null"]},
                "niche": {"type": ["string", "null"]},
                "working_area": {"type": ["string", "null"]},
            },
        },
        "framework_affiliation_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "Traditions or frameworks the article affiliates with. May be empty.",
        },
        "citation_network_signature": {
            "type": "object",
            "properties": {
                "expected_references": {"type": "array", "items": {"type": "string"}},
                "typically_cite": {"type": "array", "items": {"type": "string"}},
                "never_cite": {"type": "array", "items": {"type": "string"}},
                "notable_omissions": {"type": "array", "items": {"type": "string"}},
                "bridge_frameworks": {"type": "array", "items": {"type": "string"}},
                "self_citation_norm": {"type": ["string", "null"]},
            },
        },
        "opponents_and_foils": {
            "type": "object",
            "properties": {
                "explicit_opponents": {"type": "array", "items": {"type": "string"}},
                "implicit_foils": {"type": "array", "items": {"type": "string"}},
            },
        },
        "argument_move_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "novelty_mode": {
            "type": "object",
            "properties": {
                "mode": {"type": ["string", "null"]},
                "novelty_claim_strength": {"type": ["number", "null"]},
                "builds_on_or_opposes": {"type": ["string", "null"]},
            },
        },
        "evidence_type_profile": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "method_stance": {
            "type": "object",
            "properties": {
                "explicit_method": {"type": ["boolean", "null"]},
                "method_family": {"type": ["string", "null"]},
                "method_specificity": {"type": ["string", "null"]},
                "empirical_component": {"type": ["boolean", "null"]},
            },
        },
        "formalization_level": {"type": ["number", "null"]},
        "audience_level": {
            "type": "object",
            "properties": {
                "expertise_required": {"type": ["string", "null"]},
                "presupposed_knowledge": {"type": "array", "items": {"type": "string"}},
                "accessibility_index": {"type": ["number", "null"]},
            },
        },
        "language_register": {
            "type": "object",
            "properties": {
                "language": {"type": ["string", "null"]},
                "register": {"type": ["string", "null"]},
                "jargon_density": {"type": ["number", "null"]},
                "expected_word_count_min": {"type": ["integer", "null"]},
                "expected_word_count_max": {"type": ["integer", "null"]},
            },
        },
        "genre_position": {
            "type": "object",
            "properties": {
                "genre": {"type": ["string", "null"]},
                "genre_formality": {"type": ["number", "null"]},
                "sections_expected": {"type": "array", "items": {"type": "string"}},
            },
        },
        "geographic_affinity": {
            "type": "object",
            "properties": {
                "author_region": {"type": ["string", "null"]},
                "framework_origin_region": {"type": ["string", "null"]},
                "target_audience_region": {"type": ["string", "null"]},
                "language_of_publication": {"type": ["string", "null"]},
            },
        },
        "temporal_position": {
            "type": "object",
            "properties": {
                "recency_of_core_references": {"type": ["string", "null"]},
                "median_reference_year": {"type": ["integer", "null"]},
                "reference_time_depth_years": {"type": ["integer", "null"]},
                "field_maturity": {"type": ["string", "null"]},
            },
        },
        "article_readiness": {
            "type": "object",
            "properties": {
                "manuscript_stage": {"type": ["string", "null"]},
                "completeness": {"type": ["number", "null"]},
                "word_count": {"type": ["integer", "null"]},
                "has_abstract": {"type": ["boolean", "null"]},
                "has_bibliography": {"type": ["boolean", "null"]},
                "has_methods_section": {"type": ["boolean", "null"]},
                "formal_compliance_score": {"type": ["number", "null"]},
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": ["string", "null"]},
    },
    "required": [
        "discipline_vector", "framework_affiliation_vector",
        "argument_move_vector", "evidence_type_profile",
        "unknowns",
    ],
}


def _validate_article_fpm(parsed: dict) -> list[str]:
    warnings = []
    for vkey in ("discipline_vector", "framework_affiliation_vector",
                 "argument_move_vector", "evidence_type_profile"):
        v = parsed.get(vkey)
        if not v or not isinstance(v, dict):
            warnings.append(f"Missing or empty {vkey}")
        elif len(v) < 2:
            warnings.append(f"{vkey} has fewer than 2 components")
        else:
            for val in v.values():
                if not isinstance(val, (int, float)) or val < 0 or val > 1:
                    warnings.append(f"{vkey} contains out-of-range value: {val}")
                    break
    fl = parsed.get("formalization_level")
    if fl is not None and (not isinstance(fl, (int, float)) or fl < 0 or fl > 1):
        warnings.append(f"formalization_level out of range: {fl}")
    return warnings


ARTICLE_FIELD_POSITION_FAMILY: dict = {
    "agent_role_id": "article_field_positioner",
    "family_id": "article_field_position_v2",
    "version": "2.0",
    "system_prompt": ARTICLE_FIELD_POSITION_SYSTEM,
    "user_prompt_template": ARTICLE_FIELD_POSITION_USER_TEMPLATE,
    "output_schema": ARTICLE_FIELD_POSITION_OUTPUT_SCHEMA,
    "validator": _validate_article_fpm,
}


# ---------------------------------------------------------------------------
# Venue prompt family
# ---------------------------------------------------------------------------

VENUE_FIELD_POSITION_SYSTEM = """\
You are Venue Field Position Analyst — a specialized role within Kairoskopion, \
an evidence-first publication-positioning system.

""" + _OPEN_FIELD_DOCTRINE + """

Your task: given a VenueModel, editorial board data, published corpus data, \
and author guidelines, produce coordinate ENVELOPES for every axis of the \
FieldPositionModel. A venue is an EXTENDED REGION in academic space — \
not a point, but a range of accepted positions.

""" + _AXES_REFERENCE + """

## Venue-specific rules

1. For vector axes (discipline, framework_affiliation, argument_move,
   evidence_type): produce BOTH a center vector AND an envelope (min–max
   range per dimension). The center = what the venue typically publishes.
   The envelope = what is within scope but may be less common.
   framework_affiliation_vector and its envelope may be empty if the venue
   has no framework structure.
2. citation_network_signature for a venue:
   - expected_references → key works or authors the venue community expects
   - bridge_frameworks → cross-framework citations the venue values
   - notable_omissions → references whose absence in a submission would be
     surprising given the venue's positioning
3. institutional_signals: Prestige and ranking are per-database, per-year,
   per-category. Do not assign a single prestige tier. Fill indexing,
   open_access, apc, review_model, typical_decision_weeks from venue data.
4. geographic_affinity: fill editorial_board_regions, author_regions_published,
   anglophone_hegemony_index from editorial board and corpus data.
5. method_stance for a venue: requires_explicit_method, accepted/rejected families.
6. Do NOT guess. If venue data is insufficient for an axis, use null and
   add to unknowns. Honest unknowns are more useful than fabricated values.
7. Envelopes: [min, max] where min ≤ max. Both are 0.0–1.0.
"""

VENUE_FIELD_POSITION_USER_TEMPLATE = """\
Build FieldPositionModel coordinates (envelopes) for this venue.

## VenueModel
```json
{venue_json}
```

## Editorial Board (if available)
```json
{editorial_board_json}
```

## Published Corpus Summary (if available)
```json
{corpus_json}
```

## Author Guidelines (first 4000 chars, if available)
{guidelines_text}

Return a JSON object with all axis groups populated as venue envelopes.
"""

VENUE_FIELD_POSITION_OUTPUT_SCHEMA: dict = {
    "title": "VenueFieldPosition",
    "type": "object",
    "properties": {
        "discipline_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "Center of gravity per discipline",
        },
        "discipline_envelope": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
            },
            "description": "[min, max] range per discipline",
        },
        "subdiscipline_address": {
            "type": "object",
            "properties": {
                "primary": {"type": ["string", "null"]},
                "niche": {"type": ["string", "null"]},
                "working_area": {"type": ["string", "null"]},
            },
        },
        "framework_affiliation_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "Traditions or frameworks the venue publishes within. May be empty.",
        },
        "framework_envelope": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
            },
        },
        "citation_network_signature": {
            "type": "object",
            "properties": {
                "expected_references": {"type": "array", "items": {"type": "string"}},
                "typically_cite": {"type": "array", "items": {"type": "string"}},
                "never_cite": {"type": "array", "items": {"type": "string"}},
                "notable_omissions": {"type": "array", "items": {"type": "string"}},
                "bridge_frameworks": {"type": "array", "items": {"type": "string"}},
                "self_citation_norm": {"type": ["string", "null"]},
            },
        },
        "opponents_and_foils": {
            "type": "object",
            "properties": {
                "published_polemics": {"type": "array", "items": {"type": "string"}},
                "avoided_polemics": {"type": "array", "items": {"type": "string"}},
            },
        },
        "argument_move_vector": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "argument_move_envelope": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
            },
        },
        "novelty_mode": {
            "type": "object",
            "properties": {
                "mode": {"type": ["string", "null"]},
                "novelty_claim_strength": {"type": ["number", "null"]},
                "builds_on_or_opposes": {"type": ["string", "null"]},
            },
        },
        "evidence_type_profile": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "method_stance": {
            "type": "object",
            "properties": {
                "explicit_method": {"type": ["boolean", "null"]},
                "method_family": {"type": ["string", "null"]},
                "method_specificity": {"type": ["string", "null"]},
                "empirical_component": {"type": ["boolean", "null"]},
                "requires_explicit_method": {"type": ["boolean", "null"]},
                "accepted_method_families": {"type": "array", "items": {"type": "string"}},
                "rejected_method_families": {"type": "array", "items": {"type": "string"}},
            },
        },
        "formalization_level": {"type": ["number", "null"]},
        "audience_level": {
            "type": "object",
            "properties": {
                "expertise_required": {"type": ["string", "null"]},
                "presupposed_knowledge": {"type": "array", "items": {"type": "string"}},
                "accessibility_index": {"type": ["number", "null"]},
            },
        },
        "language_register": {
            "type": "object",
            "properties": {
                "language": {"type": ["string", "null"]},
                "register": {"type": ["string", "null"]},
                "jargon_density": {"type": ["number", "null"]},
                "expected_word_count_min": {"type": ["integer", "null"]},
                "expected_word_count_max": {"type": ["integer", "null"]},
            },
        },
        "genre_position": {
            "type": "object",
            "properties": {
                "genre": {"type": ["string", "null"]},
                "genre_formality": {"type": ["number", "null"]},
                "sections_expected": {"type": "array", "items": {"type": "string"}},
            },
        },
        "geographic_affinity": {
            "type": "object",
            "properties": {
                "author_region": {"type": ["string", "null"]},
                "framework_origin_region": {"type": ["string", "null"]},
                "target_audience_region": {"type": ["string", "null"]},
                "language_of_publication": {"type": ["string", "null"]},
                "editorial_board_regions": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
                "author_regions_published": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
                "anglophone_hegemony_index": {"type": ["number", "null"]},
            },
        },
        "institutional_signals": {
            "type": "object",
            "description": "Prestige and ranking are per-database, per-year, per-category. Do not assign a single prestige tier.",
            "properties": {
                "indexing": {"type": "array", "items": {"type": "string"}},
                "open_access": {"type": ["string", "null"]},
                "apc_range_usd_min": {"type": ["integer", "null"]},
                "apc_range_usd_max": {"type": ["integer", "null"]},
                "review_model": {"type": ["string", "null"]},
                "typical_decision_weeks": {"type": ["integer", "null"]},
            },
        },
        "temporal_position": {
            "type": "object",
            "properties": {
                "recency_of_core_references": {"type": ["string", "null"]},
                "median_reference_year": {"type": ["integer", "null"]},
                "reference_time_depth_years": {"type": ["integer", "null"]},
                "field_maturity": {"type": ["string", "null"]},
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": ["string", "null"]},
    },
    "required": [
        "discipline_vector", "discipline_envelope",
        "framework_affiliation_vector", "framework_envelope",
        "argument_move_vector", "argument_move_envelope",
        "unknowns",
    ],
}


def _validate_venue_fpm(parsed: dict) -> list[str]:
    warnings = []
    for vkey in ("discipline_vector", "framework_affiliation_vector",
                 "argument_move_vector"):
        v = parsed.get(vkey)
        if not v or not isinstance(v, dict):
            warnings.append(f"Missing or empty {vkey}")
    for ekey in ("discipline_envelope", "framework_envelope",
                 "argument_move_envelope"):
        e = parsed.get(ekey)
        if not e or not isinstance(e, dict):
            warnings.append(f"Missing or empty {ekey}")
        elif isinstance(e, dict):
            for dim, rng in e.items():
                if not isinstance(rng, list) or len(rng) != 2:
                    warnings.append(f"{ekey}[{dim}] is not [min, max]")
                elif rng[0] > rng[1]:
                    warnings.append(f"{ekey}[{dim}] min > max: {rng}")
    return warnings


VENUE_FIELD_POSITION_FAMILY: dict = {
    "agent_role_id": "venue_field_positioner",
    "family_id": "venue_field_position_v2",
    "version": "2.0",
    "system_prompt": VENUE_FIELD_POSITION_SYSTEM,
    "user_prompt_template": VENUE_FIELD_POSITION_USER_TEMPLATE,
    "output_schema": VENUE_FIELD_POSITION_OUTPUT_SCHEMA,
    "validator": _validate_venue_fpm,
}
