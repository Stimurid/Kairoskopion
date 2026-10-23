"""W12_capture_manifest_builder: bridges W3 route candidates to the W12
route stage's capture_manifest input through the EXISTING
acquire_explicit_fulltext adapter, instead of hand-curated JSON.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_w12_route_stage import stage_w12_research_route
from kairoskopion.services.w12_capture_manifest_builder import build_capture_manifest


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _fixture_pages() -> dict[str, bytes]:
    pages = {
        "SCOPE": (
            "<html><body><h1>Aims and scope</h1><p>"
            "We publish rigorous original business research, conceptual "
            "and empirical work across different industrial settings."
            "</p></body></html>"
        ).encode("utf-8"),
        "GUIDELINES": (
            "<html><body><h1>Submission policy</h1><p>"
            "Regular manuscripts are submitted via a publisher portal"
            " and must not be simultaneously under consideration elsewhere."
            "</p></body></html>"
        ).encode("utf-8"),
        "OPPONENT": (
            "<html><body><h1>A published study</h1><p>"
            "The published study uses surveys of individual managers"
            " to establish configurations of opportunity exploitation."
            "</p><p>doi:10.1007/synth2</p></body></html>"
        ).encode("utf-8"),
    }
    # Existing production HTML validator deliberately refuses tiny "full-text"
    # carrier stubs (<5000 bytes). Keep that check intact in integration tests.
    return {
        key: blob.replace(
            b"</body>",
            (b"<div>" + (b" Supplementary publisher page material." * 190)
             + b"</div></body>"),
        )
        for key, blob in pages.items()
    }


def _build_route_packet(tmp_path: Path, capture_manifest_path: Path, caps: dict[str, bytes]):
    """Stage the minimal real W3 graph state a W12 route packet must bind to,
    then point its capture_manifest at the builder's output."""
    stage = tmp_path / "factory"
    graph = OpportunityGraphStore(stage)
    src = tmp_path / "c04.txt"
    text = (
        "Title of synthetic industrial talk\n"
        "Existing industrial relationships are not the same as an emerging"
        " division of labor; new shared instruments and repeatable functions must form.\n"
    )
    src.write_bytes(text.encode("utf-8"))
    source_id = "drive:SYNTH-C04-B"
    ledger = stage / "talk_corpora" / "CASE-SYNTH-B" / "case_ledger.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({
        "case_id": "CASE-SYNTH-B",
        "source_snapshots": [{
            "source_id": source_id, "version": "v0.4",
            "key": "C04", "family": "C",
            "content_sha256": _sha(src.read_bytes()),
            "author_state": "NOT_VERIFIED",
        }],
    }), encoding="utf-8")
    graph.put("Evidence", {
        "id": "synthetic-source-evidence-b",
        "revision": "r1",
        "source_ref": source_id,
        "source_kind": "SPEECH_SCRIPT",
        "read_depth": "SECTIONS",
        "passage_anchors": [],
    })
    graph.append_event({
        "event_id": "CASE-SYNTH-B:W3:route:C-TEST-B",
        "kind": "SCHOLARLY_ROUTE_CHALLENGE",
        "route_candidate_id": "C-TEST-B",
        "subject_id": "HEAD-03",
        "journal_id": "journal-RMS-SYNTH-B",
        "source_ref": "doi:10.1007/synth2",
        "opponent_resolved": True,
        "w12_equivalent": False,
    })
    graph.append_event({
        "event_id": "CASE-SYNTH-B:W3:HEAD-03:DISCOVERY-RETURN",
        "kind": "SOURCE_CONTRADICTION",
        "subject_id": "HEAD-03",
        "source_ref": source_id,
        "original_source_binding": {
            "source_id": source_id,
            "version": "v0.4",
            "content_sha256": _sha(src.read_bytes()),
            "binding_verification": "VERIFIED_BYTES",
        },
    })

    pages = {k: v.decode("utf-8") for k, v in caps.items()}
    lengthy_en = " ".join(["A distinct industrial research question compares lasting collective "
        "standards with temporary individual opportunity exploitation."] * 9)
    lengthy_ru = " ".join(["Исследовательская постановка различает воспроизводимое совместное средство "
        "и временную индивидуальную возможность действия."] * 9)
    analysis = {name: "A negative case could refute this narrow claim, and historical "
        "multiple case evidence must be collected before any manuscript or author approval."
        for name in ("strongest_objection", "source_distinction", "empirical_falsifier",
                     "methodological_plan", "admissible_source_change", "negative_evidence")}
    packet = {
        "schema": "TRM073_W12_SOURCE_VENUE_ROUTE_INPUT_V1",
        "case_id": "CASE-SYNTH-B", "wave_id": "W4-TEST-B",
        "route_candidate_id": "C-TEST-B", "head_id": "HEAD-03",
        "claim_version_id": "C04-v0.4-CLAIM-SYNTH-B",
        "journal_name": "Review of Managerial Science",
        "journal_id": "journal-RMS-SYNTH-B",
        "route_type": "REGULAR_ROLLING", "venue_submission_type": "REGULAR_MANUSCRIPT",
        "current_cfp": False, "deadline": None, "author_gate": "HOLD",
        "author_decision": "HOLD", "coauthor_consent": "UNVERIFIED",
        "rights_gate": "OWNER_REVIEW_PENDING",
        "scientific_status": "OPPONENT_GROUNDED_AUTHOR_REVIEW_PENDING",
        "original_source": {
            "source_id": source_id, "source_version": "v0.4",
            "path": str(src), "sha256": _sha(src.read_bytes()),
            "anchor_line": 2, "anchor_quote": text.splitlines()[1],
        },
        "capture_manifest": str(capture_manifest_path),
        "official_host": "link.springer.com",
        "official_evidence": {
            kind: {
                "capture_key": key,
                "url": "https://link.springer.com/" + key.lower(),
                "anchor_quote": (pages[key].split("<p>")[1].split("</p>")[0] if "<p>" in pages[key] else "Publisher-policy evidence could not be acquired from the required official source"),
            }
            for kind, key in (("scope", "SCOPE"), ("submission_policy", "GUIDELINES"),
                              ("published_opponent", "OPPONENT"))
        },
        "opponent_doi": "10.1007/synth2",
        "opponent_url": "https://link.springer.com/opponent",
        "publisher_observed_date": "2026-10-20",
        "target_thesis": {"en": lengthy_en, "ru": lengthy_ru},
        "opponent_analysis": analysis,
        "article_seed_created": False, "world_mutation": False, "external_send": "DISABLED",
    }
    file = tmp_path / "packet.json"
    file.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    return packet, file, stage


def test_build_capture_manifest_feeds_w12_route_stage_end_to_end(tmp_path):
    caps = _fixture_pages()
    targets = {k: f"https://link.springer.com/{k.lower()}" for k in caps}
    manifest_path = tmp_path / "provider" / "captures.json"
    report = build_capture_manifest(
        targets,
        output_dir=tmp_path / "provider" / "artifacts",
        manifest_path=manifest_path,
        fixture_bytes=caps,
        fixture_content_types={k: "text/html; charset=utf-8" for k in caps},
    )
    assert report["all_validated"] is True
    for key in caps:
        assert report["captures"][key]["status"] == "validated"

    _, packet_path, stage = _build_route_packet(tmp_path, manifest_path, caps)
    result = stage_w12_research_route(packet_path, stage)
    assert result["counts"]["W12_EQUIVALENT_HELD"] == 1
    assert result["readback"]["verified"] is True


def test_blocked_capture_is_not_silently_promoted_to_validated(tmp_path):
    caps = _fixture_pages()
    # One page is a bot-interstitial: real adapter marks it unvalidated.
    caps["GUIDELINES"] = (
        b"<!doctype html><html><head><title>Just a moment...</title></head>"
        b"<body>Please verify you are human." + (b"x" * 6000) + b"</body></html>"
    )
    targets = {k: f"https://link.springer.com/{k.lower()}" for k in caps}
    manifest_path = tmp_path / "provider" / "captures.json"
    report = build_capture_manifest(
        targets,
        output_dir=tmp_path / "provider" / "artifacts",
        manifest_path=manifest_path,
        fixture_bytes=caps,
        fixture_content_types={k: "text/html; charset=utf-8" for k in caps},
    )
    assert report["all_validated"] is False
    assert report["captures"]["GUIDELINES"]["status"] == "acquired_unvalidated"
    assert report["captures"]["GUIDELINES"]["validation"]["reason"] == "html_interstitial_or_challenge"

    _, packet_path, stage = _build_route_packet(tmp_path, manifest_path, caps)
    with pytest.raises(ValueError, match="not acquired and validated"):
        stage_w12_research_route(packet_path, stage)


def test_unsupported_scheme_target_is_blocked_with_exact_url_no_network(tmp_path):
    manifest_path = tmp_path / "captures.json"
    report = build_capture_manifest(
        {"SCOPE": "ftp://link.springer.com/scope"},
        output_dir=tmp_path / "artifacts",
        manifest_path=manifest_path,
    )
    assert report["all_validated"] is False
    entry = report["captures"]["SCOPE"]
    assert entry["status"] == "blocked"
    assert entry["error_code"] == "unsupported_scheme"
    assert entry["url"] == "ftp://link.springer.com/scope"


def test_blank_or_duplicate_capture_key_rejected(tmp_path):
    with pytest.raises(ValueError, match="blank"):
        build_capture_manifest(
            {" ": "https://link.springer.com/scope"},
            output_dir=tmp_path / "artifacts",
            manifest_path=tmp_path / "captures.json",
        )


def test_no_targets_rejected(tmp_path):
    with pytest.raises(ValueError, match="no capture targets"):
        build_capture_manifest(
            {},
            output_dir=tmp_path / "artifacts",
            manifest_path=tmp_path / "captures.json",
        )



def test_second_capture_replays_frozen_publisher_bytes_without_http(tmp_path):
    pages = _fixture_pages()
    targets = {k: "https://link.springer.com/" + k.lower() for k in pages}
    manifest = tmp_path / "captures.json"
    opts = {"output_dir": tmp_path / "artifacts", "manifest_path": manifest}
    first = build_capture_manifest(
        targets, **opts, fixture_bytes=pages,
        fixture_content_types={k: "text/html" for k in pages},
    )
    assert first["newly_validated"] == 3
    assert first["verified_reused"] == 0
    second = build_capture_manifest(
        targets, **opts,
        fixture_bytes={k: b"fake new publisher page" for k in pages},
    )
    assert second["verified_reused"] == 3
    assert second["newly_validated"] == 0
    assert first["capture_manifest_sha256"] == second["capture_manifest_sha256"]


def test_tampered_frozen_html_blocks_before_reusing_manifest(tmp_path):
    pages = _fixture_pages()
    targets = {k: "https://link.springer.com/" + k.lower() for k in pages}
    manifest = tmp_path / "captures.json"
    opts = {"output_dir": tmp_path / "artifacts", "manifest_path": manifest}
    build_capture_manifest(
        targets, **opts, fixture_bytes=pages,
        fixture_content_types={k: "text/html" for k in pages},
    )
    stored = json.loads(manifest.read_text(encoding="utf-8"))
    target_path = Path(stored["GUIDELINES"]["path"])
    target_path.write_bytes(target_path.read_bytes() + b"<p>changed after capture</p>")
    with pytest.raises(ValueError, match="byte SHA mismatch"):
        build_capture_manifest(targets, **opts)


def test_partial_capture_retries_failed_page_preserving_successful_sha(tmp_path):
    pages = _fixture_pages()
    bad_pages = dict(pages)
    bad_pages["GUIDELINES"] = (
        b"<html><title>Just a moment...</title><body>"
        + b"Checking your browser" + b"x" * 6000 + b"</body></html>"
    )
    targets = {k: "https://link.springer.com/" + k.lower() for k in pages}
    manifest = tmp_path / "captures.json"
    opts = {"output_dir": tmp_path / "artifacts", "manifest_path": manifest}
    first = build_capture_manifest(
        targets, **opts, fixture_bytes=bad_pages,
        fixture_content_types={k: "text/html" for k in pages},
    )
    assert first["all_validated"] is False
    first_caps = json.loads(manifest.read_text(encoding="utf-8"))
    second = build_capture_manifest(
        targets, **opts, fixture_bytes=pages,
        fixture_content_types={k: "text/html" for k in pages},
    )
    assert second["all_validated"]
    assert second["verified_reused"] == 2
    assert second["newly_validated"] == 1
    after = json.loads(manifest.read_text(encoding="utf-8"))
    for key in ("SCOPE", "OPPONENT"):
        assert first_caps[key]["sha256"] == after[key]["sha256"]


def test_existing_capture_manifest_does_not_accept_changed_url(tmp_path):
    pages = _fixture_pages()
    targets = {k: "https://link.springer.com/" + k.lower() for k in pages}
    manifest = tmp_path / "captures.json"
    opts = {"output_dir": tmp_path / "artifacts", "manifest_path": manifest}
    build_capture_manifest(
        targets, **opts, fixture_bytes=pages,
        fixture_content_types={k: "text/html" for k in pages},
    )
    altered = dict(targets)
    altered["SCOPE"] = "https://link.springer.com/different"
    with pytest.raises(ValueError, match="pinned publisher URL changed"):
        build_capture_manifest(altered, **opts)


def test_cli_duplicate_key_is_refused_before_network(tmp_path):
    import os
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_w12_capture_manifest.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([
        sys.executable, str(script),
        "--target", "SCOPE=https://link.springer.com/scope",
        "--target", "SCOPE=https://link.springer.com/different",
        "--output-dir", str(tmp_path / "artifacts"),
        "--manifest-out", str(tmp_path / "manifest.json"),
    ], env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "duplicate --target" in result.stderr
    assert not (tmp_path / "manifest.json").exists()
