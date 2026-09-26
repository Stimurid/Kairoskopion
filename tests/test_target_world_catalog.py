from kairoskopion.kairon_provider.target_world_catalog import TargetWorldCatalog

def snap(sid="targetworld:test:1", target="journal_a", n=2):
    return {
        "snapshot_id": sid,
        "target_id": target,
        "created_at": "2026-09-26T00:00:00+00:00",
        "provider_commit": "abc",
        "corpus_manifest": {
            "artifacts": [{"title": f"A{i}"} for i in range(n)]
        },
        "target_models": {
            "genre_patterns": [{"genre": "conceptual_article"}],
            "article_models": [{"id": "m1"}],
            "confidence": "medium",
        },
        "editor_profiles": [{"name": "Editor"}],
        "evidence_refs": ["e1", "e2"],
    }

def test_ingest_freezes_digest_revision(tmp_path):
    c = TargetWorldCatalog(tmp_path)
    e1 = c.ingest(snap(), origin="KAIROSKOPION", status="PROD_ACCEPTED")
    s2 = snap(n=3)
    e2 = c.ingest(s2, origin="KAIROSKOPION", status="PROD_ACCEPTED")
    assert e1["package_id"] != e2["package_id"]
    assert len(c.list_entries("journal_a")) == 2
def test_best_for_target_prefers_status_then_recency(tmp_path):
    c = TargetWorldCatalog(tmp_path)
    c.ingest(snap("targetworld:test:dev"), origin="DEV", status="QUALIFIED_DEV")
    c.ingest(snap("targetworld:test:prod"), origin="PROD", status="PROD_ACCEPTED")
    best = c.best_for_target("journal_a")
    assert best["snapshot_id"] == "targetworld:test:prod"
    assert best["status"] == "PROD_ACCEPTED"

def test_exchange_package_roundtrip(tmp_path):
    c1 = TargetWorldCatalog(tmp_path / "one")
    e = c1.ingest(snap(), origin="KAIROSKOPION", status="PROD_ACCEPTED")
    pkg = c1.get_package(e["package_id"])
    assert pkg is not None
    c2 = TargetWorldCatalog(tmp_path / "two")
    e2 = c2.import_package(pkg)
    assert e2["content_digest"] == e["content_digest"]
    assert c2.get_package(e2["package_id"])["snapshot"]["target_id"] == "journal_a"
def test_tampered_exchange_package_is_rejected(tmp_path):
    c1 = TargetWorldCatalog(tmp_path / "one")
    e = c1.ingest(snap(), origin="KAIROSKOPION", status="PROD_ACCEPTED")
    pkg = c1.get_package(e["package_id"])
    pkg["snapshot"]["target_id"] = "tampered"
    c2 = TargetWorldCatalog(tmp_path / "two")
    try:
        c2.import_package(pkg)
    except ValueError as exc:
        assert "content_digest mismatch" in str(exc)
    else:
        raise AssertionError("tampered package must fail")

def test_summary_exposes_models_needed_by_kairon(tmp_path):
    c = TargetWorldCatalog(tmp_path)
    e = c.ingest(snap(), origin="KAIROSKOPION", status="PROD_ACCEPTED")
    assert e["corpus_size"] == 2
    assert e["article_model_count"] == 1
    assert e["editor_profile_count"] == 1
    assert "genre_patterns" in e["model_capabilities"]
    assert "article_models" in e["model_capabilities"]

def test_same_revision_merges_origins_without_status_downgrade(tmp_path):
    c = TargetWorldCatalog(tmp_path)
    e1 = c.ingest(snap(), origin="PROD", status="PROD_ACCEPTED", source_ref="prod")
    e2 = c.ingest(snap(), origin="PILOT", status="QUALIFIED_DEV", source_ref="pilot")
    assert e2["package_id"] == e1["package_id"]
    assert e2["status"] == "PROD_ACCEPTED"
    assert set(e2["origins"]) == {"PROD", "PILOT"}
    assert set(e2["source_refs"]) == {"prod", "pilot"}