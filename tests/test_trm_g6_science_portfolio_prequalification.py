"""G6 scientific novelty is source-bound and never implied by a venue table."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
MD=ROOT/"data/article_models/trm_g6_three_research_20261023.json"
PAIRS=ROOT/"data/venue_evidence_packs/trm_g6_15_pair_prequalification_20261023.jsonl"
MANIFEST=ROOT/"data/article_models/trm_g6_science_source_manifest_20261023.json"


def _models():
    return json.loads(MD.read_text(encoding="utf-8"))["models"]


def _pairs():
    return [json.loads(x) for x in PAIRS.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_three_distinct_scientific_cores_and_six_disconfirmations():
    models=_models()
    assert len(models)==3
    assert {x["id"] for x in models}=={"P1","P2","P3"}
    assert len({x["question"] for x in models})==3
    assert all(x["novelty_verdict"]=="NOT_CERTIFIED" for x in models)
    assert all(x["manuscript_exists"] is False for x in models)
    assert all(x["author_acceptance"]=="NOT_REQUESTED" for x in models)
    assert all(len(x["referee_objections"])==6 for x in models)
    assert all(all(x["required_answer_or_falsifier"] for x in m["referee_objections"]) for m in models)


def test_p1_h0_is_default_p2_trace_debt_and_p3_fulltext_debt():
    m={x["id"]:x for x in _models()}
    assert m["P1"]["status"]=="CONDITIONAL_H0_PREFERRED"
    assert "2017" in m["P1"]["source_read_status"]
    assert m["P2"]["status"]=="REQUIRES_EMPIRICAL_TRACES"
    assert "NOT RUN" in m["P2"]["source_read_status"]
    assert "BLOCKED_FULLTEXT" in m["P3"]["status"]
    assert "NOT READ" in m["P3"]["source_read_status"]


def test_exact_fifteen_unique_true_provisional_pairing():
    rows=_pairs()
    assert len(rows)==15 and len({r["record_id"] for r in rows})==15
    assert {r["record_id"] for r in rows}=={
        p+"__"+v for p in ("P1","P2","P3") for v in ("LOGOS","VF","FJ","EPN","DS")}
    assert all(r["qualified_pair"] is False for r in rows)
    assert all(r["author_approved"] is False for r in rows)
    assert all(r["original_manuscript_exists"] is False for r in rows)
    assert all(r["scholarly_quality"]=="UNADJUDICATED" for r in rows)
    assert all(r["source_work_claim_v1_v5"]=="NOT_CERTIFIED" for r in rows)


def test_venue_field_proofs_do_not_equate_toc_with_fullread():
    r=_pairs()
    assert {x["venue_read_depth"] for x in r if x["target_id"]=="DS"}=={
        "2024_INDEX_WEB_CACHED_UNREVERIFIED_HTTP500"}
    assert all("PDF_EXTRACTED" not in x["venue_read_depth"]
               for x in r if x["target_id"] in {"LOGOS","VF","DS"})
    assert all("PORTAL_CLOSED" in x["venue_submission_route"]
               for x in r if x["target_id"]=="FJ")
    assert all(x["source_article_count_context"]>0 for x in r)


def test_manifest_sha_binding_and_no_private_pdf_in_git():
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["models"]==3 and m["scientific_provisional_target_pairs"]==15
    assert m["qualified_pairs"]==0 and m["author_approved"]==0
    assert m["source_fulltexts_copied_to_git"] is False
    for f in m["outputs"]:
        p=ROOT/f["path"]
        assert p.is_file()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==f["sha256"]
        assert p.stat().st_size==f["bytes"]


def test_original_twenty_seeds_and_previous_paper_lines_preserved():
    models=_models()
    family={v for m in models for v in m["lineage"]}
    assert {"F08","S14","S20"}.issubset(family)
    rows=_pairs()
    assert not any(x.get("submitted") is True or x.get("publication_ready") is True for x in rows)
