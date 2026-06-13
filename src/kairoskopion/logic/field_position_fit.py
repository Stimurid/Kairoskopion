"""Compute fit between article and venue FieldPositionModels.

Article FPM = point (vectors are centers).
Venue FPM = region (vectors + envelopes).
Fit = per-axis containment/distance, NOT a single score.
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Per-axis status
# ---------------------------------------------------------------------------

CONTAINED = "contained"
ADJACENT = "adjacent"
OUTSIDE = "outside"
UNKNOWN = "unknown"

ADJACENT_THRESHOLD = 0.3


def _vector_distance_to_envelope(
    point: dict[str, float],
    center: dict[str, float],
    envelope: dict[str, list[float]] | None,
) -> tuple[str, float, str | None]:
    """Compare a point vector against a venue envelope.

    Returns (status, distance, closest_edge_dimension).
    """
    if not point or not center:
        return UNKNOWN, 0.0, None

    if envelope is None:
        all_dims = set(point) | set(center)
        if not all_dims:
            return UNKNOWN, 0.0, None
        sq_sum = sum(
            (point.get(d, 0.0) - center.get(d, 0.0)) ** 2
            for d in all_dims
        )
        dist = math.sqrt(sq_sum / len(all_dims))
        if dist < 0.1:
            return CONTAINED, dist, None
        if dist < ADJACENT_THRESHOLD:
            return ADJACENT, dist, None
        return OUTSIDE, dist, None

    max_overshoot = 0.0
    worst_dim = None
    all_dims = set(point) | set(envelope)

    for dim in all_dims:
        val = point.get(dim, 0.0)
        rng = envelope.get(dim)
        if rng is None or len(rng) < 2:
            continue
        lo, hi = rng[0], rng[1]
        if val < lo:
            overshoot = lo - val
        elif val > hi:
            overshoot = val - hi
        else:
            overshoot = 0.0
        if overshoot > max_overshoot:
            max_overshoot = overshoot
            worst_dim = dim

    if max_overshoot == 0.0:
        return CONTAINED, 0.0, None
    if max_overshoot < ADJACENT_THRESHOLD:
        return ADJACENT, max_overshoot, worst_dim
    return OUTSIDE, max_overshoot, worst_dim


def _scalar_distance(
    article_val: float | None,
    venue_val: float | None,
    venue_range: tuple[float, float] | None = None,
) -> tuple[str, float]:
    """Compare a scalar axis value against a venue center or range."""
    if article_val is None or venue_val is None:
        return UNKNOWN, 0.0
    if venue_range:
        lo, hi = venue_range
        if lo <= article_val <= hi:
            return CONTAINED, 0.0
        dist = min(abs(article_val - lo), abs(article_val - hi))
    else:
        dist = abs(article_val - venue_val)
    if dist < 0.1:
        return CONTAINED, dist
    if dist < ADJACENT_THRESHOLD:
        return ADJACENT, dist
    return OUTSIDE, dist


# ---------------------------------------------------------------------------
# Main fit computation
# ---------------------------------------------------------------------------

def compute_field_position_fit(
    article_fpm: dict[str, Any],
    venue_fpm: dict[str, Any],
) -> dict[str, Any]:
    """Compute multi-axis fit from two FieldPositionModel dicts.

    Returns a dict with per-axis results and an overall summary.
    No single score. No acceptance probability.
    """
    axes: list[dict[str, Any]] = []

    # --- Group 1: Discipline ---
    status, dist, edge = _vector_distance_to_envelope(
        article_fpm.get("discipline_vector", {}),
        venue_fpm.get("discipline_vector", {}),
        venue_fpm.get("discipline_envelope"),
    )
    axes.append({
        "axis": "discipline_fit",
        "status": status,
        "distance": round(dist, 3),
        "closest_edge": edge,
        "group": "disciplinary",
    })

    # --- Group 2: School/Tribe ---
    status, dist, edge = _vector_distance_to_envelope(
        article_fpm.get("school_affiliation_vector", {}),
        venue_fpm.get("school_affiliation_vector", {}),
        venue_fpm.get("school_envelope"),
    )
    axes.append({
        "axis": "school_fit",
        "status": status,
        "distance": round(dist, 3),
        "closest_edge": edge,
        "group": "camp_tribe",
    })

    # --- Group 3: Argument ---
    status, dist, edge = _vector_distance_to_envelope(
        article_fpm.get("argument_move_vector", {}),
        venue_fpm.get("argument_move_vector", {}),
        venue_fpm.get("argument_move_envelope"),
    )
    axes.append({
        "axis": "argument_move_fit",
        "status": status,
        "distance": round(dist, 3),
        "closest_edge": edge,
        "group": "argument",
    })

    # Evidence type (no envelope, use center distance)
    status, dist, _ = _vector_distance_to_envelope(
        article_fpm.get("evidence_type_profile", {}),
        venue_fpm.get("evidence_type_profile", {}),
        None,
    )
    axes.append({
        "axis": "evidence_type_fit",
        "status": status,
        "distance": round(dist, 3),
        "group": "argument",
    })

    # --- Group 4: Method ---
    a_method = article_fpm.get("method_stance", {})
    v_method = venue_fpm.get("method_stance", {})
    method_status = UNKNOWN
    if a_method and v_method:
        if v_method.get("requires_explicit_method") and not a_method.get("explicit_method"):
            method_status = OUTSIDE
        elif a_method.get("method_family"):
            rejected = v_method.get("rejected_method_families", [])
            accepted = v_method.get("accepted_method_families", [])
            mf = a_method["method_family"]
            if mf in rejected:
                method_status = OUTSIDE
            elif accepted and mf not in accepted:
                method_status = ADJACENT
            else:
                method_status = CONTAINED
        else:
            method_status = CONTAINED
    axes.append({
        "axis": "method_fit",
        "status": method_status,
        "distance": 0.0 if method_status == CONTAINED else (0.5 if method_status == ADJACENT else 1.0),
        "group": "method",
    })

    # Formalization level
    status, dist = _scalar_distance(
        article_fpm.get("formalization_level"),
        venue_fpm.get("formalization_level"),
    )
    axes.append({
        "axis": "formalization_fit",
        "status": status,
        "distance": round(dist, 3),
        "group": "method",
    })

    # --- Group 5: Audience ---
    a_aud = article_fpm.get("audience_level", {})
    v_aud = venue_fpm.get("audience_level", {})
    status, dist = _scalar_distance(
        a_aud.get("accessibility_index"),
        v_aud.get("accessibility_index"),
    )
    axes.append({
        "axis": "audience_fit",
        "status": status,
        "distance": round(dist, 3),
        "group": "audience",
    })

    # Language register: jargon density
    a_lang = article_fpm.get("language_register", {})
    v_lang = venue_fpm.get("language_register", {})
    status, dist = _scalar_distance(
        a_lang.get("jargon_density"),
        v_lang.get("jargon_density"),
    )
    axes.append({
        "axis": "jargon_fit",
        "status": status,
        "distance": round(dist, 3),
        "group": "audience",
    })

    # Language match
    a_lang_code = a_lang.get("language")
    v_lang_code = v_lang.get("language")
    if a_lang_code and v_lang_code:
        lang_status = CONTAINED if a_lang_code == v_lang_code else OUTSIDE
    else:
        lang_status = UNKNOWN
    axes.append({
        "axis": "language_match",
        "status": lang_status,
        "distance": 0.0 if lang_status == CONTAINED else 1.0,
        "group": "audience",
    })

    # Genre formality
    a_genre = article_fpm.get("genre_position", {})
    v_genre = venue_fpm.get("genre_position", {})
    status, dist = _scalar_distance(
        a_genre.get("genre_formality"),
        v_genre.get("genre_formality"),
    )
    axes.append({
        "axis": "genre_formality_fit",
        "status": status,
        "distance": round(dist, 3),
        "group": "audience",
    })

    # --- Group 6: Geographic ---
    a_geo = article_fpm.get("geographic_affinity", {})
    v_geo = venue_fpm.get("geographic_affinity", {})
    anglophone = v_geo.get("anglophone_hegemony_index")
    a_pub_lang = a_geo.get("language_of_publication")
    if anglophone is not None and anglophone > 0.8 and a_pub_lang and a_pub_lang != "en":
        geo_status = OUTSIDE
    elif anglophone is not None and anglophone > 0.5 and a_pub_lang and a_pub_lang != "en":
        geo_status = ADJACENT
    else:
        geo_status = CONTAINED if a_pub_lang else UNKNOWN
    axes.append({
        "axis": "geographic_fit",
        "status": geo_status,
        "distance": 0.0 if geo_status == CONTAINED else (0.3 if geo_status == ADJACENT else 0.8),
        "group": "geopolitical",
    })

    # --- Summary ---
    statuses = [a["status"] for a in axes if a["status"] != UNKNOWN]
    outside_count = sum(1 for s in statuses if s == OUTSIDE)
    adjacent_count = sum(1 for s in statuses if s == ADJACENT)
    contained_count = sum(1 for s in statuses if s == CONTAINED)
    unknown_count = sum(1 for a in axes if a["status"] == UNKNOWN)

    if unknown_count > len(axes) / 2:
        overall = "not_enough_data"
    elif outside_count == 0 and adjacent_count <= 2:
        overall = "strong_candidate"
    elif outside_count <= 1 and adjacent_count <= 3:
        overall = "possible"
    elif outside_count <= 2:
        overall = "possible_but_costly"
    else:
        overall = "poor_fit"

    return {
        "axes": axes,
        "overall_label": overall,
        "summary": {
            "contained": contained_count,
            "adjacent": adjacent_count,
            "outside": outside_count,
            "unknown": unknown_count,
            "total": len(axes),
        },
    }
