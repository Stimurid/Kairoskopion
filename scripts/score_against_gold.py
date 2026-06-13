"""Score a Kairoskopion e2e run against the gold §14 benchmark from
"эталон для кайрона разбор статьи 2 уже лучше.md".

Each check returns PASS / PARTIAL / FAIL plus evidence line(s). No single
score number. The report is a per-check map.

Usage:
    python scripts/score_against_gold.py --run private_inputs/runs/mavrinsky_002
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"


def _load(p: Path) -> dict[str, Any] | list[Any] | None:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _check(name: str, status: str, *evidence: str) -> dict[str, Any]:
    return {"check": name, "status": status, "evidence": list(evidence)}


# Gold-reference anchors per §14 of "эталон..."
GOLD_DISCIPLINES = {
    "continental_philosophy", "media_philosophy", "philosophy_of_technology",
    "interface_theory",
}
GOLD_INTERNAL_SCHOOLS = {"Deleuze_Guattari", "Agamben", "Foucault", "Deleuze", "Guattari"}
GOLD_FOIL = "Lacan"
GOLD_MISSING_PHILTECH = {"Simondon", "Stiegler", "Yuk Hui", "Hui"}
GOLD_MISSING_MEDIA = {"Manovich", "Galloway"}
GOLD_MISSING_STS = {"Latour", "ANT", "platform studies"}
GOLD_MISSING_HCI = {"affordances", "dark patterns", "persuasive technology"}
GOLD_AUTHORIAL_CONCEPTS = ("жадн", "щедр", "интерфейс", "избыт", "нехват")


def _has_token(haystack: str, token: str) -> bool:
    return token.lower() in haystack.lower()


# -----------------------------------------------------------------------
# §14 — ten benchmark checks
# -----------------------------------------------------------------------

def check_1_native_extraction(am: dict | None) -> dict[str, Any]:
    if not am:
        return _check("1 native_extraction", FAIL, "no article_model")
    title = am.get("title_current") or ""
    abstract = am.get("abstract_current") or ""
    lang = am.get("language") or ""
    refcnt = am.get("reference_count") or 0
    claims = am.get("core_claims") or []
    score = sum([bool(title), bool(abstract), lang == "ru", refcnt > 0, len(claims) > 0])
    status = PASS if score >= 4 else (PARTIAL if score >= 2 else FAIL)
    return _check(
        "1 native_extraction", status,
        f"title={bool(title)} abstract={bool(abstract)} lang={lang!r} refcount={refcnt} claims={len(claims)}",
    )


def check_2_academic_move(sp: dict | None, fpm: dict | None) -> dict[str, Any]:
    move_type = (sp or {}).get("argument_move_type") or ""
    desc = (sp or {}).get("argument_move_description") or ""
    vector = ((fpm or {}).get("argument_move_vector") or {})
    # Gold: concept_reconstruction + concept_introduction dominant; NOT review/empirical
    has_concept_recon = any(k in move_type.lower() or k in str(vector).lower()
                            for k in ("concept_reconstruction", "concept reconstruction"))
    has_concept_intro = any(k in move_type.lower() or k in desc.lower() or k in str(vector).lower()
                            for k in ("concept_introduction", "introduction of concept",
                                      "introduces concept", "concept introduction"))
    wrong_label = any(k in move_type.lower() or k in desc.lower()
                      for k in ("systematic_review", "empirical_conceptual_hybrid", "case_study"))
    if has_concept_recon and has_concept_intro and not wrong_label:
        return _check("2 academic_move", PASS,
                       f"move_type={move_type!r} desc_has_intro={has_concept_intro} vector_keys={list(vector)[:6]}")
    if has_concept_recon or has_concept_intro:
        return _check("2 academic_move", PARTIAL,
                       f"only partial: move_type={move_type!r} desc={desc[:120]!r}")
    return _check("2 academic_move", FAIL,
                  f"move_type={move_type!r} no concept_reconstruction/introduction signal")


def check_3_field_coordinates(fpm: dict | None) -> dict[str, Any]:
    if not fpm:
        return _check("3 field_coordinates", FAIL, "no article_field_position")
    dv = fpm.get("discipline_vector") or {}
    sv = fpm.get("school_affiliation_vector") or {}
    if not dv or not sv:
        return _check("3 field_coordinates", FAIL,
                       f"discipline_vector={dv} school_affiliation_vector={sv}")
    have_4_dims = len(dv) >= 4 and len(sv) >= 4
    floats_ok = all(isinstance(v, (int, float)) for v in dv.values()) \
        and all(isinstance(v, (int, float)) for v in sv.values())
    discipline_hit = any(
        any(_has_token(k, gold) for gold in GOLD_DISCIPLINES) for k in dv
    )
    school_hit = any(
        any(_has_token(k, gold) for gold in GOLD_INTERNAL_SCHOOLS) for k in sv
    )
    if have_4_dims and floats_ok and discipline_hit and school_hit:
        return _check("3 field_coordinates", PASS,
                       f"|dv|={len(dv)} |sv|={len(sv)} sample_dv={dict(list(dv.items())[:3])}")
    if dv and sv and (discipline_hit or school_hit):
        return _check("3 field_coordinates", PARTIAL,
                       f"|dv|={len(dv)} |sv|={len(sv)} hit_disc={discipline_hit} hit_school={school_hit}")
    return _check("3 field_coordinates", FAIL,
                  f"|dv|={len(dv)} |sv|={len(sv)}; gold disciplines/schools not found")


def check_4_tribe_recognition(sp: dict | None, fpm: dict | None) -> dict[str, Any]:
    sv = (fpm or {}).get("school_affiliation_vector") or {}
    schools = (sp or {}).get("schools_and_traditions") or []
    opps = (sp or {}).get("opponents_or_foils") or []
    sv_dump = str(sv).lower() + " " + str(schools).lower() + " " + str(opps).lower()

    internal_hits = [g for g in GOLD_INTERNAL_SCHOOLS if g.lower() in sv_dump]
    foil_hit = GOLD_FOIL.lower() in sv_dump
    foil_marked = any(
        kw in sv_dump
        for kw in ("foil", "contrastive", "opponent", "лакан"
                   if False else "lacan_as_foil")
    )
    foil_in_opponents = (
        any("lacan" in str(x).lower() for x in opps)
        or any("foil" in str(x).lower() for x in opps)
    )
    missing_bridge_hit = (
        any(m.lower() in sv_dump for m in GOLD_MISSING_PHILTECH)
        or "missing" in sv_dump
        or "absent_but_relevant" in sv_dump
        or "missing_expected" in sv_dump
    )

    have_internal = len(internal_hits) >= 2
    have_foil = foil_hit and (foil_marked or foil_in_opponents)
    have_missing = missing_bridge_hit

    score = sum([have_internal, have_foil, have_missing])
    if score == 3:
        return _check("4 tribe_recognition", PASS,
                       f"internal_hits={internal_hits} foil={GOLD_FOIL}(marked={have_foil}) missing_bridge={have_missing}")
    if score == 2:
        return _check("4 tribe_recognition", PARTIAL,
                       f"internal_hits={internal_hits} foil_hit={foil_hit} foil_marked={have_foil} missing_bridge={have_missing}")
    return _check("4 tribe_recognition", FAIL,
                  f"internal_hits={internal_hits} foil_hit={foil_hit} missing={have_missing}")


def check_5_citation_ecology(sp: dict | None, fpm: dict | None) -> dict[str, Any]:
    sig = (fpm or {}).get("citation_network_signature") or {}
    bridges = (sp or {}).get("citation_bridges_needed") or []
    blob = str(sig).lower() + " " + str(bridges).lower()

    have_must = bool(sig.get("must_cite")) or "must_cite" in blob
    have_absent = bool(sig.get("conspicuous_absence")) or "conspicuous_absence" in blob \
        or "absent" in blob
    have_pathway = "pathway" in blob or "philosophy_of_technology" in blob or "media" in blob

    score = sum([have_must, have_absent, have_pathway])
    if score == 3:
        return _check("5 citation_ecology", PASS,
                       f"must={bool(sig.get('must_cite'))} absent={have_absent} pathway-keyed={have_pathway}")
    if score >= 1:
        return _check("5 citation_ecology", PARTIAL,
                       f"must={bool(sig.get('must_cite'))} absent={have_absent} pathway-keyed={have_pathway} bridges={len(bridges)}")
    return _check("5 citation_ecology", FAIL,
                  f"signature_keys={list(sig.keys())} bridges={len(bridges)}")


def check_6_venue_logic(pathways: list | dict | None, pool: dict | None) -> dict[str, Any]:
    n_pathways = len(pathways) if isinstance(pathways, list) else len(((pathways or {}).get("pathways", [])))
    n_candidates = len(((pool or {}).get("candidates") or []))
    if n_pathways >= 2 and n_candidates >= 1:
        return _check("6 venue_logic", PASS,
                       f"pathways={n_pathways} candidates={n_candidates}")
    if n_pathways >= 1 or n_candidates >= 1:
        return _check("6 venue_logic", PARTIAL,
                       f"pathways={n_pathways} candidates={n_candidates}")
    return _check("6 venue_logic", FAIL,
                  f"pathways={n_pathways} candidates={n_candidates}")


def check_7_core_risk(am: dict | None, pcp: dict | None) -> dict[str, Any]:
    core = (am or {}).get("protected_core") or []
    pcp_core = (pcp or {}).get("protected_core") or []
    flat = []
    for x in list(core) + list(pcp_core):
        if isinstance(x, str):
            flat.append(x)
        elif isinstance(x, (list, tuple)):
            flat.extend(str(y) for y in x)
        elif isinstance(x, dict):
            flat.append(" ".join(str(v) for v in x.values()))
        else:
            flat.append(str(x))
    all_core = " ".join(flat).lower()
    have_desire = any(k in all_core for k in ("желан", "desire"))
    have_interface = "интерфейс" in all_core or "interface" in all_core
    have_apparatus = any(k in all_core for k in ("диспозитив", "dispositif", "apparatus", "захват", "capture"))
    score = sum([have_desire, have_interface, have_apparatus])
    if score >= 2 and len(core) >= 3:
        return _check("7 core_risk", PASS,
                       f"core_items={len(core)} desire={have_desire} interface={have_interface} apparatus={have_apparatus}")
    if score >= 1 or len(core) >= 1:
        return _check("7 core_risk", PARTIAL,
                       f"core_items={len(core)} desire={have_desire} interface={have_interface} apparatus={have_apparatus}")
    return _check("7 core_risk", FAIL,
                  f"core empty / no key concepts; len={len(core)}")


def check_8_evidence_discipline(sep: dict | None) -> dict[str, Any]:
    if not sep:
        return _check("8 evidence_discipline", FAIL, "no source_evidence_packet")
    sources = sep.get("input_sources") or []
    summary = sep.get("granularity_summary") or {}
    have_granularity = bool(summary)
    have_provenance = all("provenance" in s for s in sources) and len(sources) > 0
    have_access = all("access_status" in s for s in sources) and len(sources) > 0
    if have_granularity and have_provenance and have_access:
        return _check("8 evidence_discipline", PASS,
                       f"sources={len(sources)} summary={summary}")
    if have_granularity or (have_provenance and have_access):
        return _check("8 evidence_discipline", PARTIAL,
                       f"sources={len(sources)} summary={summary}")
    return _check("8 evidence_discipline", FAIL,
                  f"sources={len(sources)} summary={summary}")


def check_9_fit_vector(fit: dict | None, fpm_fit: dict | None) -> dict[str, Any]:
    axes = (fit or {}).get("axes") or []
    have_multi = len(axes) >= 6
    label = (fit or {}).get("overall_label") or ""
    no_single_score = "score" not in (fit or {}) or not isinstance((fit or {}).get("score"), (int, float))
    have_fpm_fit = bool(fpm_fit and fpm_fit.get("axes"))
    if have_multi and label and no_single_score and have_fpm_fit:
        return _check("9 fit_vector", PASS,
                       f"axes={len(axes)} label={label!r} fpm_fit_axes={len(fpm_fit.get('axes', []))}")
    if have_multi and label:
        return _check("9 fit_vector", PARTIAL,
                       f"axes={len(axes)} label={label!r} fpm_fit_available={have_fpm_fit}")
    if not fit:
        return _check("9 fit_vector", FAIL, "no fit_assessment (likely no venue selected)")
    return _check("9 fit_vector", FAIL,
                  f"axes={len(axes)} label={label!r}")


def check_10_adaptation(rw: dict | None, adapt: dict | None) -> dict[str, Any]:
    changes = (rw or {}).get("changes") or []
    have_changes = len(changes) >= 2
    have_summary = bool((rw or {}).get("summary"))
    citation_parts = (adapt or {}).get("citation_plan") if isinstance(adapt, dict) else None
    have_citation = bool(citation_parts)
    if have_changes and have_summary and have_citation:
        return _check("10 adaptation", PASS,
                       f"changes={len(changes)} summary={bool(have_summary)} citation_plan={have_citation}")
    if have_changes or have_citation:
        return _check("10 adaptation", PARTIAL,
                       f"changes={len(changes)} citation_plan={have_citation}")
    if not rw:
        return _check("10 adaptation", FAIL, "no rewrite_plan (depends on venue selection)")
    return _check("10 adaptation", FAIL, f"changes={len(changes)}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def score(run_dir: Path) -> dict[str, Any]:
    am = _load(run_dir / "01_article_model.json")
    sp = _load(run_dir / "02_semantic_profile.json")
    fpm = _load(run_dir / "03_article_field_position.json")
    sep = _load(run_dir / "04_source_evidence_packet.json")
    pcp = _load(run_dir / "05_protected_core_policy_derived.json")
    paths = _load(run_dir / "07_pathways.json")
    pool = _load(run_dir / "08_venue_pool.json")
    fit = _load(run_dir / "11_fit_assessment.json")
    fpm_fit = _load(run_dir / "12_field_position_fit.json")
    rw = _load(run_dir / "14_rewrite_plan.json")
    adapt = _load(run_dir / "15_adaptation_plan.json")

    checks = [
        check_1_native_extraction(am),
        check_2_academic_move(sp, fpm),
        check_3_field_coordinates(fpm),
        check_4_tribe_recognition(sp, fpm),
        check_5_citation_ecology(sp, fpm),
        check_6_venue_logic(paths, pool),
        check_7_core_risk(am, pcp),
        check_8_evidence_discipline(sep),
        check_9_fit_vector(fit, fpm_fit),
        check_10_adaptation(rw, adapt),
    ]
    summary = {PASS: 0, PARTIAL: 0, FAIL: 0}
    for c in checks:
        summary[c["status"]] += 1
    return {
        "run_dir": str(run_dir),
        "summary": summary,
        "checks": checks,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    rep = score(args.run)
    print("=" * 70)
    print(f"SCORING {args.run.name} against gold §14 benchmark")
    print("=" * 70)
    print(f"  PASS={rep['summary']['PASS']}  PARTIAL={rep['summary']['PARTIAL']}  FAIL={rep['summary']['FAIL']}\n")
    for c in rep["checks"]:
        flag = {"PASS": "+", "PARTIAL": "~", "FAIL": "-"}[c["status"]]
        print(f"  {flag} [{c['status']:7}] {c['check']}")
        for e in c["evidence"]:
            print(f"             {e}")
    if args.output:
        args.output.write_text(
            json.dumps(rep, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
