"""Proof that a research collection cannot self-certify scholarly publication readiness."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"benchmarks/_operator_notes/trm_g5_operator_20261022"
INDEX=ROOT/"data/venue_evidence_packs/g5_operator_official_20261022.jsonl"

def _read_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_g5_index_preserves_source_depth_and_inherited_uncertainty():
    rows=_read_jsonl(INDEX)
    assert len(rows)==92
    assert len({r["record_id"] for r in rows})==92
    live=[r for r in rows if r["venue"]!="DS"]
    legacy=[r for r in rows if r["venue"]=="DS"]
    assert len(live)==80 and len(legacy)==12
    assert all(r.get("fulltext_read") is False for r in rows)
    assert all(not r.get("doi_verified") for r in rows)
    assert all(r["read_depth"]=="OFFICIAL_INDEX_WEB_CRAWL_METADATA" for r in legacy)
    assert all(r["source_html_sha256"] is None for r in legacy)
    counts={v:sum(r["venue"]==v for r in rows) for v in ("LOGOS","VF","FJ","EPN","DS")}
    assert counts=={"LOGOS":28,"VF":22,"FJ":15,"EPN":15,"DS":12}

def test_g5_detail_pages_and_current_http_failures_not_hidden():
    rows=_read_jsonl(PACK/"article_pages_v3.jsonl")
    assert len(rows)==63
    assert len({r["record_id"] for r in rows})==63
    good=[r for r in rows if r["status"]=="OBSERVED"]
    bad=[r for r in rows if r["status"]=="FAILED"]
    assert len(good)==26 and len(bad)==37
    assert sum(bool(r.get("doi")) for r in rows)==15
    assert sum(bool(r.get("abstract")) for r in rows)==15
    assert all(r.get("fulltext_read") is False for r in rows)
    assert all(r.get("passage_support_verified") is False for r in rows)
    assert all("HTTP Error 500" in r["error"] for r in bad)

def test_g5_pdf_witnesses_page_index_not_scientific_verdict():
    witnesses=_read_jsonl(PACK/"primary_pdf_witnesses.jsonl")
    assert len(witnesses)==12 and len({r["record_id"] for r in witnesses})==12
    assert sum(r["page_count"] for r in witnesses)==171
    assert sum(r["venue"]=="FJ" for r in witnesses)==6
    assert sum(r["venue"]=="EPN" for r in witnesses)==6
    for w in witnesses:
        assert w["status"]=="RETRIEVED_AND_EXTRACTED"
        assert w["read_depth"]=="PDF_FULL_TEXT_EXTRACTED_PAGE_ANCHORED"
        assert w["scientific_claim_support_reviewed"] is False
        assert w["novelty_reviewed"] is False
        assert len(w["pdf_sha256"])==64 and len(w["derived_sha256"])==64
        assert len(w["page_witnesses"])==w["page_count"]
        assert [p["index"] for p in w["page_witnesses"]]==list(range(w["page_count"]))
        assert "NOT_AUTOMATICALLY_CONFIRMED" in w["page_index_anchor_status"]

def test_g5_indago_analogs_are_discoveries_not_scheduled_jobs():
    rows=_read_jsonl(PACK/"indago_analog_backlog.jsonl")
    assert len(rows)==8 and len({r["analog_id"] for r in rows})==8
    assert all(r["status"]=="INDAGO_BACKLOG_PROPOSAL_NOT_SCHEDULED" for r in rows)
    assert all(r["independent_novelty_verdict"]!="PASS" for r in rows)
    assert sum(r["source_depth"].startswith("PRIMARY_PDF") for r in rows)==3
    assert sum("TITLE_ONLY" in r["source_depth"] for r in rows)==5

def test_g5_repo_pack_manifest_references_unchanged_nonfulltext_files():
    manifest=json.loads((PACK/"repo_pack_manifest.json").read_text(encoding="utf-8"))
    assert manifest["private_fulltext_copied_to_git"] is False
    assert manifest["owner_manuscript_duplicated_to_git"] is False
    assert manifest["witness_pdf_bytes_private_only"] is True
    assert manifest["previous_untracked_v2_verified"]==_sha(INDEX)
    for e in manifest["tracked_entries"]:
        file=ROOT/e["repo_path"]
        assert file.is_file() and file.stat().st_size==e["bytes"]
        assert _sha(file)==e["sha256"]
