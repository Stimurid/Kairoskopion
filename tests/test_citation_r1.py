import json
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from kairoskopion.services.citation_intake_z0 import persist_audit
from kairoskopion.services.citation_r1 import consume, prepare


def _setup(tmp_path):
    source = tmp_path / "draft.md"
    source.write_text("A claim (Luckin 2016). Another (Descartes 1701).", encoding="utf-8")
    _, audit = persist_audit(source, tmp_path / "private")
    queue = audit.with_name("citation_work_orders.jsonl")
    requests = tmp_path / "requests"
    assert prepare(audit, queue, requests)["orders"] == 2
    return source, audit, queue, requests


def _run(*args):
    return subprocess.run([sys.executable, "-m", "kairoskopion.services.citation_r1", *map(str, args)],
                          capture_output=True, text=True, check=True)


def test_two_process_blocked_return_replay_and_original_preserved(tmp_path):
    source, audit, queue, requests = _setup(tmp_path)
    before = source.read_bytes()
    states = tmp_path / "states"
    for request in requests.glob("*.request.json"):
        blocked = tmp_path / "blocked"
        _run("blocked-canary", "--audit", audit, "--queue", queue,
             "--request", request, "--out", blocked)
        ret = blocked / (json.loads(request.read_text())["work_order_id"] + ".blocked.json")
        _run("consume", "--audit", audit, "--queue", queue,
             "--request", request, "--return-file", ret, "--out", states)
        state = consume(audit, queue, request, ret, states)
        assert state["outcome"] == "BLOCKED"
        assert state["verification"]["V1"] == "NOT_CHECKED"
        assert state["verification"]["V2"] == "NOT_CHECKED"
        assert state["citation_gate"] == "NOT_PUBLICATION_READY"
        assert state["proposed_patch"] is None
    assert len(list(states.glob("*.state.json"))) == 2
    assert source.read_bytes() == before


def test_reject_spoof_stale_anchor_and_permission(tmp_path):
    _, audit, queue, requests = _setup(tmp_path)
    request = next(requests.glob("*.json"))
    original = json.loads(request.read_text())
    out = tmp_path / "states"
    ret = {
        **original, "schema": "trm-cite-r1-return-v1", "outcome": "OBSERVED",
        "provider": "reader", "acquisition_authorized": False,
        "source_kind": "PRIMARY", "read_depth": "ANCHORED_PASSAGE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "access": "PUBLIC",
        "license": "PUBLIC_READ", "work_id": "w", "edition_id": "e",
        "witness_id": "x", "passage_id": "p", "byte_sha256": "0" * 64,
        "locator": "p. 1",
    }
    path = tmp_path / "ret.json"
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="authorized provider"):
        consume(audit, queue, request, path, out)
    ret["acquisition_authorized"] = True
    ret["correlation_id"] = "spoof"
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="correlation mismatch"):
        consume(audit, queue, request, path, out)
    altered = [json.loads(x) for x in queue.read_text().splitlines()]
    altered[0]["manuscript_anchor"]["locator"] = "wrong"
    bad_queue = tmp_path / "bad_queue.jsonl"
    bad_queue.write_text("".join(json.dumps(x) + "\n" for x in altered))
    with pytest.raises(ValueError, match="Stale or altered"):
        prepare(audit, bad_queue, tmp_path / "wrong")
    ret["correlation_id"] = original["correlation_id"]
    path.write_text(json.dumps(ret))
    changed_queue = tmp_path / "changed_queue.jsonl"
    changed_queue.write_bytes(queue.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="stale or spoofed"):
        consume(audit, changed_queue, request, path, out)


def test_observation_is_proposal_not_scientific_pass(tmp_path):
    _, audit, queue, requests = _setup(tmp_path)
    request = next(requests.glob("*.json"))
    req = json.loads(request.read_text())
    ret = {
        **req, "schema": "trm-cite-r1-return-v1", "outcome": "OBSERVED",
        "provider": "authorized-reader", "acquisition_authorized": True,
        "source_kind": "PUBLISHER_PAGE", "read_depth": "PUBLISHER_ABSTRACT",
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "access": "PUBLIC",
        "license": "PUBLIC_READ", "work_id": "w", "edition_id": "e",
        "witness_id": "x", "passage_id": None, "byte_sha256": None,
        "locator": "abstract", "source_author_claim": "sample claim",
        "article_author_claim": "stronger sample claim",
        "citation_mode": "PARAPHRASE",
    }
    path = tmp_path / "ret.json"
    path.write_text(json.dumps(ret))
    state = consume(audit, queue, request, path, tmp_path / "states")
    assert state["verification"]["V1"] == "IDENTITY_ONLY_PROPOSED"
    assert state["verification"]["V2"] == "N/A_PARAPHRASE"
    assert state["verification"]["V4"] == "NOT_CHECKED"
    assert state["source_author_claim"] != state["article_author_claim"]
    assert state["citation_gate"] == "NOT_PUBLICATION_READY"
    ret["retrieved_at"] = "2020-01-01T00:00:00Z"
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="Invalid retrieval time"):
        consume(audit, queue, request, path, tmp_path / "stale")
    ret["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    ret["read_depth"] = "ANCHORED_PASSAGE"
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="Passage lacks identity"):
        consume(audit, queue, request, path, tmp_path / "ambiguous")
